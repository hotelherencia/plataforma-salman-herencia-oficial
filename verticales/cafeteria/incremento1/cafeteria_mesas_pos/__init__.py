"""Incremento 1 de la vertical cafetería: mesas con QR, pedidos a cocina, cuenta
compartida con reparto, recetas/stock/movimientos, gastos con aprobación,
propuestas de compra con expiración, alertas y ledger. En memoria, sin red."""

from .empresa import EMPRESA_FIJA, Empresa

__all__ = ["EMPRESA_FIJA", "Empresa"]
