"""Pruebas #402 / PUR-004: Notas de crédito de proveedor vinculadas a facturas,
rebaja en stock (0055) y cuenta por pagar append-only e idempotente."""
import unittest
from pathlib import Path

import psycopg

from servicio.tests import facturas_sinteticas as fs
from servicio.tests.test_importacion_productos import ImportacionHttpBase, URL_TEST


class NotasCreditoProveedorTest(ImportacionHttpBase):
    def setUp(self):
        super().setUp()
        with psycopg.connect(URL_TEST) as c:
            c.execute("TRUNCATE cxp_movimientos, cuentas_por_pagar, documentos_proveedor, archivos_documentos CASCADE")
            c.commit()

    def _subir_y_confirmar_factura(self, folio="5001", rut="76123456-0"):
        xml = fs.envio_dte(fs.documento(folio=folio, rut=rut))
        r = self.admin.post("/hotel/productos/documentos/xml", json={"xml": xml})
        self.assertEqual(r.status_code, 201, r.text)
        doc = r.json()["documento"]
        linea = doc["lineas"][0]
        c = self.admin.post(
            f"/hotel/productos/documentos/{doc['documento_id']}/confirmacion",
            headers=self.idem(),
            json={
                "lineas": [
                    {
                        "accion": "crear",
                        "nombre": "Agua NC Test 500 ml",
                        "categoria": "minibar",
                        "cantidad": linea["cantidad"],
                        "unidades_por_paquete": linea["unidades_por_paquete"],
                        "costo_unitario_clp": linea["costo_unitario_clp"],
                        "precio_clp": 1500,
                    }
                ]
            },
        )
        self.assertEqual(c.status_code, 201, c.text)
        return doc, c.json()

    def test_migracion_0062_idempotente_y_cxp_append_only(self):
        sql = Path("servicio/migraciones/0062_notas_credito_cxp.sql").read_text(encoding="utf-8")
        with psycopg.connect(URL_TEST) as c:
            c.execute(sql)
            c.execute(sql)
            c.commit()

        _doc, conf = self._subir_y_confirmar_factura(folio="5010")
        cxp_id = conf["cuenta_por_pagar"]["cxp_id"]
        mov_id = conf["cuenta_por_pagar"]["movimientos"][0]["movimiento_id"]

        # Verificar trigger append-only en cxp_movimientos (prohíbe UPDATE y DELETE)
        with psycopg.connect(URL_TEST) as c:
            with self.assertRaises(psycopg.errors.RaiseException):
                c.execute("UPDATE cxp_movimientos SET monto_clp = 1 WHERE id = %s", (mov_id,))
            c.rollback()
            with self.assertRaises(psycopg.errors.RaiseException):
                c.execute("DELETE FROM cxp_movimientos WHERE id = %s", (mov_id,))
            c.rollback()
        self.assertTrue(cxp_id.startswith("CXP-"))

    def test_aplicar_nota_credito_rebaja_stock_0055_y_cxp_idempotente(self):
        factura, conf = self._subir_y_confirmar_factura(folio="5001")
        prod_id = conf["detalle"][0]["producto_id"]
        stock_inicial = self.catalogo()["Agua NC Test 500 ml"]["stock"]
        self.assertEqual(stock_inicial, 48)
        cxp_ini = conf["cuenta_por_pagar"]
        monto_factura = cxp_ini["monto_original_clp"]
        self.assertEqual(cxp_ini["estado"], "abierta")
        self.assertEqual(cxp_ini["saldo_pendiente_clp"], monto_factura)

        # Subir Nota de Crédito (DTE 61) del mismo proveedor referenciando folio 5001
        xml_nc = fs.envio_dte(fs.documento(folio="901", tipo=61, rut="76123456-0", referencia="5001"))
        r_nc = self.admin.post("/hotel/productos/documentos/xml", json={"xml": xml_nc})
        self.assertEqual(r_nc.status_code, 201, r_nc.text)
        nc = r_nc.json()["documento"]
        self.assertEqual(nc["clase"], "nota_credito")
        self.assertEqual(nc["factura_sugerida"]["documento_id"], factura["documento_id"])

        # Aplicar NC parcialmente: rebaja 1 caja de 24 unidades en stock (0055) y $10.000 en CxP
        clave_idem = self.idem()
        payload_nc = {
            "factura_id": factura["documento_id"],
            "lineas_stock": [{"producto_id": prod_id, "cantidad": 1, "unidades_por_paquete": 24}],
            "monto_rebaja_clp": 10000,
            "motivo": "Devolución 1 caja dañada",
        }
        ra1 = self.admin.post(
            f"/hotel/productos/documentos/{nc['documento_id']}/aplicar-nota-credito",
            headers=clave_idem,
            json=payload_nc,
        )
        self.assertEqual(ra1.status_code, 200, ra1.text)
        res = ra1.json()
        self.assertEqual(res["estado"], "aplicada")
        self.assertEqual(res["factura_referencia_id"], factura["documento_id"])
        self.assertEqual(res["unidades_rebajadas_stock"], 24)
        self.assertEqual(res["monto_rebajado_cxp_clp"], 10000)

        # Stock rebajado tanto en productos.stock como en core_stock_bodega (0055)
        prod_post = self.catalogo()["Agua NC Test 500 ml"]
        self.assertEqual(prod_post["stock"], 24)
        self.assertEqual(prod_post["por_bodega"].get("minibar"), 24)

        # Movimiento de stock tipo='reverso' registrado
        movs_stock = self.admin.get(f"/hotel/productos/{prod_id}/movimientos").json()["movimientos"]
        self.assertTrue(any(m["tipo"] == "reverso" and m["delta"] == -24 for m in movs_stock))

        # Cuenta por pagar refleja rebaja parcial append-only
        cxp_post = res["cuenta_por_pagar"]
        self.assertEqual(cxp_post["estado"], "parcial")
        self.assertEqual(cxp_post["notas_credito_clp"], 10000)
        self.assertEqual(cxp_post["saldo_pendiente_clp"], monto_factura - 10000)

        # Idempotencia: misma clave devuelve mismo resultado SIN rebajar de nuevo
        ra_idem = self.admin.post(
            f"/hotel/productos/documentos/{nc['documento_id']}/aplicar-nota-credito",
            headers=clave_idem,
            json=payload_nc,
        )
        self.assertEqual(ra_idem.status_code, 200)
        self.assertEqual(self.catalogo()["Agua NC Test 500 ml"]["stock"], 24)

        # Otra clave sobre la misma NC ya aplicada -> 409
        ra_dup = self.admin.post(
            f"/hotel/productos/documentos/{nc['documento_id']}/aplicar-nota-credito",
            headers=self.idem(),
            json=payload_nc,
        )
        self.assertEqual(ra_dup.status_code, 409)

        # Pagar el saldo restante en CxP cierra la cuenta por pagar
        restante = cxp_post["saldo_pendiente_clp"]
        rp = self.admin.post(
            f"/hotel/productos/cuentas-por-pagar/{cxp_post['cxp_id']}/pagos",
            headers=self.idem(),
            json={"monto_clp": restante, "medio": "transferencia", "comprobante": "TRF-9981"},
        )
        self.assertEqual(rp.status_code, 201, rp.text)
        self.assertEqual(rp.json()["estado"], "pagada")
        self.assertEqual(rp.json()["saldo_pendiente_clp"], 0)

        # Pagar sobre cuenta ya pagada -> 409
        rp_dup = self.admin.post(
            f"/hotel/productos/cuentas-por-pagar/{cxp_post['cxp_id']}/pagos",
            headers=self.idem(),
            json={"monto_clp": 100, "medio": "transferencia"},
        )
        self.assertEqual(rp_dup.status_code, 409)

    def test_validaciones_conflicto_y_permisos_nc_y_cxp(self):
        factura, conf = self._subir_y_confirmar_factura(folio="5002")
        prod_id = conf["detalle"][0]["producto_id"]

        # NC de otro proveedor -> 409
        xml_otro = fs.envio_dte(fs.documento(folio="902", tipo=61, rut="77999888-5"))
        nc_otro = self.admin.post("/hotel/productos/documentos/xml", json={"xml": xml_otro}).json()["documento"]
        r_rut = self.admin.post(
            f"/hotel/productos/documentos/{nc_otro['documento_id']}/aplicar-nota-credito",
            headers=self.idem(),
            json={"factura_id": factura["documento_id"], "monto_rebaja_clp": 1000},
        )
        self.assertEqual(r_rut.status_code, 409)

        # NC que rebaja más stock del disponible -> 409 con rollback total (CxP y NC intactas)
        xml_nc = fs.envio_dte(fs.documento(folio="903", tipo=61, rut="76123456-0"))
        nc = self.admin.post("/hotel/productos/documentos/xml", json={"xml": xml_nc}).json()["documento"]
        r_stock = self.admin.post(
            f"/hotel/productos/documentos/{nc['documento_id']}/aplicar-nota-credito",
            headers=self.idem(),
            json={
                "factura_id": factura["documento_id"],
                "lineas_stock": [{"producto_id": prod_id, "cantidad": 999, "unidades_por_paquete": 1}],
                "monto_rebaja_clp": 5000,
            },
        )
        self.assertEqual(r_stock.status_code, 409)
        self.assertEqual(self.admin.get(f"/hotel/productos/documentos/{nc['documento_id']}").json()["estado"], "pendiente")
        self.assertEqual(self.catalogo()["Agua NC Test 500 ml"]["stock"], 48)

        # Recepción y caja no tienen acceso -> 403
        for rol in ("recepcion", "caja"):
            self.assertEqual(self.otros[rol].get("/hotel/productos/cuentas-por-pagar").status_code, 403)


if __name__ == "__main__":
    unittest.main()
