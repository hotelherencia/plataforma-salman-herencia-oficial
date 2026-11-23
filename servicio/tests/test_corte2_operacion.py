"""Pruebas Corte 2 Operativo P1 (#418 parte 2):
- Turnos semanales por área (recepción, aseo, desayunos, mantención) y cambios aprobados.
- Biblioteca documental filtrada por rol y buzón de sugerencias con anonimato real.
- Inventario de activos por habitación/área y mantenimiento preventivo append-only."""
import os
import unittest
from datetime import date, timedelta
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient

from servicio import contabilidad, migracion, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST",
    "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_418",
)


class Corte2OperacionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(
            configuracion=Configuracion(
                host="127.0.0.1",
                puerto=0,
                database_url=URL_TEST,
                cookie_segura=False,
                origen_front=None,
                admin_usuario="admin_c2",
                admin_clave="Clave123!",
            )
        )
        cls.client_cm = TestClient(cls.app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def setUp(self):
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "TRUNCATE activos_mantenciones, activos_hotel, sugerencias_equipo, "
                "biblioteca_documentos, cambios_turno, turnos_personal, "
                "habitaciones, auditoria, sesiones, usuarios CASCADE"
            )
            clave_h = seguridad.hashear_clave("Clave123!")
            c.execute(
                "INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo) VALUES "
                "('USR-C2-ADM', 'admin_c2', %s, 'admin_hotel', 'EMP-SINTETICA-001', true), "
                "('USR-C2-REC', 'recep_c2', %s, 'recepcion', 'EMP-SINTETICA-001', true), "
                "('USR-C2-ASE', 'aseo_c2', %s, 'aseo', 'EMP-SINTETICA-001', true)",
                (clave_h, clave_h, clave_h),
            )
            c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, estado_preparacion, en_inventario) "
                "VALUES ('HAB-10', 'EST-1', 'doble', 2, 'disponible', 'limpia', true)"
            )
            c.commit()

        self.admin = self._login("admin_c2")
        self.recep = self._login("recep_c2")
        self.aseo = self._login("aseo_c2")

    def _login(self, usuario: str) -> TestClient:
        c = TestClient(self.app)
        r = c.post("/sesion", json={"usuario": usuario, "clave": "Clave123!"})
        self.assertEqual(r.status_code, 200, r.text)
        return c

    def test_migracion_0067_idempotente(self):
        sql = Path("servicio/migraciones/0067_corte2_turnos_biblioteca_activos.sql").read_text(encoding="utf-8")
        with psycopg.connect(URL_TEST) as c:
            c.execute(sql)
            c.execute(sql)
            c.commit()

    def test_turnos_semanales_y_cambio_aprobado(self):
        hoy = contabilidad.hoy_chile()
        # Recepción no puede crear turnos -> 403
        self.assertEqual(
            self.recep.post(
                "/hotel/equipo/turnos",
                json={"usuario_nombre": "recep_c2", "area": "recepcion", "fecha": hoy.isoformat(), "hora_inicio": "08:00", "hora_fin": "16:00"},
            ).status_code,
            403,
        )
        # Admin crea turno de aseo
        r_t = self.admin.post(
            "/hotel/equipo/turnos",
            json={"usuario_nombre": "aseo_c2", "area": "aseo", "fecha": hoy.isoformat(), "hora_inicio": "09:00", "hora_fin": "17:00"},
        )
        self.assertEqual(r_t.status_code, 201, r_t.text)
        turno_id = r_t.json()["turno_id"]

        # Aseo consulta su semana y solicita cambio
        r_list = self.aseo.get("/hotel/equipo/turnos", params={"area": "aseo"})
        self.assertEqual(r_list.status_code, 200, r_list.text)
        self.assertEqual(len(r_list.json()["turnos"]), 1)

        r_c = self.aseo.post(
            f"/hotel/equipo/turnos/{turno_id}/cambios",
            json={"reemplazo_usuario": "recep_c2", "motivo": "Control médico programado en la mañana"},
        )
        self.assertEqual(r_c.status_code, 201, r_c.text)
        cambio_id = r_c.json()["cambio_id"]

        # Aseo no puede auto-aprobar -> 403
        self.assertEqual(
            self.aseo.post(f"/hotel/equipo/cambios-turno/{cambio_id}/decision", json={"decision": "aprobado"}).status_code,
            403,
        )
        # Admin aprueba y el turno se actualiza al reemplazo
        r_ok = self.admin.post(
            f"/hotel/equipo/cambios-turno/{cambio_id}/decision",
            json={"decision": "aprobado", "nota_revision": "Coordinado con recepción"},
        )
        self.assertEqual(r_ok.status_code, 200, r_ok.text)
        self.assertEqual(r_ok.json()["estado"], "aprobado")

        despues = self.admin.get("/hotel/equipo/turnos").json()["turnos"][0]
        self.assertEqual(despues["usuario_nombre"], "recep_c2")
        self.assertEqual(despues["estado"], "cambiado")

    def test_biblioteca_por_rol_y_buzon_anonimo(self):
        # Admin publica 1 protocolo para todos y 1 manual exclusivo de recepción
        self.assertEqual(
            self.admin.post(
                "/hotel/equipo/biblioteca",
                json={"titulo": "Protocolo emergencia", "categoria": "protocolo", "rol_objetivo": "todos", "contenido": "Cortar luz y evacuar al patio."},
            ).status_code,
            201,
        )
        self.assertEqual(
            self.admin.post(
                "/hotel/equipo/biblioteca",
                json={"titulo": "Manual caja recepción", "categoria": "manual", "rol_objetivo": "recepcion", "contenido": "Revisar boletas al cierre."},
            ).status_code,
            201,
        )

        # Aseo solo ve 'todos' (1 doc); Recepción ve ambos (2 docs)
        self.assertEqual(len(self.aseo.get("/hotel/equipo/biblioteca").json()["documentos"]), 1)
        self.assertEqual(len(self.recep.get("/hotel/equipo/biblioteca").json()["documentos"]), 2)

        # Buzón de sugerencias anónimas: autor queda oculto incluso para admin
        r_s = self.aseo.post(
            "/hotel/equipo/sugerencias",
            json={"categoria": "mantencion", "mensaje": "Agregar carrito extra para ropa blanca en segundo piso", "anonimo": True},
        )
        self.assertEqual(r_s.status_code, 201, r_s.text)
        sug_id = r_s.json()["sugerencia_id"]
        self.assertIsNone(r_s.json()["autor"])

        lista_adm = self.admin.get("/hotel/equipo/sugerencias").json()["sugerencias"]
        self.assertEqual(len(lista_adm), 1)
        self.assertIsNone(lista_adm[0]["autor"])

        r_upd = self.admin.post(
            f"/hotel/equipo/sugerencias/{sug_id}/estado",
            json={"estado": "implementada", "respuesta_admin": "Carrito comprado para el piso 2."},
        )
        self.assertEqual(r_upd.status_code, 200, r_upd.text)
        self.assertEqual(r_upd.json()["estado"], "implementada")

    def test_activos_preventivo_y_mantencion_append_only(self):
        ayer = contabilidad.hoy_chile() - timedelta(days=1)
        r_a = self.admin.post(
            "/hotel/activos",
            json={
                "nombre": "Aire acondicionado Split 12000 BTU",
                "categoria": "climatizacion",
                "habitacion_id": "HAB-10",
                "frecuencia_mantencion_dias": 90,
                "proxima_mantencion": ayer.isoformat(),
            },
        )
        self.assertEqual(r_a.status_code, 201, r_a.text)
        activo_id = r_a.json()["activo_id"]
        self.assertEqual(r_a.json()["estado_preventivo"], "vencido")

        # Filtro solo_vencidos devuelve el activo
        venc = self.recep.get("/hotel/activos", params={"solo_vencidos": "true"}).json()
        self.assertEqual(venc["resumen"]["vencidos"], 1)

        # Registrar mantención preventiva recalcula próxima mantención (+90 días)
        hoy = contabilidad.hoy_chile()
        r_m = self.recep.post(
            f"/hotel/activos/{activo_id}/mantenciones",
            json={"fecha_realizada": hoy.isoformat(), "tipo": "preventiva", "descripcion": "Limpieza de filtros y revisión de voltaje", "costo_clp": 25000},
        )
        self.assertEqual(r_m.status_code, 201, r_m.text)
        esperada = (hoy + timedelta(days=90)).isoformat()
        self.assertEqual(r_m.json()["proxima_mantencion"], esperada)

        # Activo ahora queda al día
        post = self.admin.get("/hotel/activos", params={"habitacion_id": "HAB-10"}).json()["activos"][0]
        self.assertEqual(post["estado_preventivo"], "al_dia")
        self.assertEqual(post["proxima_mantencion"], esperada)

        # Inmutabilidad append-only en activos_mantenciones
        with psycopg.connect(URL_TEST) as c:
            with self.assertRaises(psycopg.Error):
                c.execute("DELETE FROM activos_mantenciones")


if __name__ == "__main__":
    unittest.main()
