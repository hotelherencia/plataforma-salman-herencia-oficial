from dataclasses import dataclass


@dataclass(frozen=True)
class Empresa:
    id: str
    nombre: str
    es_sintetico: bool


DATOS_SINTETICOS = True

EMPRESA_FIJA = Empresa(
    id="EMP-SINTETICA-001",
    nombre="Hotel Sintético Incremento 0 (dato sintético)",
    es_sintetico=DATOS_SINTETICOS,
)
