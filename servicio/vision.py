"""Lectura de facturas en foto o PDF con un proveedor de visión (2026-11-19).

Interfaz enchufable: el proveedor se elige por variables de entorno y, si no
hay ninguno, la función queda apagada limpiamente (la carga sigue a revisión
manual con lo que entregó el timbre).

Proveedor elegido por el propietario: Google Gemini.

    GEMINI_API_KEY             = clave de Google AI Studio (cabecera x-goog-api-key)
    GEMINI_MODELO              = modelo principal (por defecto gemini-3.5-flash-lite)
    GEMINI_MODELOS_RESPALDO    = lista separada por comas, se prueban en orden si
                                 el principal falla o tarda (opcional)
    VISION_TIEMPO_MAXIMO       = segundos por intento (por defecto 30)

Alternativa (por si se cambia de proveedor): VISION_PROVEEDOR=openai con
VISION_API_KEY, VISION_MODELO y VISION_URL_BASE (cualquier API compatible con
/chat/completions). VISION_PROVEEDOR=ninguno apaga la lectura aunque haya clave.

Reglas: la IA solo transcribe. Un precio que no se ve en el documento queda
vacío (nunca se inventa); la plataforma valida la suma de líneas contra el
neto/total y contra el monto del timbre, y marca las diferencias.
"""
from __future__ import annotations

import base64
import io
import json
import os
import time
import re
from typing import Callable, Protocol

import httpx

TIEMPO_MAXIMO = 30
MODELO_GEMINI = "gemini-3.5-flash-lite"
HttpPost = Callable[[str, dict, dict], dict]

INSTRUCCIONES = """Eres un transcriptor de documentos comerciales chilenos (facturas, notas de crédito, pedidos u órdenes de compra).
Devuelve SOLO un JSON con esta forma exacta:
{"tipo_documento": "factura" | "nota_credito" | "pedido" | "guia" | "otro",
 "emisor_rut": "12345678-9" | null, "emisor_razon_social": string | null,
 "folio": string | null, "fecha_emision": "AAAA-MM-DD" | null,
 "monto_neto": entero | null, "monto_exento": entero | null, "iva": entero | null, "monto_total": entero | null,
 "lineas": [{"codigo": string | null, "descripcion": string, "cantidad": número | null, "unidad": string | null,
             "precio_neto": número | null, "descuento": número | null, "total_linea": número | null,
             "nota_manuscrita": string | null}]}
Reglas:
- Transcribe solo lo que se ve. Si un dato no se lee con claridad, usa null. NUNCA inventes ni calcules precios.
- precio_neto es el precio unitario sin IVA impreso en la línea; total_linea el valor de la línea.
- Si hay anotaciones a mano junto a una línea (p. ej. "166und x 690"), cópialas tal cual en nota_manuscrita.
- "pedido" si el documento dice nota de pedido, orden de compra, cotización o no es un documento tributario.
- Números sin separador de miles (12500, no 12.500)."""


class VisionNoConfigurada(Exception):
    """No hay proveedor de visión: la lectura automática está apagada."""


class VisionFallida(Exception):
    """El proveedor respondió con error o con algo que no es el JSON pedido."""

    def __init__(self, mensaje: str, transitoria: bool = False):
        super().__init__(mensaje)
        self.transitoria = transitoria  # 429/5xx: vale la pena un segundo intento


class Proveedor(Protocol):
    nombre: str

    def extraer(self, contenido: bytes, tipo_mime: str) -> dict: ...


def _tiempo_maximo() -> float:
    try:
        return max(5.0, min(120.0, float(os.environ.get("VISION_TIEMPO_MAXIMO") or TIEMPO_MAXIMO)))
    except ValueError:
        return float(TIEMPO_MAXIMO)


def _post_json(url: str, cabeceras: dict, cuerpo: dict) -> dict:
    try:
        respuesta = httpx.post(url, headers=cabeceras, json=cuerpo, timeout=_tiempo_maximo())
    except httpx.HTTPError as error:
        raise VisionFallida(f"el proveedor de visión no respondió ({type(error).__name__})") from error
    if respuesta.status_code >= 400:
        raise VisionFallida(f"el proveedor de visión respondió {respuesta.status_code}",
                            transitoria=respuesta.status_code in (429, 500, 502, 503, 504))
    return respuesta.json()


def _png_de_pdf(contenido: bytes) -> list[bytes]:
    from .ted import imagenes_de_pdf

    salida = []
    for imagen in imagenes_de_pdf(contenido, escala=150 / 72):
        buffer = io.BytesIO()
        imagen.convert("RGB").save(buffer, "JPEG", quality=85)
        salida.append(buffer.getvalue())
    return salida


def _json_de_texto(texto: str) -> dict:
    texto = (texto or "").strip()
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        raise VisionFallida("la respuesta de visión no trae JSON")
    try:
        datos = json.loads(m.group(0))
    except json.JSONDecodeError as error:
        raise VisionFallida("la respuesta de visión no es JSON válido") from error
    if not isinstance(datos, dict):
        raise VisionFallida("la respuesta de visión no es un objeto")
    return datos


class ProveedorOpenAI:
    """Cualquier API compatible con OpenAI /chat/completions con imágenes."""
    nombre = "openai"

    def __init__(self, clave: str, modelo: str | None = None, url_base: str | None = None, post: HttpPost | None = None):
        self.clave = clave
        self.modelo = modelo or "gpt-4o-mini"
        self.url_base = (url_base or "https://api.openai.com/v1").rstrip("/")
        if not self.url_base.startswith("https://") and not self.url_base.startswith("http://127.0.0.1"):
            raise VisionNoConfigurada("VISION_URL_BASE debe ser https")
        self.post = post or _post_json

    def extraer(self, contenido: bytes, tipo_mime: str) -> dict:
        imagenes = _png_de_pdf(contenido) if tipo_mime == "application/pdf" else [contenido]
        mime = "image/jpeg" if tipo_mime == "application/pdf" else tipo_mime
        partes = [{"type": "text", "text": "Transcribe este documento."}] + [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(i).decode()}", "detail": "high"}}
            for i in imagenes
        ]
        r = self.post(f"{self.url_base}/chat/completions", {"Authorization": f"Bearer {self.clave}"}, {
            "model": self.modelo, "temperature": 0, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": INSTRUCCIONES}, {"role": "user", "content": partes}],
        })
        try:
            texto = r["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise VisionFallida("respuesta inesperada del proveedor de visión") from error
        return _json_de_texto(texto)


# Esquema de salida estructurada (responseSchema de Gemini, subconjunto OpenAPI).
_NUM = {"type": "NUMBER", "nullable": True}
_TXT = {"type": "STRING", "nullable": True}
ESQUEMA = {
    "type": "OBJECT",
    "properties": {
        "tipo_documento": {"type": "STRING", "enum": ["factura", "nota_credito", "pedido", "guia", "otro"]},
        "emisor_rut": _TXT, "emisor_razon_social": _TXT, "folio": _TXT, "fecha_emision": _TXT,
        "monto_neto": _NUM, "monto_exento": _NUM, "iva": _NUM, "monto_total": _NUM,
        "lineas": {"type": "ARRAY", "items": {
            "type": "OBJECT",
            "properties": {"codigo": _TXT, "descripcion": {"type": "STRING"}, "cantidad": _NUM, "unidad": _TXT,
                           "precio_neto": _NUM, "descuento": _NUM, "total_linea": _NUM, "nota_manuscrita": _TXT},
            "required": ["descripcion"],
        }},
    },
    "required": ["tipo_documento", "lineas"],
}


class ProveedorGemini:
    """Google Gemini (generateContent): acepta imagen o PDF directo y
    devuelve JSON con esquema. Si el modelo principal falla o tarda, prueba
    los de respaldo en orden."""
    nombre = "gemini"

    def __init__(self, clave: str, modelo: str | None = None, respaldo: list[str] | None = None,
                 post: HttpPost | None = None):
        self.clave = clave
        self.modelos = [m for m in [modelo or MODELO_GEMINI, *(respaldo or [])] if m]
        for m in self.modelos:
            if not re.fullmatch(r"[A-Za-z0-9.\-_]{1,80}", m):
                raise VisionNoConfigurada("GEMINI_MODELO no es válido")
        self.modelos = list(dict.fromkeys(self.modelos))
        self.post = post or _post_json
        self.modelo_usado: str | None = None
        self.espera_reintento = 2.0

    def extraer(self, contenido: bytes, tipo_mime: str) -> dict:
        cuerpo = {
            "systemInstruction": {"parts": [{"text": INSTRUCCIONES}]},
            "contents": [{"role": "user", "parts": [
                {"text": "Transcribe este documento."},
                {"inline_data": {"mime_type": tipo_mime, "data": base64.b64encode(contenido).decode()}},
            ]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": ESQUEMA},
        }
        ultimo: Exception | None = None
        for modelo in self.modelos:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
            for intento in range(2):  # un reintento si Google responde 429/5xx (sobrecarga momentánea)
                try:
                    r = self.post(url, {"x-goog-api-key": self.clave}, cuerpo)
                    texto = "".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"])
                    datos = _json_de_texto(texto)
                    self.modelo_usado = modelo
                    return datos
                except VisionFallida as error:
                    ultimo = error
                    if error.transitoria and intento == 0:
                        time.sleep(self.espera_reintento)
                        continue
                    break
                except (KeyError, IndexError, TypeError) as error:
                    ultimo = error
                    break
        if isinstance(ultimo, VisionFallida):
            raise ultimo
        raise VisionFallida("respuesta inesperada del proveedor de visión")


def proveedor_configurado(entorno: dict | None = None) -> Proveedor | None:
    e = os.environ if entorno is None else entorno
    nombre = (e.get("VISION_PROVEEDOR") or "").strip().lower()
    if nombre in ("ninguno", "no", "off", "apagado"):
        return None
    if nombre == "openai":
        clave = (e.get("VISION_API_KEY") or "").strip()
        return ProveedorOpenAI(clave, e.get("VISION_MODELO") or None, e.get("VISION_URL_BASE") or None) if clave else None
    if nombre in ("", "gemini"):
        clave = (e.get("GEMINI_API_KEY") or (e.get("VISION_API_KEY") if nombre == "gemini" else "") or "").strip()
        if not clave:
            return None
        respaldo = [m.strip() for m in (e.get("GEMINI_MODELOS_RESPALDO") or "").split(",") if m.strip()]
        return ProveedorGemini(clave, (e.get("GEMINI_MODELO") or "").strip() or None, respaldo)
    return None


def estado(entorno: dict | None = None) -> dict:
    try:
        p = proveedor_configurado(entorno)
    except VisionNoConfigurada:
        p = None
    return {"activa": p is not None, "proveedor": p.nombre if p else None}


# ------------------------------------------------------- normalización

def _numero(valor) -> float | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        n = float(valor)
    else:
        t = str(valor).strip().replace("$", "").replace(" ", "")
        if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", t):  # 12.500,5 (formato chileno)
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", ".")
        try:
            n = float(t)
        except ValueError:
            return None
    return n if n == n and abs(n) < 1e12 else None


def _texto(valor, maximo: int) -> str | None:
    if valor is None:
        return None
    t = " ".join(str(valor).split())
    return t[:maximo] or None


def normalizar(datos: dict) -> dict:
    """JSON del proveedor → {clase, documento, lineas} con tipos seguros."""
    from .importacion_productos import normalizar_rut_emisor

    tipo = (datos.get("tipo_documento") or "otro").lower()
    clase = {"factura": "factura", "nota_credito": "nota_credito", "pedido": "pedido"}.get(tipo, "desconocido")
    folio = _texto(datos.get("folio"), 20)
    folio = re.sub(r"\D", "", folio or "") or None
    fecha = _texto(datos.get("fecha_emision"), 10)
    if fecha and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        fecha = None
    documento = {
        "emisor_rut": normalizar_rut_emisor(_texto(datos.get("emisor_rut"), 15)),
        "emisor_razon_social": _texto(datos.get("emisor_razon_social"), 150),
        "folio": str(int(folio)) if folio else None,
        "fecha_emision": fecha,
        "monto_neto_clp": _entero(datos.get("monto_neto")),
        "monto_exento_clp": _entero(datos.get("monto_exento")),
        "iva_clp": _entero(datos.get("iva")),
        "monto_total_clp": _entero(datos.get("monto_total")),
    }
    lineas = []
    for item in (datos.get("lineas") or [])[:300]:
        if not isinstance(item, dict):
            continue
        descripcion = _texto(item.get("descripcion"), 120)
        if not descripcion:
            continue
        cantidad = _numero(item.get("cantidad"))
        precio = _numero(item.get("precio_neto"))
        total = _numero(item.get("total_linea"))
        descuento = _numero(item.get("descuento"))
        if cantidad and cantidad > 0 and total is not None:
            costo = round(total / cantidad)
        else:
            costo = round(precio) if precio is not None else None
        lineas.append({
            "linea": len(lineas) + 1,
            "codigo": _texto(item.get("codigo"), 60),
            "nombre": descripcion,
            "cantidad": cantidad if cantidad is not None and cantidad >= 0 else None,
            "unidad": _texto(item.get("unidad"), 20),
            "costo_unitario_clp": costo if costo is None or costo >= 0 else None,
            "precio_unitario_clp": round(precio) if precio is not None else None,
            "descuento_clp": round(descuento) if descuento is not None else None,
            "monto_neto_clp": round(total) if total is not None else None,
            "nota": _texto(item.get("nota_manuscrita"), 120),
        })
    return {"clase": clase, "documento": documento, "lineas": lineas}


def _entero(valor) -> int | None:
    n = _numero(valor)
    return round(n) if n is not None else None


# ------------------------------------------------------------ validación

def _tolerancia(monto: int) -> int:
    return max(2, round(abs(monto) * 0.005))


def validar(documento: dict, lineas: list[dict], ted: dict | None, receptor_esperado: str | None = None) -> list[dict]:
    """Diferencias para revisar: suma de líneas vs neto, neto+IVA vs total,
    total vs timbre, folio/RUT vs timbre, líneas sin precio o sin cantidad."""
    d: list[dict] = []
    neto = documento.get("monto_neto_clp")
    exento = documento.get("monto_exento_clp") or 0
    iva = documento.get("iva_clp")
    total = documento.get("monto_total_clp")
    montos = [l.get("monto_neto_clp") for l in lineas]
    if lineas and all(m is not None for m in montos):
        suma = sum(montos)
        base = (neto or 0) + exento if neto is not None else None
        if base is not None and abs(suma - base) > _tolerancia(base):
            d.append({"codigo": "suma_lineas", "mensaje": f"La suma de las líneas (${suma:,}) no cuadra con el neto (${base:,}).".replace(",", ".")})
    if neto is not None and iva is not None and total is not None and abs(neto + exento + iva - total) > _tolerancia(total):
        d.append({"codigo": "total", "mensaje": "Neto + IVA no da el total de la factura."})
    if ted:
        if ted.get("monto_total_clp") is not None and total is not None and abs(ted["monto_total_clp"] - total) > 1:
            d.append({"codigo": "timbre_total", "mensaje": f"El total leído (${total:,}) no coincide con el timbre del SII (${ted['monto_total_clp']:,}).".replace(",", ".")})
        if documento.get("folio") and ted.get("folio") and documento["folio"] != ted["folio"]:
            d.append({"codigo": "timbre_folio", "mensaje": f"El folio leído ({documento['folio']}) no coincide con el timbre ({ted['folio']})."})
        if documento.get("emisor_rut") and ted.get("emisor_rut") and documento["emisor_rut"] != ted["emisor_rut"]:
            d.append({"codigo": "timbre_rut", "mensaje": "El RUT del proveedor leído no coincide con el timbre."})
    receptor = (ted or {}).get("receptor_rut") or documento.get("receptor_rut")
    if receptor_esperado and receptor and receptor != receptor_esperado:
        d.append({"codigo": "receptor", "mensaje": f"El documento está emitido a otro RUT ({receptor})."})
    sin_precio = sum(1 for l in lineas if l.get("costo_unitario_clp") is None)
    if sin_precio:
        cuantas = "1 línea" if sin_precio == 1 else f"{sin_precio} líneas"
        d.append({"codigo": "sin_precio", "mensaje": f"{cuantas} sin precio legible: complétalas a mano (no se inventan precios)."})
    sin_cantidad = sum(1 for l in lineas if l.get("cantidad") in (None, 0))
    if sin_cantidad:
        d.append({"codigo": "sin_cantidad", "mensaje": "Hay líneas sin cantidad: complétalas a mano."})
    notas = [l for l in lineas if l.get("nota")]
    if notas:
        d.append({"codigo": "nota_manuscrita", "mensaje": "Hay anotaciones a mano en la factura: revisa las unidades sugeridas."})
    return d
