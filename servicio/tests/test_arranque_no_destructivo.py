"""W16-A02 / NEW-01: reiniciar el servicio nunca borra historial ni reactiva retiros.

Contra PostgreSQL real (DATABASE_URL_TEST). Reproduce el hallazgo de la
auditoría 2026-11-16: con INVENTARIO_DOCUMENTAL=1 y titular real, el arranque
borraba reservas y pagos de habitaciones fuera de HAB-01..17 y volvía a poner
a la venta una habitación retirada por mantención.
"""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import psycopg

from servicio import inventario_documental as inv
from servicio import migracion
from servicio import precios
from servicio.aplicacion import ErrorArranque, crear_app
from servicio.configuracion import Configuracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-HERENCIA-001"
ADMIN = ("admin", "clave-admin-sintetica")
_TABLAS = (
    "auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
    "pagos, cargos, solicitudes, reservas, tarifas, sesiones, usuarios, habitaciones, "
    "doc_registro, doc_control_ocupacion, doc_ocupacion_reportada, doc_tarifa, "
    "doc_habitacion, doc_paquete"
)


def _config(**extra) -> Configuracion:
    base = dict(
        host="127.0.0.1",
        puerto=0,
        database_url=URL_TEST,
        cookie_segura=False,
        origen_front=None,
        admin_usuario=ADMIN[0],
        admin_clave=ADMIN[1],
        empresa_titular=True,
        empresa_es_sintetica=False,
        inventario_documental=True,
    )
    base.update(extra)
    return Configuracion(**base)


def _limpiar() -> None:
    migracion.aplicar_migraciones(URL_TEST)
    with psycopg.connect(URL_TEST) as conexion:
        exigir_base_libre(conexion)
        conexion.execute(f"TRUNCATE {_TABLAS} RESTART IDENTITY CASCADE")
        # La siembra fija precio base en los tipos (tabla no truncada): se
        # limpian para no filtrar precios a otras pruebas.
        conexion.execute("UPDATE tipos_habitacion SET precio_base_clp = NULL WHERE precio_base_clp IS NOT NULL")
        conexion.commit()


class ArranqueNoDestructivoTest(unittest.TestCase):
    def setUp(self):
        _limpiar()

    def tearDown(self):
        _limpiar()

    def _historial_y_retiro(self) -> None:
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "UPDATE habitaciones SET estado_operativo='fuera_de_servicio', "
                "motivo_fuera_de_servicio='filtración baño', fuera_de_servicio_desde=now() "
                "WHERE id='HAB-01'"
            )
            c.execute(
                "INSERT INTO habitaciones(id, establecimiento_id, tipo, capacidad) "
                "VALUES ('HAB-18', 'EST-HERENCIA-001', 'doble', 2)"
            )
            c.execute(
                "INSERT INTO reservas(id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
                "tarifa_noche_aceptada_clp) VALUES ('RSV-X', %s, 'HAB-18', '2026-12-01', "
                "'2026-12-03', 'Huésped Sintético', 50000)",
                (EMPRESA,),
            )
            c.execute(
                "INSERT INTO pagos(id, reserva_id, monto_clp, clave, modo) "
                "VALUES ('PAG-X', 'RSV-X', 100000, 'k1', 'manual')"
            )
            # La administración cambia el precio base del tipo de HAB-02 en el
            # mantenedor (fuente única de precio, 1A.2).
            c.execute(
                "UPDATE tipos_habitacion SET precio_base_clp = 61000 "
                "WHERE id = (SELECT tipo FROM habitaciones WHERE id = 'HAB-02')"
            )
            c.commit()

    def test_reinicio_conserva_reservas_pagos_y_retiros(self):
        crear_app(configuracion=_config())  # primer arranque: siembra HAB-01..17
        with psycopg.connect(URL_TEST) as c:
            (n,) = c.execute(
                "SELECT count(*) FROM habitaciones WHERE id = ANY(%s)", (list(inv.IDS_INVENTARIO_REAL),)
            ).fetchone()
        self.assertEqual(n, 17)
        self._historial_y_retiro()

        crear_app(configuracion=_config())  # «reinicio»
        crear_app(configuracion=_config())  # y otro

        with psycopg.connect(URL_TEST) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM reservas WHERE id='RSV-X'").fetchone()[0], 1)
            self.assertEqual(c.execute("SELECT count(*) FROM pagos WHERE id='PAG-X'").fetchone()[0], 1)
            self.assertEqual(c.execute("SELECT count(*) FROM habitaciones WHERE id='HAB-18'").fetchone()[0], 1)
            estado, motivo = c.execute(
                "SELECT estado_operativo, motivo_fuera_de_servicio FROM habitaciones WHERE id='HAB-01'"
            ).fetchone()
            self.assertEqual(estado, "fuera_de_servicio")
            self.assertEqual(motivo, "filtración baño")
            # El precio fijado por la administración sigue vigente: el
            # reinicio no vuelve a poner la referencial encima.
            self.assertEqual(precios.precio_noche(c, "HAB-02", date(2026, 12, 1)).precio_clp, 61000)
            # Y la siembra ya no crea tarifas por habitación (fuente única).
            self.assertEqual(c.execute("SELECT count(*) FROM tarifas").fetchone()[0], 0)

    def test_retiro_puntual_de_ajenas_es_baja_logica(self):
        crear_app(configuracion=_config())
        self._historial_y_retiro()
        with psycopg.connect(URL_TEST) as c:
            c.execute(
                "INSERT INTO habitaciones(id, establecimiento_id, tipo, capacidad) "
                "VALUES ('HAB-SINT-999', 'EST-HERENCIA-001', 'doble', 2)"
            )
            r = inv.retirar_inventario_ajeno(c)
            a = inv.activar_inventario_real(c)
            c.commit()
            self.assertEqual(r["ids_eliminadas"], ["HAB-SINT-999"])  # sin historial: se elimina
            self.assertEqual(r["ids_fuera_de_servicio"], ["HAB-18"])  # con historial: baja lógica
            self.assertEqual(c.execute("SELECT count(*) FROM pagos WHERE id='PAG-X'").fetchone()[0], 1)
            self.assertEqual(c.execute("SELECT count(*) FROM reservas WHERE id='RSV-X'").fetchone()[0], 1)
            self.assertEqual(
                c.execute("SELECT estado_operativo FROM habitaciones WHERE id='HAB-18'").fetchone()[0],
                "fuera_de_servicio",
            )
            # La reactivación puntual no toca una retirada por mantención.
            self.assertNotIn("HAB-01", a["ids"])
            self.assertEqual(
                c.execute("SELECT estado_operativo FROM habitaciones WHERE id='HAB-01'").fetchone()[0],
                "fuera_de_servicio",
            )

    def test_en_vercel_no_siembra_inventario(self):
        crear_app(configuracion=_config(en_vercel=True))
        with psycopg.connect(URL_TEST) as c:
            (n,) = c.execute("SELECT count(*) FROM habitaciones").fetchone()
        self.assertEqual(n, 0)

    def test_sin_migrar_al_arrancar_exige_base_al_dia(self):
        self.assertEqual(migracion.migraciones_pendientes(URL_TEST), [])
        crear_app(configuracion=_config(migrar_al_arrancar=False))  # al día: arranca

    def test_sin_migrar_al_arrancar_falla_si_hay_pendientes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for ruta in migracion.DIRECTORIO_MIGRACIONES.glob("*.sql"):
                (Path(tmp) / ruta.name).write_text(ruta.read_text(encoding="utf-8"), encoding="utf-8")
            (Path(tmp) / "9999_futura.sql").write_text("SELECT 1;", encoding="utf-8")
            original = migracion.migraciones_pendientes

            def _pendientes(url, directorio=None):
                return original(url, Path(tmp))

            with mock.patch("servicio.aplicacion.migraciones_pendientes", _pendientes):
                with self.assertRaises(ErrorArranque):
                    crear_app(configuracion=_config(migrar_al_arrancar=False))


if __name__ == "__main__":
    unittest.main()
