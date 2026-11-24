"""Roles de la plataforma y catálogo transversal (#323, entrega 1A.2).

Las definiciones base viven fuera del módulo hotel, en
`core/incremento1/nucleo/roles.py`, y se persisten en `roles_catalogo` +
`empresa_modulos` (migración 0054) para habilitar futuras verticales sin
acoplar la identidad al hotel.

Dos administraciones distintas:
- **Administrador del hotel** (`admin_hotel`): el negocio. Precios, tipos y
  habitaciones, reservas, cobros, caja, reportes y bandejas.
- **Administrador de plataforma** (`admin_plataforma`): la infraestructura.
  Usuarios, seguridad y ajustes del sistema (p. ej. la tasa de IVA).
- `administrador` (rol histórico) = ambas administraciones.
"""
from __future__ import annotations

import psycopg

from core.incremento1.nucleo.roles import (
    ADMIN_HOTEL,
    ADMIN_PLATAFORMA,
    ADMINISTRADOR,
    ASEO,
    CAJA,
    CATALOGO,
    MODULO_CORE,
    MODULO_HOTEL,
    MODULOS_ACTIVOS_POR_DEFECTO,
    RECEPCION,
    DUENO,
    SUPER_ADMIN,
    CatalogoRoles,
    DefinicionRol,
)

ROLES_VALIDOS = (SUPER_ADMIN, DUENO, ADMINISTRADOR, ADMIN_HOTEL, ADMIN_PLATAFORMA, RECEPCION, CAJA, ASEO)
PATRON_ROL = "^(" + "|".join(ROLES_VALIDOS) + ")$"

ROLES_ADMIN_HOTEL = frozenset({SUPER_ADMIN, ADMINISTRADOR, ADMIN_HOTEL})
ROLES_ADMIN_PLATAFORMA = frozenset({SUPER_ADMIN, ADMINISTRADOR, ADMIN_PLATAFORMA})
# Roles que exigen doble factor (TOTP).
ROLES_ADMIN = ROLES_ADMIN_HOTEL | ROLES_ADMIN_PLATAFORMA

ETIQUETAS = CATALOGO.etiquetas()

# Jerarquía de cuentas: nadie crea, cambia la clave, vincula el correo, revoca ni da de baja una cuenta
# de rango igual o superior al suyo. Solo el súper administrador gobierna cuentas privilegiadas
# (incluidas otras de súper administrador); así un administrador de plataforma comprometido no puede
# tomar la cuenta del dueño ni de un administrador. Un rol desconocido vale 0.
RANGO = {
    SUPER_ADMIN: 100,
    DUENO: 90,
    ADMINISTRADOR: 80,
    ADMIN_PLATAFORMA: 60,
    ADMIN_HOTEL: 60,
    RECEPCION: 10,
    CAJA: 10,
    ASEO: 10,
}
RANGO_PRIVILEGIADO = 60  # desde aquí una cuenta es «privilegiada» (alertas y registro reforzado)


def es_super_admin(rol: str | None) -> bool:
    return rol == SUPER_ADMIN


def puede_gestionar(rol_actor: str | None, rol_objetivo: str | None) -> bool:
    """¿Puede `rol_actor` crear o administrar cuentas con `rol_objetivo`? Exige ser administración de
    plataforma y tener rango estrictamente mayor. El rol súper administrador no se crea ni se asigna
    por la API (hay uno solo, ligado al correo institucional): nadie lo gestiona."""
    if rol_objetivo == SUPER_ADMIN or rol_objetivo not in RANGO or not es_admin_plataforma(rol_actor):
        return False
    return rol_actor == SUPER_ADMIN or RANGO.get(rol_actor, 0) > RANGO[rol_objetivo]


# Quienes validan un cambio de rol: la administración del hotel (nunca quien lo pidió ni el afectado).
ROLES_APROBADORES = frozenset({ADMIN_HOTEL, ADMINISTRADOR})


def es_privilegiado(rol: str | None) -> bool:
    return RANGO.get(rol, 0) >= RANGO_PRIVILEGIADO


def roles_gestionables(rol_actor: str | None) -> list[str]:
    return [r for r in ROLES_VALIDOS if puede_gestionar(rol_actor, r)]


def es_admin_hotel(rol: str | None) -> bool:
    return rol in ROLES_ADMIN_HOTEL


def es_admin_plataforma(rol: str | None) -> bool:
    return rol in ROLES_ADMIN_PLATAFORMA


def exige_doble_factor(rol: str | None) -> bool:
    return rol in ROLES_ADMIN or CATALOGO.exige_doble_factor(rol)


def con_admin_hotel(*roles: str) -> frozenset[str]:
    """Conjunto de roles operativos + las dos formas de administración del hotel."""
    return frozenset(roles) | ROLES_ADMIN_HOTEL


def modulos_activos(conexion: psycopg.Connection, empresa_id: str | None = None) -> list[str]:
    """Módulos habilitados para la empresa (core + hotel por defecto)."""
    if empresa_id:
        filas = conexion.execute(
            "SELECT modulo FROM empresa_modulos WHERE empresa_id = %s AND activo ORDER BY modulo",
            (empresa_id,),
        ).fetchall()
        if filas:
            modulos = [f[0] for f in filas]
            if MODULO_CORE not in modulos:
                modulos.insert(0, MODULO_CORE)
            return modulos
    return list(MODULOS_ACTIVOS_POR_DEFECTO)


def listar_catalogo(conexion: psycopg.Connection, empresa_id: str | None = None) -> dict:
    """Devuelve el catálogo de roles filtrado por los módulos activos de la empresa (#323)."""
    activos = modulos_activos(conexion, empresa_id)
    filas = conexion.execute(
        "SELECT codigo, modulo, etiqueta, descripcion, exige_doble_factor, activo "
        "FROM roles_catalogo WHERE activo AND modulo = ANY(%s) ORDER BY orden, codigo",
        (activos,),
    ).fetchall()
    if filas:
        items = [
            {
                "codigo": f[0],
                "modulo": f[1],
                "etiqueta": f[2],
                "descripcion": f[3],
                "exige_doble_factor": bool(f[4]),
                "activo": bool(f[5]),
            }
            for f in filas
        ]
    else:
        items = [d.a_dict() for d in CATALOGO.para_modulos(activos)]
    return {"modulos_activos": activos, "roles": items}


__all__ = [
    "ADMINISTRADOR",
    "SUPER_ADMIN",
    "RANGO",
    "ROLES_APROBADORES",
    "es_super_admin",
    "puede_gestionar",
    "es_privilegiado",
    "roles_gestionables",
    "ADMIN_HOTEL",
    "ADMIN_PLATAFORMA",
    "ASEO",
    "CAJA",
    "CATALOGO",
    "CatalogoRoles",
    "DefinicionRol",
    "ETIQUETAS",
    "MODULO_CORE",
    "MODULO_HOTEL",
    "PATRON_ROL",
    "RECEPCION",
    "ROLES_ADMIN",
    "ROLES_ADMIN_HOTEL",
    "ROLES_ADMIN_PLATAFORMA",
    "ROLES_VALIDOS",
    "con_admin_hotel",
    "es_admin_hotel",
    "es_admin_plataforma",
    "exige_doble_factor",
    "listar_catalogo",
    "modulos_activos",
]
