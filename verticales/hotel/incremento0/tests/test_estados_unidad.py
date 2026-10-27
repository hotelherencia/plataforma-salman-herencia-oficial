from datetime import date
import unittest

from hotel_reservas_incremento0.dominio import EstadoOperativo, EstadoPreparacion
from hotel_reservas_incremento0.empresa import EMPRESA_FIJA
from hotel_reservas_incremento0.servicio import hotel_sintetico_con_una_unidad

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)


class EstadosUnidadTest(unittest.TestCase):
    def setUp(self):
        self.servicio = hotel_sintetico_con_una_unidad()

    def ofertas(self):
        return self.servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 2)

    def test_la_preparacion_no_quita_la_unidad_del_cupo(self):
        for estado in (EstadoPreparacion.SUCIA, EstadoPreparacion.LIMPIA, EstadoPreparacion.INSPECCIONADA):
            self.servicio.cambiar_preparacion(EMPRESA, UNIDAD, estado)
            self.assertEqual([o.unidad.id for o in self.ofertas()], [UNIDAD])
            self.assertEqual(self.ofertas()[0].unidad.estado_preparacion, estado)

    def test_unidad_bloqueada_no_aparece_en_disponibilidad(self):
        self.servicio.cambiar_estado_operativo(EMPRESA, UNIDAD, EstadoOperativo.BLOQUEADA)
        self.assertEqual(self.ofertas(), [])

    def test_unidad_fuera_de_servicio_no_aparece_en_disponibilidad(self):
        self.servicio.cambiar_estado_operativo(EMPRESA, UNIDAD, EstadoOperativo.FUERA_DE_SERVICIO)
        self.assertEqual(self.ofertas(), [])

    def test_la_preparacion_sigue_sin_quitar_cupo_con_unidad_bloqueada(self):
        self.servicio.cambiar_estado_operativo(EMPRESA, UNIDAD, EstadoOperativo.BLOQUEADA)
        self.servicio.cambiar_preparacion(EMPRESA, UNIDAD, EstadoPreparacion.LIMPIA)
        self.assertEqual(self.ofertas(), [])

    def test_al_volver_a_disponible_la_unidad_vuelve_al_cupo(self):
        self.servicio.cambiar_estado_operativo(EMPRESA, UNIDAD, EstadoOperativo.FUERA_DE_SERVICIO)
        self.servicio.cambiar_estado_operativo(EMPRESA, UNIDAD, EstadoOperativo.DISPONIBLE)
        self.assertEqual([o.unidad.id for o in self.ofertas()], [UNIDAD])

    def test_unidad_inexistente_lanza_error(self):
        with self.assertRaises(ValueError):
            self.servicio.cambiar_estado_operativo(EMPRESA, "HAB-INEXISTENTE", EstadoOperativo.BLOQUEADA)


if __name__ == "__main__":
    unittest.main()
