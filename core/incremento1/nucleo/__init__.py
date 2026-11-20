"""Incremento 1 del núcleo (000-core): contexto de empresa fijado, conectores
con permisos, efectos financieros idempotentes, aprobaciones gobernadas y
herramientas con efectos explícitos. En memoria, sin red."""

from .empresa import EMPRESA_FIJA, Empresa
from .roles import CATALOGO as CATALOGO_ROLES, CatalogoRoles, DefinicionRol
from .stock import (
    BODEGAS_BASE,
    Bodega,
    ErrorStockCore,
    EstadoReposicion,
    ServicioStockCore,
    bodega_por_categoria,
    evaluar_reposicion,
    resumir_reposicion,
)

__all__ = [
    "BODEGAS_BASE",
    "Bodega",
    "CATALOGO_ROLES",
    "CatalogoRoles",
    "DefinicionRol",
    "EMPRESA_FIJA",
    "Empresa",
    "ErrorStockCore",
    "EstadoReposicion",
    "ServicioStockCore",
    "bodega_por_categoria",
    "evaluar_reposicion",
    "resumir_reposicion",
]
