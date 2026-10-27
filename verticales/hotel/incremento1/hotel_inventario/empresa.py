from dataclasses import dataclass


@dataclass(frozen=True)
class Empresa:
    id: str
    nombre: str
    es_sintetico: bool


# Mismo id que la empresa fija del incremento 0. Se repite aquí para no acoplar
# las pruebas de los dos incrementos.
EMPRESA_FIJA = Empresa(
    id="EMP-SINTETICA-001",
    nombre="Hotel Sintético Incremento 1 (dato sintético)",
    es_sintetico=True,
)
