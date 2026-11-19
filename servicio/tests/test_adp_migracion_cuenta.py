"""ADP-4 AC-3 al desplegar sobre datos vivos: la cuenta de una reserva nace vacía y el alojamiento se asienta en
la entrada. Una reserva confirmada ANTES del cambio ya trae su cargo «Alojamiento N noches»; la entrada asentaría las
noches otra vez y cobraría doble. La migración 0032 reversa (append-only) ese cargo en las reservas aún confirmadas."""
import os
import unittest
from datetime import date, timedelta

import psycopg

from servicio import migracion
from servicio.tests.aislamiento import exigir_base_libre

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
HOY = date.today()
MIGRACION = migracion.DIRECTORIO_MIGRACIONES / "0032_cuenta_vacia_al_confirmar.sql"


class MigracionCuentaVaciaTest(unittest.TestCase):
    def setUp(self):
        migracion.aplicar_migraciones(URL_TEST)
        self.c = psycopg.connect(URL_TEST, autocommit=True)
        exigir_base_libre(self.c)
        self.c.execute(
            "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
            "pagos, cargos, reservas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
        )
        for n in (1, 2, 3, 4):
            self.c.execute(
                "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) "
                "VALUES (%s, 'EST-SINT-001', 'doble', 2)", (f"HAB-M-{n}",))

    def tearDown(self):
        self.c.close()

    def reserva(self, rid, hab, estado, cargos):
        self.c.execute(
            "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
            "tarifa_noche_aceptada_clp, estado) VALUES (%s, %s, %s, %s, %s, 'Ana', 50000, %s)",
            (rid, EMPRESA, hab, HOY + timedelta(days=10), HOY + timedelta(days=12), estado))
        for cid, concepto, monto, tipo, ref in cargos:
            self.c.execute(
                "INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo, referencia) "
                "VALUES (%s, %s, %s, %s, %s, %s)", (cid, rid, concepto, monto, tipo, ref))

    def neto(self, rid):
        return self.c.execute(
            "SELECT COALESCE(SUM(CASE WHEN tipo='reverso' THEN -monto_clp ELSE monto_clp END),0) "
            "FROM cargos WHERE reserva_id=%s", (rid,)).fetchone()[0]

    def migrar(self):
        self.c.execute(MIGRACION.read_text(encoding="utf-8"))

    def test_la_confirmada_con_alojamiento_queda_con_la_cuenta_vacia(self):
        self.reserva("R1", "HAB-M-1", "confirmada", [("C1", "Alojamiento 2 noches", 100000, "cargo", None)])
        self.migrar()
        self.assertEqual(self.neto("R1"), 0)
        (reverso,) = self.c.execute(
            "SELECT referencia, monto_clp, tipo FROM cargos WHERE reserva_id='R1' AND tipo='reverso'").fetchall()
        self.assertEqual(reverso, ("C1", 100000, "reverso"))
        # el cargo original no se toca: append-only
        self.assertEqual(self.c.execute("SELECT monto_clp FROM cargos WHERE id='C1'").fetchone()[0], 100000)

    def test_es_idempotente(self):
        self.reserva("R1", "HAB-M-1", "confirmada", [("C1", "Alojamiento 2 noches", 100000, "cargo", None)])
        self.migrar()
        self.migrar()
        self.assertEqual(self.c.execute("SELECT count(*) FROM cargos WHERE tipo='reverso'").fetchone()[0], 1)

    def test_no_toca_estadias_en_curso_ni_cerradas_ni_otros_cargos(self):
        alojamiento = ("Alojamiento 2 noches", 100000, "cargo", None)
        self.reserva("R2", "HAB-M-2", "en_estadia", [("C2", *alojamiento)])
        self.reserva("R3", "HAB-M-3", "cancelada", [("C3", *alojamiento)])
        self.reserva("R4", "HAB-M-4", "confirmada", [("C4", "Minibar", 3000, "cargo", None),
                                                      ("C5", "Cama adicional", 8000, "cargo", None)])
        self.migrar()
        self.assertEqual((self.neto("R2"), self.neto("R3"), self.neto("R4")), (100000, 100000, 11000))
        self.assertEqual(self.c.execute("SELECT count(*) FROM cargos WHERE tipo='reverso'").fetchone()[0], 0)

    def test_no_reversa_dos_veces_un_alojamiento_ya_reversado(self):
        self.reserva("R1", "HAB-M-1", "confirmada", [
            ("C1", "Alojamiento 2 noches", 100000, "cargo", None),
            ("C1R", "Reverso de Alojamiento 2 noches", 100000, "reverso", "C1")])
        self.migrar()
        self.assertEqual(self.c.execute("SELECT count(*) FROM cargos WHERE tipo='reverso'").fetchone()[0], 1)

    def test_conserva_los_pagos_ya_hechos(self):
        self.reserva("R1", "HAB-M-1", "confirmada", [("C1", "Alojamiento 2 noches", 100000, "cargo", None)])
        self.c.execute("INSERT INTO pagos (id, reserva_id, monto_clp, clave, modo) VALUES ('P1','R1',40000,'k','manual')")
        self.migrar()
        self.assertEqual(self.c.execute("SELECT sum(monto_clp) FROM pagos WHERE reserva_id='R1'").fetchone()[0], 40000)


if __name__ == "__main__":
    unittest.main()
