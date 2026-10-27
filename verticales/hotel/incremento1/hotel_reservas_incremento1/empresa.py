from dataclasses import dataclass


@dataclass(frozen=True)
class Empresa:
    id: str
    nombre: str
    es_sintetico: bool


@dataclass(frozen=True)
class Establecimiento:
    id: str
    empresa_id: str
    nombre: str
    es_sintetico: bool


DATOS_SINTETICOS = True

EMPRESA_FIJA = Empresa(
    id="EMP-SINTETICA-001",
    nombre="Hotel Sintético Incremento 1 (dato sintético)",
    es_sintetico=DATOS_SINTETICOS,
)

ESTABLECIMIENTO_FIJO = Establecimiento(
    id="EST-SINTETICO-001",
    empresa_id=EMPRESA_FIJA.id,
    nombre="Edificio Sintético (dato sintético)",
    es_sintetico=DATOS_SINTETICOS,
)
