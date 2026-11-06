"""Pruebas de caracterización para las decisiones pendientes (FUN-A01 de la
auditoría 2026-11-03, issues #296/#304/#305). Documentan con HECHOS el
comportamiento vigente — no proponen reglas nuevas: sirven de base escrita
para que el propietario ratifique o cambie cada política (D-ENT-01 y
relacionadas) y para detectar desviaciones si una decisión cambia el
comportamiento (estas pruebas avisarán en rojo).

Hechos caracterizados:
1. Precio con tarifa que cambia entre noches: se cobra tarifa(inicio) ×
   noches completas (D-TAR-02, v1-issue-17), aunque alguna noche intermedia
   tenga otra tarifa — el total no se prorratea por noche.
2. Alguna noche del rango sin tarifa vigente → 409 y nada se persiste (§2.8).
3. Salida anticipada: la reserva finaliza conservando su fin original y su
   precio aceptado completo — no hay prorrateo por salida antes de tiempo.
4. El dominio no tiene horas: reservas son fechas (date); una reserva que
   comienza «hoy» admite entrada a cualquier hora de ese día (nada de
   medianoche/DST en el contrato vigente).
5. Roles de entrada/salida (#304): hoy CUALQUIER rol autenticado puede
   registrar entrada y salida (la ruta solo exige sesión).
"""
import os
import unittest
import uuid
from datetime import date, timedelta

import psycopg
from fastapi.testclient import TestClient

from servicio import seguridad
from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
HOY = date.today()


class CaracterizacionBaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, liquidaciones, efectos_nucleo, pagos, cargos, "
                "reservas, tarifas, tareas_operativas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            from servicio.reservas import sembrar_habitaciones

            sembrar_habitaciones(conexion)
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                "VALUES ('TAR-BASE', 'HAB-SINT-101', '2026-01-01', '2027-12-31', 50000)"
            )
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.cliente = TestClient(self.app)
        self.cliente.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]})

    def clave(self):
        return f"car-{uuid.uuid4().hex[:10]}"

    def tarifa(self, tarifa_id, habitacion, desde, hasta, monto):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                "VALUES (%s, %s, %s, %s, %s)",
                (tarifa_id, habitacion, desde, hasta, monto),
            )
            conexion.commit()

    def reservar(self, inicio, fin, habitacion="HAB-SINT-101"):
        return self.cliente.post(
            "/hotel/reservas",
            json={"habitacion_id": habitacion, "inicio": str(inicio), "fin": str(fin),
                  "huesped": {"nombre": "Huésped Caracterización"}},
            headers={"Idempotency-Key": self.clave()},
        )

    def pagar(self, cliente, rid, monto):
        pago = cliente.post(
            f"/hotel/reservas/{rid}/pagos",
            json={"monto_clp": monto, "clave": f"car-pago-{uuid.uuid4().hex[:8]}", "modo": "manual"},
            headers={"Idempotency-Key": self.clave()},
        )
        self.assertEqual(pago.status_code, 201, pago.text)


class TarifaCruzadaTest(CaracterizacionBaseTest):
    """Hechos 1 y 2: precio con cambio de tarifa entre noches."""

    def test_precio_es_tarifa_de_inicio_por_noches_sin_prorrateo(self):
        # Tarifa sube a mitad del rango: noches [d, d+1) a 50000, [d+1, d+3) a 80000.
        d = HOY + timedelta(days=10)
        self.tarifa("TAR-CARA", "HAB-SINT-101", str(d + timedelta(days=1)), "2027-12-31", 80000)
        r = self.reservar(d, d + timedelta(days=3))  # 3 noches: [d, d+3)
        self.assertEqual(r.status_code, 201, r.text)
        # HECHO: cada noche tiene tarifa (pasa §2.8) pero el total usa tarifa(inicio) × noches:
        # 50000 × 3 = 150000, no 50000+80000+80000.
        self.assertEqual(r.json()["total_clp"], 150000)

    def test_noche_sin_tarifa_rechaza_y_no_persiste(self):
        d = HOY + timedelta(days=20)
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("DELETE FROM tarifas WHERE habitacion_id = 'HAB-SINT-101'")
            conexion.execute(
                "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
                "VALUES ('TAR-PARCIAL', 'HAB-SINT-101', %s, %s, 50000)",
                (str(d), str(d + timedelta(days=1))),
            )
            conexion.commit()
        r = self.reservar(d, d + timedelta(days=2))  # la segunda noche queda sin tarifa
        self.assertEqual(r.status_code, 409, r.text)
        with psycopg.connect(URL_TEST) as conexion:
            (n,) = conexion.execute("SELECT count(*) FROM reservas").fetchone()
        self.assertEqual(n, 0)


class SalidaAnticipadaTest(CaracterizacionBaseTest):
    """Hecho 3: salida antes del fin no prorratea nada."""

    def test_salida_anticipada_conserva_fin_y_precio(self):
        d = HOY - timedelta(days=1)  # reserva que ya comenzó
        r = self.reservar(d, d + timedelta(days=4))
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["reserva_id"]
        entrada = self.cliente.post(f"/hotel/reservas/{rid}/entrada",
                                    headers={"Idempotency-Key": self.clave()})
        self.assertEqual(entrada.status_code, 200, entrada.text)
        self.pagar(self.cliente, rid, 200000)  # 4 noches × 50000: la salida exige cuenta en cero
        salida = self.cliente.post(f"/hotel/reservas/{rid}/salida",
                                   headers={"Idempotency-Key": self.clave()})
        self.assertEqual(salida.status_code, 200, salida.text)
        with psycopg.connect(URL_TEST) as conexion:
            fila = conexion.execute(
                "SELECT estado, inicio, fin, tarifa_noche_aceptada_clp FROM reservas WHERE id = %s", (rid,)
            ).fetchone()
        # HECHO: finalizada, con el fin original y el precio completo aceptado.
        self.assertEqual(fila[0], "finalizada")
        self.assertEqual(str(fila[2]), str(d + timedelta(days=4)))
        self.assertEqual(fila[3], 50000)


class FechasSinHoraTest(CaracterizacionBaseTest):
    """Hecho 4: no hay horas en el dominio; la entrada solo exige inicio ≤ hoy."""

    def test_reserva_que_comienza_hoy_admite_entrada(self):
        r = self.reservar(HOY, HOY + timedelta(days=2))
        self.assertEqual(r.status_code, 201, r.text)
        rid = r.json()["reserva_id"]
        entrada = self.cliente.post(f"/hotel/reservas/{rid}/entrada",
                                    headers={"Idempotency-Key": self.clave()})
        self.assertEqual(entrada.status_code, 200, entrada.text)

    def test_reserva_futura_rechaza_entrada(self):
        r = self.reservar(HOY + timedelta(days=3), HOY + timedelta(days=5))
        rid = r.json()["reserva_id"]
        entrada = self.cliente.post(f"/hotel/reservas/{rid}/entrada",
                                    headers={"Idempotency-Key": self.clave()})
        self.assertEqual(entrada.status_code, 409, entrada.text)


class RolesEntradaSalidaTest(CaracterizacionBaseTest):
    """Hecho 5 (#304): cualquier rol autenticado puede entrar y salir hoy."""

    def _usuario(self, rol):
        nombre = f"user-{rol}-{uuid.uuid4().hex[:6]}"
        self.cliente.post("/usuarios", json={"nombre": nombre, "rol": rol, "clave": "clave-rol-1"},
                          headers={"Idempotency-Key": self.clave()})
        cliente = TestClient(self.app)
        r = cliente.post("/sesion", json={"usuario": nombre, "clave": "clave-rol-1"})
        self.assertEqual(r.status_code, 200, r.text)
        return cliente

    def test_caja_puede_entrar_y_salir(self):
        d = HOY - timedelta(days=1)
        r = self.reservar(d, d + timedelta(days=2))
        rid = r.json()["reserva_id"]
        caja = self._usuario("caja")
        entrada = caja.post(f"/hotel/reservas/{rid}/entrada", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(entrada.status_code, 200, entrada.text)  # HECHO: caja entra (solo pide sesión)
        self.pagar(caja, rid, 100000)  # 2 noches × 50000: la salida exige cuenta en cero
        salida = caja.post(f"/hotel/reservas/{rid}/salida", headers={"Idempotency-Key": self.clave()})
        self.assertEqual(salida.status_code, 200, salida.text)


if __name__ == "__main__":
    unittest.main()
