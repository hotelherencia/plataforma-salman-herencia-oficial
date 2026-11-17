"""Políticas del hotel (entrega 1A.3): única fuente editable por admin_hotel.

Horarios de llegada y salida, recargos, cancelación, no-show, depósito,
mínimo de noches, niños y cama adicional, mascotas, desayuno, estacionamiento,
medios de pago, registro de llegada/salida y FAQ. Los precios siguen
resolviéndose en servicio/precios.py (IVA incluido); este módulo aplica
encima los recargos de la política y entrega el desglose neto/IVA
(servicio/iva.py).

Los valores iniciales salen de lo ya publicado en la landing o de lo que
estaba en el código. Lo no ratificado queda `pendiente_confirmar` y no se
inventa ningún dato.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, time, timedelta
from typing import Any

import psycopg

from . import iva

CONFIRMADO = "confirmado"
PENDIENTE = "pendiente_confirmar"
NO_DEFINIDO = "no_definido"
CONFIRMACIONES = (CONFIRMADO, PENDIENTE, NO_DEFINIDO)

MODOS_RECARGO = ("monto_clp", "porcentaje_noche")
POR_RECARGO = ("hora", "noche", "estadia")
PENALIDADES = ("primera_noche", "porcentaje", "monto")

TEMAS_CONOCIMIENTO = (
    "horarios", "llegada_anticipada", "salida_tardia", "cancelacion", "no_show",
    "deposito", "minimo_noches", "ninos", "cama_adicional", "mascotas",
    "desayuno", "estacionamiento", "pagos", "registro", "faq",
)

# Texto que antes vivía hardcodeado en reservas.py. Se conserva como valor
# inicial del mantenedor, marcado pendiente de confirmar: la landing dice
# que las fuentes internas no coinciden.
TEXTO_CANCELACION_INICIAL = (
    "cancelación gratuita hasta 48 horas antes de la llegada; "
    "después se carga la primera noche"
)


def _bloque(confirmacion: str, **campos) -> dict:
    return {"confirmacion": confirmacion, **campos}


def _recargo(modo: str, valor: int, por: str) -> dict:
    return {"modo": modo, "valor": valor, "por": por}


# Hechos publicados (landing / llms-full.txt, revisión 2026-11-16) y lo que
# ya estaba en el código. Nada inventado: si no está confirmado, no_definido
# o pendiente_confirmar, sin cifras ni afirmaciones nuevas.
INICIAL: dict[str, Any] = {
    "llegada_salida": _bloque(
        PENDIENTE,
        # La web publica 14:00; un comentario en reservas.py hablaba de 15:00.
        # Se parte de lo publicado y se marca pendiente hasta que el hotel lo ratifique.
        hora_llegada_desde="14:00",
        hora_salida_hasta="12:00",
        nota_confirmacion=(
            "La web publica llegada desde las 14:00 y salida hasta las 12:00. "
            "En el código había un comentario de llegada a las 15:00. "
            "Confirmar la hora de llegada antes de automatizar cotizaciones."
        ),
        llegada_anticipada=_bloque(
            CONFIRMADO,
            permitida=True,
            hora_limite=None,
            recargo=_recargo("monto_clp", 10_000, "hora"),
            sujeto_a_disponibilidad=True,
            nota="Publicado: $10.000 por hora, IVA incluido, sujeto a disponibilidad.",
        ),
        salida_tardia=_bloque(
            CONFIRMADO,
            permitida=True,
            hora_limite=None,
            recargo=_recargo("monto_clp", 10_000, "hora"),
            sujeto_a_disponibilidad=True,
            nota="Publicado: $10.000 por hora, IVA incluido, sujeto a disponibilidad.",
        ),
    ),
    "cancelacion": _bloque(
        PENDIENTE,
        horas_antelacion_gratis=48,
        penalidad_tipo="primera_noche",
        penalidad_valor=None,
        texto_visible=TEXTO_CANCELACION_INICIAL,
        nota_confirmacion=(
            "Este texto estaba en el código de la oferta. La ficha pública "
            "indica que la política de cancelación y no-show no está confirmada "
            "(las fuentes internas no coinciden)."
        ),
    ),
    "no_show": _bloque(
        NO_DEFINIDO,
        penalidad_tipo=None,
        penalidad_valor=None,
        texto_visible=None,
        nota_confirmacion="No hay una política de no-show ratificada.",
    ),
    "deposito": _bloque(
        CONFIRMADO,
        exigido=False,
        porcentaje=None,
        monto_clp=None,
        excepcion_delegaciones_porcentaje=50,
        momento_saldo="llegada",
        nota=(
            "No se pide abono previo, salvo delegaciones (50 % de la estadía). "
            "El saldo se paga a la llegada; los clientes frecuentes pueden pagar "
            "a la salida y las empresas facturan a fin de mes."
        ),
    ),
    "minimo_noches": _bloque(NO_DEFINIDO, noches=None, nota_confirmacion="No está publicado un mínimo de noches."),
    "ninos_cama": _bloque(
        NO_DEFINIDO,
        edad_nino_hasta=None,
        recargo_nino=None,
        cama_adicional_permitida=None,
        recargo_cama_adicional=None,
        nota_confirmacion=(
            "No está confirmado el precio de persona extra, la política de niños "
            "ni el recargo por cama adicional."
        ),
    ),
    "mascotas": _bloque(
        NO_DEFINIDO,
        se_aceptan=None,
        recargo=None,
        nota_confirmacion="No está confirmado si se aceptan mascotas.",
    ),
    "desayuno": _bloque(
        CONFIRMADO,
        incluido=True,
        tipo="buffet",
        horario_desde=None,
        horario_hasta=None,
        nota="Desayuno buffet incluido (publicado). El horario del desayuno no está publicado.",
    ),
    "estacionamiento": _bloque(
        PENDIENTE,
        disponible=True,
        con_costo=None,
        recargo=None,
        nota_confirmacion=(
            "El estacionamiento aparece como servicio del hotel. "
            "No está confirmado si tiene costo."
        ),
    ),
    "medios_pago": _bloque(
        CONFIRMADO,
        medios=["efectivo", "tarjeta", "transferencia"],
        nota="Publicado en la web.",
    ),
    "registro_llegada": {
        "confirmacion": CONFIRMADO,
        "datos": [
            {
                "clave": "documento",
                "etiqueta": "Documento de identidad (RUT o pasaporte)",
                "exigido": True,
                "publico": True,
                "confirmacion": CONFIRMADO,
                "nota": "La plataforma exige el documento antes de registrar la llegada.",
            },
            {
                "clave": "patente",
                "etiqueta": "Patente del vehículo",
                "exigido": False,
                "publico": False,
                "confirmacion": NO_DEFINIDO,
                "nota": "No está definido si se pide la patente en el registro de llegada.",
            },
        ],
        "pasos": [
            {"orden": 1, "texto": "Recibir al huésped en recepción y confirmar la reserva."},
            {"orden": 2, "texto": "Registrar el documento de identidad si la reserva aún no lo trae."},
            {"orden": 3, "texto": "Cobrar el saldo de la estadía (salvo clientes frecuentes o empresas a fin de mes)."},
            {"orden": 4, "texto": "Registrar la llegada en la plataforma (la reserva pasa a en estadía)."},
        ],
        "nota": (
            "Pasos del proceso actual en la plataforma y de lo publicado sobre el pago. "
            "El administrador del hotel puede editarlos para que coincidan con la operación real."
        ),
    },
    "registro_salida": {
        "confirmacion": CONFIRMADO,
        "pasos": [
            {"orden": 1, "texto": "Revisar los cargos de la estadía y el saldo pendiente."},
            {"orden": 2, "texto": "Registrar el cobro del saldo, si lo hay."},
            {"orden": 3, "texto": "Registrar la salida en la plataforma (la reserva queda finalizada)."},
        ],
        "nota": (
            "Pasos del proceso actual en la plataforma. El administrador del hotel "
            "puede editarlos para que coincidan con la operación real."
        ),
    },
    "faq": [
        {"id": "FAQ-01", "pregunta": "¿Dónde se ubica Hotel Herencia en Chillán?",
         "respuesta": "Estamos en Calle Diego de Almagro 751, Chillán, a aproximadamente 1,5 a 1,7 km de la Plaza de Armas y a 2,8 km de la estación de trenes.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-02", "pregunta": "¿El hotel cuenta con estacionamiento?",
         "respuesta": "Sí. Hotel Herencia dispone de estacionamiento para facilitar la llegada y salida de huéspedes que viajan en auto. No está confirmado si tiene costo.",
         "publica": True, "confirmacion": PENDIENTE},
        {"id": "FAQ-03", "pregunta": "¿La estadía incluye desayuno?",
         "respuesta": "Sí. El hotel ofrece desayuno buffet incluido, junto con WiFi y aire acondicionado.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-04", "pregunta": "¿Qué tipos de habitaciones ofrece Hotel Herencia?",
         "respuesta": "El hotel tiene 17 habitaciones. En la web se muestran la Habitación Doble Pequeña, con dos camas individuales, y la Habitación con Cama Grande. Cada habitación tiene baño privado y recibe hasta 3 personas.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-05", "pregunta": "¿Cómo consultar disponibilidad o reservar?",
         "respuesta": "Puedes enviar tus fechas y el número de huéspedes por el formulario de la web, por teléfono o WhatsApp al +56 9 5649 1501, o en https://plataforma.hotelherencia.cl/reservar. Recepción revisa cada solicitud: enviar el formulario no confirma la estadía.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-06", "pregunta": "¿Qué hay cerca de Hotel Herencia?",
         "respuesta": "El hotel está a pasos de Avenida Argentina, a aproximadamente 1,5 a 1,7 km de la Plaza de Armas y a 2,8 km de la estación de trenes.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-07", "pregunta": "¿Qué servicios incluye Hotel Herencia?",
         "respuesta": "La estadía incluye desayuno buffet, WiFi, TV cable, aire acondicionado, baño privado y estacionamiento. La recepción atiende las 24 horas.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-08", "pregunta": "¿Puedo alojar con niños o en grupo?",
         "respuesta": "Cada habitación recibe hasta 3 personas. Si viajan 4 o más, recepción arma la estadía con varias habitaciones.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-09", "pregunta": "¿Es un hotel adecuado para viajes de trabajo?",
         "respuesta": "Sí. Las habitaciones están pensadas para estadías laborales o de descanso, con WiFi, aire acondicionado, desayuno y estacionamiento.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-10", "pregunta": "¿Enviar el formulario confirma la reserva?",
         "respuesta": "No. El formulario envía tu consulta o solicitud a recepción, que la revisa y te contacta. La estadía queda confirmada solo cuando recepción la confirma.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-11", "pregunta": "¿Cómo contacto a recepción de Hotel Herencia?",
         "respuesta": "Por teléfono o WhatsApp al +56 9 5649 1501, por Instagram (@hotelherencia) o con el formulario de contacto de la web.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-12", "pregunta": "¿A qué hora es la llegada y la salida?",
         "respuesta": "La llegada es a partir de las 14:00 y la salida hasta las 12:00. La llegada anticipada y la salida tardía tienen un cobro de $10.000 por hora, sujeto a disponibilidad. La hora de llegada está pendiente de confirmar (en un comentario interno aparecía 15:00).",
         "publica": True, "confirmacion": PENDIENTE},
        {"id": "FAQ-13", "pregunta": "¿Qué medios de pago aceptan?",
         "respuesta": "Efectivo, tarjeta y transferencia.",
         "publica": True, "confirmacion": CONFIRMADO},
        {"id": "FAQ-14", "pregunta": "¿Hay que pagar un abono para reservar?",
         "respuesta": "No se pide abono previo, salvo en reservas de delegaciones, que pagan el 50 % de la estadía. El saldo se paga a la llegada; los clientes frecuentes pueden pagar a la salida y las empresas facturan a fin de mes.",
         "publica": True, "confirmacion": CONFIRMADO},
    ],
}


class PoliticaInvalida(Exception):
    """400/422: el cuerpo no cumple el esquema de políticas."""

    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


def _hora(valor: Any, campo: str) -> str | None:
    if valor in (None, ""):
        return None
    if not isinstance(valor, str):
        raise PoliticaInvalida(f"{campo}: usa el formato HH:MM")
    try:
        partes = valor.strip().split(":")
        h, m = int(partes[0]), int(partes[1]) if len(partes) > 1 else 0
        if not (0 <= h <= 23 and 0 <= m <= 59) or len(partes) != 2:
            raise ValueError
        return f"{h:02d}:{m:02d}"
    except (TypeError, ValueError):
        raise PoliticaInvalida(f"{campo}: usa el formato HH:MM") from None


def parse_hora(valor: str | None) -> time | None:
    if not valor:
        return None
    h, m = valor.split(":")
    return time(int(h), int(m))


def _confirmacion(valor: Any, campo: str) -> str:
    if valor not in CONFIRMACIONES:
        raise PoliticaInvalida(f"{campo}: confirmacion debe ser confirmado, pendiente_confirmar o no_definido")
    return valor


def _entero(valor: Any, campo: str, minimo: int | None = 0, maximo: int | None = None, opcional: bool = True):
    if valor is None or valor == "":
        if opcional:
            return None
        raise PoliticaInvalida(f"{campo} es obligatorio")
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise PoliticaInvalida(f"{campo} debe ser un número entero")
    if minimo is not None and valor < minimo:
        raise PoliticaInvalida(f"{campo} debe ser al menos {minimo}")
    if maximo is not None and valor > maximo:
        raise PoliticaInvalida(f"{campo} no puede superar {maximo}")
    return valor


def _bool(valor: Any, campo: str):
    if valor is None:
        return None
    if not isinstance(valor, bool):
        raise PoliticaInvalida(f"{campo} debe ser sí o no")
    return valor


def _texto(valor: Any, campo: str, maximo: int = 2000, opcional: bool = True) -> str | None:
    if valor is None:
        if opcional:
            return None
        raise PoliticaInvalida(f"{campo} es obligatorio")
    if not isinstance(valor, str):
        raise PoliticaInvalida(f"{campo} debe ser texto")
    texto = valor.strip()
    if not texto:
        if opcional:
            return None
        raise PoliticaInvalida(f"{campo} es obligatorio")
    if len(texto) > maximo:
        raise PoliticaInvalida(f"{campo} supera {maximo} caracteres")
    return texto


def _validar_recargo(valor: Any, campo: str) -> dict | None:
    if valor is None:
        return None
    if not isinstance(valor, dict):
        raise PoliticaInvalida(f"{campo}: recargo inválido")
    modo = valor.get("modo")
    if modo not in MODOS_RECARGO:
        raise PoliticaInvalida(f"{campo}: modo de recargo debe ser monto_clp o porcentaje_noche")
    por = valor.get("por") or "hora"
    if por not in POR_RECARGO:
        raise PoliticaInvalida(f"{campo}: el recargo se aplica por hora, noche o estadía")
    monto = _entero(valor.get("valor"), f"{campo}.valor", minimo=0, maximo=100_000_000, opcional=False)
    if modo == "porcentaje_noche" and monto > 100:
        raise PoliticaInvalida(f"{campo}: el porcentaje no puede superar 100")
    return {"modo": modo, "valor": monto, "por": por}


def _validar_bloque_recargo(valor: Any, campo: str) -> dict:
    if not isinstance(valor, dict):
        valor = {}
    return {
        "confirmacion": _confirmacion(valor.get("confirmacion", NO_DEFINIDO), f"{campo}.confirmacion"),
        "permitida": _bool(valor.get("permitida"), f"{campo}.permitida"),
        "hora_limite": _hora(valor.get("hora_limite"), f"{campo}.hora_limite"),
        "recargo": _validar_recargo(valor.get("recargo"), f"{campo}.recargo"),
        "sujeto_a_disponibilidad": _bool(valor.get("sujeto_a_disponibilidad"), f"{campo}.sujeto_a_disponibilidad"),
        "nota": _texto(valor.get("nota"), f"{campo}.nota", 500),
        "nota_confirmacion": _texto(valor.get("nota_confirmacion"), f"{campo}.nota_confirmacion", 800),
    }


def validar_cuerpo(cuerpo: dict) -> dict:
    """Normaliza y valida el documento de políticas. Rechaza claves sueltas de más
    en recargos; el resto admite campos conocidos y conserva notas."""
    if not isinstance(cuerpo, dict):
        raise PoliticaInvalida("el cuerpo de las políticas es inválido")
    llegada = cuerpo.get("llegada_salida") or {}
    if not isinstance(llegada, dict):
        raise PoliticaInvalida("llegada_salida es inválida")
    cancelacion = cuerpo.get("cancelacion") or {}
    no_show = cuerpo.get("no_show") or {}
    deposito = cuerpo.get("deposito") or {}
    minimo = cuerpo.get("minimo_noches") or {}
    ninos = cuerpo.get("ninos_cama") or {}
    mascotas = cuerpo.get("mascotas") or {}
    desayuno = cuerpo.get("desayuno") or {}
    estacionamiento = cuerpo.get("estacionamiento") or {}
    pagos = cuerpo.get("medios_pago") or {}
    reg_l = cuerpo.get("registro_llegada") or {}
    reg_s = cuerpo.get("registro_salida") or {}

    penalidad = cancelacion.get("penalidad_tipo")
    if penalidad not in (None, *PENALIDADES):
        raise PoliticaInvalida("penalidad de cancelación desconocida")
    penalidad_ns = no_show.get("penalidad_tipo")
    if penalidad_ns not in (None, *PENALIDADES):
        raise PoliticaInvalida("penalidad de no-show desconocida")

    medios = pagos.get("medios") or []
    if not isinstance(medios, list) or any(not isinstance(m, str) or not m.strip() or len(m) > 40 for m in medios):
        raise PoliticaInvalida("medios de pago inválidos")

    datos = []
    for i, dato in enumerate(reg_l.get("datos") or []):
        if not isinstance(dato, dict):
            raise PoliticaInvalida("dato del registro de llegada inválido")
        clave = _texto(dato.get("clave"), f"registro_llegada.datos[{i}].clave", 40, opcional=False)
        datos.append({
            "clave": clave,
            "etiqueta": _texto(dato.get("etiqueta"), f"registro_llegada.datos[{i}].etiqueta", 120, opcional=False),
            "exigido": bool(dato.get("exigido")),
            "publico": bool(dato.get("publico")),
            "confirmacion": _confirmacion(dato.get("confirmacion", NO_DEFINIDO), f"registro_llegada.datos[{i}]"),
            "nota": _texto(dato.get("nota"), f"registro_llegada.datos[{i}].nota", 400),
        })

    def _pasos(lista, campo):
        salida = []
        for i, paso in enumerate(lista or []):
            if not isinstance(paso, dict):
                raise PoliticaInvalida(f"{campo}[{i}] inválido")
            salida.append({
                "orden": _entero(paso.get("orden"), f"{campo}[{i}].orden", minimo=1, maximo=50, opcional=False),
                "texto": _texto(paso.get("texto"), f"{campo}[{i}].texto", 400, opcional=False),
            })
        return sorted(salida, key=lambda p: p["orden"])

    faq = []
    for i, item in enumerate(cuerpo.get("faq") or []):
        if not isinstance(item, dict):
            raise PoliticaInvalida(f"faq[{i}] inválida")
        faq.append({
            "id": _texto(item.get("id") or f"FAQ-{i+1:02d}", f"faq[{i}].id", 40, opcional=False),
            "pregunta": _texto(item.get("pregunta"), f"faq[{i}].pregunta", 300, opcional=False),
            "respuesta": _texto(item.get("respuesta"), f"faq[{i}].respuesta", 2000, opcional=False),
            "publica": bool(item.get("publica", True)),
            "confirmacion": _confirmacion(item.get("confirmacion", CONFIRMADO), f"faq[{i}].confirmacion"),
        })

    return {
        "llegada_salida": {
            "confirmacion": _confirmacion(llegada.get("confirmacion", PENDIENTE), "llegada_salida.confirmacion"),
            "hora_llegada_desde": _hora(llegada.get("hora_llegada_desde"), "hora_llegada_desde"),
            "hora_salida_hasta": _hora(llegada.get("hora_salida_hasta"), "hora_salida_hasta"),
            "nota_confirmacion": _texto(llegada.get("nota_confirmacion"), "llegada_salida.nota_confirmacion", 800),
            "llegada_anticipada": _validar_bloque_recargo(llegada.get("llegada_anticipada"), "llegada_anticipada"),
            "salida_tardia": _validar_bloque_recargo(llegada.get("salida_tardia"), "salida_tardia"),
        },
        "cancelacion": {
            "confirmacion": _confirmacion(cancelacion.get("confirmacion", PENDIENTE), "cancelacion.confirmacion"),
            "horas_antelacion_gratis": _entero(cancelacion.get("horas_antelacion_gratis"), "horas_antelacion_gratis", 0, 24 * 30),
            "penalidad_tipo": penalidad,
            "penalidad_valor": _entero(cancelacion.get("penalidad_valor"), "cancelacion.penalidad_valor", 0, 100_000_000),
            "texto_visible": _texto(cancelacion.get("texto_visible"), "cancelacion.texto_visible", 800),
            "nota_confirmacion": _texto(cancelacion.get("nota_confirmacion"), "cancelacion.nota_confirmacion", 800),
        },
        "no_show": {
            "confirmacion": _confirmacion(no_show.get("confirmacion", NO_DEFINIDO), "no_show.confirmacion"),
            "penalidad_tipo": penalidad_ns,
            "penalidad_valor": _entero(no_show.get("penalidad_valor"), "no_show.penalidad_valor", 0, 100_000_000),
            "texto_visible": _texto(no_show.get("texto_visible"), "no_show.texto_visible", 800),
            "nota_confirmacion": _texto(no_show.get("nota_confirmacion"), "no_show.nota_confirmacion", 800),
        },
        "deposito": {
            "confirmacion": _confirmacion(deposito.get("confirmacion", CONFIRMADO), "deposito.confirmacion"),
            "exigido": _bool(deposito.get("exigido"), "deposito.exigido"),
            "porcentaje": _entero(deposito.get("porcentaje"), "deposito.porcentaje", 0, 100),
            "monto_clp": _entero(deposito.get("monto_clp"), "deposito.monto_clp", 0, 100_000_000),
            "excepcion_delegaciones_porcentaje": _entero(
                deposito.get("excepcion_delegaciones_porcentaje"), "delegaciones", 0, 100
            ),
            "momento_saldo": _texto(deposito.get("momento_saldo"), "deposito.momento_saldo", 40) or "llegada",
            "nota": _texto(deposito.get("nota"), "deposito.nota", 800),
        },
        "minimo_noches": {
            "confirmacion": _confirmacion(minimo.get("confirmacion", NO_DEFINIDO), "minimo_noches.confirmacion"),
            "noches": _entero(minimo.get("noches"), "minimo_noches.noches", 1, 30),
            "nota_confirmacion": _texto(minimo.get("nota_confirmacion"), "minimo_noches.nota_confirmacion", 800),
        },
        "ninos_cama": {
            "confirmacion": _confirmacion(ninos.get("confirmacion", NO_DEFINIDO), "ninos_cama.confirmacion"),
            "edad_nino_hasta": _entero(ninos.get("edad_nino_hasta"), "edad_nino_hasta", 0, 17),
            "recargo_nino": _validar_recargo(ninos.get("recargo_nino"), "recargo_nino"),
            "cama_adicional_permitida": _bool(ninos.get("cama_adicional_permitida"), "cama_adicional_permitida"),
            "recargo_cama_adicional": _validar_recargo(ninos.get("recargo_cama_adicional"), "recargo_cama_adicional"),
            "nota_confirmacion": _texto(ninos.get("nota_confirmacion"), "ninos_cama.nota_confirmacion", 800),
        },
        "mascotas": {
            "confirmacion": _confirmacion(mascotas.get("confirmacion", NO_DEFINIDO), "mascotas.confirmacion"),
            "se_aceptan": _bool(mascotas.get("se_aceptan"), "mascotas.se_aceptan"),
            "recargo": _validar_recargo(mascotas.get("recargo"), "mascotas.recargo"),
            "nota_confirmacion": _texto(mascotas.get("nota_confirmacion"), "mascotas.nota_confirmacion", 800),
        },
        "desayuno": {
            "confirmacion": _confirmacion(desayuno.get("confirmacion", CONFIRMADO), "desayuno.confirmacion"),
            "incluido": _bool(desayuno.get("incluido"), "desayuno.incluido"),
            "tipo": _texto(desayuno.get("tipo"), "desayuno.tipo", 40),
            "horario_desde": _hora(desayuno.get("horario_desde"), "desayuno.horario_desde"),
            "horario_hasta": _hora(desayuno.get("horario_hasta"), "desayuno.horario_hasta"),
            "nota": _texto(desayuno.get("nota"), "desayuno.nota", 800),
        },
        "estacionamiento": {
            "confirmacion": _confirmacion(estacionamiento.get("confirmacion", PENDIENTE), "estacionamiento.confirmacion"),
            "disponible": _bool(estacionamiento.get("disponible"), "estacionamiento.disponible"),
            "con_costo": _bool(estacionamiento.get("con_costo"), "estacionamiento.con_costo"),
            "recargo": _validar_recargo(estacionamiento.get("recargo"), "estacionamiento.recargo"),
            "nota_confirmacion": _texto(estacionamiento.get("nota_confirmacion"), "estacionamiento.nota_confirmacion", 800),
        },
        "medios_pago": {
            "confirmacion": _confirmacion(pagos.get("confirmacion", CONFIRMADO), "medios_pago.confirmacion"),
            "medios": [m.strip() for m in medios],
            "nota": _texto(pagos.get("nota"), "medios_pago.nota", 400),
        },
        "registro_llegada": {
            "confirmacion": _confirmacion(reg_l.get("confirmacion", CONFIRMADO), "registro_llegada.confirmacion"),
            "datos": datos,
            "pasos": _pasos(reg_l.get("pasos"), "registro_llegada.pasos"),
            "nota": _texto(reg_l.get("nota"), "registro_llegada.nota", 800),
        },
        "registro_salida": {
            "confirmacion": _confirmacion(reg_s.get("confirmacion", CONFIRMADO), "registro_salida.confirmacion"),
            "pasos": _pasos(reg_s.get("pasos"), "registro_salida.pasos"),
            "nota": _texto(reg_s.get("nota"), "registro_salida.nota", 800),
        },
        "faq": faq,
    }


def texto_cancelacion(cuerpo: dict) -> str:
    """Texto visible de cancelación: el del mantenedor, o uno compuesto si hay estructura."""
    bloque = (cuerpo or {}).get("cancelacion") or {}
    if bloque.get("texto_visible"):
        return bloque["texto_visible"]
    horas = bloque.get("horas_antelacion_gratis")
    tipo = bloque.get("penalidad_tipo")
    if horas is None and not tipo:
        return "La política de cancelación se confirma en recepción."
    partes = []
    if horas is not None:
        partes.append(f"cancelación gratuita hasta {horas} horas antes de la llegada")
    if tipo == "primera_noche":
        partes.append("después se carga la primera noche")
    elif tipo == "porcentaje" and bloque.get("penalidad_valor") is not None:
        partes.append(f"después se carga el {bloque['penalidad_valor']} %")
    elif tipo == "monto" and bloque.get("penalidad_valor") is not None:
        partes.append(f"después se carga ${bloque['penalidad_valor']:,}".replace(",", "."))
    return "; ".join(partes) if partes else "La política de cancelación se confirma en recepción."


def inicial() -> dict:
    return validar_cuerpo(copy.deepcopy(INICIAL))


def de(conexion: psycopg.Connection, empresa_id: str) -> dict:
    """Políticas de la empresa; si aún no hay fila, los valores iniciales (sin persistir)."""
    fila = conexion.execute(
        "SELECT cuerpo, version, actualizada_en, actualizada_por FROM politicas_hotel WHERE empresa_id = %s",
        (empresa_id,),
    ).fetchone()
    if fila is None:
        return {
            "empresa_id": empresa_id,
            "cuerpo": inicial(),
            "version": 0,
            "actualizada_en": None,
            "actualizada_por": None,
            "materializada": False,
        }
    return {
        "empresa_id": empresa_id,
        "cuerpo": validar_cuerpo(fila[0]),
        "version": fila[1],
        "actualizada_en": fila[2].isoformat() if fila[2] else None,
        "actualizada_por": fila[3],
        "materializada": True,
    }


def guardar(conexion: psycopg.Connection, empresa_id: str, cuerpo: dict, actor: str) -> dict:
    normalizado = validar_cuerpo(cuerpo)
    actual = de(conexion, empresa_id)
    version = (actual["version"] or 0) + 1
    conexion.execute(
        "INSERT INTO politicas_hotel (empresa_id, cuerpo, version, actualizada_por) "
        "VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (empresa_id) DO UPDATE SET cuerpo = EXCLUDED.cuerpo, "
        "version = EXCLUDED.version, actualizada_en = clock_timestamp(), "
        "actualizada_por = EXCLUDED.actualizada_por",
        (empresa_id, psycopg.types.json.Json(normalizado), version, actor),
    )
    return de(conexion, empresa_id)


# Campos que el visitante y el agente pueden ver. El registro interno
# (pasos de personal, datos no públicos) queda fuera.
_CAMPOS_PUBLICOS = (
    "llegada_salida", "cancelacion", "no_show", "deposito", "minimo_noches",
    "ninos_cama", "mascotas", "desayuno", "estacionamiento", "medios_pago",
)


def vista_publica(documento: dict) -> dict:
    cuerpo = documento["cuerpo"]
    publico = {clave: copy.deepcopy(cuerpo[clave]) for clave in _CAMPOS_PUBLICOS}
    publico["faq"] = [item for item in cuerpo.get("faq") or [] if item.get("publica")]
    publico["registro_llegada"] = {
        "datos": [
            d for d in (cuerpo.get("registro_llegada") or {}).get("datos") or []
            if d.get("publico")
        ],
    }
    return {
        "empresa_id": documento["empresa_id"],
        "version": documento["version"],
        "actualizada_en": documento["actualizada_en"],
        "politicas": publico,
        "texto_cancelacion": texto_cancelacion(cuerpo),
        "pendientes": pendientes(cuerpo),
    }


def vista_interna(documento: dict) -> dict:
    return {
        **documento,
        "texto_cancelacion": texto_cancelacion(documento["cuerpo"]),
        "pendientes": pendientes(documento["cuerpo"]),
    }


def pendientes(cuerpo: dict) -> list[dict]:
    """Bloques pendientes de confirmar o no definidos, para resaltarlos en la UI."""
    hallazgos: list[dict] = []

    def recorrer(nodo, ruta):
        if isinstance(nodo, dict):
            conf = nodo.get("confirmacion")
            if conf in (PENDIENTE, NO_DEFINIDO):
                hallazgos.append({
                    "ruta": ruta,
                    "confirmacion": conf,
                    "nota": nodo.get("nota_confirmacion") or nodo.get("nota"),
                })
            for clave, valor in nodo.items():
                if clave == "confirmacion":
                    continue
                recorrer(valor, f"{ruta}.{clave}" if ruta else clave)
        elif isinstance(nodo, list):
            for i, item in enumerate(nodo):
                ident = item.get("id") or item.get("clave") or item.get("orden") or i if isinstance(item, dict) else i
                recorrer(item, f"{ruta}[{ident}]")

    recorrer(cuerpo, "")
    return hallazgos


def _horas_iniciadas(solicitada: time, oficial: time, anticipada: bool) -> int:
    base = date(2000, 1, 1)
    delta = (datetime.combine(base, oficial) - datetime.combine(base, solicitada)) if anticipada else (
        datetime.combine(base, solicitada) - datetime.combine(base, oficial)
    )
    segundos = delta.total_seconds()
    if segundos <= 0:
        return 0
    return int((segundos + 3599) // 3600)


def monto_recargo(regla: dict | None, tarifa_noche: int | None, unidades: int) -> int:
    """Monto CON IVA. `unidades` son horas, noches o 1 (estadía) según la regla."""
    if not regla or unidades <= 0:
        return 0
    if regla["por"] == "estadia":
        unidades = 1
    if regla["modo"] == "monto_clp":
        return int(regla["valor"]) * unidades
    if tarifa_noche is None:
        return 0
    por_unidad = (tarifa_noche * int(regla["valor"]) + 50) // 100
    return por_unidad * unidades


def _nota_recargo(bloque: dict, concepto: str) -> dict | None:
    if bloque.get("permitida") is False:
        return {"concepto": concepto, "motivo": "no_permitida"}
    if bloque.get("confirmacion") == NO_DEFINIDO or (
        bloque.get("permitida") and not bloque.get("recargo") and bloque.get("confirmacion") != CONFIRMADO
    ):
        return {"concepto": concepto, "motivo": "pendiente_de_confirmar"}
    return None


def calcular_recargos(cuerpo: dict, tarifa_noche: int | None, noches: int, extras: dict | None) -> dict:
    """Recargos y validaciones de una estadía a partir de la política vigente.

    `extras` admite hora_llegada, hora_salida (HH:MM), cama_adicional (bool),
    ninos (int) y mascotas (bool). No inventa montos si la regla no está definida.
    """
    extras = extras or {}
    llegada = cuerpo.get("llegada_salida") or {}
    recargos: list[dict] = []
    avisos: list[dict] = []

    hora_llegada = parse_hora(_hora(extras.get("hora_llegada"), "hora_llegada") if extras.get("hora_llegada") else None)
    hora_salida = parse_hora(_hora(extras.get("hora_salida"), "hora_salida") if extras.get("hora_salida") else None)
    oficial_l = parse_hora(llegada.get("hora_llegada_desde"))
    oficial_s = parse_hora(llegada.get("hora_salida_hasta"))

    anticipada = llegada.get("llegada_anticipada") or {}
    if hora_llegada and oficial_l:
        horas = _horas_iniciadas(hora_llegada, oficial_l, anticipada=True)
        limite = parse_hora(anticipada.get("hora_limite"))
        if limite and hora_llegada < limite:
            avisos.append({"concepto": "llegada_anticipada", "motivo": "antes_de_hora_limite"})
            horas = 0
        if horas:
            if anticipada.get("permitida") and anticipada.get("recargo"):
                recargos.append({
                    "concepto": "llegada_anticipada",
                    "horas": horas,
                    "monto_clp": monto_recargo(anticipada["recargo"], tarifa_noche, horas),
                    "detalle": f"Llegada anticipada ({horas} h)",
                })
            else:
                aviso = _nota_recargo(anticipada, "llegada_anticipada")
                if aviso:
                    avisos.append(aviso)
    tardia = llegada.get("salida_tardia") or {}
    if hora_salida and oficial_s:
        horas = _horas_iniciadas(hora_salida, oficial_s, anticipada=False)
        limite = parse_hora(tardia.get("hora_limite"))
        if limite and hora_salida > limite:
            avisos.append({"concepto": "salida_tardia", "motivo": "despues_de_hora_limite"})
            horas = 0
        if horas:
            if tardia.get("permitida") and tardia.get("recargo"):
                recargos.append({
                    "concepto": "salida_tardia",
                    "horas": horas,
                    "monto_clp": monto_recargo(tardia["recargo"], tarifa_noche, horas),
                    "detalle": f"Salida tardía ({horas} h)",
                })
            else:
                aviso = _nota_recargo(tardia, "salida_tardia")
                if aviso:
                    avisos.append(aviso)

    ninos_cama = cuerpo.get("ninos_cama") or {}
    if extras.get("cama_adicional"):
        if ninos_cama.get("cama_adicional_permitida") is False:
            avisos.append({"concepto": "cama_adicional", "motivo": "no_permitida"})
        elif ninos_cama.get("recargo_cama_adicional"):
            unidades = noches if ninos_cama["recargo_cama_adicional"]["por"] == "noche" else 1
            recargos.append({
                "concepto": "cama_adicional",
                "horas": None,
                "monto_clp": monto_recargo(ninos_cama["recargo_cama_adicional"], tarifa_noche, unidades),
                "detalle": "Cama adicional",
            })
        else:
            avisos.append({"concepto": "cama_adicional", "motivo": "pendiente_de_confirmar"})
    if extras.get("ninos"):
        if ninos_cama.get("recargo_nino"):
            unidades = noches if ninos_cama["recargo_nino"]["por"] == "noche" else 1
            recargos.append({
                "concepto": "ninos",
                "horas": None,
                "monto_clp": monto_recargo(ninos_cama["recargo_nino"], tarifa_noche, unidades),
                "detalle": "Recargo por niño",
            })
        elif ninos_cama.get("confirmacion") != CONFIRMADO:
            avisos.append({"concepto": "ninos", "motivo": "pendiente_de_confirmar"})

    if extras.get("mascotas"):
        mascotas = cuerpo.get("mascotas") or {}
        if mascotas.get("se_aceptan") is False:
            avisos.append({"concepto": "mascotas", "motivo": "no_permitida"})
        elif mascotas.get("recargo"):
            unidades = noches if mascotas["recargo"]["por"] == "noche" else 1
            recargos.append({
                "concepto": "mascotas",
                "horas": None,
                "monto_clp": monto_recargo(mascotas["recargo"], tarifa_noche, unidades),
                "detalle": "Recargo por mascota",
            })
        else:
            avisos.append({"concepto": "mascotas", "motivo": "pendiente_de_confirmar"})

    minimo = cuerpo.get("minimo_noches") or {}
    minimo_noches = minimo.get("noches") if minimo.get("confirmacion") != NO_DEFINIDO else None
    cumple_minimo = True if minimo_noches is None else noches >= minimo_noches

    total_recargos = sum(r["monto_clp"] for r in recargos)
    return {
        "recargos": recargos,
        "total_recargos_clp": total_recargos,
        "avisos": avisos,
        "minimo_noches": minimo_noches,
        "cumple_minimo": cumple_minimo,
        "hora_llegada": extras.get("hora_llegada"),
        "hora_salida": extras.get("hora_salida"),
    }


def enriquecer_item(item: dict, cuerpo: dict, extras: dict | None, tasa, noches: int) -> dict:
    """Añade recargos, desglose IVA y la política de cancelación vigente al ítem de oferta."""
    calc = calcular_recargos(cuerpo, item.get("tarifa_noche_clp"), noches, extras)
    subtotal = item["total_clp"]
    total = subtotal + calc["total_recargos_clp"]
    item = dict(item)
    item["subtotal_noches_clp"] = subtotal
    item["recargos"] = calc["recargos"]
    item["total_recargos_clp"] = calc["total_recargos_clp"]
    item["total_clp"] = total
    item["desglose"] = iva.desglose(total, tasa)
    item["desglose_noches"] = iva.desglose(subtotal, tasa)
    item["politica_cancelacion"] = texto_cancelacion(cuerpo)
    item["cancelacion_confirmacion"] = (cuerpo.get("cancelacion") or {}).get("confirmacion")
    item["cumple_minimo"] = calc["cumple_minimo"]
    item["minimo_noches"] = calc["minimo_noches"]
    item["avisos_politica"] = calc["avisos"]
    item["reservable"] = calc["cumple_minimo"]
    return item


def snapshot_para_reserva(cuerpo: dict, item: dict | None = None) -> dict:
    """Lo que se congela en la reserva: cancelación, horarios y recargos aplicados."""
    llegada = cuerpo.get("llegada_salida") or {}
    return {
        "texto_cancelacion": texto_cancelacion(cuerpo),
        "cancelacion": copy.deepcopy(cuerpo.get("cancelacion") or {}),
        "no_show": copy.deepcopy(cuerpo.get("no_show") or {}),
        "hora_llegada_desde": llegada.get("hora_llegada_desde"),
        "hora_salida_hasta": llegada.get("hora_salida_hasta"),
        "recargos": (item or {}).get("recargos") or [],
        "total_recargos_clp": (item or {}).get("total_recargos_clp") or 0,
    }


def conocimiento(cuerpo: dict, tema: str | None = None) -> dict:
    """Hechos para el agente: un tema o el panorama público. Sin cifras de habitación."""
    publico = vista_publica({"empresa_id": "", "version": 0, "actualizada_en": None, "cuerpo": cuerpo})
    politicas = publico["politicas"]
    if not tema:
        return {"tema": "todas", "hechos": politicas, "texto_cancelacion": publico["texto_cancelacion"],
                "pendientes": [p["ruta"] for p in publico["pendientes"]]}
    if tema not in TEMAS_CONOCIMIENTO:
        raise PoliticaInvalida(f"tema desconocido: {tema}")
    mapa = {
        "horarios": politicas["llegada_salida"],
        "llegada_anticipada": politicas["llegada_salida"].get("llegada_anticipada"),
        "salida_tardia": politicas["llegada_salida"].get("salida_tardia"),
        "cancelacion": {**politicas["cancelacion"], "texto": publico["texto_cancelacion"]},
        "no_show": politicas["no_show"],
        "deposito": politicas["deposito"],
        "minimo_noches": politicas["minimo_noches"],
        "ninos": politicas["ninos_cama"],
        "cama_adicional": politicas["ninos_cama"],
        "mascotas": politicas["mascotas"],
        "desayuno": politicas["desayuno"],
        "estacionamiento": politicas["estacionamiento"],
        "pagos": politicas["medios_pago"],
        "registro": politicas.get("registro_llegada"),
        "faq": politicas["faq"],
    }
    hecho = mapa[tema]
    return {"tema": tema, "hechos": hecho, "pendiente": _esta_pendiente(hecho)}


def _esta_pendiente(hecho) -> bool:
    if isinstance(hecho, dict):
        if hecho.get("confirmacion") in (PENDIENTE, NO_DEFINIDO):
            return True
        if isinstance(hecho.get("confirmacion"), str):
            return hecho["confirmacion"] != CONFIRMADO
    if isinstance(hecho, list):
        return any(_esta_pendiente(x) for x in hecho)
    return False


def cifras_de_politicas(cuerpo: dict, extras: dict | None, tarifa_noche: int | None, noches: int) -> set[str]:
    """Cifras que el verificador del agente puede aceptar (vienen de la política o del recargo calculado)."""
    cifras: set[str] = set()
    llegada = cuerpo.get("llegada_salida") or {}
    for valor in (llegada.get("hora_llegada_desde"), llegada.get("hora_salida_hasta")):
        if valor:
            cifras.add(valor)
            cifras.add(valor.replace(":", ""))
    cancelacion = cuerpo.get("cancelacion") or {}
    if cancelacion.get("horas_antelacion_gratis") is not None:
        cifras.add(str(cancelacion["horas_antelacion_gratis"]))
    calc = calcular_recargos(cuerpo, tarifa_noche, noches, extras)
    for recargo in calc["recargos"]:
        cifras.add(str(recargo["monto_clp"]))
        if recargo.get("horas"):
            cifras.add(str(recargo["horas"]))
    for bloque in (
        (llegada.get("llegada_anticipada") or {}).get("recargo"),
        (llegada.get("salida_tardia") or {}).get("recargo"),
    ):
        if bloque:
            cifras.add(str(bloque["valor"]))
    return cifras
