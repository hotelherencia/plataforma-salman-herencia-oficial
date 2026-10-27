from datetime import datetime
import threading
import unittest

from hotel_reservas_incremento1.dominio import EstadoUnidad
from hotel_reservas_incremento1.empresa import EMPRESA_FIJA, ESTABLECIMIENTO_FIJO
from hotel_reservas_incremento1.puertos import PuertosVacios
from hotel_reservas_incremento1.servicio import (
    SIN_CUPO,
    AccesoDenegado,
    hotel_sintetico_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
ESTABLECIMIENTO = ESTABLECIMIENTO_FIJO.id
UNIDAD = "HAB-SINT-101"
INICIO = datetime(2026, 11, 10, 14, 0)
FIN = datetime(2026, 11, 12, 11, 0)
LLEGADA = datetime(2026, 11, 10, 15, 0)


def huesped(n="Huésped Sintético Uno"):
    from hotel_reservas_incremento1.dominio import Huesped

    return Huesped(nombre=n, documento="DOC-SINT-0001")


class EstadosUnidadTest(unittest.TestCase):
    def setUp(self):
        self.servicio = hotel_sintetico_con_una_unidad()

    def ofertas(self):
        return self.servicio.consultar_disponibilidad(EMPRESA, ESTABLECIMIENTO, INICIO, FIN, 2)

    def test_los_tres_estados_limpios_venden(self):
        for estado in (EstadoUnidad.LIMPIA, EstadoUnidad.SUCIA, EstadoUnidad.INSPECCIONADA):
            self.servicio.cambiar_estado_unidad(EMPRESA, UNIDAD, estado)
            self.assertEqual([o.unidad.id for o in self.ofertas()], [UNIDAD])

    def test_bloqueada_y_fuera_de_servicio_no_venden(self):
        for estado in (EstadoUnidad.BLOQUEADA, EstadoUnidad.FUERA_DE_SERVICIO):
            self.servicio.cambiar_estado_unidad(EMPRESA, UNIDAD, estado)
            self.assertEqual(self.ofertas(), [])

    def test_al_desbloquear_la_unidad_vuelve_a_vender(self):
        self.servicio.cambiar_estado_unidad(EMPRESA, UNIDAD, EstadoUnidad.BLOQUEADA)
        self.servicio.cambiar_estado_unidad(EMPRESA, UNIDAD, EstadoUnidad.LIMPIA)
        self.assertEqual([o.unidad.id for o in self.ofertas()], [UNIDAD])

    def test_empresa_distinta_denegada_en_consulta_y_reserva(self):
        with self.assertRaises(AccesoDenegado):
            self.servicio.consultar_disponibilidad("EMP-OTRA", ESTABLECIMIENTO, INICIO, FIN, 2)
        with self.assertRaises(AccesoDenegado):
            self.servicio.reservar("EMP-OTRA", ESTABLECIMIENTO, UNIDAD, INICIO, FIN, LLEGADA, huesped())

    def test_establecimiento_de_otra_empresa_denegado(self):
        with self.assertRaises(AccesoDenegado):
            self.servicio.consultar_disponibilidad(EMPRESA, "EST-OTRO", INICIO, FIN, 2)

    def test_una_sola_confirmada_en_diez_intentos_simultaneos(self):
        servicio = hotel_sintetico_con_una_unidad()
        barrera = threading.Barrier(10)
        resultados = []
        cerrojo = threading.Lock()

        def intentar(i):
            barrera.wait(timeout=10)
            r = servicio.reservar(EMPRESA, ESTABLECIMIENTO, UNIDAD, INICIO, FIN, LLEGADA, huesped(f"Huésped {i}"))
            with cerrojo:
                resultados.append(r)

        hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(10)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=10)

        confirmadas = [r for r in resultados if r.confirmada]
        self.assertEqual(len(confirmadas), 1)
        self.assertTrue(all(r.motivo == SIN_CUPO for r in resultados if not r.confirmada))

    def test_puertos_siguen_no_configurado(self):
        puertos = PuertosVacios()
        respuestas = [
            puertos.pms.consultar_reserva("X"),
            puertos.canal.publicar_disponibilidad(UNIDAD, (INICIO, FIN)),
            puertos.pago.iniciar_cobro("RSV", 1),
            puertos.documento_tributario.emitir("RSV"),
        ]
        for respuesta in respuestas:
            self.assertFalse(respuesta.configurado)
            self.assertEqual(respuesta.detalle, "no configurado")


if __name__ == "__main__":
    unittest.main()
