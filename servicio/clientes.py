"""Clientes (contabilidad fase 2.1): un RUT es una sola persona o empresa.

El RUT se guarda solo con números y dígito verificador, sin puntos ni guion (`123456785`); la pantalla lo
formatea. El mismo RUT con otro nombre se rechaza: el nombre se compara sin tildes, mayúsculas ni espacios de más.
"""
from __future__ import annotations

import re
import unicodedata
import uuid

import psycopg

from . import roles
from . import seguridad

ROLES_GESTION = roles.con_admin_hotel("recepcion", "caja")
TIPOS = ("persona", "empresa")
MAX_LISTA = 200
_RE_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RE_TELEFONO = re.compile(r"^[+\d\s().-]+$")


class RutInvalido(ValueError):
    """422: el RUT no cumple el formato o el dígito verificador."""


class ClienteConflicto(Exception):
    """409: el RUT ya existe con otro nombre."""


def _digito_verificador(cuerpo: int) -> str:
    suma, factor = 0, 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return "0" if resto == 11 else "K" if resto == 10 else str(resto)


def rut_clave(texto: str) -> str:
    """RUT como se guarda: números y dígito verificador, sin puntos, guion ni espacios."""
    limpio = re.sub(r"[.\s-]", "", (texto or "").strip()).upper()
    if not re.fullmatch(r"\d{7,8}[0-9K]", limpio):
        raise RutInvalido("RUT inválido: usa el formato 12.345.678-5")
    if _digito_verificador(int(limpio[:-1])) != limpio[-1]:
        raise RutInvalido("RUT inválido: el dígito verificador no corresponde")
    return limpio


def rut_visible(clave: str | None) -> str | None:
    """`123456785` → `12.345.678-5` (solo para mostrar)."""
    if not clave:
        return None
    return f"{int(clave[:-1]):,}".replace(",", ".") + f"-{clave[-1]}"


def nombre_clave(nombre: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", nombre or "") if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def buscar(conexion: psycopg.Connection, rut_normalizado: str) -> tuple | None:
    return conexion.execute(
        "SELECT id, nombre, nombre_clave FROM clientes WHERE rut = %s", (rut_normalizado,)
    ).fetchone()


def exigir_nombre_coherente(conexion: psycopg.Connection, rut_normalizado: str, nombre: str) -> None:
    existente = buscar(conexion, rut_normalizado)
    if existente is not None and existente[2] != nombre_clave(nombre):
        raise ClienteConflicto(
            f"el RUT {rut_visible(rut_normalizado)} ya está registrado a nombre de «{existente[1]}»; "
            "revisa el RUT o el nombre"
        )


def asegurar(conexion: psycopg.Connection, rut: str, nombre: str, actor: str, *, giro: str | None = None,
             direccion: str | None = None, comuna: str | None = None, correo: str | None = None,
             tipo: str = "empresa") -> str:
    """Id del cliente de ese RUT; lo crea si no existe. Mismo RUT con otro nombre → `ClienteConflicto`."""
    clave = rut_clave(rut)
    nombre = " ".join((nombre or "").split())
    exigir_nombre_coherente(conexion, clave, nombre)
    existente = buscar(conexion, clave)
    if existente is not None:
        return existente[0]
    cliente_id = f"CLI-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO clientes (id, tipo, rut, nombre, nombre_clave, giro, direccion, comuna, correo, creado_por) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (cliente_id, tipo, clave, nombre, nombre_clave(nombre), giro or None, direccion or None, comuna or None,
         correo or None, actor),
    )
    return cliente_id


class ClienteInexistente(Exception):
    """403/404: el cliente no existe."""


class ClienteInvalido(ValueError):
    """422: datos del cliente inválidos."""


def _ficha(f: tuple) -> dict:
    return {"id": f[0], "tipo": f[1], "rut": rut_visible(f[2]), "nombre": f[3], "giro": f[4],
            "direccion": f[5], "comuna": f[6], "correo": f[7], "telefono": f[8],
            "activo": f[9], "creado_en": f[10].isoformat()}


_COLUMNAS = "id, tipo, rut, nombre, giro, direccion, comuna, correo, telefono, activo, creado_en"


def _validar_telefono(telefono: str | None) -> str | None:
    limpio = " ".join((telefono or "").split()) or None
    if limpio is None:
        return None
    if len(limpio) > 30:
        raise ClienteInvalido("teléfono admite hasta 30 caracteres")
    digitos = re.sub(r"\D", "", limpio)
    if not _RE_TELEFONO.match(limpio) or not (8 <= len(digitos) <= 15):
        raise ClienteInvalido("teléfono inválido: usa entre 8 y 15 dígitos")
    return limpio


def _validar_datos(*, rut: str, nombre: str, tipo: str, giro: str | None, direccion: str | None,
                   comuna: str | None, correo: str | None, telefono: str | None) -> dict:
    nombre_limpio = " ".join((nombre or "").split())
    if not nombre_limpio or len(nombre_limpio) > 200:
        raise ClienteInvalido("nombre es obligatorio (máx. 200)")
    if tipo not in TIPOS:
        raise ClienteInvalido("tipo debe ser persona o empresa")
    giro_l, direccion_l, comuna_l = ((v or "").strip() or None for v in (giro, direccion, comuna))
    correo_l = (correo or "").strip().lower() or None
    if correo_l and (len(correo_l) > 320 or not _RE_CORREO.match(correo_l)):
        raise ClienteInvalido("correo debe tener formato de correo")
    telefono_l = _validar_telefono(telefono)
    clave = rut_clave(rut)  # RutInvalido (422)
    return {
        "tipo": tipo, "rut": clave, "nombre": nombre_limpio, "giro": giro_l,
        "direccion": direccion_l, "comuna": comuna_l, "correo": correo_l, "telefono": telefono_l,
    }


def listar(conexion: psycopg.Connection, texto: str | None = None, incluir_inactivos: bool = True) -> dict:
    """Clientes por nombre, RUT, correo o teléfono; tope fijo (la lista no se pagina: son pocos)."""
    texto = " ".join((texto or "").split())
    condiciones, parametros = [], []
    if texto:
        patron = f"%{texto}%"
        solo_rut = re.sub(r"[.\s-]", "", texto).upper()
        solo_digitos = re.sub(r"\D", "", texto)
        partes = ["nombre ILIKE %s", "correo ILIKE %s", "rut LIKE %s", "telefono ILIKE %s"]
        parametros += [patron, patron, f"%{solo_rut}%" if solo_rut else patron, patron]
        if len(solo_digitos) >= 3:
            partes.append("regexp_replace(COALESCE(telefono, ''), '[^0-9]', '', 'g') LIKE %s")
            parametros.append(f"%{solo_digitos}%")
        condiciones.append(f"({' OR '.join(partes)})")
    if not incluir_inactivos:
        condiciones.append("activo")
    donde = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""
    filas = conexion.execute(
        f"SELECT {_COLUMNAS} FROM clientes{donde} ORDER BY nombre_clave, id LIMIT {MAX_LISTA + 1}", parametros
    ).fetchall()
    return {"clientes": [_ficha(f) for f in filas[:MAX_LISTA]], "truncado": len(filas) > MAX_LISTA}


def crear(conexion: psycopg.Connection, *, rut: str, nombre: str, tipo: str = "empresa",
          giro: str | None = None, direccion: str | None = None, comuna: str | None = None,
          correo: str | None = None, telefono: str | None = None, activo: bool = True,
          actor: str) -> dict:
    """Alta manual de cliente con las mismas validaciones de RUT, correo y teléfono.
    Un RUT ya registrado devuelve `ClienteConflicto` (409). Auditoría sin valores personales."""
    datos = _validar_datos(rut=rut, nombre=nombre, tipo=tipo, giro=giro, direccion=direccion,
                           comuna=comuna, correo=correo, telefono=telefono)
    existente = buscar(conexion, datos["rut"])
    if existente is not None:
        raise ClienteConflicto(f"el RUT {rut_visible(datos['rut'])} ya está registrado a nombre de «{existente[1]}»")
    cliente_id = f"CLI-{uuid.uuid4().hex[:12]}"
    conexion.execute(
        "INSERT INTO clientes (id, tipo, rut, nombre, nombre_clave, giro, direccion, comuna, correo, telefono, "
        "activo, creado_por) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (cliente_id, datos["tipo"], datos["rut"], datos["nombre"], nombre_clave(datos["nombre"]),
         datos["giro"], datos["direccion"], datos["comuna"], datos["correo"], datos["telefono"], activo, actor),
    )
    seguridad.auditar(conexion, actor, "cliente_alta", cliente_id, "creado")
    return _ficha(conexion.execute(f"SELECT {_COLUMNAS} FROM clientes WHERE id = %s", (cliente_id,)).fetchone())


def editar(conexion: psycopg.Connection, cliente_id: str, *, rut: str, nombre: str, tipo: str,
           giro: str | None, direccion: str | None, comuna: str | None, correo: str | None,
           activo: bool, actor: str, telefono: str | None = None) -> dict:
    """Corrige la ficha del cliente. El RUT es la identidad: se puede corregir si el nuevo es válido y no
    es de otro cliente (409). Las imputaciones y movimientos ya asentados apuntan por id, así que no
    cambian. Auditoría: campos modificados, nunca valores."""
    datos = _validar_datos(rut=rut, nombre=nombre, tipo=tipo, giro=giro, direccion=direccion,
                           comuna=comuna, correo=correo, telefono=telefono)
    actual = conexion.execute(
        f"SELECT {_COLUMNAS} FROM clientes WHERE id = %s FOR UPDATE", (cliente_id,)
    ).fetchone()
    if actual is None:
        raise ClienteInexistente("cliente inexistente")
    otro = conexion.execute("SELECT nombre FROM clientes WHERE rut = %s AND id <> %s",
                            (datos["rut"], cliente_id)).fetchone()
    if otro is not None:
        raise ClienteConflicto(f"el RUT {rut_visible(datos['rut'])} ya está registrado a nombre de «{otro[0]}»")
    previo = dict(zip(("tipo", "rut", "nombre", "giro", "direccion", "comuna", "correo", "telefono", "activo"),
                      (actual[1], actual[2], actual[3], actual[4], actual[5], actual[6], actual[7], actual[8], actual[9])))
    nuevo = {**datos, "activo": activo}
    cambiados = [c for c in nuevo if nuevo[c] != previo[c]]
    if cambiados:
        conexion.execute(
            "UPDATE clientes SET tipo = %s, rut = %s, nombre = %s, nombre_clave = %s, giro = %s, direccion = %s, "
            "comuna = %s, correo = %s, telefono = %s, activo = %s WHERE id = %s",
            (datos["tipo"], datos["rut"], datos["nombre"], nombre_clave(datos["nombre"]), datos["giro"],
             datos["direccion"], datos["comuna"], datos["correo"], datos["telefono"], activo, cliente_id),
        )
        seguridad.auditar(conexion, actor, "cliente_edicion", cliente_id, ",".join(cambiados))
    return _ficha(conexion.execute(f"SELECT {_COLUMNAS} FROM clientes WHERE id = %s", (cliente_id,)).fetchone())
