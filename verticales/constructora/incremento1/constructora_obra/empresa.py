from dataclasses import dataclass


@dataclass(frozen=True)
class Empresa:
    id: str
    nombre: str
    es_sintetico: bool


EMPRESA_FIJA = Empresa(
    id="EMP-SINTETICA-001",
    nombre="Constructora Sintética Incremento 1 (dato sintético)",
    es_sintetico=True,
)
EMPRESA_COMERCIAL = Empresa(
    id="EMP-COMERCIAL-999",
    nombre="Empresa comercial sin convenio (dato sintético)",
    es_sintetico=True,
)
