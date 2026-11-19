"""Carga amigable de productos (2026-11-19, pedido del propietario).

Tres fuentes producen la misma «línea leída» y comparten la vista previa,
el emparejamiento con el catálogo y la confirmación:

- `factura_xml`: factura electrónica del SII (DTE 33 afecta / 34 exenta).
  Se leen emisor, folio, fecha y el detalle (NmbItem, QtyItem, PrcItem,
  MontoItem, UnmdItem, CdgItem).
- `planilla`: filas pegadas desde Excel/CSV; el front mapea las columnas y
  envía líneas ya normalizadas.
- `lector`: lector de códigos USB (teclado); el front acumula las lecturas.
- `foto` (reservada): una foto o PDF de factura leída por IA entraría como
  otra fuente que devuelve las mismas líneas; hoy responde «no disponible»
  porque no hay proveedor de IA elegido.

Seguridad del XML: tope de tamaño, se rechaza cualquier DOCTYPE/ENTITY
(sin entidades externas ni expansión tipo «billion laughs») y se parsea con
defusedxml (forbid_dtd/entities/external). La confirmación de una factura
vuelve a leer el XML en el servidor: emisor y folio no se aceptan del
cliente, y el índice único (emisor, tipo, folio) impide importarla dos veces.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
import uuid
import xml.etree.ElementTree as ET
from datetime import date

import psycopg
from defusedxml import DefusedXmlException
from defusedxml import ElementTree as DET

from . import productos as productos_db

MAX_XML_CARACTERES = 1_500_000
MAX_LINEAS = 300
TIPOS_DTE = {33: "Factura electrónica", 34: "Factura exenta electrónica"}
# Notas de crédito: llegan por el correo de intercambio; restan (o se marcan) al revisar.
TIPOS_NOTA_CREDITO = {61: "Nota de crédito electrónica"}
FUENTES = ("factura_xml", "planilla", "lector", "foto")
UMBRAL_PARECIDO = 0.72
_PROHIBIDO = re.compile(r"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)
_DECLARACION = re.compile(r"^\s*<\?xml[^>]*\?>", re.IGNORECASE)


class FacturaInvalida(Exception):
    """422: el archivo no es una factura electrónica que se pueda leer."""


class ImportacionInvalida(Exception):
    """409: la confirmación no se puede aplicar (producto inexistente, etc.)."""


class ImportacionDuplicada(Exception):
    """409: esa factura ya se importó."""

    def __init__(self, mensaje: str, previa: dict):
        super().__init__(mensaje)
        self.previa = previa


class FuenteNoDisponible(Exception):
    """503: la fuente existe en el diseño pero no está configurada (foto/IA)."""


# ---------------------------------------------------------------- lectura XML

def _local(etiqueta: str) -> str:
    return etiqueta.rsplit("}", 1)[-1]


def _hijo(elemento, nombre: str):
    for h in elemento:
        if _local(h.tag) == nombre:
            return h
    return None


def _texto(elemento, *ruta: str) -> str | None:
    actual = elemento
    for nombre in ruta:
        if actual is None:
            return None
        actual = _hijo(actual, nombre)
    if actual is None or actual.text is None:
        return None
    return actual.text.strip() or None


def _numero(valor: str | None) -> float | None:
    if valor is None:
        return None
    try:
        n = float(valor.replace(",", "."))
    except ValueError:
        return None
    return n if n == n and abs(n) < 1e12 else None


def normalizar_rut_emisor(rut: str | None) -> str | None:
    if not rut:
        return None
    limpio = re.sub(r"[.\s]", "", rut).upper()
    return limpio if re.fullmatch(r"\d{1,8}-[0-9K]", limpio) else None


def _raiz_xml(contenido: str | bytes):
    """Parseo seguro: tope de tamaño, sin DOCTYPE/ENTITY (defusedxml + filtro
    previo) y sin recursos externos. Bytes respetan la codificación declarada
    (los DTE suelen venir en ISO-8859-1)."""
    if isinstance(contenido, bytes):
        if len(contenido) > MAX_XML_CARACTERES:
            raise FacturaInvalida("El archivo es demasiado grande para una factura (máximo 1,5 MB).")
        if _PROHIBIDO.search(contenido.decode("latin-1")):
            raise FacturaInvalida("El archivo trae definiciones no permitidas y no se puede leer por seguridad.")
        datos = contenido.lstrip(b"\xef\xbb\xbf")
    else:
        if not isinstance(contenido, str) or not contenido.strip():
            raise FacturaInvalida("El archivo está vacío.")
        if len(contenido) > MAX_XML_CARACTERES:
            raise FacturaInvalida("El archivo es demasiado grande para una factura (máximo 1,5 MB).")
        if _PROHIBIDO.search(contenido):
            raise FacturaInvalida("El archivo trae definiciones no permitidas y no se puede leer por seguridad.")
        datos = _DECLARACION.sub("", contenido.lstrip("\ufeff"), count=1)
    if not datos.strip():
        raise FacturaInvalida("El archivo está vacío.")
    try:
        return DET.fromstring(datos, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except DefusedXmlException as error:
        raise FacturaInvalida("El archivo trae definiciones no permitidas y no se puede leer por seguridad.") from error
    except (ET.ParseError, ValueError) as error:
        raise FacturaInvalida("El archivo no es un XML válido. Descarga nuevamente el XML de la factura desde el SII o tu proveedor.") from error


def documentos_xml(raiz) -> list:
    return [e for e in raiz.iter() if _local(e.tag) == "Documento"]


def _ted_de(doc) -> dict | None:
    from . import ted as ted_mod

    nodo = next((e for e in doc.iter() if _local(e.tag) == "TED"), None)
    if nodo is None:
        return None
    try:
        return ted_mod.parsear_ted(ET.tostring(nodo, encoding="unicode"))
    except ted_mod.TimbreIlegible:
        return None


def leer_documento_dte(doc, tipos: dict | None = None) -> dict:
    """Un nodo <Documento> → {documento, lineas, ted}. `tipos`: los TipoDTE
    aceptados (por defecto facturas 33/34)."""
    tipos = tipos or TIPOS_DTE
    encabezado = _hijo(doc, "Encabezado")
    if encabezado is None:
        raise FacturaInvalida("La factura no trae encabezado (emisor, folio y fecha).")
    tipo = _numero(_texto(encabezado, "IdDoc", "TipoDTE"))
    tipo = int(tipo) if tipo is not None else None
    if tipo not in tipos:
        raise FacturaInvalida("Solo se pueden cargar facturas electrónicas (tipo 33 o 34). Este documento es de otro tipo.")
    es_nota = tipo in TIPOS_NOTA_CREDITO
    folio = _texto(encabezado, "IdDoc", "Folio")
    if not folio or not re.fullmatch(r"\d{1,12}", folio):
        raise FacturaInvalida("La factura no trae un folio válido.")
    folio = str(int(folio))
    rut = normalizar_rut_emisor(_texto(encabezado, "Emisor", "RUTEmisor"))
    if not rut:
        raise FacturaInvalida("La factura no trae un RUT de emisor válido.")
    razon = _texto(encabezado, "Emisor", "RznSoc") or _texto(encabezado, "Emisor", "RznSocEmisor") or ""
    fecha_txt = _texto(encabezado, "IdDoc", "FchEmis")
    try:
        fecha = date.fromisoformat(fecha_txt) if fecha_txt else None
    except ValueError:
        fecha = None
    totales = _hijo(encabezado, "Totales")
    lineas = []
    for detalle in (d for d in doc if _local(d.tag) == "Detalle"):
        nombre = (_texto(detalle, "NmbItem") or "").strip()
        if not nombre:
            continue
        codigo = None
        for cdg in (c for c in detalle if _local(c.tag) == "CdgItem"):
            codigo = _texto(cdg, "VlrCodigo")
            if codigo:
                break
        cantidad = _numero(_texto(detalle, "QtyItem"))
        precio = _numero(_texto(detalle, "PrcItem"))
        monto = _numero(_texto(detalle, "MontoItem"))
        descuento = _numero(_texto(detalle, "DescuentoMonto"))
        if cantidad is not None and cantidad > 0 and monto is not None:
            costo = round(monto / cantidad)
        else:
            costo = round(precio) if precio is not None else None
        lineas.append({
            "linea": len(lineas) + 1,
            "codigo": (codigo or "")[:60] or None,
            "nombre": nombre[:120],
            "descripcion": ((_texto(detalle, "DscItem") or "")[:200] or None),
            "cantidad": cantidad if cantidad is not None else 1,
            "unidad": (_texto(detalle, "UnmdItem") or "")[:20] or None,
            "costo_unitario_clp": costo if costo is None or costo >= 0 else None,
            "precio_unitario_clp": round(precio) if precio is not None else None,
            "descuento_clp": round(descuento) if descuento is not None else None,
            "monto_neto_clp": round(monto) if monto is not None else None,
        })
        if len(lineas) > MAX_LINEAS:
            raise FacturaInvalida(f"La factura trae más de {MAX_LINEAS} líneas; divídela en cargas más pequeñas.")
    if not lineas and not es_nota:
        raise FacturaInvalida("La factura no trae líneas de detalle con productos.")
    referencias = []
    for ref in (r for r in doc if _local(r.tag) == "Referencia"):
        referencias.append({
            "tipo": (_texto(ref, "TpoDocRef") or "")[:10] or None,
            "folio": (_texto(ref, "FolioRef") or "")[:20] or None,
            "fecha": (_texto(ref, "FchRef") or "")[:10] or None,
            "codigo": (_texto(ref, "CodRef") or "")[:2] or None,
            "razon": (_texto(ref, "RazonRef") or "")[:120] or None,
        })
    nombres = {**TIPOS_DTE, **TIPOS_NOTA_CREDITO}
    documento = {
        "tipo_dte": tipo,
        "tipo_nombre": nombres.get(tipo, f"Documento tipo {tipo}"),
        "folio": folio,
        "fecha_emision": fecha.isoformat() if fecha else None,
        "emisor_rut": rut,
        "emisor_razon_social": razon[:150],
        "receptor_rut": normalizar_rut_emisor(_texto(encabezado, "Receptor", "RUTRecep")),
        "receptor_razon_social": (_texto(encabezado, "Receptor", "RznSocRecep") or "")[:150] or None,
        "monto_neto_clp": _entero(_texto(totales, "MntNeto")) if totales is not None else None,
        "monto_exento_clp": _entero(_texto(totales, "MntExe")) if totales is not None else None,
        "iva_clp": _entero(_texto(totales, "IVA")) if totales is not None else None,
        "monto_total_clp": _entero(_texto(totales, "MntTotal")) if totales is not None else None,
        "referencias": referencias,
    }
    return {"documento": documento, "lineas": lineas, "ted": _ted_de(doc)}


def leer_factura_xml(texto: str) -> dict:
    """Devuelve {documento, lineas} de un DTE 33/34. Lanza FacturaInvalida
    con un mensaje en castellano para la recepción."""
    raiz = _raiz_xml(texto)
    documentos = documentos_xml(raiz)
    if not documentos:
        raise FacturaInvalida("El archivo no parece una factura electrónica del SII (no trae el documento).")
    if len(documentos) > 1:
        raise FacturaInvalida(f"El archivo trae {len(documentos)} documentos. Sube una factura por vez.")
    leido = leer_documento_dte(documentos[0])
    return {"documento": leido["documento"], "lineas": leido["lineas"]}


def _entero(valor: str | None) -> int | None:
    n = _numero(valor)
    return round(n) if n is not None else None


def leer_fuente(origen: str, xml: str | None, lineas: list[dict] | None) -> dict:
    """Punto único de entrada: cada fuente devuelve {documento, lineas}."""
    if origen == "factura_xml":
        return leer_factura_xml(xml or "")
    if origen in ("planilla", "lector"):
        if not lineas:
            raise FacturaInvalida("No hay filas para cargar.")
        return {"documento": None, "lineas": [dict(l, linea=i + 1) for i, l in enumerate(lineas)]}
    if origen == "foto":
        raise FuenteNoDisponible(
            "La lectura de facturas desde foto o PDF requiere activar un proveedor de inteligencia artificial."
        )
    raise FacturaInvalida("Origen de carga desconocido.")


# ----------------------------------------------------------- emparejamiento

def normalizar_nombre(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFKD", texto or "") if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sin_tildes.lower()).split())


def _catalogo(conexion: psycopg.Connection) -> list[dict]:
    return [
        {"producto_id": f[0], "nombre": f[1], "categoria": f[2], "precio_clp": f[3], "activo": f[4],
         "controla_stock": f[5], "stock": f[6] if f[5] else None, "codigo": f[7], "costo_clp": f[8]}
        for f in conexion.execute(
            "SELECT id, nombre, categoria, precio_clp, activo, controla_stock, stock, codigo, costo_clp FROM productos"
        ).fetchall()
    ]


def _parecido(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    # Otro formato (500 ml / 1500 ml, 350 ml / 1,5 L) es otro producto: no se sugiere sumarlo.
    if sorted(re.findall(r"\d+", a)) != sorted(re.findall(r"\d+", b)):
        return 0.0
    base = difflib.SequenceMatcher(None, a, b).ratio()
    pa, pb = set(a.split()), set(b.split())
    jaccard = len(pa & pb) / len(pa | pb) if pa | pb else 0
    contenido = 1.0 if (a in b or b in a) and min(len(a), len(b)) >= 4 else 0
    return max(base, jaccard, 0.8 * contenido)


def emparejar(conexion: psycopg.Connection, lineas: list[dict]) -> list[dict]:
    """Agrega a cada línea `coincidencia` (producto del catálogo o None) y
    `confianza`: 'codigo' | 'nombre' | 'parecido' | None."""
    catalogo = _catalogo(conexion)
    por_codigo = {p["codigo"].lower(): p for p in catalogo if p["codigo"]}
    por_nombre = {normalizar_nombre(p["nombre"]): p for p in catalogo}
    resultado = []
    for linea in lineas:
        codigo = (linea.get("codigo") or "").strip().lower()
        nombre = normalizar_nombre(linea.get("nombre") or "")
        producto, confianza, puntaje = None, None, None
        if codigo and codigo in por_codigo:
            producto, confianza, puntaje = por_codigo[codigo], "codigo", 1.0
        elif nombre and nombre in por_nombre:
            producto, confianza, puntaje = por_nombre[nombre], "nombre", 1.0
        elif nombre:
            mejor = max(catalogo, key=lambda p: _parecido(nombre, normalizar_nombre(p["nombre"])), default=None)
            if mejor is not None:
                p = _parecido(nombre, normalizar_nombre(mejor["nombre"]))
                if p >= UMBRAL_PARECIDO:
                    producto, confianza, puntaje = mejor, "parecido", round(p, 2)
        resultado.append({**linea, "coincidencia": producto, "confianza": confianza, "puntaje": puntaje})
    return resultado


def importacion_previa(conexion: psycopg.Connection, documento: dict | None) -> dict | None:
    if not documento:
        return None
    fila = conexion.execute(
        "SELECT id, creado_en, actor, lineas, unidades FROM importaciones_productos "
        "WHERE emisor_rut = %s AND tipo_dte = %s AND folio = %s",
        (documento["emisor_rut"], documento["tipo_dte"], documento["folio"]),
    ).fetchone()
    if fila is None:
        return None
    return {"importacion_id": fila[0], "registrada_en": fila[1].isoformat(), "actor": fila[2],
            "lineas": fila[3], "unidades": fila[4]}


def vista_previa(conexion: psycopg.Connection, origen: str, xml: str | None, lineas: list[dict] | None) -> dict:
    leido = leer_fuente(origen, xml, lineas)
    return {
        "origen": origen,
        "documento": leido["documento"],
        "lineas": emparejar(conexion, leido["lineas"]),
        "ya_importada": importacion_previa(conexion, leido["documento"]),
    }


# ------------------------------------------------------------- confirmación

def _motivo(origen: str, documento: dict | None) -> str:
    if origen == "factura_xml" and documento:
        razon = documento.get("emisor_razon_social") or documento["emisor_rut"]
        return f"Factura N° {documento['folio']} · {razon}"[:200]
    return {"planilla": "Carga desde planilla", "lector": "Ingreso con lector de códigos"}.get(origen, "Carga de productos")


def _codigo_libre(conexion, codigo: str | None, excepto: str | None = None) -> bool:
    if not codigo:
        return False
    fila = conexion.execute(
        "SELECT id FROM productos WHERE lower(codigo) = lower(%s)", (codigo,)
    ).fetchone()
    return fila is None or fila[0] == excepto


def confirmar(conexion: psycopg.Connection, origen: str, documento: dict | None, lineas: list[dict], actor: str) -> dict:
    """Aplica la carga en una sola transacción: crea los productos nuevos,
    suma el stock (con movimiento referido a la carga) y actualiza costo,
    código y, si se indicó, el precio de venta. Todo o nada."""
    activas = [l for l in lineas if l["accion"] != "omitir"]
    if not activas:
        raise ImportacionInvalida("No hay líneas para cargar: todas quedaron omitidas.")
    importacion_id = f"IMP-{uuid.uuid4().hex[:12]}"
    motivo = _motivo(origen, documento)
    creados, actualizados, unidades, sin_stock = 0, 0, 0, 0
    detalle = []
    try:
        with conexion.transaction():
            conexion.execute(
                "INSERT INTO importaciones_productos (id, origen, emisor_rut, emisor_razon_social, tipo_dte, folio, "
                "fecha_emision, lineas, total_neto_clp, actor) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (importacion_id, origen,
                 documento and documento.get("emisor_rut"), documento and documento.get("emisor_razon_social"),
                 documento and documento.get("tipo_dte"), documento and documento.get("folio"),
                 documento and documento.get("fecha_emision"), len(activas),
                 documento and documento.get("monto_neto_clp"), actor),
            )
            nuevos_por_nombre: dict[str, str] = {}
            for linea in activas:
                cantidad = int(linea.get("cantidad") or 0)
                costo = linea.get("costo_unitario_clp")
                codigo = (linea.get("codigo") or "").strip() or None
                if linea["accion"] == "crear":
                    clave_nombre = normalizar_nombre(linea["nombre"])
                    if clave_nombre in nuevos_por_nombre:
                        linea = {**linea, "accion": "sumar", "producto_id": nuevos_por_nombre[clave_nombre], "precio_clp": None}
                    else:
                        if not linea.get("precio_clp"):
                            raise ImportacionInvalida(f"Falta el precio de venta de «{linea['nombre']}».")
                        if codigo and not _codigo_libre(conexion, codigo):
                            raise ImportacionInvalida(f"El código {codigo} ya pertenece a otro producto: elige «sumar a existente».")
                        controla = bool(linea.get("controla_stock", True))
                        producto_id = f"PRD-{uuid.uuid4().hex[:10]}"
                        try:
                            with conexion.transaction():
                                conexion.execute(
                                    "INSERT INTO productos (id, nombre, categoria, precio_clp, controla_stock, stock, codigo, costo_clp) "
                                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                                    (producto_id, linea["nombre"].strip(), linea["categoria"], linea["precio_clp"],
                                     controla, cantidad if controla else 0, codigo, costo),
                                )
                        except psycopg.errors.UniqueViolation as error:
                            raise ImportacionInvalida(
                                f"Ya existe un producto llamado «{linea['nombre'].strip()}»: elige «sumar a existente»."
                            ) from error
                        nuevos_por_nombre[clave_nombre] = producto_id
                        if controla and cantidad:
                            productos_db._movimiento(conexion, producto_id, cantidad, motivo, actor,
                                                     importacion_id=importacion_id)
                            unidades += cantidad
                        elif not controla:
                            sin_stock += 1
                        creados += 1
                        detalle.append({"nombre": linea["nombre"].strip(), "accion": "creado", "producto_id": producto_id,
                                        "cantidad": cantidad if controla else 0})
                        continue
                # sumar a un producto existente
                producto_id = linea.get("producto_id")
                if not producto_id:
                    raise ImportacionInvalida(f"Elige a qué producto sumar «{linea['nombre']}».")
                try:
                    producto = productos_db.obtener(conexion, producto_id, bloqueo=True)
                except productos_db.ProductoInvalido as error:
                    raise ImportacionInvalida(f"El producto elegido para «{linea['nombre']}» ya no existe.") from error
                cambios, valores = ["actualizado_en = now()"], []
                if costo is not None:
                    cambios.append("costo_clp = %s")
                    valores.append(costo)
                if codigo and _codigo_libre(conexion, codigo, excepto=producto_id):
                    cambios.append("codigo = COALESCE(codigo, %s)")
                    valores.append(codigo)
                if linea.get("precio_clp") and linea["precio_clp"] != producto["precio_clp"]:
                    cambios.append("precio_clp = %s")
                    valores.append(linea["precio_clp"])
                suma = cantidad if producto["controla_stock"] else 0
                if suma:
                    cambios.append("stock = stock + %s")
                    valores.append(suma)
                conexion.execute(f"UPDATE productos SET {', '.join(cambios)} WHERE id = %s", (*valores, producto_id))
                if suma:
                    productos_db._movimiento(conexion, producto_id, suma, motivo, actor,
                                             importacion_id=importacion_id)
                    unidades += suma
                elif cantidad:
                    sin_stock += 1
                actualizados += 1
                detalle.append({"nombre": producto["nombre"], "accion": "sumado", "producto_id": producto_id, "cantidad": suma})
            conexion.execute(
                "UPDATE importaciones_productos SET unidades = %s, productos_nuevos = %s WHERE id = %s",
                (unidades, creados, importacion_id),
            )
    except psycopg.errors.UniqueViolation as error:
        if not documento:
            raise ImportacionInvalida("Otro usuario cambió el catálogo al mismo tiempo. Revisa y vuelve a confirmar.") from error
        previa = importacion_previa(conexion, documento) or {}
        raise ImportacionDuplicada(
            f"La factura N° {documento['folio']} de {documento.get('emisor_razon_social') or documento['emisor_rut']} ya fue cargada"
            " antes: el stock no se suma dos veces.",
            previa,
        ) from error
    return {
        "importacion_id": importacion_id,
        "origen": origen,
        "documento": documento,
        "creados": creados,
        "actualizados": actualizados,
        "unidades": unidades,
        "sin_control_de_stock": sin_stock,
        "omitidas": len(lineas) - len(activas),
        "detalle": detalle,
    }


def historial(conexion: psycopg.Connection, limite: int = 15) -> list[dict]:
    return [
        {"importacion_id": f[0], "origen": f[1], "emisor_razon_social": f[2], "emisor_rut": f[3], "folio": f[4],
         "fecha_emision": f[5].isoformat() if f[5] else None, "lineas": f[6], "unidades": f[7],
         "productos_nuevos": f[8], "actor": f[9], "registrada_en": f[10].isoformat()}
        for f in conexion.execute(
            "SELECT id, origen, emisor_razon_social, emisor_rut, folio, fecha_emision, lineas, unidades, "
            "productos_nuevos, actor, creado_en FROM importaciones_productos ORDER BY creado_en DESC LIMIT %s",
            (limite,),
        ).fetchall()
    ]
