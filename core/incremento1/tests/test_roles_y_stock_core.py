"""Pruebas unitarias de dominio del core: catálogo transversal de roles (#323)
y servicio compartido de stock con bodegas y reposición (#358)."""
import unittest

from nucleo.roles import (
    CATALOGO,
    CatalogoRoles,
    DefinicionRol,
    MODULO_CORE,
    MODULO_HOTEL,
)
from nucleo.stock import (
    BODEGA_CAFETERIA,
    BODEGA_MINIBAR,
    BODEGA_PRINCIPAL,
    ErrorStockCore,
    ServicioStockCore,
    bodega_por_categoria,
    evaluar_reposicion,
)


class RolesCoreTest(unittest.TestCase):
    def test_catalogo_separa_roles_core_y_hotel(self):
        solo_core = CATALOGO.codigos([MODULO_CORE])
        self.assertEqual(solo_core, ("dueno", "administrador", "admin_plataforma"))

        con_hotel = CATALOGO.codigos([MODULO_CORE, MODULO_HOTEL])
        self.assertIn("admin_hotel", con_hotel)
        self.assertIn("recepcion", con_hotel)
        self.assertIn("caja", con_hotel)
        self.assertIn("aseo", con_hotel)

    def test_catalogo_admite_nuevas_verticales_sin_activarlas_por_defecto(self):
        cat = CatalogoRoles()
        cat.registrar(DefinicionRol("barista", "cafeteria", "Barista", "POS cafetería", False, True, 70))
        self.assertNotIn("barista", cat.codigos([MODULO_CORE, MODULO_HOTEL]))
        self.assertIn("barista", cat.codigos([MODULO_CORE, MODULO_HOTEL, "cafeteria"]))
        self.assertTrue(cat.exige_doble_factor("admin_plataforma"))
        self.assertFalse(cat.exige_doble_factor("barista"))


class StockCoreTest(unittest.TestCase):
    def test_bodega_por_categoria(self):
        self.assertEqual(bodega_por_categoria("minibar"), BODEGA_MINIBAR)
        self.assertEqual(bodega_por_categoria("cafeteria"), BODEGA_CAFETERIA)
        self.assertEqual(bodega_por_categoria("extra"), BODEGA_PRINCIPAL)

    def test_evaluacion_reposicion_sin_stock_bajo_minimo_y_ok(self):
        cero = evaluar_reposicion("P1", "Agua", "minibar", stock_actual=0, stock_minimo=5, costo_clp=500)
        self.assertEqual(cero.nivel, "sin_stock")
        self.assertEqual(cero.sugerido_reponer, 10)
        self.assertEqual(cero.valorizacion_costo_clp, 0)

        bajo = evaluar_reposicion("P2", "Café", "cafeteria", stock_actual=3, stock_minimo=5, costo_clp=1200)
        self.assertEqual(bajo.nivel, "bajo_minimo")
        self.assertEqual(bajo.sugerido_reponer, 7)
        self.assertEqual(bajo.valorizacion_costo_clp, 3600)

        ok = evaluar_reposicion("P3", "Jugo", "minibar", stock_actual=12, stock_minimo=5, costo_clp=800)
        self.assertEqual(ok.nivel, "ok")
        self.assertEqual(ok.sugerido_reponer, 0)
        self.assertEqual(ok.valorizacion_costo_clp, 9600)

    def test_transferencia_entre_bodegas_conserva_total_y_rechaza_negativo(self):
        svc = ServicioStockCore()
        svc.registrar_producto("P1", "Agua mineral", "minibar", stock_minimo=6, costo_clp=450)
        svc.mover("P1", BODEGA_PRINCIPAL, "entrada", 20, "factura proveedor")
        origen, destino = svc.transferir("P1", BODEGA_PRINCIPAL, BODEGA_MINIBAR, 8, "reposición piso 2")
        self.assertEqual(origen, 12)
        self.assertEqual(destino, 8)
        self.assertEqual(svc.stock_de("P1"), 20)

        # También puede transferir a cafetería desde el mismo servicio core.
        origen2, cafe = svc.transferir("P1", BODEGA_PRINCIPAL, BODEGA_CAFETERIA, 5, "barra mañana")
        self.assertEqual(origen2, 7)
        self.assertEqual(cafe, 5)
        self.assertEqual(svc.stock_de("P1"), 20)

        with self.assertRaises(ErrorStockCore):
            svc.transferir("P1", BODEGA_CAFETERIA, BODEGA_MINIBAR, 6)

        rep = svc.reporte_reposicion()
        self.assertEqual(rep["resumen"]["unidades_totales"], 20)
        self.assertEqual(rep["resumen"]["valorizacion_costo_clp"], 9000)


if __name__ == "__main__":
    unittest.main()
