from datetime import date, datetime
import threading
import unittest

from hotel_inventario.dominio import EstadoUnidad, Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import SIN_CUPO, hotel_sintetico, servicio_con_una_unidad

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")


def carrera(servicio, intentos):
    barrera = threading.Barrier(intentos)
    resultados = []
    cerrojo = threading.Lock()

    def intentar(i):
        huesped = Huesped(nombre=f"Huésped Sintético {i}", documento=f"DOC-SINT-{i:04d}")
        barrera.wait(timeout=20)
        r = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, huesped)
        with cerrojo:
            resultados.append(r)

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(intentos)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=20)
    return resultados


class ConcurrenciaUltimaUnidadTest(unittest.TestCase):
    def test_AT_005_cien_intentos_concurrentes_confirman_como_maximo_una_reserva_local(self):
        servicio = servicio_con_una_unidad()
        resultados = carrera(servicio, 100)
        confirmadas = [r for r in resultados if r.confirmada]
        self.assertEqual(len(confirmadas), 1)
        self.assertTrue(all(r.motivo == SIN_CUPO for r in resultados if not r.confirmada))

    def test_ADV_001_cien_intentos_sobre_la_ultima_habitacion_una_sola_confirmacion(self):
        servicio = servicio_con_una_unidad()
        resultados = carrera(servicio, 100)
        self.assertEqual(len([r for r in resultados if r.confirmada]), 1)
        self.assertEqual(len(resultados), 100)

    def test_AC_US_HOT_001_01_ultima_unidad_cien_intentos_maximo_una_con_cupo(self):
        servicio = servicio_con_una_unidad()
        resultados = carrera(servicio, 100)
        self.assertEqual(len([r for r in resultados if r.confirmada]), 1)

    def test_AC_US_HOT_001_02_sucia_hoy_vendible_en_fecha_futura(self):
        servicio = hotel_sintetico()
        futuro = servicio.consultar_disponibilidad(EMPRESA, date(2026, 12, 1), date(2026, 12, 3), 2)
        self.assertIn("HAB-SINT-102", {u.id for u in futuro})
        sucia = next(u for u in futuro if u.id == "HAB-SINT-102")
        self.assertIs(sucia.estado, EstadoUnidad.SUCIA)
        self.assertEqual(sucia.estado, EstadoUnidad.SUCIA)


if __name__ == "__main__":
    unittest.main()
