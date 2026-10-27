from datetime import datetime
import unittest

from cafeteria_mesas_pos.dominio import EstadoGasto, EstadoMesa
from cafeteria_mesas_pos.empresa import EMPRESA_FIJA
from cafeteria_mesas_pos.servicio import (
    AccesoDenegado,
    FlujoAutorizadoRequerido,
    cafeteria_sintetica,
)

EMPRESA = EMPRESA_FIJA.id
AHORA = datetime(2026, 11, 10, 12, 0, 0)


def mesa_con_cafe(servicio, cantidad=4, cliente="comensal-1"):
    mesa = servicio.abrir_mesa(EMPRESA, "MESA-1")
    servicio.agregar_item(EMPRESA, mesa.qr_token, "PROD-CAFE", cantidad, cliente)
    return mesa


class MesaPedidoIdsTest(unittest.TestCase):
    def test_AT_001_qr_activo_abre_la_carta_y_qr_revocado_o_modificado_no_accede(self):
        servicio = cafeteria_sintetica()
        mesa = servicio.abrir_mesa(EMPRESA, "MESA-1")
        self.assertEqual(servicio.acceder_carta(EMPRESA, mesa.qr_token).id, "MESA-1")

        servicio.revocar_qr(EMPRESA, "MESA-1")
        with self.assertRaises(AccesoDenegado):
            servicio.acceder_carta(EMPRESA, mesa.qr_token)
        with self.assertRaises(AccesoDenegado):
            servicio.acceder_carta(EMPRESA, "QR-SINT-9999")

    def test_AT_002_editar_tras_enviar_a_cocina_exige_flujo_autorizado(self):
        servicio = cafeteria_sintetica()
        mesa = mesa_con_cafe(servicio)
        servicio.agregar_item(EMPRESA, mesa.qr_token, "PROD-CAFE", 1, "comensal-2")
        servicio.confirmar_pedido(EMPRESA, mesa.qr_token, "pedido-1", AHORA)

        with self.assertRaises(FlujoAutorizadoRequerido):
            servicio.editar_item_enviado(EMPRESA, mesa.qr_token, "PROD-CAFE")

    def test_AT_003_confirmar_pedido_crea_una_sola_comanda_con_mesa_hora_y_estado(self):
        servicio = cafeteria_sintetica()
        mesa = mesa_con_cafe(servicio)
        primera = servicio.confirmar_pedido(EMPRESA, mesa.qr_token, "pedido-9", AHORA)
        segunda = servicio.confirmar_pedido(EMPRESA, mesa.qr_token, "pedido-9", AHORA)
        self.assertEqual(primera.id, segunda.id)
        self.assertEqual(primera.mesa_id, "MESA-1")
        self.assertEqual(primera.hora, AHORA)
        self.assertEqual(primera.estado, "enviado")

    def test_AT_004_dos_cobros_concurrentes_no_consumen_dos_veces_el_mismo_saldo(self):
        servicio = cafeteria_sintetica()
        mesa = mesa_con_cafe(servicio, cantidad=1)
        servicio.pagar_items(EMPRESA, mesa.qr_token, "comensal-1", "item-cafe-1", 2_500)
        with self.assertRaises(ValueError):
            servicio.pagar_items(EMPRESA, mesa.qr_token, "comensal-2", "item-cafe-1", 2_500)

    def test_ADV_001_dos_personas_pagan_el_mismo_item_solo_una_imputacion(self):
        servicio = cafeteria_sintetica()
        mesa = mesa_con_cafe(servicio, cantidad=1)
        servicio.pagar_items(EMPRESA, mesa.qr_token, "A", "item-unico", 2_500)
        with self.assertRaises(ValueError):
            servicio.pagar_items(EMPRESA, mesa.qr_token, "B", "item-unico", 2_500)

    def test_AT_015_reparto_10000_en_tres_con_residuo_a_la_ultima(self):
        servicio = cafeteria_sintetica()
        mesa = mesa_con_cafe(servicio, cantidad=4)
        comandas_antes = len(servicio._comandas)
        reparto = servicio.reparto_igual(EMPRESA, mesa.qr_token, 3)
        montos = [p.monto_clp for p in reparto.partes]
        self.assertEqual(montos, [3333, 3333, 3334])
        self.assertEqual(sum(montos), 10_000)
        self.assertEqual(len(servicio._comandas), comandas_antes)

    def test_AT_015_descuento_y_propina_diferenciados(self):
        servicio = cafeteria_sintetica()
        mesa = mesa_con_cafe(servicio, cantidad=4)
        reparto = servicio.reparto_igual(EMPRESA, mesa.qr_token, 2, descuento_clp=1_000, propina_clp=500)
        self.assertEqual(reparto.descuento_clp, 1_000)
        self.assertEqual(reparto.propina_clp, 500)
        self.assertEqual(sum(p.monto_clp for p in reparto.partes), 9_500)

    def test_AC_US_CAF_001_01_la_regla_de_residuo_muestra_3333_3333_3334(self):
        servicio = cafeteria_sintetica()
        mesa = mesa_con_cafe(servicio, cantidad=4)
        reparto = servicio.reparto_igual(EMPRESA, mesa.qr_token, 3)
        self.assertEqual([p.monto_clp for p in reparto.partes], [3333, 3333, 3334])

    def test_AC_US_CAF_001_02_la_parte_pagada_conserva_su_monto_al_modificar_el_reparto(self):
        servicio = cafeteria_sintetica()
        mesa = mesa_con_cafe(servicio, cantidad=4)
        servicio.reparto_igual(EMPRESA, mesa.qr_token, 3)
        servicio.pagar_parte(EMPRESA, mesa.qr_token, "parte-1", clave="pago-p1", monto_clp=3333)

        reparto = servicio.reparto_igual(EMPRESA, mesa.qr_token, 3)
        parte_1 = next(p for p in reparto.partes if p.cliente == "parte-1")
        self.assertTrue(parte_1.pagada)
        self.assertEqual(parte_1.monto_clp, 3333)
        self.assertEqual(parte_1.clave_pago, "pago-p1")
        self.assertEqual(sum(p.monto_clp for p in reparto.partes), 10_000)

    def test_AT_016_dos_ejecuciones_del_mismo_hecho_no_duplican_la_alerta(self):
        servicio = cafeteria_sintetica()
        primera = servicio.alerta_anulacion(EMPRESA, "anul-1", 40_000, umbral_clp=30_000, ahora=AHORA)
        segunda = servicio.alerta_anulacion(EMPRESA, "anul-1", 40_000, umbral_clp=30_000, ahora=AHORA)
        self.assertEqual(primera.id, segunda.id)
        self.assertEqual(len(servicio._alertas), 1)
        self.assertIsNone(
            servicio.alerta_anulacion(EMPRESA, "anul-2", 10_000, umbral_clp=30_000, ahora=AHORA)
        )

    def test_AC_US_CAF_003_01_la_alerta_ya_emitida_se_identifica_sin_nueva_accion(self):
        servicio = cafeteria_sintetica()
        primera = servicio.alerta_anulacion(EMPRESA, "ventana-1", 99_000, 50_000, AHORA)
        reejecutada = servicio.alerta_anulacion(EMPRESA, "ventana-1", 99_000, 50_000, AHORA)
        self.assertEqual(primera.id, reejecutada.id)
        self.assertEqual(len(servicio._alertas), 1)


if __name__ == "__main__":
    unittest.main()
