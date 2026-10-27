"""Incremento 1 del núcleo (000-core): contexto de empresa fijado, conectores
con permisos, efectos financieros idempotentes, aprobaciones gobernadas y
herramientas con efectos explícitos. En memoria, sin red."""

from .empresa import EMPRESA_FIJA, Empresa

__all__ = ["EMPRESA_FIJA", "Empresa"]
