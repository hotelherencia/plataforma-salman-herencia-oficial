"""Carga amigable de productos (2026-11-19): factura XML del SII, planilla y
lector de códigos. Lectura segura del XML, emparejamiento con el catálogo,
idempotencia por factura (emisor + tipo + folio) y permisos. HTTP contra
PostgreSQL real, datos sintéticos.
"""
import os
import unittest
import uuid
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient

from servicio import importacion_productos as imp
from servicio import seguridad
from servicio.tests.aislamiento import exigir_base_libre
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
EMPRESA = "EMP-SINTETICA-001"
ADMIN = ("admin", "clave-admin-sintetica")
FACTURA = (Path(__file__).parent / "datos" / "factura_33_sintetica.xml").read_bytes().decode("iso-8859-1")


def factura(folio="1001", tipo="33", rut="76.123.456-0"):
    return FACTURA.replace("<Folio>1001</Folio>", f"<Folio>{folio}</Folio>").replace(
        "<TipoDTE>33</TipoDTE>", f"<TipoDTE>{tipo}</TipoDTE>").replace("76.123.456-0", rut)


class LecturaFacturaTest(unittest.TestCase):
    """Lectura pura del XML (sin base)."""

    def test_lee_emisor_folio_fecha_y_detalle(self):
        leido = imp.leer_factura_xml(FACTURA)
        d = leido["documento"]
        self.assertEqual((d["tipo_dte"], d["folio"], d["fecha_emision"]), (33, "1001", "2026-11-18"))
        self.assertEqual(d["emisor_rut"], "76123456-0")
        self.assertEqual(d["emisor_razon_social"], "DISTRIBUIDORA SINTÉTICA DE BEBIDAS SPA")
        self.assertEqual((d["monto_neto_clp"], d["iva_clp"], d["monto_total_clp"]), (39800, 7562, 47362))
        self.assertEqual(len(leido["lineas"]), 3)
        agua, cola, papas = leido["lineas"]
        self.assertEqual((agua["codigo"], agua["nombre"], agua["cantidad"], agua["unidad"], agua["costo_unitario_clp"]),
                         ("7801620001234", "Agua mineral sin gas 500 ml", 24, "UN", 650))
        # El costo sale de MontoItem / QtyItem: incluye el descuento de la línea.
        self.assertEqual(cola["costo_unitario_clp"], 833)
        self.assertIsNone(papas["codigo"])

    def test_sin_espacio_de_nombres_y_utf8_tambien(self):
        sin_ns = FACTURA.replace(' xmlns="http://www.sii.cl/SiiDte"', "").replace('encoding="ISO-8859-1"', 'encoding="UTF-8"')
        self.assertEqual(len(imp.leer_factura_xml(sin_ns)["lineas"]), 3)

    def test_envio_con_un_documento_se_acepta_y_con_dos_se_rechaza(self):
        cuerpo = FACTURA.split("?>", 1)[1]
        envio = f'<EnvioDTE xmlns="http://www.sii.cl/SiiDte"><SetDTE>{cuerpo}</SetDTE></EnvioDTE>'
        self.assertEqual(imp.leer_factura_xml(envio)["documento"]["folio"], "1001")
        doble = f'<EnvioDTE><SetDTE>{cuerpo}{cuerpo}</SetDTE></EnvioDTE>'
        with self.assertRaisesRegex(imp.FacturaInvalida, "2 documentos"):
            imp.leer_factura_xml(doble)

    def test_rechaza_entidades_y_doctype(self):
        bomba = ('<?xml version="1.0"?><!DOCTYPE lol [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;">]>'
                 "<DTE><Documento>&lol2;</Documento></DTE>")
        externa = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><DTE>&e;</DTE>'
        for texto in (bomba, externa, "<!doctype dte><DTE/>"):
            with self.assertRaisesRegex(imp.FacturaInvalida, "seguridad"):
                imp.leer_factura_xml(texto)

    def test_rechaza_tamano_excesivo_xml_roto_y_otros_tipos(self):
        with self.assertRaisesRegex(imp.FacturaInvalida, "demasiado grande"):
            imp.leer_factura_xml("<a>" + "x" * imp.MAX_XML_CARACTERES + "</a>")
        with self.assertRaisesRegex(imp.FacturaInvalida, "no es un XML válido"):
            imp.leer_factura_xml("<DTE><Documento>")
        with self.assertRaisesRegex(imp.FacturaInvalida, "tipo 33 o 34"):
            imp.leer_factura_xml(factura(tipo="39"))
        with self.assertRaisesRegex(imp.FacturaInvalida, "no parece una factura"):
            imp.leer_factura_xml("<Otra><Cosa/></Otra>")
        with self.assertRaisesRegex(imp.FacturaInvalida, "vacío"):
            imp.leer_factura_xml("   ")

    def test_factura_exenta_34(self):
        self.assertEqual(imp.leer_factura_xml(factura(tipo="34"))["documento"]["tipo_dte"], 34)

    def test_foto_queda_reservada_sin_proveedor(self):
        with self.assertRaises(imp.FuenteNoDisponible):
            imp.leer_fuente("foto", None, None)

    def test_normalizar_nombre_sin_tildes_ni_simbolos(self):
        self.assertEqual(imp.normalizar_nombre("  Café   Molido, 250g "), "cafe molido 250g")

    def test_parecido_exige_las_mismas_medidas(self):
        # Un formato distinto (500 ml vs 1500 ml, 350 vs 1,5 L) es otro producto: nunca se sugiere sumarlo.
        self.assertGreaterEqual(imp._parecido("papas fritas americanas 45g", "papas fritas 45 g"), imp.UMBRAL_PARECIDO)
        self.assertEqual(imp._parecido("agua mineral 500 ml", "agua mineral 1500 ml"), 0.0)
        self.assertEqual(imp._parecido("bebida cola 350 ml", "bebida cola 1 5 l"), 0.0)
        self.assertEqual(imp._parecido("cafe molido 250g", "cafe molido"), 0.0)


class ImportacionHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario=ADMIN[0], admin_clave=ADMIN[1],
        )
        cls.app = crear_app(configuracion=cls.config)

    def setUp(self):
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute(
                "TRUNCATE auditoria, claves_idempotencia, movimientos_stock, importaciones_productos, productos, "
                "sesiones, usuarios RESTART IDENTITY CASCADE"
            )
            seguridad.asegurar_admin_inicial(conexion, EMPRESA, ADMIN[0], ADMIN[1])
            conexion.commit()
        self.app.state.freno_logins = seguridad.FrenoDeLogins()
        self.admin = TestClient(self.app)
        self.assertEqual(self.admin.post("/sesion", json={"usuario": ADMIN[0], "clave": ADMIN[1]}).status_code, 200)
        self.otros = {}
        for nombre, rol in (("recep1", "recepcion"), ("caja1", "caja")):
            r = self.admin.post("/usuarios", json={"nombre": nombre, "rol": rol, "clave": f"clave-{nombre}-1"}, headers=self.idem())
            self.assertEqual(r.status_code, 201, r.text)
            cliente = TestClient(self.app)
            self.assertEqual(cliente.post("/sesion", json={"usuario": nombre, "clave": f"clave-{nombre}-1"}).status_code, 200)
            self.otros[rol] = cliente

    def idem(self):
        return {"Idempotency-Key": f"k-{uuid.uuid4().hex[:10]}"}

    def producto(self, nombre, precio=1500, stock=None, codigo=None):
        cuerpo = {"nombre": nombre, "categoria": "minibar", "precio_clp": precio}
        if stock is not None:
            cuerpo |= {"controla_stock": True, "stock": stock}
        if codigo:
            cuerpo["codigo"] = codigo
        r = self.admin.post("/hotel/productos", json=cuerpo, headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()

    def previa(self, xml=FACTURA, cliente=None):
        return (cliente or self.admin).post("/hotel/productos/importacion/vista-previa", json={"origen": "factura_xml", "xml": xml})

    def lineas_confirmadas(self, previa):
        lineas = []
        for l in previa["lineas"]:
            base = {"nombre": l["nombre"], "codigo": l["codigo"], "cantidad": int(l["cantidad"]),
                    "costo_unitario_clp": l["costo_unitario_clp"]}
            if l["coincidencia"]:
                lineas.append({**base, "accion": "sumar", "producto_id": l["coincidencia"]["producto_id"]})
            else:
                lineas.append({**base, "accion": "crear", "categoria": "minibar", "precio_clp": 1990})
        return lineas

    def catalogo(self):
        return {p["nombre"]: p for p in self.admin.get("/hotel/productos?inactivos=true").json()["productos"]}

    def test_vista_previa_empareja_por_codigo_nombre_y_parecido(self):
        self.producto("Agua sin gas", codigo="7801620001234", stock=2)
        self.producto("Bebida Cola Lata 350 ml", stock=0)
        self.producto("Papas fritas americanas 45g", stock=1)
        r = self.previa()
        self.assertEqual(r.status_code, 200, r.text)
        datos = r.json()
        self.assertIsNone(datos["ya_importada"])
        self.assertEqual(datos["documento"]["folio"], "1001")
        agua, cola, papas = datos["lineas"]
        self.assertEqual((agua["confianza"], agua["coincidencia"]["nombre"]), ("codigo", "Agua sin gas"))
        self.assertEqual((cola["confianza"], cola["coincidencia"]["nombre"]), ("nombre", "Bebida Cola Lata 350 ml"))
        self.assertEqual(papas["confianza"], "parecido")
        # La vista previa no escribe nada.
        self.assertEqual(self.catalogo()["Agua sin gas"]["stock"], 2)

    def test_confirmar_crea_suma_stock_y_registra_la_factura(self):
        self.producto("Agua sin gas", codigo="7801620001234", stock=2, precio=1500)
        previa = self.previa().json()
        lineas = self.lineas_confirmadas(previa)
        r = self.admin.post("/hotel/productos/importacion", json={"origen": "factura_xml", "xml": FACTURA, "lineas": lineas},
                            headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        res = r.json()
        self.assertEqual((res["creados"], res["actualizados"], res["unidades"]), (2, 1, 56))
        cat = self.catalogo()
        self.assertEqual(cat["Agua sin gas"]["stock"], 26)
        self.assertEqual(cat["Agua sin gas"]["costo_clp"], 650)
        self.assertEqual(cat["Agua sin gas"]["precio_clp"], 1500)  # el precio de venta no cambia solo
        self.assertEqual(cat["Bebida cola lata 350 ml"]["stock"], 12)
        self.assertEqual(cat["Bebida cola lata 350 ml"]["codigo"], "COLA-350")
        self.assertTrue(cat["Papas fritas corte americano 45 g"]["controla_stock"])
        movs = self.admin.get(f"/hotel/productos/{cat['Agua sin gas']['producto_id']}/movimientos").json()["movimientos"]
        self.assertTrue(movs[0]["motivo"].startswith("Factura N° 1001"), movs[0])
        hist = self.admin.get("/hotel/productos/importaciones").json()["importaciones"]
        self.assertEqual((hist[0]["folio"], hist[0]["unidades"], hist[0]["productos_nuevos"]), ("1001", 56, 2))
        with psycopg.connect(URL_TEST) as c:
            (n,) = c.execute("SELECT count(*) FROM movimientos_stock WHERE importacion_id = %s", (res["importacion_id"],)).fetchone()
            (aud,) = c.execute("SELECT count(*) FROM auditoria WHERE accion = 'productos_importacion'").fetchone()
        self.assertEqual((n, aud), (3, 1))

    def test_la_misma_factura_no_se_importa_dos_veces(self):
        lineas = self.lineas_confirmadas(self.previa().json())
        r1 = self.admin.post("/hotel/productos/importacion", json={"origen": "factura_xml", "xml": FACTURA, "lineas": lineas},
                             headers=self.idem())
        self.assertEqual(r1.status_code, 201, r1.text)
        previa = self.previa().json()
        self.assertEqual(previa["ya_importada"]["importacion_id"], r1.json()["importacion_id"])
        lineas2 = self.lineas_confirmadas(previa)
        r2 = self.admin.post("/hotel/productos/importacion", json={"origen": "factura_xml", "xml": FACTURA, "lineas": lineas2},
                             headers=self.idem())
        self.assertEqual(r2.status_code, 409, r2.text)
        self.assertIn("ya fue cargada", r2.json()["detail"])
        self.assertEqual(self.catalogo()["Bebida cola lata 350 ml"]["stock"], 12)  # no se sumó de nuevo
        # Otro folio del mismo emisor sí entra.
        otra = factura(folio="1002")
        r3 = self.admin.post("/hotel/productos/importacion",
                             json={"origen": "factura_xml", "xml": otra, "lineas": self.lineas_confirmadas(self.previa(otra).json())},
                             headers=self.idem())
        self.assertEqual(r3.status_code, 201, r3.text)
        self.assertEqual(self.catalogo()["Bebida cola lata 350 ml"]["stock"], 24)

    def test_reintento_con_la_misma_clave_no_duplica(self):
        lineas = self.lineas_confirmadas(self.previa().json())
        clave = self.idem()
        cuerpo = {"origen": "factura_xml", "xml": FACTURA, "lineas": lineas}
        r1 = self.admin.post("/hotel/productos/importacion", json=cuerpo, headers=clave)
        r2 = self.admin.post("/hotel/productos/importacion", json=cuerpo, headers=clave)
        self.assertEqual((r1.status_code, r2.status_code), (201, 201))
        self.assertEqual(r1.json()["importacion_id"], r2.json()["importacion_id"])
        self.assertEqual(self.catalogo()["Bebida cola lata 350 ml"]["stock"], 12)

    def test_emisor_y_folio_salen_del_xml_no_del_cliente(self):
        lineas = self.lineas_confirmadas(self.previa().json())
        r = self.admin.post("/hotel/productos/importacion",
                            json={"origen": "factura_xml", "xml": FACTURA, "lineas": lineas, "documento": {"folio": "9"}},
                            headers=self.idem())
        self.assertEqual(r.status_code, 422)  # campo extra rechazado
        r = self.admin.post("/hotel/productos/importacion", json={"origen": "factura_xml", "xml": "<a/>", "lineas": lineas},
                            headers=self.idem())
        self.assertEqual(r.status_code, 422)

    def test_todo_o_nada_si_una_linea_falla(self):
        self.producto("Bebida cola lata 350 ml", stock=0)
        lineas = [
            {"accion": "crear", "nombre": "Agua mineral sin gas 500 ml", "categoria": "minibar", "cantidad": 24, "precio_clp": 1500},
            {"accion": "crear", "nombre": "Bebida cola lata 350 ml", "categoria": "minibar", "cantidad": 12, "precio_clp": 1500},
        ]
        r = self.admin.post("/hotel/productos/importacion", json={"origen": "planilla", "lineas": lineas}, headers=self.idem())
        self.assertEqual(r.status_code, 409, r.text)
        self.assertIn("sumar a existente", r.json()["detail"])
        self.assertNotIn("Agua mineral sin gas 500 ml", self.catalogo())
        with psycopg.connect(URL_TEST) as c:
            (n,) = c.execute("SELECT count(*) FROM importaciones_productos").fetchone()
        self.assertEqual(n, 0)

    def test_crear_exige_precio_de_venta(self):
        r = self.admin.post("/hotel/productos/importacion", json={"origen": "planilla", "lineas": [
            {"accion": "crear", "nombre": "Maní salado", "cantidad": 3}]}, headers=self.idem())
        self.assertEqual(r.status_code, 409)
        self.assertIn("precio de venta", r.json()["detail"])

    def test_planilla_y_lector_usan_el_mismo_flujo(self):
        p = self.producto("Chocolate 30 g", stock=1, codigo="780000000017")
        previa = self.admin.post("/hotel/productos/importacion/vista-previa", json={"origen": "lector", "lineas": [
            {"codigo": "780000000017", "nombre": "780000000017", "cantidad": 3},
            {"codigo": "999", "nombre": "999", "cantidad": 1}]}).json()
        self.assertEqual(previa["lineas"][0]["coincidencia"]["producto_id"], p["producto_id"])
        self.assertIsNone(previa["lineas"][1]["coincidencia"])
        r = self.admin.post("/hotel/productos/importacion", json={"origen": "lector", "lineas": [
            {"accion": "sumar", "producto_id": p["producto_id"], "nombre": "Chocolate 30 g", "cantidad": 3},
            {"accion": "omitir", "nombre": "999", "cantidad": 1}]}, headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual((r.json()["unidades"], r.json()["omitidas"]), (3, 1))
        self.assertEqual(self.catalogo()["Chocolate 30 g"]["stock"], 4)
        # Búsqueda exacta por código (lector).
        encontrados = self.admin.get("/hotel/productos", params={"codigo": "780000000017"}).json()["productos"]
        self.assertEqual([x["nombre"] for x in encontrados], ["Chocolate 30 g"])

    def test_dos_lineas_nuevas_con_el_mismo_nombre_se_juntan(self):
        r = self.admin.post("/hotel/productos/importacion", json={"origen": "planilla", "lineas": [
            {"accion": "crear", "nombre": "Maní salado", "cantidad": 3, "precio_clp": 1200},
            {"accion": "crear", "nombre": "maní  salado", "cantidad": 2, "precio_clp": 1200}]}, headers=self.idem())
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self.catalogo()["Maní salado"]["stock"], 5)

    def test_codigo_repetido_al_crear_se_explica(self):
        self.producto("Agua sin gas", codigo="ABC-1")
        r = self.admin.post("/hotel/productos", json={"nombre": "Otra agua", "categoria": "minibar", "precio_clp": 900,
                                                      "codigo": "abc-1"}, headers=self.idem())
        self.assertEqual(r.status_code, 409)
        self.assertIn("código", r.json()["detail"])

    def test_solo_la_administracion_carga_productos(self):
        for rol, cliente in self.otros.items():
            self.assertEqual(self.previa(cliente=cliente).status_code, 403, rol)
            r = cliente.post("/hotel/productos/importacion", json={"origen": "planilla", "lineas": [
                {"accion": "crear", "nombre": "X producto", "cantidad": 1, "precio_clp": 100}]}, headers=self.idem())
            self.assertEqual(r.status_code, 403, rol)
            self.assertEqual(cliente.get("/hotel/productos/importaciones").status_code, 403, rol)
        sin_sesion = TestClient(self.app)
        self.assertEqual(self.previa(cliente=sin_sesion).status_code, 401)

    def test_errores_de_lectura_en_castellano_y_foto_no_disponible(self):
        r = self.previa(xml='<?xml version="1.0"?><!DOCTYPE a [<!ENTITY b "c">]><a>&b;</a>')
        self.assertEqual(r.status_code, 422)
        self.assertIn("seguridad", r.json()["detail"])
        r = self.admin.post("/hotel/productos/importacion/vista-previa", json={"origen": "foto"})
        self.assertEqual(r.status_code, 503)
        self.assertIn("inteligencia artificial", r.json()["detail"])
        r = self.admin.post("/hotel/productos/importacion", json={"origen": "planilla", "lineas": [
            {"accion": "omitir", "nombre": "Nada", "cantidad": 1}]}, headers=self.idem())
        self.assertEqual(r.status_code, 409)
        self.assertNotIn("Traceback", r.text)


if __name__ == "__main__":
    unittest.main()
