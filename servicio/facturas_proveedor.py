"""Facturas de proveedores: bandeja de documentos por revisar (2026-11-19).

Pedido del propietario: «hacer todavía más fácil la carga de productos».
Todo documento de un proveedor entra a una bandeja y espera la revisión de
la administración; NADA toca el stock hasta que se confirma.

Entradas
- `correo`: buzón de intercambio del SII (propósito `recepcion_dte`): los
  XML EnvioDTE que llegan (facturas 33/34 y notas de crédito 61).
- `xml`: el XML subido a mano.
- `foto` / `pdf`: la foto del celular o el PDF. Se lee el timbre del SII
  (PDF417) para identificar el documento sin IA y, si hay proveedor de
  visión configurado, se transcriben las líneas. Sin IA, la administración
  completa las líneas a mano (la foto queda a la vista).

Clases: factura, nota_credito (se marca y se archiva: no descuenta stock
sola), pedido (orden/nota de pedido: borrador sin stock hasta que llegue la
factura) y desconocido (la administración elige).

Un documento (proveedor + tipo + folio) entra una sola vez, venga por donde
venga, y una factura ya cargada al inventario no se vuelve a cargar.

Envases: al confirmar se recuerda, por proveedor + ítem, a qué producto
corresponde y cuántas unidades trae cada envase («Caja x 18» = 18).
"""
from __future__ import annotations

import hashlib
import os
import uuid

import psycopg
from psycopg.types.json import Jsonb

from . import importacion_productos as importacion
from . import ted as ted_mod
from . import unidades_paquete as paquetes
from . import vision

MAX_ARCHIVO = 10 * 1024 * 1024
MIME_IMAGEN = ("image/jpeg", "image/png", "image/webp")
MIME_PERMITIDOS = MIME_IMAGEN + ("application/pdf",)
CLASES = ("factura", "nota_credito", "pedido", "desconocido")
ESTADOS_ABIERTOS = ("pendiente", "borrador")


class DocumentoInvalido(Exception):
    """422: archivo o datos que no se pueden usar."""


class DocumentoNoEncontrado(Exception):
    """404."""


class DocumentoEnConflicto(Exception):
    """409: estado que no permite la operación, o duplicado."""

    def __init__(self, mensaje: str, documento_id: str | None = None):
        super().__init__(mensaje)
        self.documento_id = documento_id


# ------------------------------------------------------------ utilidades

def tipo_real(contenido: bytes) -> str | None:
    """Tipo según los primeros bytes (no se confía en la cabecera del navegador)."""
    if contenido.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return "image/webp"
    if contenido.startswith(b"%PDF-"):
        return "application/pdf"
    return None


def rut_hotel() -> str | None:
    return importacion.normalizar_rut_emisor(os.environ.get("EMPRESA_RUT"))


def _id(prefijo: str) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:12]}"


def guardar_archivo(conexion: psycopg.Connection, contenido: bytes, tipo_mime: str, nombre: str | None, actor: str) -> tuple[str, bool]:
    """Guarda el archivo (o reutiliza uno idéntico). Devuelve (id, ya_existía)."""
    if not contenido:
        raise DocumentoInvalido("El archivo está vacío.")
    if len(contenido) > MAX_ARCHIVO:
        raise DocumentoInvalido("El archivo es demasiado grande (máximo 10 MB). Reduce la foto o el PDF.")
    sha = hashlib.sha256(contenido).hexdigest()
    fila = conexion.execute("SELECT id FROM archivos_documentos WHERE sha256 = %s", (sha,)).fetchone()
    if fila:
        return fila[0], True
    archivo_id = _id("ARC")
    conexion.execute(
        "INSERT INTO archivos_documentos (id, sha256, tipo_mime, tamano, contenido, nombre, creado_por) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (archivo_id, sha, tipo_mime, len(contenido), contenido, (nombre or "")[:120] or None, actor),
    )
    return archivo_id, False


def leer_archivo(conexion: psycopg.Connection, documento_id: str) -> tuple[bytes, str]:
    fila = conexion.execute(
        "SELECT a.contenido, a.tipo_mime FROM documentos_proveedor d JOIN archivos_documentos a ON a.id = d.archivo_id "
        "WHERE d.id = %s", (documento_id,),
    ).fetchone()
    if not fila:
        raise DocumentoNoEncontrado("El documento no tiene archivo.")
    return bytes(fila[0]), fila[1]


def _existente(conexion, clase: str, emisor: str | None, tipo: int | None, folio: str | None):
    if not emisor or not folio:
        return None
    return conexion.execute(
        "SELECT id, estado FROM documentos_proveedor WHERE clase = %s AND emisor_rut = %s "
        "AND coalesce(tipo_dte, 0) = %s AND folio = %s ORDER BY (estado = 'descartada'), creado_en DESC LIMIT 1",
        (clase, emisor, tipo or 0, folio),
    ).fetchone()


def _insertar(conexion, *, clase, origen, lectura, documento, lineas, ted, referencias, discrepancias, actor,
              archivo_id=None, buzon_id=None, mensaje_id=None, remitente=None) -> str:
    documento_id = _id("DOC")
    estado = "borrador" if clase == "pedido" else "pendiente"
    conexion.execute(
        "INSERT INTO documentos_proveedor (id, clase, origen, estado, lectura, emisor_rut, emisor_razon_social, tipo_dte, "
        "folio, fecha_emision, monto_neto_clp, monto_exento_clp, iva_clp, monto_total_clp, lineas, ted, referencias, "
        "discrepancias, archivo_id, buzon_id, mensaje_id, remitente, actor) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (documento_id, clase, origen, estado, lectura, documento.get("emisor_rut"), documento.get("emisor_razon_social"),
         documento.get("tipo_dte"), documento.get("folio"), documento.get("fecha_emision"),
         documento.get("monto_neto_clp"), documento.get("monto_exento_clp"), documento.get("iva_clp"),
         documento.get("monto_total_clp"), Jsonb(lineas), Jsonb(ted) if ted else None, Jsonb(referencias or []),
         Jsonb(discrepancias), archivo_id, buzon_id, (mensaje_id or "")[:200] or None, (remitente or "")[:200] or None, actor),
    )
    return documento_id


# ------------------------------------------------------- entrada por XML

def crear_desde_xml(conexion: psycopg.Connection, contenido: bytes | str, origen: str, actor: str,
                    buzon_id: str | None = None, mensaje_id: str | None = None, remitente: str | None = None) -> dict:
    """XML del SII (DTE suelto o EnvioDTE con varios) → documentos pendientes.
    Devuelve {creados, repetidos, ignorados} (listas de dicts breves)."""
    raiz = importacion._raiz_xml(contenido)
    nombre_raiz = importacion._local(raiz.tag)
    resultado = {"creados": [], "repetidos": [], "ignorados": []}
    if nombre_raiz in ("RespuestaDTE", "EnvioRecibos", "ResultadoDTE", "RecepcionEnvio"):
        resultado["ignorados"].append({"motivo": "acuse o respuesta del SII (no es una factura)"})
        return resultado
    documentos = importacion.documentos_xml(raiz)
    if not documentos:
        raise importacion.FacturaInvalida("El archivo no parece una factura electrónica del SII (no trae el documento).")
    aceptados = {**importacion.TIPOS_DTE, **importacion.TIPOS_NOTA_CREDITO}
    archivo_id = None
    for nodo in documentos[:50]:
        try:
            leido = importacion.leer_documento_dte(nodo, aceptados)
        except importacion.FacturaInvalida as error:
            resultado["ignorados"].append({"motivo": str(error)})
            continue
        doc = leido["documento"]
        clase = "nota_credito" if doc["tipo_dte"] in importacion.TIPOS_NOTA_CREDITO else "factura"
        existe = _existente(conexion, clase, doc["emisor_rut"], doc["tipo_dte"], doc["folio"])
        ya_importada = importacion.importacion_previa(conexion, doc)
        if existe or ya_importada:
            resultado["repetidos"].append({"documento_id": existe[0] if existe else None, "folio": doc["folio"],
                                           "emisor_rut": doc["emisor_rut"]})
            continue
        if archivo_id is None:
            datos = contenido if isinstance(contenido, bytes) else contenido.encode("utf-8")
            archivo_id, _ = guardar_archivo(conexion, datos, "application/xml", "factura.xml", actor)
        lineas = leido["lineas"]
        discrepancias = vision.validar(doc, lineas, leido["ted"], rut_hotel())
        discrepancias = [d for d in discrepancias if d["codigo"] not in ("sin_precio",)] if clase == "nota_credito" else discrepancias
        if clase == "nota_credito":
            discrepancias.insert(0, {"codigo": "nota_credito",
                                     "mensaje": "Nota de crédito: no descuenta stock sola. Revisa y ajusta el stock si corresponde."})
        documento_id = _insertar(conexion, clase=clase, origen=origen, lectura="xml", documento=doc, lineas=lineas,
                                 ted=leido["ted"], referencias=doc.get("referencias"), discrepancias=discrepancias,
                                 actor=actor, archivo_id=archivo_id, buzon_id=buzon_id, mensaje_id=mensaje_id,
                                 remitente=remitente)
        resultado["creados"].append({"documento_id": documento_id, "clase": clase, "folio": doc["folio"],
                                     "emisor_rut": doc["emisor_rut"]})
    return resultado


# --------------------------------------------------- entrada por foto/PDF

def crear_desde_archivo(conexion: psycopg.Connection, contenido: bytes, tipo_mime: str, nombre: str | None, actor: str,
                        proveedor=None, usar_vision: bool = True) -> dict:
    """Foto o PDF → documento en la bandeja. Lee el timbre (sin IA) y, si hay
    proveedor de visión, las líneas. Devuelve {documento_id, repetido}."""
    real = tipo_real(contenido or b"")
    if real is None or real not in MIME_PERMITIDOS:
        raise DocumentoInvalido("Sube una foto (JPG, PNG o WebP) o un PDF de la factura.")
    if tipo_mime and tipo_mime != real and not (tipo_mime == "image/jpg" and real == "image/jpeg"):
        raise DocumentoInvalido("El archivo no es del tipo que dice ser.")
    archivo_id, ya_existia = guardar_archivo(conexion, contenido, real, nombre, actor)
    if ya_existia:
        fila = conexion.execute(
            "SELECT id FROM documentos_proveedor WHERE archivo_id = %s AND estado <> 'descartada' ORDER BY creado_en DESC LIMIT 1",
            (archivo_id,),
        ).fetchone()
        if fila:
            return {"documento_id": fila[0], "repetido": True}
    timbre = ted_mod.leer_timbre(contenido, real)
    documento: dict = {}
    lineas: list[dict] = []
    clase = "desconocido"
    lectura = "manual"
    aviso_ia = None
    if proveedor is None and usar_vision:
        try:
            proveedor = vision.proveedor_configurado()
        except vision.VisionNoConfigurada:
            proveedor = None
    if proveedor is not None:
        try:
            extraido = vision.normalizar(proveedor.extraer(contenido, real))
            documento, lineas, clase, lectura = extraido["documento"], extraido["lineas"], extraido["clase"], "ia"
        except vision.VisionFallida as error:
            aviso_ia = f"La lectura automática no respondió ({error}). Completa las líneas a mano."
    if timbre:
        # El timbre manda: es el dato oficial del SII.
        documento = {**documento, "emisor_rut": timbre["emisor_rut"], "tipo_dte": timbre["tipo_dte"],
                     "folio": timbre["folio"], "fecha_emision": timbre["fecha_emision"] or documento.get("fecha_emision")}
        if documento.get("monto_total_clp") is None:
            documento["monto_total_clp"] = timbre["monto_total_clp"]
        clase = "nota_credito" if timbre["tipo_dte"] == 61 else ("factura" if timbre["tipo_dte"] in (33, 34) else clase)
        if lectura == "manual":
            lectura = "timbre"
    elif clase == "factura" and not documento.get("tipo_dte"):
        documento["tipo_dte"] = 33
    if clase == "pedido":
        documento["tipo_dte"] = None
    if clase == "nota_credito" and not documento.get("tipo_dte"):
        documento["tipo_dte"] = 61
    existe = _existente(conexion, clase, documento.get("emisor_rut"), documento.get("tipo_dte"), documento.get("folio"))
    if existe and existe[1] != "descartada":
        return {"documento_id": existe[0], "repetido": True}
    discrepancias = vision.validar(documento, lineas, timbre, rut_hotel()) if lineas or timbre else []
    if proveedor is None and not lineas:
        discrepancias.insert(0, {"codigo": "sin_lectura",
                                 "mensaje": "La lectura automática de líneas no está activada: escribe las líneas mirando la foto."})
    if aviso_ia:
        discrepancias.insert(0, {"codigo": "ia_fallo", "mensaje": aviso_ia})
    if not timbre and clase in ("factura", "nota_credito", "desconocido"):
        discrepancias.append({"codigo": "sin_timbre",
                              "mensaje": "No se pudo leer el timbre del SII: confirma el RUT del proveedor y el folio."})
    if clase == "nota_credito":
        discrepancias.insert(0, {"codigo": "nota_credito",
                                 "mensaje": "Nota de crédito: no descuenta stock sola. Revisa y ajusta el stock si corresponde."})
    origen = "pdf" if real == "application/pdf" else "foto"
    try:
        with conexion.transaction():
            documento_id = _insertar(conexion, clase=clase, origen=origen, lectura=lectura, documento=documento,
                                     lineas=lineas, ted=timbre, referencias=[], discrepancias=discrepancias,
                                     actor=actor, archivo_id=archivo_id)
    except psycopg.errors.UniqueViolation:
        existe = _existente(conexion, clase, documento.get("emisor_rut"), documento.get("tipo_dte"), documento.get("folio"))
        return {"documento_id": existe[0] if existe else None, "repetido": True}
    return {"documento_id": documento_id, "repetido": False}


# ----------------------------------------------------------- consulta

_COLUMNAS = ("id, clase, origen, estado, lectura, emisor_rut, emisor_razon_social, tipo_dte, folio, fecha_emision, "
             "monto_neto_clp, monto_exento_clp, iva_clp, monto_total_clp, lineas, ted, referencias, discrepancias, "
             "archivo_id, remitente, importacion_id, pedido_id, actor, creado_en, actualizado_en")


def _vista(f) -> dict:
    return {
        "documento_id": f[0], "clase": f[1], "origen": f[2], "estado": f[3], "lectura": f[4],
        "emisor_rut": f[5], "emisor_razon_social": f[6], "tipo_dte": f[7],
        "tipo_nombre": ted_mod.TIPOS_CONOCIDOS.get(f[7]) if f[7] else ("Pedido" if f[1] == "pedido" else None),
        "folio": f[8], "fecha_emision": f[9].isoformat() if f[9] else None,
        "monto_neto_clp": f[10], "monto_exento_clp": f[11], "iva_clp": f[12], "monto_total_clp": f[13],
        "lineas": f[14] or [], "ted": f[15], "referencias": f[16] or [], "discrepancias": f[17] or [],
        "tiene_archivo": bool(f[18]), "remitente": f[19], "importacion_id": f[20], "pedido_id": f[21],
        "actor": f[22], "creado_en": f[23].isoformat(), "actualizado_en": f[24].isoformat(),
    }


def _fila(conexion, documento_id: str, bloquear: bool = False):
    fila = conexion.execute(
        f"SELECT {_COLUMNAS} FROM documentos_proveedor WHERE id = %s{' FOR UPDATE' if bloquear else ''}", (documento_id,)
    ).fetchone()
    if fila is None:
        raise DocumentoNoEncontrado("No existe ese documento.")
    return fila


def listar(conexion: psycopg.Connection, estados: tuple[str, ...] = ESTADOS_ABIERTOS, limite: int = 50) -> list[dict]:
    filas = conexion.execute(
        f"SELECT {_COLUMNAS} FROM documentos_proveedor WHERE estado = ANY(%s) ORDER BY creado_en DESC LIMIT %s",
        (list(estados), limite),
    ).fetchall()
    salida = []
    for f in filas:
        v = _vista(f)
        v["cantidad_lineas"] = len(v.pop("lineas"))
        v.pop("ted", None)
        salida.append(v)
    return salida


def _equivalencias(conexion, emisor: str | None) -> dict:
    if not emisor:
        return {}
    return {f[0]: {"producto_id": f[1], "unidades_por_paquete": f[2], "nota": f[3], "equivalencia_id": f[4]}
            for f in conexion.execute(
                "SELECT e.clave, e.producto_id, e.unidades_por_paquete, e.nota, e.id FROM equivalencias_proveedor e "
                "JOIN productos p ON p.id = e.producto_id WHERE e.emisor_rut = %s", (emisor,)).fetchall()}


def lineas_para_revision(conexion, emisor: str | None, lineas: list[dict]) -> list[dict]:
    """Empareja con el catálogo y aplica lo recordado del proveedor; sugiere
    unidades por envase y lee la nota manuscrita («166und x 690»)."""
    recordadas = _equivalencias(conexion, emisor)
    catalogo = {p["producto_id"]: p for p in importacion._catalogo(conexion)}
    base = [{**l, "nombre": l.get("nombre") or "", "cantidad": l.get("cantidad") if l.get("cantidad") is not None else 0}
            for l in lineas]
    emparejadas = importacion.emparejar(conexion, base)
    salida = []
    for linea in emparejadas:
        clave = paquetes.clave_item(linea.get("codigo"), linea.get("nombre"))
        eq = recordadas.get(clave)
        factor, origen_factor = 1, None
        if eq and eq["producto_id"] in catalogo:
            linea["coincidencia"] = {k: catalogo[eq["producto_id"]][k] for k in
                                     ("producto_id", "nombre", "categoria", "precio_clp", "activo", "controla_stock", "stock", "codigo")}
            linea["confianza"] = "recordado"
            linea["puntaje"] = 1.0
            factor, origen_factor = eq["unidades_por_paquete"], "recordado"
        else:
            sugerido = paquetes.unidades_por_paquete(linea.get("nombre"), linea.get("descripcion"), linea.get("unidad"))
            if sugerido:
                factor, origen_factor = sugerido, "texto"
        nota = paquetes.leer_nota_cantidad(linea.get("nota"))
        if nota and linea.get("cantidad") and nota["unidades"] != linea["cantidad"]:
            # «1 UN» con la nota «166und x 690»: 166 unidades a $690.
            linea["unidades_nota"] = nota["unidades"]
            if (linea.get("cantidad") or 0) <= 1:
                factor, origen_factor = nota["unidades"], "nota"
        linea["clave_item"] = clave
        linea["unidades_por_paquete"] = factor
        linea["origen_unidades"] = origen_factor
        salida.append(linea)
    return salida


def detalle(conexion: psycopg.Connection, documento_id: str) -> dict:
    v = _vista(_fila(conexion, documento_id))
    v["lineas"] = lineas_para_revision(conexion, v["emisor_rut"], v["lineas"])
    v["ya_importada"] = (importacion.importacion_previa(conexion, v)
                         if v["emisor_rut"] and v["folio"] and v["tipo_dte"] else None)
    v["pedido_sugerido"] = None
    if v["clase"] == "factura" and v["estado"] == "pendiente" and v["emisor_rut"]:
        folios_ref = [r.get("folio") for r in v["referencias"] if r.get("folio")]
        fila = conexion.execute(
            "SELECT id, folio, fecha_emision FROM documentos_proveedor WHERE clase = 'pedido' AND estado = 'borrador' "
            "AND emisor_rut = %s ORDER BY (folio = ANY(%s)) DESC, creado_en DESC LIMIT 1",
            (v["emisor_rut"], folios_ref),
        ).fetchone()
        if fila:
            v["pedido_sugerido"] = {"documento_id": fila[0], "folio": fila[1],
                                    "fecha_emision": fila[2].isoformat() if fila[2] else None}
    v["factura_origen"] = None
    if v["clase"] == "nota_credito" and v["estado"] == "pendiente":
        v["factura_origen"] = _factura_referida(conexion, v)
    v["lectura_automatica"] = vision.estado()
    return v


# ----------------------------------------------------------- edición

CAMPOS_EDITABLES = ("clase", "emisor_rut", "emisor_razon_social", "tipo_dte", "folio", "fecha_emision",
                    "monto_neto_clp", "monto_exento_clp", "iva_clp", "monto_total_clp", "lineas")


def actualizar(conexion: psycopg.Connection, documento_id: str, cambios: dict, actor: str) -> dict:
    """Corrige encabezado o líneas (p. ej. escritas a mano sin IA). Solo en
    documentos abiertos; recalcula las diferencias."""
    f = _fila(conexion, documento_id, bloquear=True)
    v = _vista(f)
    if v["estado"] not in ESTADOS_ABIERTOS:
        raise DocumentoEnConflicto("Este documento ya no se puede editar.", documento_id)
    nuevo = {**{k: v[k] for k in CAMPOS_EDITABLES}, **{k: val for k, val in cambios.items() if k in CAMPOS_EDITABLES}}
    if "emisor_rut" in cambios and cambios["emisor_rut"]:
        rut = importacion.normalizar_rut_emisor(cambios["emisor_rut"])
        if not rut:
            raise DocumentoInvalido("El RUT del proveedor no es válido (ej.: 76123456-0).")
        nuevo["emisor_rut"] = rut
    if v["ted"] and v["lectura"] != "xml":
        # El timbre es oficial: no se reescribe lo que dice el SII.
        for k in ("emisor_rut", "tipo_dte", "folio"):
            if k in cambios and cambios[k] and str(cambios[k]) != str(v["ted"].get(k)):
                raise DocumentoInvalido("El RUT, el tipo y el folio vienen del timbre del SII y no se cambian.")
    if v["lectura"] == "xml":
        for k in ("emisor_rut", "tipo_dte", "folio"):
            if k in cambios and str(cambios[k]) != str(v[k]):
                raise DocumentoInvalido("Los datos del XML del SII no se cambian.")
    if nuevo.get("folio"):
        nuevo["folio"] = str(int(str(nuevo["folio"])))
    clase = nuevo["clase"]
    if clase == "pedido":
        nuevo["tipo_dte"] = None
    elif clase == "factura" and not nuevo.get("tipo_dte"):
        nuevo["tipo_dte"] = 33
    elif clase == "nota_credito":
        nuevo["tipo_dte"] = 61
    estado = "borrador" if clase == "pedido" else "pendiente"
    lineas = [{**l, "linea": i + 1} for i, l in enumerate(nuevo["lineas"])]
    doc = {k: nuevo[k] for k in CAMPOS_EDITABLES if k != "lineas"}
    discrepancias = [d for d in v["discrepancias"] if d["codigo"] in ("nota_credito", "sin_timbre")]
    discrepancias += vision.validar(doc, lineas, v["ted"], rut_hotel())
    try:
        with conexion.transaction():
            conexion.execute(
                "UPDATE documentos_proveedor SET clase=%s, estado=%s, emisor_rut=%s, emisor_razon_social=%s, tipo_dte=%s, "
                "folio=%s, fecha_emision=%s, monto_neto_clp=%s, monto_exento_clp=%s, iva_clp=%s, monto_total_clp=%s, "
                "lineas=%s, discrepancias=%s, actualizado_en=now() WHERE id=%s",
                (clase, estado, nuevo["emisor_rut"], nuevo["emisor_razon_social"], nuevo["tipo_dte"], nuevo["folio"],
                 nuevo["fecha_emision"], nuevo["monto_neto_clp"], nuevo["monto_exento_clp"], nuevo["iva_clp"],
                 nuevo["monto_total_clp"], Jsonb(lineas), Jsonb(discrepancias), documento_id),
            )
    except psycopg.errors.UniqueViolation as error:
        raise DocumentoEnConflicto("Ya hay otro documento con ese proveedor y folio en la bandeja.") from error
    return detalle(conexion, documento_id)


# -------------------------------------------------------- confirmación

def confirmar(conexion: psycopg.Connection, documento_id: str, lineas: list[dict], actor: str,
              pedido_id: str | None = None) -> dict:
    """Carga la factura al inventario: cantidad × unidades por envase, costo
    por unidad, y recuerda proveedor + ítem → producto y envase."""
    f = _fila(conexion, documento_id, bloquear=True)
    v = _vista(f)
    if v["estado"] != "pendiente":
        raise DocumentoEnConflicto("Este documento ya fue cargado o descartado.", documento_id)
    if v["clase"] != "factura":
        raise DocumentoEnConflicto({
            "nota_credito": "Una nota de crédito no suma stock: archívala y ajusta el stock si corresponde.",
            "pedido": "Un pedido no suma stock: espera la factura.",
        }.get(v["clase"], "Indica primero si el documento es una factura, una nota de crédito o un pedido."), documento_id)
    if not (v["emisor_rut"] and v["folio"] and v["tipo_dte"]):
        raise DocumentoInvalido("Falta el RUT del proveedor o el folio de la factura: complétalos antes de cargar.")
    documento = {k: v[k] for k in ("tipo_dte", "folio", "fecha_emision", "emisor_rut", "emisor_razon_social",
                                   "monto_neto_clp")}
    convertidas = []
    for l in lineas:
        factor = int(l.get("unidades_por_paquete") or 1)
        cantidad_envases = l.get("cantidad") or 0
        costo_envase = l.get("costo_unitario_clp")
        convertidas.append({
            **{k: l.get(k) for k in ("accion", "producto_id", "nombre", "categoria", "codigo", "precio_clp", "controla_stock")},
            "cantidad": int(round(cantidad_envases * factor)),
            "costo_unitario_clp": round(costo_envase / factor) if costo_envase is not None else None,
        })
    origen_imp = "factura_xml" if v["lectura"] == "xml" else "foto"
    with conexion.transaction():
        resultado = importacion.confirmar(conexion, origen_imp, documento, convertidas, actor)
        creados = iter([d for d in resultado["detalle"]])
        recordadas = 0
        for original, convertida in zip(lineas, convertidas):
            if convertida["accion"] == "omitir":
                continue
            hecho = next(creados, None)
            producto_id = convertida.get("producto_id") if convertida["accion"] == "sumar" else (hecho or {}).get("producto_id")
            if not producto_id or original.get("recordar") is False:
                continue
            clave = paquetes.clave_item(original.get("codigo_proveedor") or original.get("codigo"),
                                        original.get("nombre_proveedor") or original.get("nombre"))
            conexion.execute(
                "INSERT INTO equivalencias_proveedor (id, emisor_rut, clave, descripcion, producto_id, unidades_por_paquete, "
                "nota, actualizado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (emisor_rut, clave) DO UPDATE SET "
                "producto_id = EXCLUDED.producto_id, unidades_por_paquete = EXCLUDED.unidades_por_paquete, "
                "descripcion = EXCLUDED.descripcion, actualizado_por = EXCLUDED.actualizado_por, actualizado_en = now()",
                (_id("EQV"), v["emisor_rut"], clave,
                 (original.get("nombre_proveedor") or original.get("nombre") or "")[:120], producto_id,
                 max(1, int(original.get("unidades_por_paquete") or 1)), None, actor),
            )
            recordadas += 1
        pedido = pedido_id or v["pedido_id"]
        if pedido:
            conexion.execute(
                "UPDATE documentos_proveedor SET estado = 'facturado', actualizado_en = now() "
                "WHERE id = %s AND clase = 'pedido' AND estado = 'borrador' AND emisor_rut = %s",
                (pedido, v["emisor_rut"]),
            )
        conexion.execute(
            "UPDATE documentos_proveedor SET estado = 'cargada', importacion_id = %s, pedido_id = %s, actualizado_en = now() "
            "WHERE id = %s", (resultado["importacion_id"], pedido, documento_id),
        )
        if v["monto_total_clp"] is not None and v["monto_total_clp"] >= 0:
            conexion.execute(
                "INSERT INTO cuenta_proveedor_movimientos (emisor_rut, documento_id, tipo, monto_clp, actor) "
                "VALUES (%s, %s, 'factura', %s, %s) ON CONFLICT (documento_id, tipo) DO NOTHING",
                (v["emisor_rut"], documento_id, v["monto_total_clp"], actor),
            )
    return {**resultado, "documento_id": documento_id, "equivalencias_recordadas": recordadas}


def _factura_referida(conexion, nota: dict, factura_id: str | None = None) -> dict | None:
    """Factura ya cargada a la que apunta la nota de crédito (mismo proveedor), o la elegida a mano."""
    if factura_id:
        fila = conexion.execute(
            "SELECT id, folio, fecha_emision, monto_total_clp FROM documentos_proveedor "
            "WHERE id = %s AND clase = 'factura' AND estado = 'cargada' AND emisor_rut = %s",
            (factura_id, nota["emisor_rut"]),
        ).fetchone()
    else:
        folios = [str(r.get("folio")) for r in nota["referencias"]
                  if r.get("folio") and str(r.get("tipo") or "") in ("33", "34", "")]
        if not folios or not nota["emisor_rut"]:
            return None
        fila = conexion.execute(
            "SELECT id, folio, fecha_emision, monto_total_clp FROM documentos_proveedor "
            "WHERE clase = 'factura' AND estado = 'cargada' AND emisor_rut = %s AND folio = ANY(%s) "
            "ORDER BY creado_en DESC LIMIT 1",
            (nota["emisor_rut"], folios),
        ).fetchone()
    if fila is None:
        return None
    return {"documento_id": fila[0], "folio": fila[1],
            "fecha_emision": fila[2].isoformat() if fila[2] else None, "monto_total_clp": fila[3]}


def aplicar_nota_credito(conexion: psycopg.Connection, documento_id: str, lineas: list[dict], actor: str,
                         factura_id: str | None = None) -> dict:
    """Aplica una nota de crédito de proveedor (#402): devuelve unidades (baja de stock con movimiento
    «devolucion») y rebaja la cuenta por pagar del proveedor. Todo o nada; un documento se aplica una
    sola vez y exige la factura de origen ya cargada. El stock nunca queda negativo."""
    from . import productos as productos_db  # evita ciclos de importación
    from core.incremento1.nucleo import stock as stock_core

    v = _vista(_fila(conexion, documento_id, bloquear=True))
    if v["clase"] != "nota_credito":
        raise DocumentoEnConflicto("Este documento no es una nota de crédito.", documento_id)
    if v["estado"] == "aplicada":
        raise DocumentoEnConflicto("Esta nota de crédito ya fue aplicada: no se vuelve a mover el stock.", documento_id)
    if v["estado"] != "pendiente":
        raise DocumentoEnConflicto("Esta nota de crédito ya no está en la bandeja.", documento_id)
    if not (v["emisor_rut"] and v["folio"]):
        raise DocumentoInvalido("Falta el RUT del proveedor o el folio de la nota de crédito: complétalos antes de aplicar.")
    total = v["monto_total_clp"]
    if total is None or total < 0:
        raise DocumentoInvalido("Falta el monto total de la nota de crédito: complétalo antes de aplicar.")
    factura = _factura_referida(conexion, v, factura_id)
    if factura is None:
        raise DocumentoEnConflicto(
            "La factura de origen aún no está cargada al inventario: cárgala primero o elígela a mano.", documento_id)
    acumulado = conexion.execute(
        "SELECT COALESCE(-SUM(monto_clp), 0) FROM cuenta_proveedor_movimientos "
        "WHERE tipo = 'nota_credito' AND referencia_documento_id = %s", (factura["documento_id"],),
    ).fetchone()[0]
    if factura["monto_total_clp"] is not None and acumulado + total > factura["monto_total_clp"]:
        raise DocumentoInvalido(
            f"Las notas de crédito de la factura {factura['folio']} sumarían más que su total "
            f"({acumulado + total} de {factura['monto_total_clp']}).")
    motivo = f"Nota de crédito {v['folio']} (factura {factura['folio']})"
    aplicadas = []
    with conexion.transaction():
        for l in lineas:
            if l.get("accion") != "descontar":
                continue
            producto_id = l.get("producto_id")
            if not producto_id:
                raise DocumentoInvalido(f"Elige el producto de «{l.get('nombre') or 'la línea'}» o márcala como «no descontar».")
            unidades = int(round((l.get("cantidad") or 0) * int(l.get("unidades_por_paquete") or 1)))
            if unidades <= 0:
                raise DocumentoInvalido(f"La cantidad de «{l.get('nombre') or producto_id}» debe ser mayor que cero.")
            try:
                producto = productos_db.obtener(conexion, producto_id, bloqueo=True)
            except productos_db.ProductoInvalido as error:
                raise DocumentoInvalido(str(error)) from error
            if not producto["controla_stock"]:
                raise DocumentoInvalido(f"«{producto['nombre']}» no controla stock: no se puede devolver.")
            if producto["stock"] - unidades < 0:
                raise DocumentoInvalido(
                    f"«{producto['nombre']}»: la devolución de {unidades} deja el stock negativo (hay {producto['stock']}).")
            bodega = stock_core.bodega_por_categoria(producto["categoria"])
            try:
                productos_db.registrar_stock_bodega(conexion, producto_id, bodega, -unidades)
            except productos_db.ProductoInvalido as error:
                raise DocumentoInvalido(f"«{producto['nombre']}»: {error}") from error
            conexion.execute("UPDATE productos SET stock = stock - %s, actualizado_en = now() WHERE id = %s",
                             (unidades, producto_id))
            productos_db._movimiento(conexion, producto_id, -unidades, motivo, actor, bodega_codigo=bodega, tipo="devolucion")
            aplicadas.append({"producto_id": producto_id, "nombre": producto["nombre"], "unidades": unidades,
                              "stock_antes": producto["stock"], "stock_despues": producto["stock"] - unidades})
        if total:
            conexion.execute(
                "INSERT INTO cuenta_proveedor_movimientos (emisor_rut, documento_id, tipo, monto_clp, "
                "referencia_documento_id, actor) VALUES (%s, %s, 'nota_credito', %s, %s, %s)",
                (v["emisor_rut"], documento_id, -total, factura["documento_id"], actor),
            )
        resumen = {"factura_folio": factura["folio"], "monto_rebajado_clp": total, "lineas": aplicadas}
        conexion.execute(
            "UPDATE documentos_proveedor SET estado = 'aplicada', factura_origen_id = %s, aplicacion = %s, "
            "actualizado_en = now() WHERE id = %s",
            (factura["documento_id"], Jsonb(resumen), documento_id),
        )
    return {"documento_id": documento_id, "estado": "aplicada", "factura_origen_id": factura["documento_id"], **resumen,
            "saldo_proveedor_clp": saldo_proveedor(conexion, v["emisor_rut"])["saldo_clp"]}


def saldo_proveedor(conexion: psycopg.Connection, emisor_rut: str) -> dict:
    """Cuenta por pagar del proveedor: facturas cargadas menos notas de crédito aplicadas (PUR-004).
    Los pagos al proveedor quedan fuera de esta versión."""
    filas = conexion.execute(
        "SELECT m.id, m.tipo, m.monto_clp, m.registrado_en, d.folio, m.actor "
        "FROM cuenta_proveedor_movimientos m JOIN documentos_proveedor d ON d.id = m.documento_id "
        "WHERE m.emisor_rut = %s ORDER BY m.registrado_en, m.id", (emisor_rut,),
    ).fetchall()
    return {
        "emisor_rut": emisor_rut,
        "saldo_clp": sum(f[2] for f in filas),
        "movimientos": [{"movimiento_id": f[0], "tipo": f[1], "monto_clp": f[2], "folio": f[4],
                         "registrado_en": f[3].isoformat(), "actor": f[5]} for f in filas],
    }


def descartar(conexion: psycopg.Connection, documento_id: str, actor: str) -> dict:
    v = _vista(_fila(conexion, documento_id, bloquear=True))
    if v["estado"] not in ESTADOS_ABIERTOS:
        raise DocumentoEnConflicto("Este documento ya no está en la bandeja.", documento_id)
    estado = "archivada" if v["clase"] == "nota_credito" else "descartada"
    conexion.execute("UPDATE documentos_proveedor SET estado = %s, actualizado_en = now() WHERE id = %s",
                     (estado, documento_id))
    return {"documento_id": documento_id, "estado": estado}


# ------------------------------------------------------- equivalencias

def listar_equivalencias(conexion: psycopg.Connection, emisor: str | None = None) -> list[dict]:
    filas = conexion.execute(
        "SELECT e.id, e.emisor_rut, e.clave, e.descripcion, e.producto_id, p.nombre, e.unidades_por_paquete, e.nota, "
        "e.actualizado_por, e.actualizado_en, "
        "(SELECT d.emisor_razon_social FROM documentos_proveedor d WHERE d.emisor_rut = e.emisor_rut "
        " AND d.emisor_razon_social IS NOT NULL ORDER BY d.creado_en DESC LIMIT 1) "
        "FROM equivalencias_proveedor e JOIN productos p ON p.id = e.producto_id "
        "WHERE (%s::text IS NULL OR e.emisor_rut = %s) ORDER BY e.emisor_rut, e.descripcion LIMIT 500",
        (emisor, emisor),
    ).fetchall()
    return [{"equivalencia_id": f[0], "emisor_rut": f[1], "clave": f[2], "descripcion": f[3], "producto_id": f[4],
             "producto_nombre": f[5], "unidades_por_paquete": f[6], "nota": f[7], "actualizado_por": f[8],
             "actualizado_en": f[9].isoformat(), "emisor_razon_social": f[10]} for f in filas]


def cambiar_equivalencia(conexion: psycopg.Connection, equivalencia_id: str, cambios: dict, actor: str) -> dict:
    fila = conexion.execute("SELECT id FROM equivalencias_proveedor WHERE id = %s FOR UPDATE", (equivalencia_id,)).fetchone()
    if not fila:
        raise DocumentoNoEncontrado("No existe esa equivalencia.")
    sets, valores = ["actualizado_por = %s", "actualizado_en = now()"], [actor]
    if cambios.get("producto_id"):
        if not conexion.execute("SELECT 1 FROM productos WHERE id = %s", (cambios["producto_id"],)).fetchone():
            raise DocumentoInvalido("El producto elegido no existe.")
        sets.append("producto_id = %s")
        valores.append(cambios["producto_id"])
    if cambios.get("unidades_por_paquete") is not None:
        sets.append("unidades_por_paquete = %s")
        valores.append(int(cambios["unidades_por_paquete"]))
    if "nota" in cambios:
        sets.append("nota = %s")
        valores.append((cambios["nota"] or "")[:120] or None)
    conexion.execute(f"UPDATE equivalencias_proveedor SET {', '.join(sets)} WHERE id = %s", (*valores, equivalencia_id))
    return next(e for e in listar_equivalencias(conexion) if e["equivalencia_id"] == equivalencia_id)


def eliminar_equivalencia(conexion: psycopg.Connection, equivalencia_id: str) -> None:
    if conexion.execute("DELETE FROM equivalencias_proveedor WHERE id = %s", (equivalencia_id,)).rowcount == 0:
        raise DocumentoNoEncontrado("No existe esa equivalencia.")

