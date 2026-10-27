from dataclasses import dataclass


@dataclass(frozen=True)
class Empresa:
    id: str
    nombre: str
    es_sintetico: bool


EMPRESA_FIJA = Empresa(
    id="EMP-SINTETICA-001",
    nombre="Núcleo Sintético Incremento 1 (dato sintético)",
    es_sintetico=True,
)
