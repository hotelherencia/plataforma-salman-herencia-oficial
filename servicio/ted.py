"""Timbre electrónico del SII (TED) de facturas en papel o foto (2026-11-19).

Toda factura electrónica impresa lleva el «timbre»: un código PDF417 con el
XML `<TED><DD>…</DD><FRMT>…</FRMT></TED>`. Sus datos identifican el documento
sin depender de una IA:

- RE: RUT del emisor · TD: tipo de DTE · F: folio · FE: fecha de emisión
- RR: RUT del receptor · RSR: razón social del receptor
- MNT: monto total · IT1: primer ítem (descripción)

Se usa para identificar la factura, evitar cargarla dos veces (emisor + tipo
+ folio) y validar el total que lea la IA o el administrador.

Decodificación con zxing-cpp (bindings de Python mantenidos, ruedas
manylinux para Python 3.12/3.13, sin dependencias del sistema) y Pillow para
preparar la imagen; los PDF se renderizan con pypdfium2. El XML del timbre se
parsea con defusedxml (sin DTD ni entidades).
"""
from __future__ import annotations

import io
import re
from datetime import date

from defusedxml import ElementTree as DET

MAX_LADO = 4200          # px: más grande no mejora la lectura y cuesta memoria
MAX_PAGINAS_PDF = 3
TIPOS_CONOCIDOS = {33: "Factura electrónica", 34: "Factura exenta electrónica",
                   61: "Nota de crédito electrónica", 56: "Nota de débito electrónica",
                   52: "Guía de despacho electrónica", 39: "Boleta electrónica"}


class TimbreIlegible(Exception):
    """El texto leído no es un timbre del SII."""


def _rut(valor: str | None) -> str | None:
    if not valor:
        return None
    limpio = re.sub(r"[.\s]", "", valor).upper()
    return limpio if re.fullmatch(r"\d{1,8}-[0-9K]", limpio) else None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parsear_ted(texto: str | bytes) -> dict:
    """Texto del PDF417 (o el nodo TED de un XML) → datos del timbre."""
    if isinstance(texto, bytes):
        try:
            texto = texto.decode("utf-8")
        except UnicodeDecodeError:
            texto = texto.decode("latin-1")
    if not isinstance(texto, str) or "<TED" not in texto or len(texto) > 20_000:
        raise TimbreIlegible("no es un timbre del SII")
    inicio = texto.index("<TED")
    fin = texto.find("</TED>", inicio)
    fragmento = texto[inicio:fin + 6] if fin > 0 else texto[inicio:]
    try:
        raiz = DET.fromstring(fragmento, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except Exception as error:  # noqa: BLE001 (ParseError o DTD prohibida)
        # Algunos lectores cortan la firma (FRMT): basta con el DD completo.
        m = re.search(r"<DD>.*?</DD>", texto, re.S)
        if not m:
            raise TimbreIlegible("timbre incompleto") from error
        try:
            raiz = DET.fromstring(f"<TED>{m.group(0)}</TED>", forbid_dtd=True, forbid_entities=True, forbid_external=True)
        except Exception as error2:  # noqa: BLE001
            raise TimbreIlegible("timbre incompleto") from error2
    dd = next((e for e in raiz.iter() if _local(e.tag) == "DD"), None)
    if dd is None:
        raise TimbreIlegible("el timbre no trae datos")
    campos = {_local(h.tag): (h.text or "").strip() for h in dd}
    try:
        tipo = int(campos.get("TD", ""))
        folio = str(int(campos.get("F", "")))
    except ValueError as error:
        raise TimbreIlegible("el timbre no trae tipo o folio") from error
    rut = _rut(campos.get("RE"))
    if not rut:
        raise TimbreIlegible("el timbre no trae el RUT del emisor")
    try:
        fecha = date.fromisoformat(campos.get("FE", "")).isoformat()
    except ValueError:
        fecha = None
    try:
        monto = int(campos.get("MNT", ""))
    except ValueError:
        monto = None
    return {
        "emisor_rut": rut,
        "tipo_dte": tipo,
        "tipo_nombre": TIPOS_CONOCIDOS.get(tipo, f"Documento tipo {tipo}"),
        "folio": folio,
        "fecha_emision": fecha,
        "receptor_rut": _rut(campos.get("RR")),
        "receptor_razon_social": (campos.get("RSR") or "")[:150] or None,
        "monto_total_clp": monto,
        "primer_item": (campos.get("IT1") or "")[:120] or None,
    }


# --------------------------------------------------------------- imágenes

def _variantes(imagen):
    """Versiones de la foto que suelen hacer legible un PDF417 de celular:
    contraste, ampliación, recorte de la mitad inferior (donde va el timbre)
    y pequeñas rotaciones (una foto a mano nunca queda derecha). Se rota la
    imagen ya ampliada y con remuestreo bicúbico para no borrar las barras."""
    from PIL import Image, ImageFilter, ImageOps

    gris = ImageOps.exif_transpose(imagen).convert("L")
    if max(gris.size) > MAX_LADO:
        gris.thumbnail((MAX_LADO, MAX_LADO))
    yield gris
    contraste = ImageOps.autocontrast(gris, cutoff=2)
    yield contraste
    ancho, alto = gris.size
    factor = 2 if max(ancho, alto) < 2600 else 1
    inferior = contraste.crop((0, alto // 2, ancho, alto))
    if factor > 1:
        inferior = inferior.resize((inferior.width * factor, inferior.height * factor), Image.Resampling.BICUBIC)
    nitida = inferior.filter(ImageFilter.UnsharpMask(radius=2, percent=160, threshold=2))
    yield nitida
    for angulo in (-1, 1, -2, 2, -3, 3, -4, 4, -5, 5, -6, 6, -8, 8, -10, 10):
        yield nitida.rotate(angulo, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=255)
    for angulo in (-3, 3, -7, 7):
        yield contraste.rotate(angulo, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=255)
    yield nitida.point(lambda p: 255 if p > 128 else 0)


def _leer_pdf417(imagen) -> list[str]:
    import zxingcpp

    textos = []
    for variante in _variantes(imagen):
        try:
            resultados = zxingcpp.read_barcodes(variante, formats=zxingcpp.BarcodeFormat.PDF417, try_rotate=True,
                                                try_downscale=True)
        except TypeError:  # versiones sin try_downscale
            resultados = zxingcpp.read_barcodes(variante, formats=zxingcpp.BarcodeFormat.PDF417)
        for r in resultados:
            texto = r.text
            if not texto and getattr(r, "bytes", None):
                texto = bytes(r.bytes).decode("latin-1")
            if texto and "<TED" in texto:
                textos.append(texto)
        if textos:
            break
    return textos


def imagenes_de_pdf(contenido: bytes, escala: float = 200 / 72):
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(contenido)
    try:
        for i in range(min(len(pdf), MAX_PAGINAS_PDF)):
            yield pdf[i].render(scale=escala).to_pil()
    finally:
        pdf.close()


def leer_timbre(contenido: bytes, tipo_mime: str) -> dict | None:
    """Foto (JPEG/PNG/WebP) o PDF → datos del timbre, o None si no se pudo
    leer. Nunca lanza por una imagen ilegible: la carga sigue a revisión."""
    from PIL import Image

    try:
        if tipo_mime == "application/pdf":
            imagenes = imagenes_de_pdf(contenido)
        else:
            Image.MAX_IMAGE_PIXELS = 60_000_000  # tope anti «bomba de descompresión»
            imagenes = [Image.open(io.BytesIO(contenido))]
        for imagen in imagenes:
            for texto in _leer_pdf417(imagen):
                try:
                    return parsear_ted(texto)
                except TimbreIlegible:
                    continue
    except Exception:  # noqa: BLE001 (imagen corrupta, PDF dañado, bomba)
        return None
    return None
