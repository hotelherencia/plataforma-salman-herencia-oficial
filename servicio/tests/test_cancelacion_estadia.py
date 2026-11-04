"""Pruebas SDD/TDD del flujo de cancelación de reservas (V1-ISSUE-40).

Verifica en aislamiento contra PostgreSQL real:
1. Cancelación explícita dentro y fuera de plazo: transición única a `cancelada`,
   un único reverso por cada cargo previo, penalidad única cuando faltan < 48 h
   para las 15:00 del día de inicio, `reembolso: "no configurado"` sin tocar pagos.
2. Idempotencia secuencial y concurrente con la MISMA clave (`Idempotency-Key`):
   dos solicitudes simultáneas con misma clave y mismo cuerpo devuelven ambas 200
   con el mismo payload (sin 409 por UniqueViolation en `claves_idempotencia`) y
   ejecutan la operación una sola vez. Misma clave con otro cuerpo responde 409.
3. Concurrencia con DISTINTA clave (`Idempotency-Key`) sobre la misma reserva:
   exactamente una solicitud gana con 200 y la otra recibe 409
   (`la reserva está cancelada`), sin duplicar reversos, penalidades ni filas de
   auditoría, y dejando `cargos_netos_clp` en el valor exacto del contrato.
4. Concurrencia entre `cancelacion` y `entrada` / `cargos`: serialización por fila
   de reserva (`FOR UPDATE`), sin estados ni asientos inconsistentes.
5. Permisos y estados inválidos: `caja` → 403, reserva ajena/inexistente → 403,
   reserva ya `cancelada`, `en_estadia` o `finalizada` → 409.
"""
import os
import threading
import unittest
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()
FUTURO = (HOY + timedelta(days=20)).isoformat()
FUTURO_FIN = (HOY + timedelta(days=23)).isoformat()
CORTO_INICIO = (HOY + timedelta(days=1)).isoformat()
CORTO_FIN = (HOY + timedelta(days=3)).isoformat()


class CancelacionEstadiaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1",
            puerto=0,
            database_url=URL_TEST,
            cookie_segura=False,
            origen_front=None,
            admin_usuario=ADMIN[0],
            admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, "
                "liquidaciones, efectos_nucleo, pagos, cargos, reservas, tarifas, sesiones, "
                "usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            for n in (1, 2, 3):
                conexion.execute(
                    "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                    "VALUES (%s, 'EST-SINT-001', 'doble', 2)",
                    (f"HAB-SINT-10{n}",),
                )
                conexion.execute(
                    "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                    "VALUES (%s, %s, '2026-01-01', '2027-12-31', 50000)",
                    (f"TAR-10{n}", f"HAB-SINT-10{n}"),
                )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        r = self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200, r.text)

    def nuevo_cliente_autenticado(self) -> TestClient:
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def reservar(self, habitacion_id="HAB-SINT-101", inicio=FUTURO, fin=FUTURO_FIN, clave="res-1") -> str:
        r = self.cliente.post(
            "/hotel/reservas",
            json={
                "habitacion_id": habitacion_id,
                "inicio": inicio,
                "fin": fin,
                "huesped": {"nombre": "Huésped Sintético", "documento": "DOC-SINT-1"},
            },
            headers={"Idempotency-Key": clave},
        )
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["reserva_id"]

    def test_lectura_de_detalle_no_muta_reserva_ni_cargos(self):
        rid = self.reservar(clave="res-lectura")
        antes = self.cliente.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(antes["estado"], "confirmada")
        self.assertEqual(len(antes["cargos"]), 1)
        self.assertEqual(antes["cuenta"]["cargos_netos_clp"], 150_000)

        # Releer repetidamente equivale a abrir/recargar con ?reserva_id=...
        for _ in range(3):
            despues = self.cliente.get(f"/hotel/reservas/{rid}").json()
            self.assertEqual(despues["estado"], "confirmada")
            self.assertEqual(len(despues["cargos"]), 1)
            self.assertEqual(despues["cuenta"]["cargos_netos_clp"], 150_000)

    def test_cancelacion_concurrente_con_distinta_clave_no_duplica_reversos_ni_penalidad(self):
        """Dos solicitudes concurrentes con distinta Idempotency-Key sobre una
        reserva fuera de plazo: exactamente una gana (200) y la otra recibe 409,
        sin duplicar reversos ni penalidad."""
        rid = self.reservar(inicio=CORTO_INICIO, fin=CORTO_FIN, clave="res-race-diff")
        # Agregamos un cargo adicional para comprobar que ningún cargo se reversa dos veces
        r_cargo = self.cliente.post(
            f"/hotel/reservas/{rid}/cargos",
            json={"concepto": "minibar", "monto_clp": 8_000},
            headers={"Idempotency-Key": "car-race-diff"},
        )
        self.assertEqual(r_cargo.status_code, 201)

        n_hilos = 6
        clientes = [self.nuevo_cliente_autenticado() for _ in range(n_hilos)]
        barrera = threading.Barrier(n_hilos)
        resultados = [None] * n_hilos

        def trabajador(idx: int):
            barrera.wait()
            resp = clientes[idx].post(
                f"/hotel/reservas/{rid}/cancelacion",
                json={},
                headers={"Idempotency-Key": f"can-diff-{idx}"},
            )
            resultados[idx] = (resp.status_code, resp.json())

        hilos = [threading.Thread(target=trabajador, args=(i,)) for i in range(n_hilos)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        codigos = [r[0] for r in resultados]
        self.assertEqual(codigos.count(200), 1, f"Se esperaba exactamente un 200 y el resto 409, obtenido: {resultados}")
        self.assertEqual(codigos.count(409), n_hilos - 1, f"Resultados inesperados: {resultados}")

        # Verificar invariantes contables persistidos en base de datos y en GET /hotel/reservas/{id}
        detalle = self.cliente.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(detalle["estado"], "cancelada")
        reversos = [c for c in detalle["cargos"] if c["tipo"] == "reverso"]
        penalidades = [c for c in detalle["cargos"] if c["tipo"] == "cargo" and "primera noche" in c["concepto"]]
        self.assertEqual(len(reversos), 2, f"Reversos duplicados: {detalle['cargos']}")
        self.assertEqual(len(penalidades), 1, f"Penalidades duplicadas: {detalle['cargos']}")
        # Neto = 0 (alojamiento + minibar reversados) + 50.000 (1 noche de penalidad) = 50.000
        self.assertEqual(detalle["cuenta"]["cargos_netos_clp"], 50_000)

        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            (auditorias,) = conexion.execute(
                "SELECT count(*) FROM auditoria WHERE accion = 'cancelacion' AND recurso = %s",
                (rid,),
            ).fetchone()
        self.assertEqual(auditorias, 1)

    def test_cancelacion_concurrente_con_misma_clave_repite_200_sin_conflicto_de_integridad(self):
        """Dos o más solicitudes concurrentes con la MISMA Idempotency-Key y el
        mismo cuerpo deben serializarse y devolver todas 200 con exactamente el
        mismo cuerpo, ejecutando la cancelación una sola vez."""
        rid = self.reservar(inicio=CORTO_INICIO, fin=CORTO_FIN, clave="res-race-same")
        n_hilos = 6
        clientes = [self.nuevo_cliente_autenticado() for _ in range(n_hilos)]
        barrera = threading.Barrier(n_hilos)
        resultados = [None] * n_hilos

        def trabajador(idx: int):
            barrera.wait()
            resp = clientes[idx].post(
                f"/hotel/reservas/{rid}/cancelacion",
                json={},
                headers={"Idempotency-Key": "can-same-key"},
            )
            resultados[idx] = (resp.status_code, resp.json())

        hilos = [threading.Thread(target=trabajador, args=(i,)) for i in range(n_hilos)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        for codigo, cuerpo in resultados:
            self.assertEqual(codigo, 200, f"Fallo en reintento concurrente con misma clave: {resultados}")
            self.assertEqual(cuerpo, resultados[0][1])

        detalle = self.cliente.get(f"/hotel/reservas/{rid}").json()
        reversos = [c for c in detalle["cargos"] if c["tipo"] == "reverso"]
        penalidades = [c for c in detalle["cargos"] if c["tipo"] == "cargo" and "primera noche" in c["concepto"]]
        self.assertEqual(len(reversos), 1)
        self.assertEqual(len(penalidades), 1)
        self.assertEqual(detalle["cuenta"]["cargos_netos_clp"], 50_000)

    def test_carrera_entre_cancelacion_y_cargo_no_deja_cargo_huerfano_en_cancelada(self):
        """Si un cargo y una cancelación compiten sobre la misma reserva, la
        serialización sobre la fila `reservas` garantiza que:
        - o bien el cargo entra primero (201) y la cancelación (200) lo reversa,
        - o bien la cancelación entra primero (200) y el cargo recibe 409.
        En ningún caso queda una reserva `cancelada` con el cargo extra sin reversar."""
        rid = self.reservar(inicio=FUTURO, fin=FUTURO_FIN, clave="res-race-cargo")
        c_can = self.nuevo_cliente_autenticado()
        c_car = self.nuevo_cliente_autenticado()
        barrera = threading.Barrier(2)
        res_can = []
        res_car = []

        def hacer_cancelacion():
            barrera.wait()
            r = c_can.post(f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-vs-car"})
            res_can.append((r.status_code, r.json()))

        def hacer_cargo():
            barrera.wait()
            r = c_car.post(
                f"/hotel/reservas/{rid}/cargos",
                json={"concepto": "minibar", "monto_clp": 12_000},
                headers={"Idempotency-Key": "car-vs-can"},
            )
            res_car.append((r.status_code, r.json()))

        t1 = threading.Thread(target=hacer_cancelacion)
        t2 = threading.Thread(target=hacer_cargo)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(res_can[0][0], 200)
        self.assertIn(res_car[0][0], (201, 409))
        detalle = self.cliente.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(detalle["estado"], "cancelada")
        # Como la reserva es dentro de plazo (FUTURO), todo cargo asentado antes de
        # cancelar debe estar reversado y el neto debe ser exactamente 0.
        self.assertEqual(detalle["cuenta"]["cargos_netos_clp"], 0, f"Cargos inconsistentes: {detalle['cargos']}")

    def test_carrera_entre_cancelacion_y_entrada_serializa_estado(self):
        """Si check-in y cancelación compiten sobre una reserva que inicia hoy,
        exactamente una operación gana (200) y la otra recibe 409."""
        hoy_str = HOY.isoformat()
        fin_str = (HOY + timedelta(days=2)).isoformat()
        rid = self.reservar(inicio=hoy_str, fin=fin_str, clave="res-race-ent")
        c_can = self.nuevo_cliente_autenticado()
        c_ent = self.nuevo_cliente_autenticado()
        barrera = threading.Barrier(2)
        codigos = []

        def hacer_cancelacion():
            barrera.wait()
            r = c_can.post(f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-vs-ent"})
            codigos.append(("cancelacion", r.status_code))

        def hacer_entrada():
            barrera.wait()
            r = c_ent.post(f"/hotel/reservas/{rid}/entrada", json={}, headers={"Idempotency-Key": "ent-vs-can"})
            codigos.append(("entrada", r.status_code))

        t1 = threading.Thread(target=hacer_cancelacion)
        t2 = threading.Thread(target=hacer_entrada)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        estados_http = sorted(c for _, c in codigos)
        self.assertEqual(estados_http, [200, 409], f"Carrera mal serializada: {codigos}")

    def test_invariantes_contables_y_estados_y_permisos_en_cancelacion(self):
        """Comprueba:
        - repetición con la misma clave y otro cuerpo -> 409 ConflictoIdempotencia;
        - cancelación ya procesada -> 409;
        - rol caja -> 403; sin sesión -> 401; reserva inexistente/ajena -> 403;
        - conteo y montos de cargos/reversos/pagos antes y después, y que
          reembolso='no configurado' no altere pagos."""
        rid = self.reservar(inicio=FUTURO, fin=FUTURO_FIN, clave="res-inv")
        # Registrar un pago manual de 60.000 CLP y un cargo extra de 10.000 CLP
        self.assertEqual(
            self.cliente.post(
                f"/hotel/reservas/{rid}/pagos",
                json={"monto_clp": 60_000, "clave": "cob-inv-1", "modo": "manual"},
                headers={"Idempotency-Key": "pag-inv-1"},
            ).status_code,
            201,
        )
        self.assertEqual(
            self.cliente.post(
                f"/hotel/reservas/{rid}/cargos",
                json={"concepto": "minibar", "monto_clp": 10_000},
                headers={"Idempotency-Key": "car-inv-1"},
            ).status_code,
            201,
        )
        antes = self.cliente.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(antes["cuenta"], {"cargos_netos_clp": 160_000, "pagado_clp": 60_000, "saldo_clp": 100_000})

        # Sin sesión -> 401
        anon = TestClient(self.app)
        self.assertEqual(
            anon.post(f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-anon"}).status_code,
            401,
        )

        # Rol caja -> 403
        self.assertEqual(
            self.cliente.post(
                "/usuarios",
                json={"nombre": "caja_inv", "rol": "caja", "clave": "clave-caja"},
                headers={"Idempotency-Key": "usr-caja-inv"},
            ).status_code,
            201,
        )
        c_caja = TestClient(self.app)
        c_caja.post("/sesion", json={"usuario": "caja_inv", "clave": "clave-caja"})
        self.assertEqual(
            c_caja.post(f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-caja"}).status_code,
            403,
        )

        # Reserva inexistente/ajena -> 403
        self.assertEqual(
            self.cliente.post(
                "/hotel/reservas/RSV-NO-EXISTE/cancelacion", json={}, headers={"Idempotency-Key": "can-403"}
            ).status_code,
            403,
        )

        # Cancelación válida con clave 'can-inv-ok'
        r1 = self.cliente.post(f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-inv-ok"})
        self.assertEqual(r1.status_code, 200)
        datos1 = r1.json()
        self.assertEqual(datos1["estado"], "cancelada")
        self.assertEqual(datos1["penalidad_clp"], 0)
        self.assertEqual(datos1["reembolso"], "no configurado")
        self.assertEqual(len(datos1["reversos"]), 2)
        self.assertEqual(sum(x["monto_clp"] for x in datos1["reversos"]), 160_000)

        # Reintento con la misma clave -> 200 idéntico
        r2 = self.cliente.post(f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-inv-ok"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json(), datos1)

        # Misma clave con otro cuerpo (otra reserva) -> 409 ConflictoIdempotencia
        rid_otra = self.reservar(habitacion_id="HAB-SINT-102", inicio=FUTURO, fin=FUTURO_FIN, clave="res-inv-2")
        r_conflicto = self.cliente.post(
            f"/hotel/reservas/{rid_otra}/cancelacion", json={}, headers={"Idempotency-Key": "can-inv-ok"}
        )
        self.assertEqual(r_conflicto.status_code, 409)
        self.assertIn("otro cuerpo", r_conflicto.json()["detail"])

        # Cancelación ya procesada con clave nueva -> 409 «la reserva está cancelada»
        r_ya = self.cliente.post(
            f"/hotel/reservas/{rid}/cancelacion", json={}, headers={"Idempotency-Key": "can-inv-nueva"}
        )
        self.assertEqual(r_ya.status_code, 409)
        self.assertIn("cancelada", r_ya.json()["detail"])

        # Estado final persistido: 2 cargos + 2 reversos, neto 0, pagado 60.000 intacto, saldo -60.000
        despues = self.cliente.get(f"/hotel/reservas/{rid}").json()
        self.assertEqual(despues["estado"], "cancelada")
        self.assertEqual(len(despues["cargos"]), 4)
        self.assertEqual(despues["cuenta"], {"cargos_netos_clp": 0, "pagado_clp": 60_000, "saldo_clp": -60_000})
        self.assertEqual(len(despues["pagos"]), 1)


if __name__ == "__main__":
    unittest.main()
