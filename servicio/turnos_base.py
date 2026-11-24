"""Turnos base semanales desde la hoja `Horario` del Excel del hotel (#467).

Solo lee la hoja `Horario` (nombre de pila y franja). **No usa `Personal Vigente`**: esa hoja trae RUT,
sueldos y AFP, datos que no deben pasar por el repositorio ni por estos CSV. La persona real se enlaza
con el usuario de la plataforma en la columna `usuario` del CSV, que completa la administración fuera
del repo cuando las cuentas ya existen (cada una con su invitación; no se guardan claves).

Reglas del hotel (Administración, 21-11-2026):
- El lunes el turno de noche se alarga hasta las 11:00 (cubre hasta que llega la recepcionista de día).
- Un turno que termina a las 00:00 se guarda hasta las 23:59 (la tabla exige fin > inicio en el mismo día).
- Quien tiene contrato a plazo (p. ej. hasta 31-12-2026) lleva `hasta`: no se generan turnos después.
"""
from __future__ import annotations

import csv
import hashlib
import re
from datetime import date, time, timedelta
from pathlib import Path

import psycopg

from . import seguridad
from .apertura_excel import leer_hojas

DIAS = ("Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo")
_SECCIONES = (("turnos recepci", "recepcion"), ("turnos personal de aseo", "aseo"))
_CELDA = re.compile(r"^\s*(?P<nombre>.+?)[\s.]*\(\s*(?P<ini>\d{1,2}:\d{2})\s*-\s*(?P<fin>\d{1,2}:\d{2})\s*\)\s*$")
COLUMNAS = ["dia_semana", "area", "nombre_horario", "hora_inicio", "hora_fin", "nota", "usuario", "hasta"]
LUNES_HASTA = "11:00"


def _sin_acentos(t: str) -> str:
    return t.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


def plantilla(ruta_xlsx: Path, fin_contrato: dict[str, str] | None = None) -> list[dict]:
    """Filas `dia_semana (0=lunes)`, área, nombre de pila, franja, `usuario` vacío y `hasta` opcional."""
    fin_contrato = {k.lower(): v for k, v in (fin_contrato or {}).items()}
    filas_hoja = leer_hojas(ruta_xlsx, ("Horario",))["Horario"]
    area = None
    salida: list[dict] = []
    for fila in filas_hoja:
        primera = _sin_acentos(fila.get("A", ""))
        seccion = next((a for prefijo, a in _SECCIONES if primera.startswith(prefijo)), None)
        if seccion:
            area = seccion
            continue
        if area is None or primera.startswith("lunes") and "(" not in primera:
            continue
        for i, columna in enumerate("ABCDEFG"):
            m = _CELDA.match(fila.get(columna, ""))
            if not m:
                continue
            nombre = m["nombre"].strip()
            ini, fin = m["ini"].zfill(5), m["fin"].zfill(5)
            nota = ""
            if fin == "00:00":
                fin, nota = "23:59", "termina a las 00:00"
            salida.append({"dia_semana": i, "area": area, "nombre_horario": nombre, "hora_inicio": ini,
                           "hora_fin": fin, "nota": nota, "usuario": "", "hasta": fin_contrato.get(nombre.lower(), "")})
    # Lunes: el turno de noche cubre hasta que llega la recepcionista de día.
    llegada_lunes = [f["hora_inicio"] for f in salida if f["dia_semana"] == 0 and f["area"] == "recepcion" and f["hora_inicio"] > "00:00"]
    for f in salida:
        if f["dia_semana"] == 0 and f["area"] == "recepcion" and f["hora_inicio"] == "00:00" and llegada_lunes:
            f["hora_fin"] = max(LUNES_HASTA, f["hora_fin"])
            f["nota"] = "lunes: cubre hasta que llega recepción de día"
    return salida


def escribir_plantilla(filas: list[dict], destino: Path) -> None:
    with destino.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNAS)
        w.writeheader()
        w.writerows(filas)


def _hora(texto: str) -> time:
    h, m = texto.split(":")
    return time(int(h), int(m))


def cargar_turnos_csv(conexion: psycopg.Connection, empresa_id: str, ruta_csv: Path, desde: date, semanas: int, *,
                      aplicar: bool = False, actor: str = "migracion_apertura") -> dict:
    """Valida (y con `aplicar` genera) los turnos de `semanas` semanas desde el lunes de `desde`.
    Idempotente: el índice único (fecha, usuario, franja) evita repetir; el id sale de esos mismos datos."""
    if not 1 <= semanas <= 26:
        raise ValueError("semanas debe estar entre 1 y 26")
    lunes = desde - timedelta(days=desde.weekday())
    errores: list[dict] = []
    validas: list[dict] = []
    usuarios = {r[0] for r in conexion.execute("SELECT nombre FROM usuarios WHERE empresa_id = %s", (empresa_id,)).fetchall()}
    with ruta_csv.open(encoding="utf-8-sig", newline="") as fh:
        for linea, fila in enumerate(csv.DictReader(fh), start=2):
            try:
                usuario = (fila.get("usuario") or "").strip()
                if not usuario:
                    raise ValueError(f"falta el usuario de «{fila.get('nombre_horario')}»")
                if usuario not in usuarios:
                    raise ValueError(f"el usuario «{usuario}» no existe en la plataforma")
                if fila["area"] not in ("recepcion", "aseo", "desayunos", "mantencion"):
                    raise ValueError(f"área inválida «{fila['area']}»")
                dia = int(fila["dia_semana"])
                if not 0 <= dia <= 6:
                    raise ValueError("dia_semana debe ir de 0 (lunes) a 6 (domingo)")
                ini, fin = _hora(fila["hora_inicio"]), _hora(fila["hora_fin"])
                if fin <= ini:
                    raise ValueError("hora_fin debe ser posterior a hora_inicio")
                hasta = date.fromisoformat(fila["hasta"]) if (fila.get("hasta") or "").strip() else None
                validas.append({"dia": dia, "area": fila["area"], "usuario": usuario, "ini": ini, "fin": fin,
                                "nota": (fila.get("nota") or "").strip()[:200] or None, "hasta": hasta})
            except (ValueError, KeyError) as err:
                errores.append({"linea": linea, "error": str(err)})
    aplicados = omitidos = 0
    if aplicar and not errores:
        with conexion.transaction():
            for s in range(semanas):
                for t in validas:
                    fecha = lunes + timedelta(days=7 * s + t["dia"])
                    if fecha < desde or (t["hasta"] and fecha > t["hasta"]):
                        continue
                    clave = f"{fecha}|{t['usuario']}|{t['ini']}|{t['fin']}"
                    resultado = conexion.execute(
                        "INSERT INTO turnos (id, fecha, area, usuario, hora_inicio, hora_fin, nota, creado_por) "
                        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                        (f"TUR-B{hashlib.md5(clave.encode()).hexdigest()[:10]}", fecha, t["area"], t["usuario"],
                         t["ini"], t["fin"], t["nota"], actor),
                    )
                    aplicados += resultado.rowcount
                    omitidos += 1 - resultado.rowcount
            seguridad.auditar(conexion, actor, "apertura_turnos", ruta_csv.name, f"aplicados={aplicados},omitidos={omitidos}")
    return {"archivo": ruta_csv.name, "plantillas": len(validas), "aplicados": aplicados, "omitidos": omitidos,
            "errores": errores, "aprobado": not errores}
