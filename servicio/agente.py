"""Agente de reservas N0 — copiloto de recepción (spec 005, V1-ISSUE-29).

El agente nunca es autoridad: cupo, tarifa, total, política y vencimiento los
produce `reservas.oferta`, la misma operación de `/hotel/oferta`. El modelo
de lenguaje (puerto, `modelo_lenguaje.py`) solo elige una plantilla y un
saludo libre acotado; el texto del borrador lo compone el servidor con las
cifras del turno y un verificador determinista rechaza cualquier borrador
cuyas referencias no vengan de ese turno (SC-001 por construcción).

Dominio puro (sin base ni red): `redactar`, `validar_decision`, `componer`,
`verificar`, `NIVELES`. El orquestador `procesar` corre dentro de la
petición (sin cola ni worker), con tope de `MAX_TURNOS` turnos.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime

import psycopg

from . import canal_publico
from . import reservas
from . import seguridad
from .modelo_lenguaje import NoConfigurado

MAX_TURNOS = 3
MAX_SALUDO = 280
MAX_TEXTO_CONSULTA = 4000
VERSION_PROMPT = "n0-2026-11-09"
VERSION_POLITICA = "n0-2026-11-04"

CANALES = frozenset({"manual", "landing", "correo", "whatsapp"})
PLANTILLAS = frozenset({"cotizacion", "sin_disponibilidad", "pedir_dato", "escalar"})
PLANTILLAS_INFORMATIVAS = frozenset({"cotizacion", "sin_disponibilidad", "pedir_dato"})
ROLES_GESTION = frozenset({"recepcion", "administrador"})

# Lista cerrada de herramientas por nivel (FR-A02). En N0 el modelo solo puede
# consultar la oferta y proponer borrador; N2 añade crear_solicitud, que
# envuelve la misma operación del canal público (v1-issue-22).
NIVELES = {
    "N0": ("consultar_disponibilidad", "proponer_borrador"),
    "N1": ("consultar_disponibilidad", "proponer_borrador"),
    "N2": ("consultar_disponibilidad", "proponer_borrador", "crear_solicitud"),
}

# NFR-A02: el modelo jamás envía autoridad como argumento.
_CAMPOS_PROHIBIDOS = frozenset(
    {"empresa_id", "rol", "tarifa", "total", "precio", "clave", "idempotency_key", "usuario", "estado"}
)

_AGRUPACION_RUT = "[rut]"
_AGRUPACION_CORREO = "[correo]"
_AGRUPACION_TELEFONO = "[teléfono]"
_AGRUPACION_TARJETA = "[tarjeta]"

_RE_CORREO = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_RE_TELEFONO_LARGO = re.compile(r"\+\s?5\s?6[\s-]?9[\s-]?\d{4}[\s-]?\d{4}")
_RE_TELEFONO_LOCAL = re.compile(r"\b9\d{8}\b")
_RE_RUT_PUNTOS = re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b")
_RE_RUT_PLANO = re.compile(r"\b\d{7,9}-[\dkK]\b")
_RE_TARJETA = re.compile(r"\b(?:\d[ -]?){13,19}\b")


class DecisionInvalida(Exception):
    """La decisión del modelo nombra herramienta/argumentos fuera de la lista."""

    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


class ConsultaInvalida(Exception):
    """400: validación de la consulta entrante o de la política."""

    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


class ConsultaAjenaOInexistente(Exception):
    """403 sin revelar cuál es el caso (igual que el resto de la API)."""


class TransicionInvalida(Exception):
    """409: el borrador no admite la operación en su estado actual."""


class PoliticaInvalida(Exception):
    """409: cambio de política no permitido (subir de nivel sin evaluación)."""

    def __init__(self, detalle: str):
        super().__init__(detalle)
        self.detalle = detalle


def redactar(texto: str) -> str:
    """NFR-A03: quita RUT, tarjetas, correos y teléfonos antes de persistir
    o enviar al modelo. Las fechas y la cantidad de personas se conservan."""
    if not texto:
        return ""
    salida = _RE_CORREO.sub(_AGRUPACION_CORREO, texto)
    salida = _RE_TELEFONO_LARGO.sub(_AGRUPACION_TELEFONO, salida)
    salida = _RE_TELEFONO_LOCAL.sub(_AGRUPACION_TELEFONO, salida)
    salida = _RE_RUT_PUNTOS.sub(_AGRUPACION_RUT, salida)
    salida = _RE_RUT_PLANO.sub(_AGRUPACION_RUT, salida)
    salida = _RE_TARJETA.sub(_AGRUPACION_TARJETA, salida)
    return salida


def _como_fecha(valor) -> date:
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except (ValueError, TypeError):
        raise DecisionInvalida(f"fecha invalida: {valor!r}")


def validar_decision(decision: dict, politica: dict, herramientas_permitidas) -> dict:
    """FR-A02/NFR-A02: lista cerrada + argumentos validados. Sin ejecutar."""
    if not isinstance(decision, dict) or not isinstance(decision.get("argumentos"), dict):
        raise DecisionInvalida("decision mal formada")
    herramienta = decision.get("herramienta")
    if herramienta not in herramientas_permitidas:
        raise DecisionInvalida(f"herramienta no permitida: {herramienta}")
    argumentos = dict(decision["argumentos"])
    prohibidos = sorted(_CAMPOS_PROHIBIDOS & set(argumentos))
    if prohibidos:
        raise DecisionInvalida(f"argumentos no permitidos: {', '.join(prohibidos)}")
    if herramienta == "consultar_disponibilidad":
        inicio = _como_fecha(argumentos.get("inicio"))
        fin = _como_fecha(argumentos.get("fin"))
        personas = argumentos.get("personas")
        if fin <= inicio:
            raise DecisionInvalida("fin debe ser mayor que inicio")
        if inicio < date.today():
            raise DecisionInvalida("inicio debe ser hoy o una fecha futura")
        if not isinstance(personas, int) or isinstance(personas, bool) or not 1 <= personas <= 30:
            raise DecisionInvalida("personas debe estar entre 1 y 30")
        if (fin - inicio).days > int(politica.get("max_noches") or 30):
            raise DecisionInvalida("el rango supera el maximo de noches de la politica")
    elif herramienta == "proponer_borrador":
        if argumentos.get("plantilla") not in PLANTILLAS:
            raise DecisionInvalida(f"plantilla desconocida: {argumentos.get('plantilla')}")
        saludo = argumentos.get("saludo") or ""
        if not isinstance(saludo, str) or len(saludo) > MAX_SALUDO:
            raise DecisionInvalida(f"saludo invalido (maximo {MAX_SALUDO} caracteres)")
        if not isinstance(argumentos.get("campos") or {}, dict):
            raise DecisionInvalida("campos invalidos")
    elif herramienta == "crear_solicitud":
        ref = argumentos.get("oferta_item_ref")
        if isinstance(ref, bool) or not isinstance(ref, int) or ref < 0:
            raise DecisionInvalida("oferta_item_ref invalida")
        if not isinstance(argumentos.get("nombre"), str) or not argumentos["nombre"].strip():
            raise DecisionInvalida("nombre es obligatorio")
        if not isinstance(argumentos.get("contacto"), str) or not argumentos["contacto"].strip():
            raise DecisionInvalida("contacto es obligatorio")
    return {"herramienta": herramienta, "argumentos": argumentos}


def _argumentos_traza(argumentos: dict) -> dict:
    """La traza no guarda correo, teléfono, RUT ni tarjeta."""
    return {
        clave: redactar(valor) if isinstance(valor, str) else valor
        for clave, valor in (argumentos or {}).items()
    }


def _clp(monto: int) -> str:
    """Formato CLP del servidor (miles con punto), el único que ven los
    borradores: el front replica este formato, no lo calcula."""
    return f"${int(monto):,}".replace(",", ".")


def _item_oferta(campos: dict, resultados: dict) -> dict:
    oferta = resultados["consultar_disponibilidad"]["oferta"]
    indice = int((campos or {}).get("item", 0))
    return oferta[indice]


def componer(plantilla: str, campos: dict, saludo: str, resultados: dict) -> str:
    """FR-A03: el texto lo compone el servidor; las cifras salen de las
    herramientas del turno, jamás del modelo."""
    saludo = (saludo or "").strip()
    if plantilla == "cotizacion":
        item = _item_oferta(campos, resultados)
        return (
            f"{saludo}\n\n"
            f"Tenemos disponibilidad: {item['habitacion_id']} ({item['tipo']}) — "
            f"{_clp(item['tarifa_noche_clp'])} por noche, {_clp(item['total_clp'])} en total. "
            f"Cancelación: {item['politica_cancelacion']}. "
            f"Cotización vigente hasta {item['vigente_hasta']}."
        )
    if plantilla == "sin_disponibilidad":
        return (
            f"{saludo}\n\n"
            "Para esas fechas no tenemos disponibilidad. Si pruebas con otro "
            "rango, te vuelvo a cotizar con gusto."
        )
    if plantilla == "pedir_dato":
        faltante = (campos or {}).get("faltante") or "las fechas de llegada y salida, y cuántas personas viajan"
        return f"{saludo}\n\n¿Me ayudas con {faltante}?"
    if plantilla == "escalar":
        return f"{saludo}\n\nDerivo tu consulta con recepción para atenderte mejor."
    raise DecisionInvalida(f"plantilla desconocida: {plantilla}")


def verificar(borrador: dict, resultados: dict) -> str:
    """Verificador determinista (FR-A03): «ok» o «rechazo:<motivo>»."""
    plantilla = borrador.get("plantilla")
    if plantilla not in PLANTILLAS:
        return "rechazo:plantilla_desconocida"
    saludo = borrador.get("saludo") or ""
    if any(c.isdigit() for c in saludo) or "$" in saludo:
        return "rechazo:cifra_en_texto_libre"
    if plantilla == "cotizacion":
        oferta = (resultados.get("consultar_disponibilidad") or {}).get("oferta")
        if not oferta:
            return "rechazo:referencia_inexistente"
        item = (borrador.get("campos") or {}).get("item", 0)
        if not isinstance(item, int) or isinstance(item, bool) or not 0 <= item < len(oferta):
            return "rechazo:referencia_inexistente"
    return "ok"


# ---------------------------------------------------------------------------
# Persistencia y orquestación (psycopg; se ejercita con la base de pruebas)
# ---------------------------------------------------------------------------

def asegurar_agente_servicio(conexion: psycopg.Connection, empresa_id: str) -> None:
    """FR-A06: identidad de servicio `agente` por empresa. Sin clave utilizable
    (el hash no es argon2: `autenticar` devuelve None siempre) y fuera de
    todos los ROLES_*; la API de usuarios la rechazaría (rol con pattern)."""
    fila = conexion.execute(
        "SELECT id FROM usuarios WHERE empresa_id = %s AND nombre = 'agente'",
        (empresa_id,),
    ).fetchone()
    if fila is None:
        conexion.execute(
            "INSERT INTO usuarios (id, empresa_id, nombre, rol, clave_hash) "
            "VALUES (%s, %s, 'agente', 'agente', '!sin-clave-utilizable!')",
            (f"USR-AGT-{uuid.uuid4().hex[:10]}", empresa_id),
        )


def politica_de(conexion: psycopg.Connection, empresa_id: str) -> dict:
    fila = conexion.execute(
        "SELECT nivel, horario, max_noches, max_personas, tope_mensual_clp, evaluacion_ref "
        "FROM politica_agente WHERE empresa_id = %s",
        (empresa_id,),
    ).fetchone()
    if fila is None:
        return {
            "nivel": "N0", "horario": None, "max_noches": 30, "max_personas": 30,
            "tope_mensual_clp": None, "evaluacion_ref": None,
        }
    return {
        "nivel": fila[0], "horario": fila[1], "max_noches": fila[2],
        "max_personas": fila[3], "tope_mensual_clp": fila[4], "evaluacion_ref": fila[5],
    }


def registrar_consulta(
    conexion: psycopg.Connection, empresa_id: str, canal_origen: str, texto: str, registrada_por: str
) -> dict:
    """FR-A01: registra la consulta con el texto redactado (NFR-A03); el
    original sin redactar no se guarda."""
    if canal_origen not in CANALES:
        raise ConsultaInvalida(f"canal_origen debe ser uno de: {', '.join(sorted(CANALES))}")
    texto_redactado = redactar(texto or "")
    if not 1 <= len(texto_redactado) <= MAX_TEXTO_CONSULTA:
        raise ConsultaInvalida(f"texto debe tener entre 1 y {MAX_TEXTO_CONSULTA} caracteres")
    consulta_id = f"CON-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO consultas_agente (id, empresa_id, canal_origen, texto_redactado, registrada_por, estado) "
        "VALUES (%s, %s, %s, %s, %s, 'pendiente')",
        (consulta_id, empresa_id, canal_origen, texto_redactado, registrada_por),
    )
    seguridad.auditar(conexion, registrada_por, "agente_consulta_registrada", consulta_id, "pendiente")
    return _fila_consulta(conexion, empresa_id, consulta_id)


def _fila_consulta(conexion: psycopg.Connection, empresa_id: str, consulta_id: str) -> dict:
    fila = conexion.execute(
        "SELECT id, canal_origen, texto_redactado, recibida_en, registrada_por, estado, motivo "
        "FROM consultas_agente WHERE id = %s AND empresa_id = %s",
        (consulta_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise ConsultaAjenaOInexistente("acceso denegado")
    return {
        "consulta_id": fila[0], "empresa_id": empresa_id, "canal_origen": fila[1],
        "texto_redactado": fila[2],
        "recibida_en": fila[3].isoformat(), "registrada_por": fila[4],
        "estado": fila[5], "motivo": fila[6],
    }


def _fila_borrador(conexion: psycopg.Connection, borrador_id: str) -> dict:
    fila = conexion.execute(
        "SELECT id, consulta_id, plantilla, campos, texto_compuesto, oferta_emitida_en, "
        "vigente_hasta, estado, aprobado_por, aprobado_en, version "
        "FROM borradores_agente WHERE id = %s",
        (borrador_id,),
    ).fetchone()
    if fila is None:
        raise ConsultaAjenaOInexistente("acceso denegado")
    return {
        "borrador_id": fila[0], "consulta_id": fila[1], "plantilla": fila[2],
        "campos": fila[3], "texto_compuesto": fila[4],
        "oferta_emitida_en": fila[5].isoformat() if fila[5] else None,
        "vigente_hasta": fila[6].isoformat() if fila[6] else None,
        "estado": fila[7], "aprobado_por": fila[8],
        "aprobado_en": fila[9].isoformat() if fila[9] else None, "version": fila[10],
    }


def listar_consultas(conexion: psycopg.Connection, empresa_id: str, estado: str | None) -> dict:
    if estado is not None and estado not in ("pendiente", "procesada", "escalada"):
        raise ConsultaInvalida("estado debe ser pendiente, procesada o escalada")
    if estado is None:
        filas = conexion.execute(
            "SELECT id FROM consultas_agente WHERE empresa_id = %s ORDER BY recibida_en, id",
            (empresa_id,),
        ).fetchall()
    else:
        filas = conexion.execute(
            "SELECT id FROM consultas_agente WHERE empresa_id = %s AND estado = %s ORDER BY recibida_en, id",
            (empresa_id, estado),
        ).fetchall()
    consultas = []
    for (consulta_id,) in filas:
        fila = _fila_consulta(conexion, empresa_id, consulta_id)
        fila.pop("texto_redactado")
        consultas.append(fila)
    return {"consultas": consultas}


def detalle_consulta(conexion: psycopg.Connection, empresa_id: str, consulta_id: str) -> dict:
    consulta = _fila_consulta(conexion, empresa_id, consulta_id)
    borradores = conexion.execute(
        "SELECT id FROM borradores_agente WHERE consulta_id = %s ORDER BY version, id",
        (consulta_id,),
    ).fetchall()
    trazas = conexion.execute(
        "SELECT turno, herramienta, decision, verificacion, modelo, creada_en, resultado "
        "FROM trazas_agente WHERE consulta_id = %s ORDER BY turno, creada_en",
        (consulta_id,),
    ).fetchall()
    return {
        **consulta,
        "borradores": [_fila_borrador(conexion, fila[0]) for fila in borradores],
        "traza": [_resumen_traza(t) for t in trazas],
    }


def _resumen_traza(fila) -> dict:
    """La bandeja ve el identificador de la solicitud creada, no el contacto."""
    resumen = {
        "turno": fila[0], "herramienta": fila[1], "decision": fila[2], "verificacion": fila[3],
        "modelo": fila[4], "creada_en": fila[5].isoformat(),
    }
    resultado = fila[6]
    if isinstance(resultado, str):
        resultado = json.loads(resultado)
    if isinstance(resultado, dict) and resultado.get("solicitud_id"):
        resumen["solicitud_id"] = resultado["solicitud_id"]
    return resumen


def _trazar(conexion, consulta_id, turno, herramienta, argumentos, resultado, decision, verificacion, modelo):
    conexion.execute(
        "INSERT INTO trazas_agente (id, consulta_id, turno, herramienta, argumentos, resultado, "
        "decision, verificacion, version_prompt, version_politica, modelo) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (f"TRZ-{uuid.uuid4().hex[:12]}", consulta_id, turno, herramienta,
         json.dumps(argumentos or {}, ensure_ascii=False), json.dumps(resultado or {}, ensure_ascii=False),
         decision, verificacion, VERSION_PROMPT, VERSION_POLITICA, modelo),
    )


def _escalar(conexion, consulta_id: str, motivo: str) -> dict:
    conexion.execute(
        "UPDATE consultas_agente SET estado = 'escalada', motivo = %s WHERE id = %s",
        (motivo, consulta_id),
    )
    seguridad.auditar(conexion, f"agente:{consulta_id}", "agente_consulta_escalada", consulta_id, motivo)
    return {"estado": "escalado", "motivo": motivo}


def envio_automatico(politica: dict, plantilla: str, texto_original: str) -> bool:
    """N1 envía solo información y cae a N0 si la política no lo permite.

    Horario definido y sin regla de evaluación: no se envía (no se inventa
    la ventana). Datos sensibles en el texto original: no se envía.
    """
    if politica.get("nivel") != "N1":
        return False
    if plantilla not in PLANTILLAS_INFORMATIVAS:
        return False
    if politica.get("horario"):
        return False
    if redactar(texto_original or "") != (texto_original or ""):
        return False
    return True


def resumen_oferta_para_el_modelo(argumentos: dict, oferta: dict) -> dict:
    """Lo mínimo para el turno siguiente: índices y tipo, sin cifras.

    El servidor sigue siendo quien compone tarifa y total. El modelo solo
    necesita saber si hay ítems y cuál referenciar.
    """
    items = [
        {"item": indice, "tipo": item.get("tipo")}
        for indice, item in enumerate(oferta.get("oferta") or [])
    ]
    return {
        "herramienta": "consultar_disponibilidad",
        "inicio": argumentos.get("inicio"),
        "fin": argumentos.get("fin"),
        "personas": argumentos.get("personas"),
        "n_items": len(items),
        "items": items,
    }


def notas_de_herramienta(decision: dict, resumen: dict) -> list[dict]:
    """Decisión ya ejecutada y su resultado, en el mismo dialecto {rol, texto}."""
    return [
        {
            "rol": "assistant",
            "texto": json.dumps(
                {"herramienta": decision["herramienta"], "argumentos": decision["argumentos"]},
                ensure_ascii=False,
            ),
        },
        {"rol": "user", "texto": json.dumps(resumen, ensure_ascii=False)},
    ]


def _crear_solicitud_del_turno(
    conexion, empresa_id: str, consulta_id: str, turno: int, argumentos: dict,
    resultados: dict, politica: dict, modelo_nombre: str,
) -> dict:
    """N2: la misma operación del canal público, una sola vez por consulta.

    No cobra (Q-HOT-03: 0 CLP sin aprobación humana). El cupo lo decide
    `crear_solicitud`. La traza guarda el contacto redactado.
    """
    rango = resultados.get("rango")
    oferta = (resultados.get("consultar_disponibilidad") or {}).get("oferta") or []
    ref = argumentos["oferta_item_ref"]
    traza_args = _argumentos_traza(argumentos)

    def rechazar(motivo: str) -> dict:
        _trazar(conexion, consulta_id, turno, "crear_solicitud", traza_args, {},
                "rechazada", motivo, modelo_nombre)
        return {"escalar": True, "motivo": motivo}

    if rango is None or not isinstance(ref, int) or not 0 <= ref < len(oferta):
        return rechazar("crear_solicitud sin oferta del turno")
    inicio = _como_fecha(rango["inicio"])
    fin = _como_fecha(rango["fin"])
    personas = rango["personas"]
    if (personas > int(politica.get("max_personas") or 30)
            or (fin - inicio).days > int(politica.get("max_noches") or 30)):
        return rechazar("supera el limite de la politica")
    try:
        solicitud = canal_publico.crear_solicitud(
            conexion, empresa_id, oferta[ref]["habitacion_id"], inicio, fin, personas,
            argumentos["nombre"].strip(), argumentos["contacto"].strip(),
            f"agente:{consulta_id}", origen="agente",
        )
    except (canal_publico.SinCupoOSinTarifa, canal_publico.SolicitudInvalida,
            canal_publico.ClaveEnConflicto) as error:
        return rechazar(str(error))
    reintento = bool(solicitud.get("reintento"))
    _trazar(conexion, consulta_id, turno, "crear_solicitud", traza_args,
            {"solicitud_id": solicitud["solicitud_id"], "reintento": reintento},
            "ejecutada", "ok", modelo_nombre)
    return {
        "escalar": False,
        "solicitud_id": solicitud["solicitud_id"],
        "reintento": reintento,
    }


def procesar(
    conexion: psycopg.Connection, consulta: dict, modelo, politica: dict,
    texto_original: str | None = None, canal=None,
) -> dict:
    """Orquestador del turno (FR-A02, FR-A09, NFR-A05): a lo sumo MAX_TURNOS
    llamadas al modelo; la última decisión debe proponer un borrador que
    supere el verificador. Todo queda en la traza con `actor='agente:<id>'`."""
    empresa_id = consulta["empresa_id"]
    consulta_id = consulta["consulta_id"]
    nivel = politica.get("nivel", "N0")
    permitidas = NIVELES.get(nivel, NIVELES["N0"])
    resultados: dict = {}
    fallos_modelo = 0
    mensajes = [{"rol": "user", "texto": consulta["texto_redactado"]}]
    for turno in range(1, MAX_TURNOS + 1):
        try:
            decision = modelo.decidir(
                mensajes=list(mensajes),
                herramientas=list(permitidas),
            )
        except NoConfigurado:
            raise
        except Exception:
            fallos_modelo += 1
            _trazar(conexion, consulta_id, turno, "modelo", {}, {"error": "modelo no responde"},
                    "reintento" if fallos_modelo == 1 else "fallo", "error", getattr(modelo, "nombre", "desconocido"))
            if fallos_modelo >= 2:
                return _escalar(conexion, consulta_id, "modelo no responde")
            continue
        try:
            normalizada = validar_decision(decision, politica, permitidas)
        except DecisionInvalida as error:
            _trazar(conexion, consulta_id, turno, decision.get("herramienta", "?"),
                    _argumentos_traza(decision.get("argumentos") or {}), {}, "rechazada",
                    f"rechazo:{error}", modelo.nombre)
            seguridad.auditar(conexion, f"agente:{consulta_id}", "agente_decision_rechazada",
                              consulta_id, str(error))
            return _escalar(conexion, consulta_id, f"decision invalida: {error}")
        herramienta = normalizada["herramienta"]
        argumentos = normalizada["argumentos"]
        if herramienta == "consultar_disponibilidad":
            oferta = reservas.oferta(
                conexion, _como_fecha(argumentos["inicio"]), _como_fecha(argumentos["fin"]),
                argumentos["personas"], datetime.now(),
            )
            resultados["consultar_disponibilidad"] = oferta
            resultados["rango"] = {
                "inicio": argumentos["inicio"], "fin": argumentos["fin"],
                "personas": argumentos["personas"],
            }
            _trazar(conexion, consulta_id, turno, herramienta, argumentos,
                    {"n_items": len(oferta["oferta"]), "emitida_en": oferta["emitida_en"]},
                    "ejecutada", "ok", modelo.nombre)
            mensajes.extend(notas_de_herramienta(
                normalizada, resumen_oferta_para_el_modelo(argumentos, oferta)
            ))
            continue
        if herramienta == "crear_solicitud":
            creado = _crear_solicitud_del_turno(
                conexion, empresa_id, consulta_id, turno, argumentos, resultados, politica,
                modelo.nombre,
            )
            if creado.get("escalar"):
                return _escalar(conexion, consulta_id, creado["motivo"])
            mensajes.extend(notas_de_herramienta(
                {"herramienta": "crear_solicitud", "argumentos": {"oferta_item_ref": argumentos["oferta_item_ref"]}},
                {"herramienta": "crear_solicitud", "solicitud_id": creado["solicitud_id"],
                 "reintento": creado["reintento"]},
            ))
            continue
        propuesta = {
            "plantilla": argumentos["plantilla"],
            "campos": argumentos.get("campos") or {},
            "saludo": argumentos.get("saludo") or "",
        }
        veredicto = verificar(propuesta, resultados)
        _trazar(conexion, consulta_id, turno, herramienta, argumentos, {},
                "proponer", veredicto, modelo.nombre)
        if veredicto != "ok":
            return _escalar(conexion, consulta_id, f"verificacion: {veredicto}")
        texto = componer(propuesta["plantilla"], propuesta["campos"], propuesta["saludo"], resultados)
        oferta_res = resultados.get("consultar_disponibilidad") or {}
        items = oferta_res.get("oferta") or []
        indice = propuesta["campos"].get("item", 0) if propuesta["plantilla"] == "cotizacion" else 0
        vigente_hasta = items[indice]["vigente_hasta"] if items and 0 <= indice < len(items) else None
        borrador_id = f"BOR-{uuid.uuid4().hex[:12]}"
        conexion.execute(
            "INSERT INTO borradores_agente (id, consulta_id, plantilla, campos, texto_compuesto, "
            "oferta_emitida_en, vigente_hasta, estado, version) VALUES (%s, %s, %s, %s, %s, %s, %s, "
            "'pendiente_aprobacion', 1)",
            (borrador_id, consulta_id, propuesta["plantilla"],
             json.dumps(propuesta["campos"], ensure_ascii=False), texto,
             oferta_res.get("emitida_en"), vigente_hasta),
        )
        conexion.execute(
            "UPDATE consultas_agente SET estado = 'procesada', motivo = NULL WHERE id = %s",
            (consulta_id,),
        )
        seguridad.auditar(conexion, f"agente:{consulta_id}", "agente_borrador_propuesto",
                          borrador_id, "pendiente_aprobacion")
        origen = consulta["texto_redactado"] if texto_original is None else texto_original
        if envio_automatico(politica, propuesta["plantilla"], origen):
            from .canal_salida import CanalNoConfigurado, SinCanal

            puerto = canal or SinCanal()
            try:
                puerto.enviar(
                    {"consulta_id": consulta_id, "canal_origen": consulta["canal_origen"]},
                    texto,
                )
                estado_envio = "enviado"
                detalle_envio = getattr(puerto, "nombre", "canal")
            except CanalNoConfigurado:
                estado_envio = "pendiente_envio"
                detalle_envio = "canal no configurado"
            conexion.execute(
                "UPDATE borradores_agente SET estado = %s WHERE id = %s AND estado = 'pendiente_aprobacion'",
                (estado_envio, borrador_id),
            )
            seguridad.auditar(
                conexion, f"agente:{consulta_id}", "agente_borrador_envio", borrador_id, detalle_envio
            )
        borrador = _fila_borrador(conexion, borrador_id)
        borrador["consulta"] = _fila_consulta(conexion, empresa_id, consulta_id)
        return borrador
    return _escalar(conexion, consulta_id, f"tope de {MAX_TURNOS} turnos alcanzado")


def _borrador_de_la_empresa(conexion, empresa_id, borrador_id) -> dict:
    fila = conexion.execute(
        "SELECT b.id, b.estado, b.plantilla, b.campos, b.texto_compuesto, b.consulta_id, "
        "b.vigente_hasta, b.version, c.empresa_id "
        "FROM borradores_agente b JOIN consultas_agente c ON c.id = b.consulta_id "
        "WHERE b.id = %s AND c.empresa_id = %s",
        (borrador_id, empresa_id),
    ).fetchone()
    if fila is None:
        raise ConsultaAjenaOInexistente("acceso denegado")
    return {
        "borrador_id": fila[0], "estado": fila[1], "plantilla": fila[2], "campos": fila[3],
        "texto_compuesto": fila[4], "consulta_id": fila[5], "vigente_hasta": fila[6],
        "version": fila[7], "empresa_id": fila[8],
    }


def aprobar(conexion, empresa_id, borrador_id, actor, texto_editado, ahora: datetime) -> dict:
    """FR-A05: recotiza al aprobar si la oferta venció. Si la cifra cambió,
    409 «la oferta cambió» con un borrador nuevo; el viejo no queda aprobado."""
    borrador = _borrador_de_la_empresa(conexion, empresa_id, borrador_id)
    if borrador["estado"] != "pendiente_aprobacion":
        raise TransicionInvalida("el borrador ya esta resuelto")
    if borrador["plantilla"] == "cotizacion" and borrador["vigente_hasta"]:
        vigente_hasta = borrador["vigente_hasta"]
        if not isinstance(vigente_hasta, datetime):
            vigente_hasta = datetime.fromisoformat(str(vigente_hasta))
        ahora_cmp = ahora
        if vigente_hasta.tzinfo is not None and ahora_cmp.tzinfo is None:
            ahora_cmp = ahora_cmp.replace(tzinfo=vigente_hasta.tzinfo)
        if ahora_cmp > vigente_hasta:
            return _recotizar(conexion, borrador, actor)
    estado_nuevo = "editado" if (texto_editado or "").strip() else "aprobado"
    texto_final = (texto_editado or "").strip() or borrador["texto_compuesto"]
    actualizado = conexion.execute(
        "UPDATE borradores_agente SET estado = %s, aprobado_por = %s, aprobado_en = now(), "
        "texto_compuesto = %s WHERE id = %s AND estado = 'pendiente_aprobacion'",
        (estado_nuevo, actor, texto_final, borrador_id),
    )
    if actualizado.rowcount == 0:
        raise TransicionInvalida("el borrador ya esta resuelto")
    seguridad.auditar(conexion, actor, "agente_borrador_aprobado", borrador_id, estado_nuevo)
    return {"estado": estado_nuevo, "borrador": _fila_borrador(conexion, borrador_id)}


def _recotizar(conexion, borrador: dict, actor: str) -> dict:
    """FR-A05: repite la herramienta del turno (argumentos de la traza) y
    compara el ítem referenciado. Igual → aprueba; distinto → borrador nuevo."""
    traza = conexion.execute(
        "SELECT argumentos FROM trazas_agente WHERE consulta_id = %s AND herramienta = "
        "'consultar_disponibilidad' ORDER BY turno DESC LIMIT 1",
        (borrador["consulta_id"],),
    ).fetchone()
    if traza is None:
        raise TransicionInvalida("sin argumentos de cotizacion en la traza")
    argumentos = traza[0] if isinstance(traza[0], dict) else json.loads(traza[0])
    oferta = reservas.oferta(
        conexion, _como_fecha(argumentos["inicio"]), _como_fecha(argumentos["fin"]),
        argumentos["personas"], datetime.now(),
    )
    items = oferta.get("oferta") or []
    item_nuevo = borrador["campos"].get("item", 0)
    if items and 0 <= item_nuevo < len(items):
        texto_nuevo = componer("cotizacion", borrador["campos"], "", {"consultar_disponibilidad": oferta})
        if texto_nuevo.split("\n\n", 1)[1] == borrador["texto_compuesto"].split("\n\n", 1)[1]:
            actualizado = conexion.execute(
                "UPDATE borradores_agente SET estado = 'aprobado', aprobado_por = %s, aprobado_en = now() "
                "WHERE id = %s AND estado = 'pendiente_aprobacion'",
                (actor, borrador["borrador_id"]),
            )
            if actualizado.rowcount == 0:
                raise TransicionInvalida("el borrador ya esta resuelto")
            seguridad.auditar(conexion, actor, "agente_borrador_aprobado", borrador["borrador_id"], "aprobado")
            return {"estado": "aprobado", "borrador": _fila_borrador(conexion, borrador["borrador_id"]),
                    "recotizado": False}
    nuevo_id = f"BOR-{uuid.uuid4().hex[:12]}"
    saludo = borrador["texto_compuesto"].split("\n\n", 1)[0]
    texto_nuevo = componer("cotizacion", borrador["campos"], saludo, {"consultar_disponibilidad": oferta})
    conexion.execute(
        "INSERT INTO borradores_agente (id, consulta_id, plantilla, campos, texto_compuesto, "
        "oferta_emitida_en, vigente_hasta, estado, version) VALUES (%s, %s, 'cotizacion', %s, %s, %s, %s, "
        "'pendiente_aprobacion', %s)",
        (nuevo_id, borrador["consulta_id"], json.dumps(borrador["campos"], ensure_ascii=False),
         texto_nuevo, oferta["emitida_en"],
         items[item_nuevo]["vigente_hasta"] if items and 0 <= item_nuevo < len(items) else None,
         borrador["version"] + 1),
    )
    seguridad.auditar(conexion, actor, "agente_oferta_cambio", borrador["borrador_id"],
                      f"borrador_nuevo:{nuevo_id}")
    return {
        "estado": "oferta_cambiada",
        "detail": "la oferta cambió",
        "borrador": _fila_borrador(conexion, nuevo_id),
    }


def descartar(conexion, empresa_id, borrador_id, motivo, actor) -> dict:
    borrador = _borrador_de_la_empresa(conexion, empresa_id, borrador_id)
    if borrador["estado"] not in ("pendiente_aprobacion", "pendiente_envio"):
        raise TransicionInvalida("el borrador ya esta resuelto")
    actualizado = conexion.execute(
        "UPDATE borradores_agente SET estado = 'descartado' WHERE id = %s AND estado = %s",
        (borrador_id, borrador["estado"]),
    )
    if actualizado.rowcount == 0:
        raise TransicionInvalida("el borrador ya esta resuelto")
    seguridad.auditar(conexion, actor, "agente_borrador_descartado", borrador_id,
                      (motivo or "").strip() or "sin motivo")
    return {"estado": "descartado", "borrador": _fila_borrador(conexion, borrador_id)}


def actualizar_politica(conexion, empresa_id, datos: dict, actor: str) -> dict:
    """FR-A07: política por empresa; subir de nivel exige `evaluacion_ref`
    (compuerta SC-003). Solo el administrador llega aquí (la ruta exige rol)."""
    nivel = datos.get("nivel")
    if nivel is not None and nivel not in NIVELES:
        raise ConsultaInvalida("nivel debe ser N0, N1 o N2")
    actual = politica_de(conexion, empresa_id)
    if nivel and int(nivel[1]) > int(actual["nivel"][1]) and not datos.get("evaluacion_ref"):
        raise PoliticaInvalida("subir de nivel exige evaluacion_ref (SC-003)")
    campos = {
        "nivel": nivel or actual["nivel"],
        "horario": datos.get("horario", actual["horario"]),
        "max_noches": datos.get("max_noches", actual["max_noches"]),
        "max_personas": datos.get("max_personas", actual["max_personas"]),
        "tope_mensual_clp": datos.get("tope_mensual_clp", actual["tope_mensual_clp"]),
        "evaluacion_ref": datos.get("evaluacion_ref", actual["evaluacion_ref"]),
    }
    conexion.execute(
        "INSERT INTO politica_agente (empresa_id, nivel, horario, max_noches, max_personas, "
        "tope_mensual_clp, evaluacion_ref, actualizada_por, actualizada_en) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now()) "
        "ON CONFLICT (empresa_id) DO UPDATE SET nivel = EXCLUDED.nivel, horario = EXCLUDED.horario, "
        "max_noches = EXCLUDED.max_noches, max_personas = EXCLUDED.max_personas, "
        "tope_mensual_clp = EXCLUDED.tope_mensual_clp, evaluacion_ref = EXCLUDED.evaluacion_ref, "
        "actualizada_por = EXCLUDED.actualizada_por, actualizada_en = now()",
        (empresa_id, campos["nivel"], campos["horario"], campos["max_noches"], campos["max_personas"],
         campos["tope_mensual_clp"], campos["evaluacion_ref"], actor),
    )
    seguridad.auditar(conexion, actor, "agente_politica_actualizada", empresa_id, campos["nivel"])
    return {"empresa_id": empresa_id, **campos}
