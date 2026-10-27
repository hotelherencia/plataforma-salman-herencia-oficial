from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoPuerto:
    configurado: bool
    detalle: str


NO_CONFIGURADO = ResultadoPuerto(configurado=False, detalle="no configurado")


class PuertoPago:
    def iniciar_cobro(self, cuenta_id: str, monto_clp: int) -> ResultadoPuerto:
        return NO_CONFIGURADO


class PuertoDocumento:
    def emitir(self, cuenta_id: str) -> ResultadoPuerto:
        return NO_CONFIGURADO


class PuertosVacios:
    def __init__(self) -> None:
        self.pago = PuertoPago()
        self.documento = PuertoDocumento()
