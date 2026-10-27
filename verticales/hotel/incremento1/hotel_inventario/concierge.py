"""Concierge local: decide, deriva y deduplica, sin enviar mensajes.

El envío por WhatsApp es un puerto externo que este módulo no toca; las
respuestas son registros locales (derivaciones, borradores y contadores).
"""

from .dominio import RespuestaConcierge


class ConciergeLocal:
    def __init__(self, servicio) -> None:
        self._servicio = servicio
        self._atencion_humana: set[str] = set()
        self._hechos_notificados: set[str] = set()

    def atender(self, empresa_id: str, conversacion_id: str, mensaje: str) -> RespuestaConcierge:
        if conversacion_id in self._atencion_humana:
            return RespuestaConcierge(
                texto="la conversación está en atención humana; no se dispara ninguna acción automática",
                accion="ninguna",
                escalado=True,
            )
        texto = mensaje.lower()
        quiere_cancelar = "cancelar" in texto
        quiere_devolver = "devolver" in texto or "reembolso" in texto
        if quiere_cancelar and quiere_devolver:
            transferencia = self._servicio.derivar_a_recepcion(
                empresa_id, conversacion_id, "cancelación y devolución solicitadas"
            )
            self._atencion_humana.add(conversacion_id)
            return RespuestaConcierge(
                texto="preparo el contexto y escalo; no cancelo ni devuelvo",
                accion="escalado",
                escalado=True,
                transferencia_id=transferencia.id,
            )
        if quiere_cancelar or quiere_devolver:
            transferencia = self._servicio.derivar_a_recepcion(
                empresa_id, conversacion_id, "solicitud de cancelación"
            )
            self._atencion_humana.add(conversacion_id)
            return RespuestaConcierge(
                texto=(
                    "derivo a recepción con resumen mínimo y referencia; "
                    "no cancelo ni marco resuelto"
                ),
                accion="escalado",
                escalado=True,
                transferencia_id=transferencia.id,
            )
        return RespuestaConcierge(
            texto="consulta registrada; respondo con datos vigentes del sistema",
            accion="informar",
            escalado=False,
        )

    def notificar_hecho(self, empresa_id: str, hecho_id: str, link: str) -> RespuestaConcierge:
        if hecho_id in self._hechos_notificados:
            return RespuestaConcierge(
                texto="hecho ya notificado; no repito confirmación ni upsell",
                accion="ninguna",
                escalado=False,
                link=None,
            )
        self._hechos_notificados.add(hecho_id)
        return RespuestaConcierge(
            texto="notificación del hecho con link al flujo controlado",
            accion="notificar",
            escalado=False,
            link=link,
        )
