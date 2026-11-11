"""Identidad del titular real del hotel (no es el tenant de pruebas).

Los datos coinciden con la política de tratamiento publicada en la landing
(versión 2026-11-10-aviso-02): Herencia SpA, RUT 76.707.504-9, domicilio en
5 de Abril 441, oficina 3, Chillán. El id técnico `EMP-HERENCIA-001` reemplaza
al marcador `EMP-SINTETICA-001` cuando el despliegue activa EMPRESA_TITULAR=1
o fija EMPRESA_ID / EMPRESA_NOMBRE.
"""
from nucleo.empresa import Empresa

EMPRESA_TITULAR_ID = "EMP-HERENCIA-001"
EMPRESA_TITULAR_NOMBRE = "Herencia SpA"
EMPRESA_TITULAR_RUT = "76.707.504-9"
EMPRESA_TITULAR_DOMICILIO = "5 de Abril 441, oficina 3, Chillán, Región de Ñuble"
EMPRESA_TITULAR_MARCA = "Hotel Herencia"

EMPRESA_TITULAR = Empresa(
    id=EMPRESA_TITULAR_ID,
    nombre=EMPRESA_TITULAR_NOMBRE,
    es_sintetico=False,
)
