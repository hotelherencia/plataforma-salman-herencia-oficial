"""ADP-1 (2026-10-30): recargar el singleton del dominio desde filas y alta de unidades.

AC-1 `recargar` rellena las estructuras y reinicia el contador de ids.
AC-2 `alta_unidad` es aditivo y rechaza id duplicado.
AC-4 `_tarifas_aceptadas` se reconstruye desde la tarifa aceptada de cada reserva.
"""
from datetime import date, datetime
import unittest

from hotel_inventario.dominio import (
    Cargo,
    Liquidacion,
    EstadoReserva,
    EstadoTarea,
    EstadoUnidad,
    Huesped,
    Pago,
    Reserva,
    TareaOperativa,
    TipoCargo,
    Unidad,
)
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    ReservaNoCancelable,
    SIN_CUPO,
    UNIDAD_INEXISTENTE,
    hotel_sintetico,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
EST = "EST-SINT-001"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


def unidad(n, tarifa=50_000, estado=EstadoUnidad.LIMPIA, mantenimiento=False):
    return Unidad(f"HAB-SINT-{n}", EST, 2, tarifa, estado, mantenimiento)


def reserva(rid="RSV-SINT-0007", unidad_id="HAB-SINT-201", inicio=INICIO, fin=FIN):
    return Reserva(rid, EMPRESA, unidad_id, inicio, fin, HUESPED, EstadoReserva.CONFIRMADA)


class AltaUnidadTest(unittest.TestCase):
    def setUp(self):
        self.hotel = servicio_con_una_unidad()

    def test_alta_unidad_la_ofrece_en_la_disponibilidad(self):
        self.hotel.alta_unidad(unidad(202))
        ids = {u.id for u in self.hotel.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)}
        self.assertIn("HAB-SINT-202", ids)

    def test_alta_unidad_rechaza_id_duplicado(self):
        with self.assertRaises(ValueError):
            self.hotel.alta_unidad(unidad(101))

    def test_alta_unidad_rechaza_otro_establecimiento(self):
        ajena = Unidad("HAB-AJENA-1", "EST-OTRO", 2, 50_000)
        with self.assertRaises(ValueError):
            self.hotel.alta_unidad(ajena)

    def test_alta_unidad_no_altera_las_existentes(self):
        antes = self.hotel.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)
        self.hotel.alta_unidad(unidad(203))
        despues = {u.id for u in self.hotel.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)}
        self.assertTrue({u.id for u in antes} <= despues)


class RecargaTest(unittest.TestCase):
    def setUp(self):
        self.hotel = hotel_sintetico()

    def recargar(self, **kw):
        base = dict(
            unidades=(unidad(201), unidad(202)),
            reservas=(),
            cargos=(),
            pagos=(),
            tareas=(),
            tarifas_aceptadas={},
            tarifas_por_rango=(),
        )
        base.update(kw)
        self.hotel.recargar(**base)

    def test_reemplaza_las_unidades_por_las_de_las_filas(self):
        self.recargar()
        ids = {u.id for u in self.hotel.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)}
        self.assertEqual(ids, {"HAB-SINT-201", "HAB-SINT-202"})

    def test_sin_unidades_no_hay_oferta(self):
        self.recargar(unidades=())
        self.assertEqual(self.hotel.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2), [])

    def test_reserva_cargada_ocupa_el_cupo(self):
        self.recargar(unidades=(unidad(201),), reservas=(reserva(),))
        self.assertEqual(self.hotel.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2), [])

    def test_reserva_cancelada_cargada_no_ocupa_cupo(self):
        cancelada = Reserva("RSV-SINT-0007", EMPRESA, "HAB-SINT-201", INICIO, FIN, HUESPED,
                            EstadoReserva.CANCELADA)
        self.recargar(unidades=(unidad(201),), reservas=(cancelada,))
        ids = {u.id for u in self.hotel.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)}
        self.assertEqual(ids, {"HAB-SINT-201"})

    def test_contador_de_ids_supera_los_cargados(self):
        pago = Pago("PGO-SINT-0012", "RSV-SINT-0007", 1_000, "k1")
        cargo = Cargo("CGO-SINT-0003", "RSV-SINT-0007", TipoCargo.CARGO, "noche", 50_000)
        tarea = TareaOperativa("TSK-SINT-0020", EMPRESA, "HAB-SINT-201", "limpieza", EstadoTarea.PENDIENTE)
        self.recargar(unidades=(unidad(201),), reservas=(reserva(),), cargos=(cargo,),
                      pagos=(pago,), tareas=(tarea,))
        self.assertEqual(self.hotel._nuevo_id("RSV"), "RSV-SINT-0021")

    def test_contador_arranca_en_uno_sin_filas(self):
        self.recargar()
        self.assertEqual(self.hotel._nuevo_id("RSV"), "RSV-SINT-0001")

    def test_ids_ajenos_al_formato_no_rompen_el_contador(self):
        self.recargar(unidades=(unidad(201),), reservas=(reserva("RSV-EXTERNA-ABC"),))
        self.assertEqual(self.hotel._nuevo_id("RSV"), "RSV-SINT-0001")

    def test_reserva_nueva_tras_recarga_no_colisiona(self):
        self.recargar(unidades=(unidad(201), unidad(202)), reservas=(reserva("RSV-SINT-0001"),))
        res = self.hotel.reservar(EMPRESA, "HAB-SINT-202", INICIO, FIN, HUESPED)
        self.assertTrue(res.confirmada)
        self.assertNotEqual(res.reserva.id, "RSV-SINT-0001")

    def test_tarifa_por_rango_se_expande_por_dia(self):
        self.recargar(unidades=(unidad(201),),
                      tarifas_por_rango=(("HAB-SINT-201", date(2026, 11, 10), date(2026, 11, 12),
                                          80_000, "temporada"),))
        for d in (date(2026, 11, 10), date(2026, 11, 11), date(2026, 11, 12)):
            self.assertEqual(self.hotel.tarifa_vigente(EMPRESA, "HAB-SINT-201", d), 80_000)
        self.assertEqual(self.hotel.tarifa_vigente(EMPRESA, "HAB-SINT-201", date(2026, 11, 13)), 50_000)

    def test_tarifas_aceptadas_alimentan_la_penalizacion(self):
        self.recargar(unidades=(unidad(201, tarifa=50_000),), reservas=(reserva(),),
                      tarifas_aceptadas={"RSV-SINT-0007": 77_000})
        self.assertEqual(self.hotel._tarifa_de_reserva("RSV-SINT-0007"), 77_000)

    def test_recargar_es_idempotente(self):
        for _ in range(2):
            self.recargar(unidades=(unidad(201),), reservas=(reserva(),))
        self.assertEqual(len(self.hotel._reservas), 1)
        self.assertEqual(len(self.hotel._unidades), 1)

    def test_recargar_descarta_el_estado_anterior(self):
        self.hotel.reservar(EMPRESA, "HAB-SINT-101", INICIO, FIN, HUESPED)
        self.recargar()
        self.assertEqual(self.hotel._reservas, {})
        self.assertEqual(self.hotel._pagos, [])
        self.assertEqual(self.hotel._cargos, [])
        self.assertEqual(self.hotel._tareas, {})
        self.assertEqual(self.hotel._tarifas_aceptadas, {})
        self.assertEqual(self.hotel._tarifas_por_fecha, {})

    def test_recargar_reemplaza_las_liquidaciones(self):
        self.hotel._liquidaciones["RSV-VIEJA"] = Liquidacion("RSV-VIEJA", 1, 1, 0)
        liq = Liquidacion("RSV-SINT-0007", 100, 100, 0)
        self.recargar(unidades=(unidad(201),), reservas=(reserva(),), liquidaciones=(liq,))
        self.assertEqual(self.hotel._liquidaciones, {"RSV-SINT-0007": liq})
        self.recargar()
        self.assertEqual(self.hotel._liquidaciones, {})

    def test_reserva_inexistente_tras_recarga_no_es_cancelable(self):
        self.recargar()
        with self.assertRaises((ReservaNoCancelable, ValueError, KeyError)):
            self.hotel.cancelar(EMPRESA, "RSV-SINT-0001", datetime(2026, 11, 1, 10, 0))


if __name__ == "__main__":
    unittest.main()
