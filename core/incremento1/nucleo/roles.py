"""Catálogo transversal de roles en el core (#323).

Desacopla la definición de roles del módulo hotel: cada rol declara el módulo
al que pertenece (`core`, `hotel`, o futuras verticales cuando se habiliten).
Las verticales cerradas no exponen roles activos por defecto.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

MODULO_CORE = "core"
MODULO_HOTEL = "hotel"
MODULOS_ACTIVOS_POR_DEFECTO = (MODULO_CORE, MODULO_HOTEL)

DUENO = "dueno"
ADMINISTRADOR = "administrador"
ADMIN_HOTEL = "admin_hotel"
ADMIN_PLATAFORMA = "admin_plataforma"
RECEPCION = "recepcion"
CAJA = "caja"
ASEO = "aseo"


@dataclass(frozen=True)
class DefinicionRol:
    codigo: str
    modulo: str
    etiqueta: str
    descripcion: str
    exige_doble_factor: bool = False
    activo: bool = True
    orden: int = 100

    def a_dict(self) -> dict:
        return {
            "codigo": self.codigo,
            "modulo": self.modulo,
            "etiqueta": self.etiqueta,
            "descripcion": self.descripcion,
            "exige_doble_factor": self.exige_doble_factor,
            "activo": self.activo,
        }


CATALOGO_BASE: tuple[DefinicionRol, ...] = (
    DefinicionRol(
        codigo=DUENO,
        modulo=MODULO_CORE,
        etiqueta="Dueño (lectura global)",
        descripcion="Ve ventas, caja, ocupación y cuentas de todo el grupo y deja observaciones a la administración; no cambia datos",
        exige_doble_factor=True,
        orden=5,
    ),
    DefinicionRol(
        codigo=ADMINISTRADOR,
        modulo=MODULO_CORE,
        etiqueta="Administrador (hotel y plataforma)",
        descripcion="Acceso completo de negocio y plataforma",
        exige_doble_factor=True,
        orden=10,
    ),
    DefinicionRol(
        codigo=ADMIN_PLATAFORMA,
        modulo=MODULO_CORE,
        etiqueta="Administrador de plataforma",
        descripcion="Usuarios, seguridad y ajustes transversales del sistema",
        exige_doble_factor=True,
        orden=20,
    ),
    DefinicionRol(
        codigo=ADMIN_HOTEL,
        modulo=MODULO_HOTEL,
        etiqueta="Administrador del hotel",
        descripcion="Precios, habitaciones, reservas, caja, productos y reportes del hotel",
        exige_doble_factor=True,
        orden=30,
    ),
    DefinicionRol(
        codigo=RECEPCION,
        modulo=MODULO_HOTEL,
        etiqueta="Recepción",
        descripcion="Reservas, llegadas, salidas, solicitudes y coordinación de aseo",
        exige_doble_factor=False,
        orden=40,
    ),
    DefinicionRol(
        codigo=CAJA,
        modulo=MODULO_HOTEL,
        etiqueta="Caja",
        descripcion="Cobros, apertura y cierre de turno de caja",
        exige_doble_factor=False,
        orden=50,
    ),
    DefinicionRol(
        codigo=ASEO,
        modulo=MODULO_HOTEL,
        etiqueta="Aseo",
        descripcion="Lista de habitaciones por limpiar y confirmación de limpieza",
        exige_doble_factor=False,
        orden=60,
    ),
)


class CatalogoRoles:
    """Registro transversal de roles por módulo."""

    def __init__(self, definiciones: Iterable[DefinicionRol] = CATALOGO_BASE) -> None:
        self._por_codigo: dict[str, DefinicionRol] = {d.codigo: d for d in definiciones}

    def registrar(self, definicion: DefinicionRol) -> None:
        self._por_codigo[definicion.codigo] = definicion

    def obtener(self, codigo: str | None) -> DefinicionRol | None:
        if not codigo:
            return None
        return self._por_codigo.get(codigo)

    def para_modulos(self, modulos: Iterable[str] = MODULOS_ACTIVOS_POR_DEFECTO) -> list[DefinicionRol]:
        permitidos = set(modulos)
        return sorted(
            (d for d in self._por_codigo.values() if d.activo and d.modulo in permitidos),
            key=lambda d: (d.orden, d.codigo),
        )

    def codigos(self, modulos: Iterable[str] = MODULOS_ACTIVOS_POR_DEFECTO) -> tuple[str, ...]:
        return tuple(d.codigo for d in self.para_modulos(modulos))

    def etiquetas(self) -> dict[str, str]:
        return {d.codigo: d.etiqueta for d in self._por_codigo.values()}

    def exige_doble_factor(self, codigo: str | None) -> bool:
        d = self.obtener(codigo)
        return bool(d and d.exige_doble_factor)


CATALOGO = CatalogoRoles()
