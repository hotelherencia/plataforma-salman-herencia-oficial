"""Puerto del modelo de lenguaje del agente (spec 005, D-AGT-02 pendiente).

Sin adaptador real autorizado, el único modelo disponible es el guionado de
las pruebas (NFR-A04: ninguna prueba de CI llama a un proveedor real). El
adaptador real se cargará solo si la configuración lo nombra.
"""
from __future__ import annotations

from typing import Any, Protocol


class NoConfigurado(Exception):
    """503 «modelo no configurado»: el puerto no tiene adaptador."""


class ModeloFallo(Exception):
    """El modelo no respondió o devolvió algo inutilizable."""


class ModeloLenguaje(Protocol):
    def decidir(self, mensajes: list[dict], herramientas: list[str]) -> dict[str, Any]:
        """Devuelve {"herramienta": str, "argumentos": dict} o lanza."""
        ...


class SinAdaptador:
    """Puerto sin proveedor: toda consulta queda pendiente (503)."""

    nombre = "sin_adaptador"

    def decidir(self, mensajes: list[dict], herramientas: list[str]) -> dict[str, Any]:
        raise NoConfigurado("modelo no configurado")


class ModeloGuionado:
    """Modelo falso determinista: entrega las decisiones del guion en orden.

    `decisiones` registra todo lo pedido, para que las pruebas afirmen cuántas
    veces se llamó al modelo (idempotencia, AG-S13).
    """

    nombre = "guionado"

    def __init__(self, guion: list[dict[str, Any]]):
        self._guion = list(guion)
        self.decisiones: list[dict[str, Any]] = []

    def decidir(self, mensajes: list[dict], herramientas: list[str]) -> dict[str, Any]:
        if not self._guion:
            raise ModeloFallo("guion agotado")
        decision = self._guion.pop(0)
        self.decisiones.append(decision)
        return decision
