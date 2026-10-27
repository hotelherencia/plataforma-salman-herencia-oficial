import unittest
from datetime import date, datetime

from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Huesped, Unidad
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.puertos import (
    NO_CONFIGURADO,
    PuertoCanal,
    PuertoDocumentoTributario,
    PuertoPago,
    PuertoPMS,
    PuertosVacios,
)
from hotel_inventario.servicio import ServicioHotelInventario

EMPRESA = EMPRESA_FIJA.id
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
ESTABLECIMIENTO = Establecimiento(id="EST-SINT-001", empresa_id=EMPRESA, nombre="Establecimiento sintético")
UNIDADES = (Unidad("HAB-SINT-101", ESTABLECIMIENTO.id, 2, 50_000, EstadoUnidad.LIMPIA),)


class PuertoQueFalla:
    """Si el servicio llama a un puerto, la prueba falla."""

    def __getattr__(self, nombre):
        def llamada(*args, **kwargs):
            raise AssertionError(f"el servicio invocó el puerto: {nombre}")

        return llamada


class PuertosNoConfiguradosTest(unittest.TestCase):
    def test_cada_puerto_devuelve_no_configurado(self):
        self.assertFalse(PuertoPMS().consultar_reserva("X").configurado)
        self.assertFalse(PuertoCanal().recibir_evento({}).configurado)
        self.assertFalse(PuertoPago().iniciar_cobro("R", 1).configurado)
        self.assertFalse(PuertoDocumentoTributario().emitir("R").configurado)
        self.assertEqual(PuertoPago().iniciar_cobro("R", 1).detalle, NO_CONFIGURADO.detalle)

    def test_el_flujo_completo_no_invoca_ningun_puerto(self):
        servicio = ServicioHotelInventario(ESTABLECIMIENTO, UNIDADES, puertos=PuertoQueFalla())
        reserva = servicio.reservar(EMPRESA, "HAB-SINT-101", INICIO, FIN, HUESPED).reserva
        servicio.consultar_disponibilidad(EMPRESA, INICIO, FIN, 1)
        servicio.asentar_cargo(EMPRESA, reserva.id, "Extra sintético", 5_000)
        servicio.cancelar(EMPRESA, reserva.id, datetime.combine(INICIO, datetime.min.time()))
        self.assertEqual(servicio.saldo_clp(EMPRESA, reserva.id), 50_000 + 5_000)

    def test_los_puertos_vacios_existen_en_el_contenedor(self):
        puertos = PuertosVacios()
        self.assertFalse(puertos.pms.consultar_reserva("X").configurado)
        self.assertFalse(puertos.documento_tributario.emitir("R").configurado)


if __name__ == "__main__":
    unittest.main()
