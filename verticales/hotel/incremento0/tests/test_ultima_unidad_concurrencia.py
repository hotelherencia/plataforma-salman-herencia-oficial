from datetime import date
import threading
import unittest

from hotel_reservas_incremento0.dominio import Huesped
from hotel_reservas_incremento0.empresa import EMPRESA_FIJA
from hotel_reservas_incremento0.servicio import SIN_CUPO, hotel_sintetico_con_una_unidad

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
INTENTOS = 10


class UltimaUnidadConcurrenciaTest(unittest.TestCase):
    def test_dos_reservas_simultaneas_de_la_ultima_unidad_no_confirman_ambas(self):
        servicio = hotel_sintetico_con_una_unidad()
        barrera = threading.Barrier(INTENTOS)
        resultados = []
        cerrojo_resultados = threading.Lock()

        def intentar(i):
            huesped = Huesped(nombre=f"Huésped Sintético {i}", documento=f"DOC-SINT-{i:04d}")
            barrera.wait(timeout=10)
            resultado = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, huesped)
            with cerrojo_resultados:
                resultados.append(resultado)

        hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(INTENTOS)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=10)

        confirmadas = [r for r in resultados if r.confirmada]
        rechazadas = [r for r in resultados if not r.confirmada]

        self.assertEqual(len(resultados), INTENTOS)
        self.assertEqual(len(confirmadas), 1)
        self.assertEqual(len(rechazadas), INTENTOS - 1)
        self.assertTrue(all(r.motivo == SIN_CUPO for r in rechazadas))
        self.assertEqual(len(servicio.reservas_confirmadas(EMPRESA)), 1)


if __name__ == "__main__":
    unittest.main()
