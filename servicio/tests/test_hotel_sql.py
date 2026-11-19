"""ADP-2: adaptador `servicio/hotel_sql.py` entre el dominio y las tablas.

Traduce y persiste; no decide. Las pruebas ejercen filas reales de PostgreSQL.
"""
import os
import sys
import unittest
from datetime import date, datetime

import psycopg

from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import RAIZ  # fija sys.path del dominio
from servicio import hotel_sql
from servicio.migracion import aplicar_migraciones

from hotel_inventario.dominio import (
    EstadoReserva, EstadoTarea, EstadoUnidad, Establecimiento, Huesped, TipoCargo,
)
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import ServicioHotelInventario

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = EMPRESA_FIJA.id
EST = "EST-SINT-001"
D = date


def hotel_vacio():
    est = Establecimiento(id=EST, empresa_id=EMPRESA, nombre="x")
    return ServicioHotelInventario(est, ())


def con_precio_propio(c) -> bool:
    return hotel_sql._existe(c, "habitaciones", "precio_propio_clp")


def sembrar(c):
    c.execute(
        "TRUNCATE auditoria, tareas_operativas, claves_idempotencia, liquidaciones, efectos_nucleo, "
        "pagos, cargos, reservas, tarifas, sesiones, usuarios, habitaciones RESTART IDENTITY CASCADE"
    )
    for hid, op, prep, mant in (
        ("HAB-SINT-101", "disponible", "limpia", False),
        ("HAB-SINT-102", "disponible", "sucia", False),
        ("HAB-SINT-103", "ocupada", "limpia", False),
        ("HAB-SINT-104", "bloqueada", "limpia", False),
        ("HAB-SINT-105", "fuera_de_servicio", "limpia", False),
        ("HAB-SINT-106", "disponible", "inspeccionada", True),
    ):
        c.execute(
            "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad, estado_operativo, "
            "estado_preparacion, mantenimiento) VALUES (%s,%s,'doble',2,%s,%s,%s)",
            (hid, EST, op, prep, mant),
        )
        if con_precio_propio(c):  # el precio base de la unidad existe solo en esquemas con precios
            c.execute("UPDATE habitaciones SET precio_propio_clp = 60000 WHERE id = %s", (hid,))


class HotelSqlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        aplicar_migraciones(URL_TEST)  # esta prueba no construye la app que migra

    def setUp(self):
        self.c = psycopg.connect(URL_TEST)
        self.addCleanup(self.c.close)
        exigir_base_libre(self.c)
        sembrar(self.c)
        self.base = 60000 if con_precio_propio(self.c) else 0
        self.hotel = hotel_vacio()

    def tearDown(self):
        self.c.rollback()

    def tarifa_marzo(self):
        """Precio explícito para marzo: no depende de que el esquema tenga precio base por unidad."""
        self.c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                       "VALUES ('T-MAR','HAB-SINT-101','2026-03-01','2026-04-01',60000)")

    def recargar(self):
        hotel_sql.recargar(self.c, self.hotel, EMPRESA, rango=(D(2026, 1, 1), D(2026, 6, 1)))

    # --- AC-1 / AC-3 recarga ---
    def test_recarga_proyecta_estados_de_habitacion(self):
        self.recargar()
        u = self.hotel._unidades
        self.assertIs(u["HAB-SINT-101"].estado, EstadoUnidad.LIMPIA)
        self.assertIs(u["HAB-SINT-102"].estado, EstadoUnidad.SUCIA)
        self.assertIs(u["HAB-SINT-103"].estado, EstadoUnidad.OCUPADA)
        self.assertIs(u["HAB-SINT-104"].estado, EstadoUnidad.BLOQUEADA)
        self.assertIs(u["HAB-SINT-105"].estado, EstadoUnidad.FUERA_DE_SERVICIO)
        self.assertIs(u["HAB-SINT-106"].estado, EstadoUnidad.INSPECCIONADA)
        self.assertTrue(u["HAB-SINT-106"].mantenimiento)
        self.assertFalse(u["HAB-SINT-101"].mantenimiento)
        self.assertEqual(u["HAB-SINT-101"].tarifa_noche_clp, self.base)
        self.assertEqual(u["HAB-SINT-101"].capacidad, 2)

    def test_recarga_traduce_estados_de_reserva(self):
        for rid, est in (("R1", "confirmada"), ("R2", "en_estadia"), ("R3", "finalizada"), ("R4", "cancelada")):
            self.c.execute(
                "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
                "huesped_documento, tarifa_noche_aceptada_clp, estado) VALUES (%s,%s,%s,%s,%s,'Ana','1-9',70000,%s)",
                (rid, EMPRESA, "HAB-SINT-101", D(2026, 1, 1 + int(rid[1]) * 3), D(2026, 1, 3 + int(rid[1]) * 3), est),
            )
        self.recargar()
        r = self.hotel._reservas
        self.assertIs(r["R1"].estado, EstadoReserva.CONFIRMADA)
        self.assertIs(r["R2"].estado, EstadoReserva.HOSPEDADA)
        self.assertIs(r["R3"].estado, EstadoReserva.SALIDA)
        self.assertIs(r["R4"].estado, EstadoReserva.CANCELADA)
        self.assertEqual(r["R1"].huesped.nombre, "Ana")
        self.assertEqual(r["R1"].huesped.documento, "1-9")
        # AC-4 de ADP-1: tarifa aceptada desde la fila
        self.assertEqual(self.hotel._tarifa_de_reserva("R1"), 70000)

    def test_recarga_ignora_reservas_de_otra_empresa(self):
        self.c.execute(
            "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
            "tarifa_noche_aceptada_clp) VALUES ('RX','EMP-OTRA','HAB-SINT-101','2026-01-01','2026-01-03','Z',1)"
        )
        self.recargar()
        self.assertNotIn("RX", self.hotel._reservas)

    def test_recarga_lee_cargos_pagos_y_tareas(self):
        self.c.execute(
            "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
            "tarifa_noche_aceptada_clp) VALUES ('R1',%s,'HAB-SINT-101','2026-01-01','2026-01-03','Ana',50000)",
            (EMPRESA,),
        )
        self.c.execute("INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo) VALUES ('C1','R1','noche',50000,'cargo')")
        self.c.execute("INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo, referencia) "
                       "VALUES ('C2','R1','ajuste',1000,'reverso','C1')")
        self.c.execute("INSERT INTO pagos (id, reserva_id, monto_clp, clave, modo) VALUES ('P1','R1',20000,'k1','manual')")
        self.c.execute("INSERT INTO pagos (id, reserva_id, monto_clp, clave, modo, estado) "
                       "VALUES ('P2','R1',5000,'k2','pasarela','pendiente')")
        self.c.execute("INSERT INTO tareas_operativas (id, habitacion_id, tipo, estado) VALUES ('T1','HAB-SINT-102','limpieza','pendiente')")
        self.recargar()
        self.assertEqual([c.id for c in self.hotel._cargos], ["C1", "C2"])
        self.assertIs(self.hotel._cargos[1].tipo, TipoCargo.REVERSO)
        self.assertEqual(self.hotel._cargos[1].referencia, "C1")
        self.assertEqual([(p.id, p.monto_clp, p.clave) for p in self.hotel._pagos], [("P1", 20000, "k1")])
        t = self.hotel._tareas["T1"]
        self.assertEqual((t.unidad_id, t.tipo, t.estado), ("HAB-SINT-102", "limpieza", EstadoTarea.PENDIENTE))

    def test_tarifas_rango_semiabierto_y_vigencia(self):
        # fecha_hasta es exclusiva (como en servicio/reservas.py): [desde, hasta)
        self.c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                       "VALUES ('T-A','HAB-SINT-101','2026-02-01','2026-02-10',80000)")
        self.c.execute("INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp) "
                       "VALUES ('T-B','HAB-SINT-101','2026-02-05','2026-02-08',90000)")
        self.recargar()
        h = self.hotel
        self.assertEqual(h.tarifa_vigente(EMPRESA, "HAB-SINT-101", D(2026, 2, 1)), 80000)
        self.assertEqual(h.tarifa_vigente(EMPRESA, "HAB-SINT-101", D(2026, 2, 9)), 80000)
        self.assertEqual(h.tarifa_vigente(EMPRESA, "HAB-SINT-101", D(2026, 2, 10)), self.base)  # excluida
        # mayor fecha_desde gana donde se solapan
        self.assertEqual(h.tarifa_vigente(EMPRESA, "HAB-SINT-101", D(2026, 2, 5)), 90000)
        self.assertEqual(h.tarifa_vigente(EMPRESA, "HAB-SINT-101", D(2026, 2, 8)), 80000)

    # --- AC-2 persistir ---
    def test_persistir_inserta_reserva_y_hace_ida_y_vuelta(self):
        self.tarifa_marzo()
        self.recargar()
        res = self.hotel.reservar(EMPRESA, "HAB-SINT-101", D(2026, 3, 1), D(2026, 3, 3), Huesped("Bea", "2-7"))
        self.assertTrue(res.confirmada)
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)
        fila = self.c.execute(
            "SELECT habitacion_id, inicio, fin, huesped_nombre, huesped_documento, estado, "
            "tarifa_noche_aceptada_clp FROM reservas WHERE id=%s", (res.reserva.id,)).fetchone()
        self.assertEqual(fila, ("HAB-SINT-101", D(2026, 3, 1), D(2026, 3, 3), "Bea", "2-7", "confirmada", 60000))
        otro = hotel_vacio()
        hotel_sql.recargar(self.c, otro, EMPRESA)
        self.assertIn(res.reserva.id, otro._reservas)

    def test_persistir_proyecta_checkin_y_checkout(self):
        self.tarifa_marzo()
        self.recargar()
        res = self.hotel.reservar(EMPRESA, "HAB-SINT-101", D(2026, 3, 1), D(2026, 3, 3), Huesped("Bea", "2-7"))
        rid = res.reserva.id
        self.hotel.check_in(EMPRESA, rid, datetime(2026, 3, 1, 15, 0))
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)
        self.assertEqual(self.c.execute("SELECT estado FROM reservas WHERE id=%s", (rid,)).fetchone()[0], "en_estadia")
        self.assertEqual(self.c.execute("SELECT estado_operativo FROM habitaciones WHERE id='HAB-SINT-101'").fetchone()[0], "ocupada")

    def test_persistir_sucia_es_disponible_mas_preparacion(self):
        self.tarifa_marzo()
        self.recargar()
        res = self.hotel.reservar(EMPRESA, "HAB-SINT-101", D(2026, 3, 1), D(2026, 3, 3), Huesped("Bea", "2-7"))
        rid = res.reserva.id
        self.hotel.check_in(EMPRESA, rid, datetime(2026, 3, 1, 15, 0))
        self.hotel.check_out(EMPRESA, rid, datetime(2026, 3, 3, 11, 0))
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)
        op, prep = self.c.execute("SELECT estado_operativo, estado_preparacion FROM habitaciones WHERE id='HAB-SINT-101'").fetchone()
        self.assertEqual((op, prep), ("disponible", "sucia"))
        self.assertEqual(self.c.execute("SELECT estado FROM reservas WHERE id=%s", (rid,)).fetchone()[0], "finalizada")
        tareas = self.c.execute("SELECT habitacion_id, tipo, estado FROM tareas_operativas").fetchall()
        self.assertIn(("HAB-SINT-101", "limpieza", "pendiente"), tareas)

    def test_persistir_mantiene_espejo_de_mantenimiento(self):
        self.recargar()
        # sin cambios: persistir no altera las filas
        antes = self.c.execute("SELECT id, estado_operativo, estado_preparacion, mantenimiento FROM habitaciones ORDER BY id").fetchall()
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)
        despues = self.c.execute("SELECT id, estado_operativo, estado_preparacion, mantenimiento FROM habitaciones ORDER BY id").fetchall()
        self.assertEqual(antes, despues)

    def test_cargos_append_only_y_sin_duplicar(self):
        self.tarifa_marzo()
        self.recargar()
        res = self.hotel.reservar(EMPRESA, "HAB-SINT-101", D(2026, 3, 1), D(2026, 3, 3), Huesped("Bea", "2-7"))
        rid = res.reserva.id
        self.hotel.check_in(EMPRESA, rid, datetime(2026, 3, 1, 15, 0))
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)  # idempotente
        n = self.c.execute("SELECT count(*) FROM cargos WHERE reserva_id=%s", (rid,)).fetchone()[0]
        self.assertEqual(n, len(self.hotel._cargos))
        self.assertGreaterEqual(n, 1)

    def test_pago_se_inserta_una_vez_y_conserva_efecto_nucleo(self):
        self.tarifa_marzo()
        self.recargar()
        res = self.hotel.reservar(EMPRESA, "HAB-SINT-101", D(2026, 3, 1), D(2026, 3, 3), Huesped("Bea", "2-7"))
        rid = res.reserva.id
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)
        self.hotel.registrar_pago(EMPRESA, rid, 10000, "clave-1")
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)
        self.c.execute("UPDATE pagos SET efecto_nucleo_id='EF-1' WHERE reserva_id=%s AND clave='clave-1'", (rid,))
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)
        filas = self.c.execute("SELECT monto_clp, modo, efecto_nucleo_id FROM pagos WHERE reserva_id=%s", (rid,)).fetchall()
        self.assertEqual(filas, [(10000, "manual", "EF-1")])

    def test_persistir_no_borra_filas_ausentes_del_dominio(self):
        self.c.execute(
            "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
            "tarifa_noche_aceptada_clp) VALUES ('R9',%s,'HAB-SINT-101','2026-01-01','2026-01-03','Ana',50000)",
            (EMPRESA,),
        )
        hotel_sql.persistir(self.c, self.hotel, EMPRESA)  # dominio vacío
        self.assertEqual(self.c.execute("SELECT count(*) FROM reservas WHERE id='R9'").fetchone()[0], 1)
        self.assertEqual(self.c.execute("SELECT count(*) FROM habitaciones").fetchone()[0], 6)


if __name__ == "__main__":
    unittest.main()
