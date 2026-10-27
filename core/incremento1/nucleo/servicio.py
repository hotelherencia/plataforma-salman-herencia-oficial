import threading
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from .empresa import EMPRESA_FIJA, Empresa

EMPRESA_DESCONOCIDA = "empresa desconocida"


class AccesoDenegado(Exception):
    pass


class EfectoNoAplicable(Exception):
    pass


@dataclass(frozen=True)
class Conector:
    id: str
    permisos: frozenset
    placeholder: bool = False


@dataclass(frozen=True)
class EfectoPago:
    id: str
    clave: str
    estado: str
    monto_clp: int


@dataclass(frozen=True)
class Aprobacion:
    id: str
    monto_clp: int
    parametros: tuple[tuple[str, object], ...]
    vigente_hasta: datetime
    usada: bool = False


class Nucleo:
    """Núcleo local: la empresa nace del contexto fijado al construir el servicio,
    no de un campo libre del llamador; toda operación exige la empresa esperada."""

    def __init__(self, empresa: Empresa = EMPRESA_FIJA) -> None:
        self._empresa = empresa
        self._conectores: dict[str, Conector] = {}
        self._referencias: dict[str, str] = {}
        self._efectos: dict[str, EfectoPago] = {}
        self._deudas: dict[str, int] = {}
        self._aprobaciones: dict[str, Aprobacion] = {}
        self._herramientas: dict[str, frozenset] = {}
        self._excluidos: list[tuple[str, str]] = []
        self._ids = 0
        self._cerrojo = threading.Lock()

    @property
    def empresa(self) -> Empresa:
        return self._empresa

    def registrar_conector(self, empresa_id: str, conector_id: str, permisos: set, placeholder: bool = False) -> Conector:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            conector = Conector(id=conector_id, permisos=frozenset(permisos), placeholder=placeholder)
            self._conectores[conector_id] = conector
            return conector

    def vincular_referencia(self, empresa_id: str, conector_id: str, referencia: str) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._referencias[referencia] = conector_id

    def usar_referencia(self, empresa_id: str, referencia: str, operacion: str) -> str:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            conector_id = self._referencias.get(referencia)
            if conector_id is None:
                raise AccesoDenegado("referencia no habilitada")
            conector = self._conectores[conector_id]
            if conector.placeholder:
                self._excluidos.append((conector_id, "placeholder"))
                raise AccesoDenegado("conector bloqueado: efectos desconocidos")
            if operacion not in conector.permisos:
                raise AccesoDenegado("operación fuera del permiso del conector")
            return f"ok:{operacion}"

    def registrar_deuda(self, empresa_id: str, deuda_id: str, monto_clp: int) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._deudas[deuda_id] = monto_clp

    def aplicar_resultado_pago(self, empresa_id: str, clave: str, estado: str, monto_clp: int) -> EfectoPago:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            existente = self._efectos.get(clave)
            if existente is not None:
                return existente
            efecto = EfectoPago(id=self._nuevo_id("EFX"), clave=clave, estado=estado, monto_clp=monto_clp)
            self._efectos[clave] = efecto
            if estado == "autorizado":
                for deuda_id, monto in list(self._deudas.items()):
                    if monto == monto_clp:
                        self._deudas[deuda_id] = 0
            return efecto

    def deuda(self, empresa_id: str, deuda_id: str) -> int:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return self._deudas.get(deuda_id, 0)

    def aprobar(self, empresa_id: str, monto_clp: int, parametros: dict, ahora: datetime, vigencia_minutos: int) -> Aprobacion:
        self._exigir_empresa(empresa_id)
        aprobacion = Aprobacion(
            id=self._nuevo_id("APR"),
            monto_clp=monto_clp,
            parametros=tuple(sorted(parametros.items())),
            vigente_hasta=ahora + timedelta(minutes=vigencia_minutos),
        )
        self._aprobaciones[aprobacion.id] = aprobacion
        return aprobacion

    def ejecutar_con_aprobacion(self, empresa_id: str, aprobacion_id: str, monto_clp: int, parametros: dict, ahora: datetime) -> str:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            aprobacion = self._aprobaciones.get(aprobacion_id)
            if (
                aprobacion is None
                or aprobacion.usada
                or ahora > aprobacion.vigente_hasta
                or aprobacion.monto_clp != monto_clp
                or tuple(sorted(parametros.items())) != aprobacion.parametros
            ):
                raise EfectoNoAplicable("aprobación inválida: monto, parámetros, vigencia o uso")
            self._aprobaciones[aprobacion_id] = replace(aprobacion, usada=True)
            return "ejecutado"

    def registrar_herramienta(self, empresa_id: str, nombre: str, efectos_permitidos: set) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._herramientas[nombre] = frozenset(efectos_permitidos)

    def invocar_herramienta(self, empresa_id: str, nombre: str, efecto_solicitado: str) -> str:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            permitidos = self._herramientas.get(nombre)
            if permitidos is None or efecto_solicitado not in permitidos:
                self._excluidos.append((nombre, efecto_solicitado))
                raise AccesoDenegado("efecto excluido: no se ejecuta ni se llama al destino")
            return f"ok:{efecto_solicitado}"

    def efectos_excluidos(self, empresa_id: str) -> list[tuple[str, str]]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return list(self._excluidos)

    def _exigir_empresa(self, empresa_id: str) -> None:
        if empresa_id != self._empresa.id:
            raise AccesoDenegado(EMPRESA_DESCONOCIDA)

    def _nuevo_id(self, prefijo: str) -> str:
        self._ids += 1
        return f"{prefijo}-SINT-{self._ids:04d}"


def nucleo_sintetico() -> Nucleo:
    return Nucleo()
