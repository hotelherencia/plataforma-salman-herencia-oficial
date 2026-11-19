"""Generador de facturas sintéticas (imagen con timbre PDF417 y XML EnvioDTE)
para las pruebas de facturas de proveedores. Sin datos reales."""
from __future__ import annotations

import io

import zxingcpp
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def ted_xml(rut="76123456-0", tipo=33, folio="3797574", total=51253, item="AGUA MINERAL SIN GAS 500 ML"):
    return (f'<TED version="1.0"><DD><RE>{rut}</RE><TD>{tipo}</TD><F>{folio}</F><FE>2026-11-18</FE>'
            f'<RR>76707504-9</RR><RSR>HOTEL HERENCIA</RSR><MNT>{total}</MNT><IT1>{item}</IT1>'
            '<CAF version="1.0"><DA><RE>' + rut + '</RE><RS>PROVEEDOR</RS><TD>' + str(tipo) + '</TD><RNG><D>1</D>'
            '<H>9999999</H></RNG><FA>2026-01-01</FA><RSAPK><M>' + 'A' * 172 + '</M><E>Aw==</E></RSAPK><IDK>100</IDK>'
            '</DA><FRMA algoritmo="SHA1withRSA">' + 'B' * 88 + '</FRMA></CAF><TSTED>2026-11-18T10:00:00</TSTED></DD>'
            '<FRMT algoritmo="SHA1withRSA">' + 'C' * 172 + '</FRMT></TED>')


def _pdf417(texto: str) -> Image.Image:
    codigo = zxingcpp.create_barcode(texto, zxingcpp.BarcodeFormat.PDF417).to_image(scale=3)
    alto, ancho = memoryview(codigo).shape
    return Image.frombytes("L", (ancho, alto), bytes(codigo))


def _fuente(tamano, negrita=False):
    try:
        return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if negrita else ''}.ttf", tamano)
    except OSError:
        return ImageFont.load_default()


def pagina(folio="3797574", rut="76123456-0", tipo=33, con_timbre=True, total=None):
    lineas = [("78016200", "AGUA MINERAL SIN GAS 500 ML CAJA X 24", 2, "CJ", 12000),
              ("", "BEBIDA COLA LATA 350 ML X 6", 3, "UN", 3990)]
    neto = sum(q * p for _, _, q, _, p in lineas)
    total = total or neto + round(neto * 0.19)
    img = Image.new("RGB", (1240, 1754), "white")
    d = ImageDraw.Draw(img)
    f, fb = _fuente(24), _fuente(28, True)
    d.text((60, 60), "DISTRIBUIDORA PRUEBA SPA", font=fb, fill="black")
    d.rectangle((800, 50, 1180, 200), outline="red", width=4)
    d.text((830, 70), f"R.U.T.: {rut}", font=fb, fill="red")
    d.text((830, 110), "FACTURA ELECTRONICA", font=fb, fill="red")
    d.text((830, 150), f"N° {folio}", font=fb, fill="red")
    y = 380
    for c, desc, q, u, p in lineas:
        d.text((60, y), f"{c}  {desc}  {q} {u}  {p}  {q * p}", font=f, fill="black")
        y += 40
    d.text((800, y + 40), f"TOTAL: $ {total}", font=fb, fill="black")
    if con_timbre:
        codigo = _pdf417(ted_xml(rut, tipo, folio, total))
        codigo = codigo.resize((560, int(560 * codigo.height / codigo.width)))
        img.paste(codigo.convert("RGB"), (60, y + 120))
    return img


def jpeg(img: Image.Image, rotacion=0.0, desenfoque=0.0, calidad=85, escala=1) -> bytes:
    """`escala=2` simula la foto de un celular a resolución completa (~2500 px
    de ancho): el timbre necesita ~3 px por módulo para leerse."""
    if escala != 1:
        img = img.resize((img.width * escala, img.height * escala))
    if rotacion:
        img = img.rotate(rotacion, expand=True, fillcolor=(210, 210, 210))
    if desenfoque:
        img = img.filter(ImageFilter.GaussianBlur(desenfoque))
    salida = io.BytesIO()
    img.save(salida, "JPEG", quality=calidad)
    return salida.getvalue()


def pdf(img: Image.Image) -> bytes:
    salida = io.BytesIO()
    img.save(salida, "PDF", resolution=150)
    return salida.getvalue()


def envio_dte(*documentos: str) -> str:
    return ('<?xml version="1.0" encoding="ISO-8859-1"?>\n<EnvioDTE xmlns="http://www.sii.cl/SiiDte" version="1.0">'
            '<SetDTE ID="SetDoc"><Caratula version="1.0"><RutEmisor>76123456-0</RutEmisor></Caratula>'
            + "".join(f'<DTE version="1.0">{d}</DTE>' for d in documentos) + "</SetDTE></EnvioDTE>")


def documento(folio="5001", tipo=33, rut="76123456-0", lineas=(("CJ-AGUA24", "Agua mineral 500 ml caja x 24", 2, 12000),),
              referencia=None):
    detalle = "".join(
        f"<Detalle><NroLinDet>{i + 1}</NroLinDet><CdgItem><TpoCodigo>INT1</TpoCodigo><VlrCodigo>{c}</VlrCodigo></CdgItem>"
        f"<NmbItem>{n}</NmbItem><QtyItem>{q}</QtyItem><UnmdItem>CJ</UnmdItem><PrcItem>{p}</PrcItem>"
        f"<MontoItem>{q * p}</MontoItem></Detalle>"
        for i, (c, n, q, p) in enumerate(lineas))
    neto = sum(q * p for _, _, q, p in lineas)
    iva = round(neto * 0.19)
    ref = (f"<Referencia><NroLinRef>1</NroLinRef><TpoDocRef>801</TpoDocRef><FolioRef>{referencia}</FolioRef>"
           "<FchRef>2026-11-17</FchRef></Referencia>") if referencia else ""
    return (f'<Documento ID="F{folio}"><Encabezado><IdDoc><TipoDTE>{tipo}</TipoDTE><Folio>{folio}</Folio>'
            f"<FchEmis>2026-11-18</FchEmis></IdDoc><Emisor><RUTEmisor>{rut}</RUTEmisor><RznSoc>DISTRIBUIDORA PRUEBA SPA"
            "</RznSoc></Emisor><Receptor><RUTRecep>76707504-9</RUTRecep><RznSocRecep>HOTEL HERENCIA</RznSocRecep>"
            f"</Receptor><Totales><MntNeto>{neto}</MntNeto><IVA>{iva}</IVA><MntTotal>{neto + iva}</MntTotal></Totales>"
            f"</Encabezado>{detalle}{ref}<TED version=\"1.0\"><DD><RE>{rut}</RE><TD>{tipo}</TD><F>{folio}</F>"
            f"<FE>2026-11-18</FE><MNT>{neto + iva}</MNT></DD></TED></Documento>")
