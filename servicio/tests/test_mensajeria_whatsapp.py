"""Puerto de entrada WhatsApp (spec 006, #324).

Ninguna prueba llama a Meta: el cuerpo se firma en el proceso con un secreto
de prueba y se entrega al webhook. Sin puerto configurado no se persiste nada.
"""
import hashlib
import hmac
import json

import psycopg

from servicio.mensajeria import PuertoWhatsapp
from servicio.tests.test_agente_servicio import URL_TEST, AgenteServicioBaseTest

SECRETO = "secreto-de-prueba"
TOKEN = "token-de-prueba"
NUMERO = "PHONE-PRUEBA-1"


def firmar(cuerpo: bytes, secreto: str = SECRETO) -> str:
    digest = hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def carga(mensaje_id: str, texto: str, remitente: str = "56900000001", numero: str = NUMERO) -> bytes:
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "field": "messages",
                "value": {
                    "metadata": {"phone_number_id": numero},
                    "messages": [{
                        "from": remitente,
                        "id": mensaje_id,
                        "type": "text",
                        "text": {"body": texto},
                    }],
                },
            }],
        }],
    }
    return json.dumps(payload, separators=(",", ":")).encode()


class WebhookWhatsappTest(AgenteServicioBaseTest):
    def setUp(self):
        super().setUp()
        self.app.state.mensajeria = None

    def activar(self):
        self.app.state.mensajeria = PuertoWhatsapp(SECRETO, TOKEN, NUMERO)

    def post(self, cuerpo: bytes, firma: str | None = None):
        headers = {"content-type": "application/json"}
        if firma is not None:
            headers["x-hub-signature-256"] = firma
        return self.cliente.post("/mensajeria/whatsapp/webhook", content=cuerpo, headers=headers)

    def consultas(self) -> list[tuple]:
        with psycopg.connect(URL_TEST) as conexion:
            return conexion.execute(
                "SELECT id, canal_origen, texto_redactado FROM consultas_agente ORDER BY recibida_en, id"
            ).fetchall()

    def test_sin_puerto_responde_503_y_no_persiste(self):
        cuerpo = carga("wamid.apagado", "hola, 2 personas")
        respuesta = self.post(cuerpo, firmar(cuerpo))
        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(respuesta.json()["detail"], "no configurado")
        verificacion = self.cliente.get(
            "/mensajeria/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": TOKEN, "hub.challenge": "123"},
        )
        self.assertEqual(verificacion.status_code, 503)
        self.assertEqual(self.consultas(), [])

    def test_firma_invalida_o_numero_ajeno_no_persiste(self):
        self.activar()
        cuerpo = carga("wamid.firma", "hola")
        firma = self.post(cuerpo, "sha256=00")
        self.assertEqual(firma.status_code, 403)
        ajeno = carga("wamid.ajeno", "hola", numero="OTRO-NUMERO")
        rechazado = self.post(ajeno, firmar(ajeno))
        self.assertEqual(rechazado.status_code, 403)
        self.assertEqual(self.consultas(), [])

    def test_el_token_de_verificacion_distinto_se_rechaza(self):
        self.activar()
        mal = self.cliente.get(
            "/mensajeria/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "999"},
        )
        self.assertEqual(mal.status_code, 403)
        bien = self.cliente.get(
            "/mensajeria/whatsapp/webhook",
            params={"hub.mode": "subscribe", "hub.verify_token": TOKEN, "hub.challenge": "999"},
        )
        self.assertEqual(bien.status_code, 200)
        self.assertEqual(bien.text, "999")

    def test_mensaje_valido_crea_una_consulta_y_el_reintento_no_duplica(self):
        self.activar()
        self.usar_guion([
            {"herramienta": "proponer_borrador",
             "argumentos": {"plantilla": "pedir_dato", "campos": {}, "saludo": "Hola"}},
        ])
        cuerpo = carga("wamid.uno", "mi fono es +56911111111, somos 2", remitente="56900000001")
        alta = self.post(cuerpo, firmar(cuerpo))
        self.assertEqual(alta.status_code, 200)
        consulta_id = alta.json()["consultas"][0]
        filas = self.consultas()
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0][0], consulta_id)
        self.assertEqual(filas[0][1], "whatsapp")
        self.assertNotIn("56911111111", filas[0][2])
        self.assertNotIn("56900000001", filas[0][2])
        self.assertIn("[teléfono]", filas[0][2])
        reintento = self.post(cuerpo, firmar(cuerpo))
        self.assertEqual(reintento.status_code, 200)
        self.assertEqual(reintento.json()["consultas"], [consulta_id])
        self.assertEqual(len(self.consultas()), 1)

    def test_el_mensaje_siguiente_ve_el_texto_anterior(self):
        self.activar()
        primero = carga("wamid.ctx1", "quiero una doble", remitente="56900000002")
        self.post(primero, firmar(primero))
        segundo = carga("wamid.ctx2", "somos 2", remitente="56900000002")
        self.post(segundo, firmar(segundo))
        filas = self.consultas()
        self.assertEqual(len(filas), 2)
        self.assertIn("quiero una doble", filas[1][2])
        self.assertIn("somos 2", filas[1][2])

    def test_aviso_de_entrega_no_crea_consulta(self):
        self.activar()
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "field": "messages",
                    "value": {
                        "metadata": {"phone_number_id": NUMERO},
                        "statuses": [{"id": "wamid.salida", "status": "delivered"}],
                    },
                }],
            }],
        }
        cuerpo = json.dumps(payload, separators=(",", ":")).encode()
        respuesta = self.post(cuerpo, firmar(cuerpo))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["consultas"], [])
        self.assertEqual(self.consultas(), [])

    def test_el_freno_por_remitente_no_persiste_el_exceso(self):
        self.activar()
        self.app.state.freno_solicitudes.max_por_minuto = 1
        uno = carga("wamid.freno1", "primera", remitente="56900000003")
        self.assertEqual(self.post(uno, firmar(uno)).status_code, 200)
        dos = carga("wamid.freno2", "segunda", remitente="56900000003")
        exceso = self.post(dos, firmar(dos))
        self.assertEqual(exceso.status_code, 429)
        self.assertEqual(len(self.consultas()), 1)
