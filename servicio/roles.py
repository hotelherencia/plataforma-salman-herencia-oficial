"""Roles de la plataforma y qué puede hacer cada uno (entrega 1A.2).

Dos administraciones distintas:

- **Administrador del hotel** (`admin_hotel`): el negocio. Precios, tipos y
  habitaciones, reservas, cobros, caja, reportes y bandejas.
- **Administrador de plataforma** (`admin_plataforma`): la infraestructura.
  Usuarios, seguridad y ajustes del sistema (p. ej. la tasa de IVA). No
  opera el hotel; puede consultar lo que cualquier sesión consulta.
- `administrador` (rol histórico) = ambas administraciones. Los usuarios
  existentes conservan todo su acceso: no se migra ni se bloquea a nadie.

Todo rol administrativo exige doble factor (aviso de enrolamiento y regla de
Google de 27f9ccf). `recepcion` y `caja` no cambian.
"""
from __future__ import annotations

ADMINISTRADOR = "administrador"
ADMIN_HOTEL = "admin_hotel"
ADMIN_PLATAFORMA = "admin_plataforma"
RECEPCION = "recepcion"
CAJA = "caja"

ROLES_VALIDOS = (ADMINISTRADOR, ADMIN_HOTEL, ADMIN_PLATAFORMA, RECEPCION, CAJA)
PATRON_ROL = "^(" + "|".join(ROLES_VALIDOS) + ")$"

ROLES_ADMIN_HOTEL = frozenset({ADMINISTRADOR, ADMIN_HOTEL})
ROLES_ADMIN_PLATAFORMA = frozenset({ADMINISTRADOR, ADMIN_PLATAFORMA})
# Roles que exigen doble factor (TOTP).
ROLES_ADMIN = ROLES_ADMIN_HOTEL | ROLES_ADMIN_PLATAFORMA

ETIQUETAS = {
    ADMINISTRADOR: "Administrador (hotel y plataforma)",
    ADMIN_HOTEL: "Administrador del hotel",
    ADMIN_PLATAFORMA: "Administrador de plataforma",
    RECEPCION: "Recepción",
    CAJA: "Caja",
}


def es_admin_hotel(rol: str | None) -> bool:
    return rol in ROLES_ADMIN_HOTEL


def es_admin_plataforma(rol: str | None) -> bool:
    return rol in ROLES_ADMIN_PLATAFORMA


def exige_doble_factor(rol: str | None) -> bool:
    return rol in ROLES_ADMIN


def con_admin_hotel(*roles: str) -> frozenset[str]:
    """Conjunto de roles operativos + las dos formas de administración del hotel."""
    return frozenset(roles) | ROLES_ADMIN_HOTEL
