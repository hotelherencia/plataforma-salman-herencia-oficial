import sys
from datetime import date
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "core" / "incremento1"))

from nucleo.servicio import AccesoDenegado as AccesoNucleo  # noqa: E402
from nucleo.servicio import Nucleo  # noqa: E402

from hotel_inventario.dominio import EstadoUnidad, Establecimiento, Huesped, Unidad  # noqa: E402
from hotel_inventario.empresa import EMPRESA_FIJA  # noqa: E402
from hotel_inventario.servicio import ServicioHotelInventario  # noqa: E402

EMPRESA = EMPRESA_FIJA.id
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
ESTABLECIMIENTO = Establecimiento(id="EST-SINT-001", empresa_id=EMPRESA, nombre="Establecimiento sintético")
UNIDADES = (Unidad("HAB-SINT-101", ESTABLECIMIENTO.id, 2, 50_000, EstadoUnidad.LIMPIA),)


class CobroEspia:
    """Registra cada llamada al núcleo; si `rechazar` es verdadero, la rechaza como lo haría el núcleo."""

    def __init__(self, rechazar: bool = False) -> None:
        self.llamadas: list[tuple[str, str, str, int]] = []
        self._rechazar = rechazar

    def aplicar_resultado_pago(self, empresa_id, clave, estado, monto_clp):
        self.llamadas.append((empresa_id, clave, estado, monto_clp))
        if self._rechazar:
            raise AccesoNucleo("empresa desconocida")
        return None


class CobroDelHotelPasaPorNucleoTest(unittest.TestCase):
    def _servicio_con_reserva(self, cobros):
        servicio = ServicioHotelInventario(ESTABLECIMIENTO, UNIDADES, cobros=cobros)
        reserva = servicio.reservar(EMPRESA, "HAB-SINT-101", INICIO, FIN, HUESPED).reserva
        return servicio, reserva

    def test_el_cobro_se_registra_llamando_al_nucleo(self):
        # Falla si el hotel vuelve a registrar el pago por su cuenta sin llamar al núcleo.
        espia = CobroEspia()
        servicio, reserva = self._servicio_con_reserva(espia)

        servicio.registrar_pago(EMPRESA, reserva.id, 20_000, clave="cob-001")

        self.assertEqual(len(espia.llamadas), 1)
        empresa_id, clave, estado, monto = espia.llamadas[0]
        self.assertEqual(empresa_id, EMPRESA)
        self.assertEqual(clave, f"{reserva.id}:cob-001")
        self.assertEqual(estado, "pendiente")
        self.assertEqual(monto, 20_000)

    def test_el_reintento_con_la_misma_clave_no_duplica_el_efecto(self):
        espia = CobroEspia()
        servicio, reserva = self._servicio_con_reserva(espia)

        primero = servicio.registrar_pago(EMPRESA, reserva.id, 20_000, clave="cob-001")
        reintento = servicio.registrar_pago(EMPRESA, reserva.id, 20_000, clave="cob-001")

        self.assertEqual(primero.id, reintento.id)
        self.assertEqual(len(espia.llamadas), 1)
        self.assertEqual(len(servicio.pagos(EMPRESA, reserva.id)), 1)

    def test_si_el_nucleo_rechaza_el_hotel_no_guarda_el_pago(self):
        espia = CobroEspia(rechazar=True)
        servicio, reserva = self._servicio_con_reserva(espia)

        with self.assertRaises(AccesoNucleo):
            servicio.registrar_pago(EMPRESA, reserva.id, 20_000, clave="cob-001")

        self.assertEqual(servicio.pagos(EMPRESA, reserva.id), ())

    def test_con_el_nucleo_real_el_efecto_queda_en_el_nucleo(self):
        nucleo = Nucleo(empresa=EMPRESA_FIJA)
        servicio, reserva = self._servicio_con_reserva(nucleo)

        servicio.registrar_pago(EMPRESA, reserva.id, 20_000, clave="cob-001", estado="pendiente")

        # Una segunda aplicación con otro estado devuelve el efecto ya registrado, sin cambiarlo.
        efecto = nucleo.aplicar_resultado_pago(EMPRESA, f"{reserva.id}:cob-001", "autorizado", 20_000)
        self.assertEqual(efecto.estado, "pendiente")
        self.assertEqual(efecto.monto_clp, 20_000)


if __name__ == "__main__":
    unittest.main()
