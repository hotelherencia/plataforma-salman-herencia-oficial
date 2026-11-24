"""Convierte el Excel de levantamiento del hotel en los CSV saneados de la carga de apertura (#468).

No escribe en la base: produce `inventario_inicial.csv`, `incidencias_iniciales.csv` y
`activos_iniciales.csv`, que luego valida y aplica `scripts/cargar_apertura_operativa.py`
(con `--dry-run` por defecto). Lee el XLSX directamente (el archivo del hotel trae estilos que
`openpyxl` rechaza) y **se niega a abrir la hoja `Redes`**: ahí viven credenciales compartidas
que no deben pasar por el repositorio ni por estos CSV.
"""
from __future__ import annotations

import csv
import hashlib
import re
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
HOJAS_PROHIBIDAS = {"redes"}
HOJAS_USADAS = (
    "Detalle de habitaciones", "Inventario Lavanderia", "Inventario Cocina",
    "Insumos Desayuno", "Insumos Aseo", "Otras observaciones",
)
RESPONSABLE = "Mantenimiento"
EQUIPOS_COCINA = (
    "refrigerador", "encimera", "campana", "lavaplatos", "horno", "hervidor", "termo",
    "microondas", "baño maria", "tostador",
)
EQUIPOS_LAVANDERIA = ("secadora", "lavadora", "plancha", "tabla de planchar")


class HojaProhibida(Exception):
    """La hoja pedida contiene credenciales o no pertenece a la carga."""


def _texto(c: ET.Element, compartidas: list[str]) -> str | None:
    v = c.find("m:v", _NS)
    tipo = c.get("t")
    if tipo == "s" and v is not None:
        return compartidas[int(v.text)]
    if tipo == "inlineStr":
        return "".join(t.text or "" for t in c.iter("{%s}t" % _NS["m"]))
    return v.text if v is not None else None


def leer_hojas(ruta: Path, nombres: tuple[str, ...] = HOJAS_USADAS) -> dict[str, list[dict[str, str]]]:
    """Devuelve `{hoja: [ {columna: texto} ... ]}` solo de las hojas pedidas."""
    for nombre in nombres:
        if nombre.strip().lower() in HOJAS_PROHIBIDAS:
            raise HojaProhibida(f"la hoja «{nombre}» no se lee: contiene credenciales")
    with zipfile.ZipFile(ruta) as z:
        compartidas: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", _NS):
                compartidas.append("".join(t.text or "" for t in si.iter("{%s}t" % _NS["m"])))
        rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        destinos = {
            s.get("name"): rels[s.get("{%s}id" % _NS["r"])]
            for s in ET.fromstring(z.read("xl/workbook.xml")).find("m:sheets", _NS)
        }
        salida: dict[str, list[dict[str, str]]] = {}
        for nombre in nombres:
            destino = destinos[nombre]
            destino = destino.lstrip("/") if destino.startswith("/") else "xl/" + destino
            filas = []
            for row in ET.fromstring(z.read(destino)).iter("{%s}row" % _NS["m"]):
                fila = {}
                for c in row.findall("m:c", _NS):
                    valor = _texto(c, compartidas)
                    if valor is not None and valor.strip() != "":
                        fila[re.match(r"[A-Z]+", c.get("r")).group()] = valor.strip()
                if fila:
                    filas.append(fila)
            salida[nombre] = filas
    return salida


def _slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9]+", "-", base).strip("-")[:28] or "ITEM"


def _entero_inicial(texto: str | None) -> int:
    """'5 paquetes' → 5; '—', 'Pendiente' o vacío → 0."""
    m = re.match(r"\s*(\d+)", texto or "")
    return int(m.group(1)) if m else 0


def _codigo_unico(prefijo: str, nombre: str, usados: set[str]) -> str:
    codigo = f"{prefijo}-{_slug(nombre)}"
    n = 2
    while codigo in usados:
        codigo = f"{prefijo}-{_slug(nombre)}-{n}"
        n += 1
    usados.add(codigo)
    return codigo


def _es_equipo(nombre: str, equipos: tuple[str, ...]) -> bool:
    return any(e in nombre.lower() for e in equipos)


def filas_inventario(hojas: dict[str, list[dict[str, str]]]) -> list[dict]:
    """Insumos de desayuno y aseo, ropa de lavandería y menaje de cocina → `inventario_inicial.csv`."""
    usados: set[str] = set()
    filas: list[dict] = []

    def _fila(codigo, nombre, categoria, bodega, stock, costo):
        filas.append({
            "codigo": codigo, "nombre": nombre, "categoria": categoria, "bodega_codigo": bodega,
            "stock_inicial": stock, "stock_minimo": 0, "precio_clp": 1,
            "costo_clp": costo if costo else "", "activo": "false",
        })

    for hoja, prefijo, categoria, bodega in (
        ("Insumos Desayuno", "DES", "cafeteria", "insumos_desayuno"),
        ("Insumos Aseo", "ASE", "servicio", "insumos_aseo"),
    ):
        for fila in hojas[hoja][1:]:  # la primera es la cabecera
            nombre = fila.get("A", "").strip()
            if not nombre:
                continue
            marca = fila.get("C", "")
            nombre_completo = nombre if marca in ("", "—") else f"{nombre} ({marca})"
            _fila(_codigo_unico(prefijo, nombre, usados), nombre_completo[:120], categoria, bodega,
                  _entero_inicial(fila.get("F")), _entero_inicial(fila.get("D")))

    for fila in hojas["Inventario Lavanderia"][2:]:
        nombre = fila.get("A", "").strip()
        if not nombre or "B" not in fila:
            continue
        stock = _entero_inicial(fila.get("B")) + _entero_inicial(fila.get("C"))
        _fila(_codigo_unico("LAV", nombre, usados), nombre, "servicio", "lavanderia", stock, 0)

    for fila in hojas["Inventario Cocina"][1:]:
        nombre = fila.get("A", "").strip()
        if not nombre or _es_equipo(nombre, EQUIPOS_COCINA):
            continue  # los equipos van como activos, no como stock
        _fila(_codigo_unico("COC", nombre, usados), nombre, "servicio", "cocina", _entero_inicial(fila.get("B")), 0)
    return filas


def _hab(numero: str) -> str:
    return f"HAB-{int(numero):02d}"


def _malo(valor: str | None, *palabras: str) -> bool:
    v = (valor or "").lower()
    return any(p in v for p in palabras)


def filas_incidencias(hojas: dict[str, list[dict[str, str]]]) -> list[dict]:
    """Hallazgos del levantamiento → `incidencias_iniciales.csv` (una por hallazgo, sin duplicar)."""
    detalle = hojas["Detalle de habitaciones"]
    habitaciones: dict[str, dict[str, str]] = {}
    for fila in detalle[1:]:
        numero = fila.get("A", "")
        if numero.isdigit() and numero not in habitaciones and "B" in fila:  # ignora la fila parcial repetida
            habitaciones[numero] = fila
    out: list[dict] = []

    def _inc(codigo, habitacion, area, descripcion, gravedad):
        out.append({
            "codigo_externo": codigo, "habitacion_id": habitacion, "area": area,
            "descripcion": descripcion[:1000], "gravedad": gravedad, "responsable": RESPONSABLE,
            "plazo": "", "costo_clp": "", "bloquea_disponibilidad": "false",
        })

    for numero, f in habitaciones.items():
        h, n = _hab(numero), int(numero)
        if _malo(f.get("D"), "cambiar"):
            _inc(f"XL-H{n:02d}-COLCHON", h, "", f"Cambiar colchón (levantamiento): {f['D']}", "media")
        if _malo(f.get("O"), "suelta"):
            _inc(f"XL-H{n:02d}-CERRADURA", h, "", "Cerradura suelta: reapretar o reemplazar", "alta")
        if _malo(f.get("Z"), "suelta"):
            _inc(f"XL-H{n:02d}-CORREDERA", h, "", "Corredera suelta", "media")
        pintura = [f[c] for c in ("L", "M") if _malo(f.get(c), "empast", "humedad", "grieta", "descasc")]
        if pintura:
            _inc(f"XL-H{n:02d}-PINTURA", h, "", "Empaste / pintura / humedad: " + "; ".join(pintura), "baja")
        if _malo(f.get("P"), "reparar"):
            _inc(f"XL-H{n:02d}-AIRE", h, "",
                 "Aire acondicionado por reparar. Revisar antes la electricidad (206 V medidos, debería ser 220 V).",
                 "critica")
    sin_repisa = sorted(int(n) for n, f in habitaciones.items() if _malo(f.get("R"), "falta"))
    if sin_repisa:
        _inc("XL-COMUN-REPISAS", "", "habitaciones",
             "Falta repisa de vidrio del espejo de baño en las habitaciones: " + ", ".join(map(str, sin_repisa)), "baja")
    _inc("XL-COMUN-LUCES-BANO", "", "habitaciones", "Luces de baño oxidadas en todas las habitaciones: cambiar", "media")
    _inc("XL-COMUN-FILTROS", "", "habitaciones", "Filtros de ventilación por cambiar en todas las habitaciones", "media")

    for fila in hojas["Otras observaciones"][1:]:
        nombre, obs = fila.get("A", ""), fila.get("B", "")
        if not obs:
            continue  # encabezados de sección y sugerencias de pasajeros sin acción concreta
        bajo = nombre.lower()
        if bajo == "hb 2":
            _inc("XL-H02-DUCHA", "HAB-02", "", f"{obs}: filtración en la ducha", "alta")
        elif bajo == "hb 10":
            _inc("XL-H10-ELECTRICIDAD", "HAB-10", "", obs, "critica")
        elif bajo.startswith("hb "):
            continue  # empastes ya incluidos por habitación
        elif bajo == "motor de agua":
            _inc("XL-COMUN-MOTOR-AGUA", "", "mantencion", f"Motor de agua: {obs}", "critica")
        elif bajo.startswith("techo patio"):
            _inc("XL-COMUN-GOTERAS", "", "lavanderia", f"Techo del patio de lavandería: {obs}", "critica")
        elif "estantes" in bajo:
            _inc("XL-COMUN-ESTANTES", "", "lavanderia", f"Estantes de lavandería: {obs}", "baja")
        elif bajo == "timbre":
            _inc("XL-COMUN-TIMBRE", "", "recepcion", f"Timbre: {obs}", "baja")
        elif "llaveros" in bajo:
            _inc("XL-COMUN-LLAVEROS", "", "recepcion", f"Llaveros de habitaciones: {obs}", "baja")
        elif "computador" in bajo:
            _inc("XL-COMUN-PC-RECEPCION", "", "recepcion", f"Computador de recepción: {obs}", "media")
    for fila in hojas["Inventario Cocina"][1:]:
        if "enchufe" in fila.get("C", "").lower():
            _inc("XL-COMUN-ENCIMERA", "", "cocina", f"{fila['A']}: {fila['C']}", "alta")
    return out


def filas_activos(hojas: dict[str, list[dict[str, str]]], proxima_mantencion: str) -> list[dict]:
    """Equipos por habitación y áreas comunes, con su plan de mantención anual → `activos_iniciales.csv`."""
    out: list[dict] = []

    def _act(codigo, habitacion, area, nombre, categoria, estado, notas, mantencion=""):
        out.append({
            "codigo_externo": codigo, "habitacion_id": habitacion, "area": area, "nombre": nombre,
            "categoria": categoria, "estado": estado, "notas": notas[:300],
            "mantencion_descripcion": mantencion, "mantencion_cada_dias": "365" if mantencion else "",
            "mantencion_proxima": proxima_mantencion if mantencion else "",
        })

    vistos = set()
    for f in hojas["Detalle de habitaciones"][1:]:
        numero = f.get("A", "")
        if not numero.isdigit() or numero in vistos or "B" not in f:
            continue
        vistos.add(numero)
        h, n = _hab(numero), int(numero)
        estado = "en_reparacion" if _malo(f.get("P"), "reparar") else "operativo"
        _act(f"XL-ACT-H{n:02d}-AIRE", h, "", "Aire acondicionado", "climatizacion", estado,
             f.get("P", ""), "Mantención anual del aire acondicionado")
        _act(f"XL-ACT-H{n:02d}-CALEFONT", h, "", "Calefont", "sanitario", "operativo",
             f.get("AA", ""), "Mantención anual del calefont")
    _act("XL-ACT-COMUN-MOTOR-AGUA", "", "mantencion", "Motor de agua", "sanitario", "en_reparacion",
         "No para hasta desenchufarlo")
    for fila in hojas["Inventario Lavanderia"][2:]:
        nombre = fila.get("E", "")
        if nombre and _es_equipo(nombre, EQUIPOS_LAVANDERIA):
            _act(f"XL-ACT-LAV-{_slug(nombre)}", "", "lavanderia", nombre, "electrico", "operativo",
                 f"Cantidad {fila.get('F', '1')}. {fila.get('G', '')}")
    for fila in hojas["Inventario Cocina"][1:]:
        nombre = fila.get("A", "")
        if nombre and _es_equipo(nombre, EQUIPOS_COCINA):
            estado = "en_reparacion" if "reparar" in fila.get("C", "").lower() else "operativo"
            _act(f"XL-ACT-COC-{_slug(nombre)}", "", "cocina", nombre, "electrico", estado,
                 f"Cantidad {fila.get('B', '1')}. {fila.get('C', '')}")
    return out


def _escribir(ruta: Path, columnas: list[str], filas: list[dict]) -> None:
    with ruta.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)


def generar(xlsx: Path, salida: Path, proxima_mantencion: str = "2026-12-15") -> dict[str, int]:
    """Escribe los tres CSV en `salida` y devuelve cuántas filas tiene cada uno."""
    hojas = leer_hojas(xlsx)
    salida.mkdir(parents=True, exist_ok=True)
    inv, inc, act = filas_inventario(hojas), filas_incidencias(hojas), filas_activos(hojas, proxima_mantencion)
    _escribir(salida / "inventario_inicial.csv", list(inv[0]), inv)
    _escribir(salida / "incidencias_iniciales.csv", list(inc[0]), inc)
    _escribir(salida / "activos_iniciales.csv", list(act[0]), act)
    return {"inventario": len(inv), "incidencias": len(inc), "activos": len(act)}


def id_activo(codigo_externo: str) -> str:
    return f"ACT-{hashlib.md5(codigo_externo.lower().encode()).hexdigest()[:10]}"
