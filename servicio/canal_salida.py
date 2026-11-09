"""Puerto de salida del agente N1 (spec 005, T060).

D-AGT-03 (qué canal: correo, WhatsApp, chat) sigue sin nombrar un adaptador.
Sin adaptador, `enviar` responde «canal no configurado» y el borrador queda
`pendiente_envio`. No hay llamadas a correo ni a Meta.
"""


class CanalNoConfigurado(Exception):
    """503 «canal no configurado»: el puerto no tiene adaptador."""


class SinCanal:
    """Puerto sin canal autorizado."""

    nombre = "sin_canal"

    def enviar(self, destino: dict, texto: str) -> None:
        raise CanalNoConfigurado("canal no configurado")
