from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoPuerto:
    configurado: bool
    detalle: str


NO_CONFIGURADO = ResultadoPuerto(configurado=False, detalle="no configurado")


class PuertoPMS:
    def consultar_reserva(self, referencia_externa: str) -> ResultadoPuerto:
        return NO_CONFIGURADO

    def propagar_disponibilidad(self, unidad_id: str, rango) -> ResultadoPuerto:
        return NO_CONFIGURADO


class PuertoCanal:
    def publicar_disponibilidad(self, unidad_id: str, rango) -> ResultadoPuerto:
        return NO_CONFIGURADO

    def recibir_evento(self, evento) -> ResultadoPuerto:
        return NO_CONFIGURADO


class PuertoPago:
    def iniciar_cobro(self, reserva_id: str, monto_clp: int) -> ResultadoPuerto:
        return NO_CONFIGURADO


class PuertoDocumentoTributario:
    def emitir(self, reserva_id: str) -> ResultadoPuerto:
        return NO_CONFIGURADO


class PuertosVacios:
    def __init__(self) -> None:
        self.pms = PuertoPMS()
        self.canal = PuertoCanal()
        self.pago = PuertoPago()
        self.documento_tributario = PuertoDocumentoTributario()
