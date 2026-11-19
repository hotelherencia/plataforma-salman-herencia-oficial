"""Facturas de proveedores (2026-11-19): timbre PDF417 del SII en fotos,
lectura con IA enchufable (Gemini), envases por proveedor, pedidos en
borrador, buzón de intercambio (recepcion_dte) y la bandeja de revisión.
Nada toca el stock hasta que la administración confirma.

Sin red: la IA y los buzones son dobles de prueba. Imágenes y XML sintéticos.
"""
import email.message
import json
import unittest
from datetime import datetime, timezone
from unittest import mock

import psycopg

from servicio import correo
from servicio import facturas_proveedor as fp
from servicio import ted, unidades_paquete as up, vision
from servicio.tests import facturas_sinteticas as fs
from servicio.tests.test_importacion_productos import ImportacionHttpBase, URL_TEST


class TimbreTest(unittest.TestCase):
    def test_parsea_el_timbre_y_rechaza_lo_que_no_es(self):
        datos = ted.parsear_ted(fs.ted_xml(folio="000123", total=9990))
        self.assertEqual((datos["emisor_rut"], datos["tipo_dte"], datos["folio"], datos["monto_total_clp"]),
                         ("76123456-0", 33, "123", 9990))
        self.assertEqual(ted.parsear_ted(fs.ted_xml().encode("latin-1"))["fecha_emision"], "2026-11-18")
        for malo in ("hola", "<TED><DD><RE>x</RE></DD></TED>",
                     '<TED><DD><RE>&xxe;</RE><TD>33</TD><F>1</F></DD></TED>'):
            with self.assertRaises(ted.TimbreIlegible):
                ted.parsear_ted(malo)

    def test_lee_el_timbre_de_una_foto_inclinada_y_de_un_pdf(self):
        pagina = fs.pagina(folio="777")
        for rot in (0, 2, -3):
            with self.subTest(rotacion=rot):
                r = ted.leer_timbre(fs.jpeg(pagina, rot, 1.0, escala=2), "image/jpeg")
                self.assertIsNotNone(r)
                self.assertEqual(r["folio"], "777")
        self.assertEqual(ted.leer_timbre(fs.pdf(pagina), "application/pdf")["folio"], "777")

    def test_imagen_sin_timbre_o_corrupta_no_rompe(self):
        self.assertIsNone(ted.leer_timbre(fs.jpeg(fs.pagina(con_timbre=False)), "image/jpeg"))
        self.assertIsNone(ted.leer_timbre(b"\xff\xd8\xffbasura", "image/jpeg"))
        self.assertIsNone(ted.leer_timbre(b"%PDF-1.4 roto", "application/pdf"))


class EnvasesTest(unittest.TestCase):
    def test_unidades_por_envase_desde_el_texto(self):
        casos = {"Caja x 18": 18, "BEBIDA 350 ML X 12 UN": 12, "Pack de 6 cervezas": 6, "Display 24": 24,
                 "Galletas 12x30g": 12, "Leche x 6": 6, "Agua mineral 500 ml": None, "Jugo 1,5 lt": None,
                 "Queso 1 kg": None, "Torta 166und x 690": None, "": None}
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(up.unidades_por_paquete(texto), esperado)

    def test_nota_manuscrita_unidades_por_precio(self):
        self.assertEqual(up.leer_nota_cantidad("166und x 690"), {"unidades": 166, "precio_unitario": 690})
        self.assertEqual(up.leer_nota_cantidad("12 un x 1.250"), {"unidades": 12, "precio_unitario": 1250})
        self.assertIsNone(up.leer_nota_cantidad("entregar lunes"))

    def test_clave_de_item_por_codigo_o_descripcion(self):
        self.assertEqual(up.clave_item("AB-1", "x"), "cod:ab-1")
        self.assertEqual(up.clave_item(None, "  Café  Molido, 250g "), "txt:cafe molido 250g")


class GeminiFalso:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def __call__(self, url, cabeceras, cuerpo):
        self.llamadas.append((url, cabeceras, cuerpo))
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return {"candidates": [{"content": {"parts": [{"text": json.dumps(r)}]}}]}


EXTRACCION = {
    "tipo_documento": "factura", "emisor_rut": "76.123.456-0", "emisor_razon_social": "DISTRIBUIDORA PRUEBA SPA",
    "folio": "3797574", "fecha_emision": "2026-11-18", "monto_neto": 35970, "iva": 6834, "monto_total": 42804,
    "lineas": [
        {"codigo": "78016200", "descripcion": "AGUA MINERAL SIN GAS 500 ML CAJA X 24", "cantidad": 2, "unidad": "CJ",
         "precio_neto": 12000, "total_linea": 24000},
        {"codigo": None, "descripcion": "BEBIDA COLA LATA 350 ML X 6", "cantidad": 3, "unidad": "UN",
         "precio_neto": 3990, "total_linea": 11970},
    ],
}


class VisionTest(unittest.TestCase):
    def test_apagada_sin_clave_y_gemini_por_defecto_con_clave(self):
        self.assertIsNone(vision.proveedor_configurado({}))
        self.assertEqual(vision.estado({}), {"activa": False, "proveedor": None})
        p = vision.proveedor_configurado({"GEMINI_API_KEY": "k", "GEMINI_MODELOS_RESPALDO": "m2, m3"})
        self.assertEqual(p.modelos, ["gemini-3.5-flash-lite", "m2", "m3"])
        self.assertIsNone(vision.proveedor_configurado({"GEMINI_API_KEY": "k", "VISION_PROVEEDOR": "ninguno"}))
        self.assertEqual(vision.proveedor_configurado({"VISION_PROVEEDOR": "openai", "VISION_API_KEY": "k"}).nombre, "openai")

    def test_gemini_usa_cabecera_esquema_y_modelo_de_respaldo(self):
        post = GeminiFalso([vision.VisionFallida("tardó"), EXTRACCION])
        p = vision.ProveedorGemini("clave-secreta", "principal", ["respaldo"], post=post)
        datos = p.extraer(b"\xff\xd8\xffx", "image/jpeg")
        self.assertEqual(datos["folio"], "3797574")
        self.assertEqual(p.modelo_usado, "respaldo")
        url, cabeceras, cuerpo = post.llamadas[1]
        self.assertIn("models/respaldo:generateContent", url)
        self.assertNotIn("clave-secreta", url)  # la clave va en la cabecera, nunca en la URL
        self.assertEqual(cabeceras, {"x-goog-api-key": "clave-secreta"})
        self.assertEqual(cuerpo["generationConfig"]["responseMimeType"], "application/json")
        self.assertIn("lineas", cuerpo["generationConfig"]["responseSchema"]["properties"])

    def test_gemini_reintenta_una_vez_si_google_esta_sobrecargado(self):
        post = GeminiFalso([vision.VisionFallida("503", transitoria=True), EXTRACCION])
        p = vision.ProveedorGemini("k", "principal", post=post)
        p.espera_reintento = 0
        self.assertEqual(p.extraer(b"\xff\xd8\xffx", "image/jpeg")["folio"], "3797574")
        self.assertEqual([u for u, _, _ in post.llamadas], [post.llamadas[0][0]] * 2)
        post = GeminiFalso([vision.VisionFallida("400")])
        with self.assertRaises(vision.VisionFallida):
            vision.ProveedorGemini("k", "principal", post=post).extraer(b"x", "image/jpeg")
        self.assertEqual(len(post.llamadas), 1)  # un 400 no se reintenta

    def test_normaliza_sin_inventar_precios_y_valida_contra_el_timbre(self):
        datos = json.loads(json.dumps(EXTRACCION))
        datos["lineas"][1]["precio_neto"] = None
        datos["lineas"][1]["total_linea"] = None
        n = vision.normalizar(datos)
        self.assertEqual(n["documento"]["emisor_rut"], "76123456-0")
        self.assertIsNone(n["lineas"][1]["costo_unitario_clp"])  # nunca se inventa
        self.assertEqual(n["lineas"][0]["costo_unitario_clp"], 12000)
        timbre = {"monto_total_clp": 50000, "folio": "999", "emisor_rut": "76123456-0"}
        codigos = {d["codigo"] for d in vision.validar(n["documento"], n["lineas"], timbre)}
        self.assertTrue({"timbre_total", "timbre_folio", "sin_precio"} <= codigos)
        ok = vision.normalizar(EXTRACCION)
        self.assertEqual(vision.validar(ok["documento"], ok["lineas"], {"monto_total_clp": 42804, "folio": "3797574"}), [])
        mal = {**ok["documento"], "monto_neto_clp": 40000}
        self.assertIn("suma_lineas", {d["codigo"] for d in vision.validar(mal, ok["lineas"], None)})

    def test_numeros_chilenos(self):
        self.assertEqual(vision._numero("12.500"), 12500)
        self.assertEqual(vision._numero("$ 1.234,5"), 1234.5)
        self.assertEqual(vision._numero("0,5"), 0.5)
        self.assertIsNone(vision._numero("abc"))


class CorreoDteTest(unittest.TestCase):
    def test_solo_adjuntos_xml_de_tamano_razonable(self):
        m = email.message.EmailMessage()
        m["From"] = "Facturación <dte@proveedor.test>"
        m["Date"] = "Wed, 18 Nov 2026 10:00:00 +0000"
        m.set_content("adjunto factura")
        m.add_attachment(fs.envio_dte(fs.documento()).encode("latin-1"), maintype="application", subtype="xml",
                         filename="DTE_33_5001.xml")
        m.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf", filename="factura.pdf")
        m.add_attachment(b"<x/>" * (correo.MAX_ADJUNTO_DTE // 3), maintype="application", subtype="xml", filename="enorme.xml")
        adjuntos = correo.adjuntos_xml_de_mensaje(m.as_bytes(), "imap:1")
        self.assertEqual([a.nombre for a in adjuntos], ["DTE_33_5001.xml"])
        self.assertEqual(adjuntos[0].remitente, "dte@proveedor.test")

    def test_buzon_recepcion_se_valida(self):
        limpio, _ = correo.validar("recepcion_dte", "imap", {"host": "imap.hotel.test", "usuario": "dte@hotel.test"},
                                   {"clave": "x"}, {})
        self.assertEqual(limpio["carpeta_entrada"], "INBOX")
        with self.assertRaises(correo.CorreoInvalido):
            correo.validar("recepcion_dte", "smtp", {"host": "h"}, {"clave": "x"}, {})


class BuzonFalso:
    def __init__(self, adjuntos):
        self.adjuntos = adjuntos

    def adjuntos_xml_desde(self, desde):
        return self.adjuntos


class FacturasHttpTest(ImportacionHttpBase):
    def setUp(self):
        super().setUp()
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("TRUNCATE documentos_proveedor, equivalencias_proveedor, archivos_documentos, buzones_correo CASCADE")
            conexion.commit()
        self.sin_ia = mock.patch.object(vision, "proveedor_configurado", return_value=None)
        self.sin_ia.start()
        self.addCleanup(self.sin_ia.stop)

    def con_ia(self, respuesta):
        self.sin_ia.stop()
        p = vision.ProveedorGemini("k", post=GeminiFalso([respuesta] * 5))
        self.sin_ia = mock.patch.object(vision, "proveedor_configurado", return_value=p)
        self.sin_ia.start()

    def subir(self, contenido, tipo="image/jpeg", cliente=None):
        return (cliente or self.admin).post("/hotel/productos/documentos/archivo", content=contenido,
                                            headers={"Content-Type": tipo, "X-Nombre-Archivo": "factura.jpg"})

    def stock(self, nombre):
        return self.catalogo()[nombre]["stock"]

    # ---- foto sin IA
    def test_foto_sin_ia_queda_pendiente_identificada_por_el_timbre(self):
        foto = fs.jpeg(fs.pagina(folio="4401"), 2, 1.0, escala=2)
        r = self.subir(foto)
        self.assertEqual(r.status_code, 201, r.text)
        d = r.json()
        self.assertEqual((d["estado"], d["clase"], d["lectura"], d["folio"], d["emisor_rut"]),
                         ("pendiente", "factura", "timbre", "4401", "76123456-0"))
        self.assertIn("sin_lectura", {x["codigo"] for x in d["discrepancias"]})
        self.assertFalse(d["lectura_automatica"]["activa"])
        otra = self.subir(foto)
        self.assertEqual((otra.status_code, otra.json()["documento_id"], otra.json()["repetido"]), (200, d["documento_id"], True))
        # Otra foto del mismo documento (otro encuadre): el timbre la reconoce.
        tercera = self.subir(fs.jpeg(fs.pagina(folio="4401"), 0, 0.4, calidad=70))
        self.assertEqual(tercera.json()["documento_id"], d["documento_id"])
        archivo = self.admin.get(f"/hotel/productos/documentos/{d['documento_id']}/archivo")
        self.assertEqual(archivo.status_code, 200)
        self.assertEqual(archivo.headers["content-type"], "image/jpeg")
        self.assertEqual(archivo.headers["x-content-type-options"], "nosniff")
        self.assertIn("sandbox", archivo.headers["content-security-policy"])

    def test_archivos_invalidos(self):
        self.assertEqual(self.subir(b"hola", "text/plain").status_code, 422)
        self.assertEqual(self.subir(fs.pdf(fs.pagina()), "image/jpeg").status_code, 422)  # dice ser foto y es PDF
        self.assertEqual(self.subir(b"\xff\xd8\xff" + b"0" * (fp.MAX_ARCHIVO + 1)).status_code, 413)
        # Las demás rutas conservan el tope general de 256 KB.
        self.assertEqual(self.admin.post("/hotel/productos", content=b"x" * 300_000,
                                         headers={"Content-Type": "application/json"}).status_code, 413)
        self.assertEqual(self.subir(b"", "image/jpeg").status_code, 422)

    def test_completar_a_mano_y_cargar_con_envases(self):
        d = self.subir(fs.jpeg(fs.pagina(folio="4402"))).json()
        # Sin IA: la administración escribe las líneas mirando la foto.
        r = self.admin.put(f"/hotel/productos/documentos/{d['documento_id']}", json={
            "lineas": [{"codigo": "78016200", "nombre": "AGUA MINERAL 500 ML CAJA X 24", "cantidad": 2, "unidad": "CJ",
                        "costo_unitario_clp": 12000, "monto_neto_clp": 24000}],
            "monto_neto_clp": 24000})
        self.assertEqual(r.status_code, 200, r.text)
        linea = r.json()["lineas"][0]
        self.assertEqual((linea["unidades_por_paquete"], linea["origen_unidades"]), (24, "texto"))
        # El folio del timbre no se reescribe.
        self.assertEqual(self.admin.put(f"/hotel/productos/documentos/{d['documento_id']}", json={"folio": "1"}).status_code, 422)
        c = self.admin.post(f"/hotel/productos/documentos/{d['documento_id']}/confirmacion", headers=self.idem(), json={
            "lineas": [{"accion": "crear", "nombre": "Agua mineral 500 ml", "nombre_proveedor": linea["nombre"],
                        "codigo_proveedor": "78016200", "categoria": "minibar", "cantidad": 2, "unidades_por_paquete": 24,
                        "costo_unitario_clp": 12000, "precio_clp": 1500}]})
        self.assertEqual(c.status_code, 201, c.text)
        self.assertEqual(c.json()["unidades"], 48)
        self.assertEqual(c.json()["equivalencias_recordadas"], 1)
        producto = self.catalogo()["Agua mineral 500 ml"]
        self.assertEqual((producto["stock"], producto["costo_clp"]), (48, 500))  # costo por unidad
        self.assertEqual(self.admin.get(f"/hotel/productos/documentos/{d['documento_id']}").json()["estado"], "cargada")
        # La siguiente factura del mismo proveedor ya trae el producto y el envase.
        self.con_ia({**EXTRACCION, "folio": "4403"})
        d2 = self.subir(fs.jpeg(fs.pagina(folio="4403"))).json()
        l0 = d2["lineas"][0]
        self.assertEqual((l0["confianza"], l0["coincidencia"]["nombre"], l0["unidades_por_paquete"], l0["origen_unidades"]),
                         ("recordado", "Agua mineral 500 ml", 24, "recordado"))
        eqs = self.admin.get("/hotel/productos/equivalencias").json()["equivalencias"]
        self.assertEqual(len(eqs), 1)
        cambio = self.admin.put(f"/hotel/productos/equivalencias/{eqs[0]['equivalencia_id']}", json={"unidades_por_paquete": 12})
        self.assertEqual(cambio.json()["unidades_por_paquete"], 12)
        self.assertEqual(self.admin.delete(f"/hotel/productos/equivalencias/{eqs[0]['equivalencia_id']}").status_code, 200)

    def test_con_ia_lee_lineas_y_la_factura_no_se_carga_dos_veces(self):
        self.con_ia(EXTRACCION)
        d = self.subir(fs.jpeg(fs.pagina())).json()
        self.assertEqual((d["lectura"], len(d["lineas"]), d["monto_total_clp"]), ("ia", 2, 42804))
        self.assertEqual(d["discrepancias"], [])
        lineas = [{"accion": "crear", "nombre": l["nombre"][:60], "cantidad": l["cantidad"],
                   "unidades_por_paquete": l["unidades_por_paquete"], "costo_unitario_clp": l["costo_unitario_clp"],
                   "precio_clp": 1990} for l in d["lineas"]]
        url = f"/hotel/productos/documentos/{d['documento_id']}/confirmacion"
        self.assertEqual(self.admin.post(url, headers=self.idem(), json={"lineas": lineas}).status_code, 201)
        self.assertEqual(self.admin.post(url, headers=self.idem(), json={"lineas": lineas}).status_code, 409)
        # El mismo folio por XML tampoco vuelve a entrar.
        xml = fs.envio_dte(fs.documento(folio="3797574"))
        r = self.admin.post("/hotel/productos/documentos/xml", json={"xml": xml})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(r.json()["repetidos"]), 1)

    def test_diferencia_con_el_timbre_queda_marcada(self):
        self.con_ia({**EXTRACCION, "monto_total": 99999})
        d = self.subir(fs.jpeg(fs.pagina(folio="4404"))).json()
        self.assertIn("timbre_total", {x["codigo"] for x in d["discrepancias"]})

    def test_ia_caida_no_impide_la_carga_manual(self):
        self.sin_ia.stop()
        p = vision.ProveedorGemini("k", post=GeminiFalso([vision.VisionFallida("504")]))
        self.sin_ia = mock.patch.object(vision, "proveedor_configurado", return_value=p)
        self.sin_ia.start()
        d = self.subir(fs.jpeg(fs.pagina(folio="4405"))).json()
        self.assertEqual(d["folio"], "4405")
        self.assertIn("ia_fallo", {x["codigo"] for x in d["discrepancias"]})

    # ---- pedidos
    def test_pedido_queda_en_borrador_y_se_cierra_con_la_factura(self):
        self.con_ia({**EXTRACCION, "tipo_documento": "pedido", "folio": "21027"})
        pedido = self.subir(fs.jpeg(fs.pagina(con_timbre=False))).json()
        self.assertEqual((pedido["clase"], pedido["estado"], pedido["tipo_dte"]), ("pedido", "borrador", None))
        r = self.admin.post(f"/hotel/productos/documentos/{pedido['documento_id']}/confirmacion", headers=self.idem(),
                            json={"lineas": [{"accion": "crear", "nombre": "Agua", "cantidad": 1, "precio_clp": 100}]})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.stock_total(), 0)
        xml = fs.envio_dte(fs.documento(folio="6001", referencia="21027"))
        doc = self.admin.post("/hotel/productos/documentos/xml", json={"xml": xml}).json()["documento"]
        self.assertEqual(doc["pedido_sugerido"]["documento_id"], pedido["documento_id"])
        linea = doc["lineas"][0]
        c = self.admin.post(f"/hotel/productos/documentos/{doc['documento_id']}/confirmacion", headers=self.idem(), json={
            "pedido_id": pedido["documento_id"],
            "lineas": [{"accion": "crear", "nombre": "Agua 500 ml", "cantidad": linea["cantidad"],
                        "unidades_por_paquete": linea["unidades_por_paquete"], "costo_unitario_clp": linea["costo_unitario_clp"],
                        "precio_clp": 1200}]})
        self.assertEqual(c.status_code, 201, c.text)
        self.assertEqual(self.stock("Agua 500 ml"), 48)
        self.assertEqual(self.admin.get(f"/hotel/productos/documentos/{pedido['documento_id']}").json()["estado"], "facturado")

    def stock_total(self):
        return sum(p["stock"] or 0 for p in self.catalogo().values())

    # ---- XML / correo
    def test_envio_con_factura_y_nota_de_credito(self):
        xml = fs.envio_dte(fs.documento(folio="7001"), fs.documento(folio="88", tipo=61))
        r = self.admin.post("/hotel/productos/documentos/xml", json={"xml": xml})
        self.assertEqual(r.status_code, 201, r.text)
        clases = sorted(c["clase"] for c in r.json()["creados"])
        self.assertEqual(clases, ["factura", "nota_credito"])
        bandeja = self.admin.get("/hotel/productos/documentos").json()["documentos"]
        nota = next(d for d in bandeja if d["clase"] == "nota_credito")
        self.assertIn("nota_credito", {x["codigo"] for x in nota["discrepancias"]})
        c = self.admin.post(f"/hotel/productos/documentos/{nota['documento_id']}/confirmacion", headers=self.idem(),
                            json={"lineas": [{"accion": "omitir", "nombre": "xx"}]})
        self.assertEqual(c.status_code, 409)
        self.assertEqual(self.admin.post(f"/hotel/productos/documentos/{nota['documento_id']}/descarte").json()["estado"], "archivada")
        self.assertEqual(self.admin.post("/hotel/productos/documentos/xml", json={"xml": xml}).status_code, 200)
        dtd = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><DTE>&e;</DTE>'
        self.assertEqual(self.admin.post("/hotel/productos/documentos/xml", json={"xml": dtd}).status_code, 422)

    def test_buzon_de_intercambio_crea_pendientes_sin_tocar_stock(self):
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute(
                "INSERT INTO buzones_correo (id, empresa_id, etiqueta, proposito, proveedor, parametros, actualizado_por) "
                "VALUES ('BZN-dte1', 'EMP-SINTETICA-001', 'intercambio', 'recepcion_dte', 'imap', '{}', 'admin')")
            conexion.commit()
        ahora = datetime.now(timezone.utc)
        adjuntos = [
            correo.AdjuntoXml("imap:1", ahora, "dte@proveedor.test", "a.xml",
                              fs.envio_dte(fs.documento(folio="9001"), fs.documento(folio="9002")).encode("latin-1")),
            correo.AdjuntoXml("imap:2", ahora, "dte@proveedor.test", "acuse.xml",
                              b'<RespuestaDTE xmlns="http://www.sii.cl/SiiDte"><Resultado/></RespuestaDTE>'),
            correo.AdjuntoXml("imap:3", ahora, "x@y.test", "otro.xml", b"<no-cierra>"),
        ]
        fabrica = lambda fila: BuzonFalso(adjuntos)  # noqa: E731
        with psycopg.connect(URL_TEST) as conexion:
            r1 = correo.revisar_recepcion_dte(conexion, "EMP-SINTETICA-001", fabrica)
            r2 = correo.revisar_recepcion_dte(conexion, "EMP-SINTETICA-001", fabrica)
            conexion.commit()
            ultimo = conexion.execute("SELECT ultimo_resultado, ultimo_error FROM buzones_correo").fetchone()
        self.assertEqual((r1["documentos"], r1["errores"]), (2, 0))
        self.assertEqual((r2["documentos"], r2["repetidos"]), (0, 2))
        self.assertIsNone(ultimo[1])
        bandeja = self.admin.get("/hotel/productos/documentos").json()
        self.assertEqual(sorted(d["folio"] for d in bandeja["documentos"]), ["9001", "9002"])
        self.assertTrue(all(d["origen"] == "correo" and d["estado"] == "pendiente" for d in bandeja["documentos"]))
        self.assertTrue(bandeja["buzon_recepcion"])
        self.assertEqual(self.stock_total(), 0)

    def test_solo_la_administracion(self):
        for rol in ("recepcion", "caja"):
            cliente = self.otros[rol]
            self.assertEqual(cliente.get("/hotel/productos/documentos").status_code, 403)
            self.assertEqual(self.subir(fs.jpeg(fs.pagina()), cliente=cliente).status_code, 403)
            self.assertEqual(cliente.get("/hotel/productos/equivalencias").status_code, 403)
            self.assertEqual(cliente.post("/hotel/productos/recepcion-correo").status_code, 403)


if __name__ == "__main__":
    unittest.main()
