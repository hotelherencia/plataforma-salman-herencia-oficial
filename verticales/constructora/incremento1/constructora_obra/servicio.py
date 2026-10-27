import itertools
import threading
from dataclasses import dataclass, replace
from datetime import datetime

from .empresa import EMPRESA_FIJA, Empresa

EMPRESA_DESCONOCIDA = "empresa desconocida"
SIN_CONVENIO = "sin convenio ni permiso"


class AccesoDenegado(Exception):
    pass


@dataclass(frozen=True)
class ReporteAvance:
    id: str
    partida: str
    porcentaje_acumulado: float
    actor: str
    aporte_clave: str
    estado: str


@dataclass(frozen=True)
class Presupuesto:
    version: int
    monto_clp: int
    linea_base_clp: int
    motivo: str
    aprobador: str


@dataclass(frozen=True)
class OrdenCompra:
    id: str
    material: str
    cantidad: int
    estado: str
    aprobador: str | None = None


@dataclass(frozen=True)
class Recepcion:
    evento_clave: str
    orden_id: str
    recibidas: int
    aceptadas: int
    rechazadas: int
    pendientes: int


@dataclass(frozen=True)
class Observacion:
    id: str
    item: str
    reportante: str
    estado: str
    solucion: str | None = None


class ServicioConstructora:
    def __init__(self, empresa: Empresa = EMPRESA_FIJA) -> None:
        self._empresa = empresa
        self._reportes: dict[str, ReporteAvance] = {}
        self._aportes: set[str] = set()
        self._partidas: dict[str, float] = {}
        self._presupuesto = Presupuesto(version=1, monto_clp=100, linea_base_clp=100, motivo="base", aprobador="base")
        self._compromiso_total = 0
        self._ordenes: dict[str, OrdenCompra] = {}
        self._stock: dict[str, int] = {}
        self._recepciones: dict[str, Recepcion] = {}
        self._observaciones: dict[str, Observacion] = {}
        self._comentarios_oficiales: list[str] = []
        self._ids = itertools.count(1)
        self._cerrojo = threading.Lock()

    @property
    def empresa(self) -> Empresa:
        return self._empresa

    def informar_avance(
        self, empresa_id: str, partida: str, porcentaje_acumulado: float, actor: str, aporte_clave: str
    ) -> ReporteAvance:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if aporte_clave in self._aportes:
                return next(r for r in self._reportes.values() if r.aporte_clave == aporte_clave)
            self._aportes.add(aporte_clave)
            anterior = self._partidas.get(partida, 0.0)
            estado = "registrado"
            if porcentaje_acumulado < anterior:
                estado = "requiere_aprobacion_rectificacion"
            self._partidas[partida] = max(anterior, porcentaje_acumulado)
            reporte = ReporteAvance(
                id=self._nuevo_id("RPT"),
                partida=partida,
                porcentaje_acumulado=porcentaje_acumulado,
                actor=actor,
                aporte_clave=aporte_clave,
                estado=estado,
            )
            self._reportes[reporte.id] = reporte
            return reporte

    def avance_partida(self, empresa_id: str, partida: str) -> float:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return self._partidas.get(partida, 0.0)

    def calcular_desvio(self, empresa_id: str, programado_clp: int, ejecutado_clp: int, umbral: float) -> tuple[str, float | None]:
        self._exigir_empresa(empresa_id)
        if programado_clp == 0:
            return ("sin_evaluacion", None)
        desvio = (ejecutado_clp - programado_clp) / programado_clp
        if desvio > umbral:
            return ("alerta", desvio)
        return ("dentro", desvio)

    def modificar_presupuesto(self, empresa_id: str, monto_clp: int, motivo: str, aprobador: str) -> Presupuesto:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._presupuesto = Presupuesto(
                version=self._presupuesto.version + 1,
                monto_clp=monto_clp,
                linea_base_clp=self._presupuesto.linea_base_clp,
                motivo=motivo,
                aprobador=aprobador,
            )
            return self._presupuesto

    def fijar_compromiso_total(self, empresa_id: str, monto_clp: int) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._compromiso_total = monto_clp

    def disponible_presupuesto(self, empresa_id: str) -> int:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return self._presupuesto.monto_clp - self._compromiso_total

    def crear_orden(self, empresa_id: str, material: str, cantidad: int, aprobador: str) -> OrdenCompra:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            orden = OrdenCompra(
                id=self._nuevo_id("ORD"),
                material=material,
                cantidad=cantidad,
                estado="aprobada",
                aprobador=aprobador,
            )
            self._ordenes[orden.id] = orden
            return orden

    def nota_con_instrucciones(self, empresa_id: str, texto: str) -> str:
        self._exigir_empresa(empresa_id)
        return "borrador de solicitud creado; sin envio a proveedor"

    def recibir(self, empresa_id: str, orden_id: str, evento_clave: str, recibidas: int, rechazadas: int = 0) -> Recepcion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if evento_clave in self._recepciones:
                return self._recepciones[evento_clave]
            orden = self._ordenes[orden_id]
            aceptadas = recibidas - rechazadas
            anterior = self._recepciones_pendientes(orden_id)
            recepcion = Recepcion(
                evento_clave=evento_clave,
                orden_id=orden_id,
                recibidas=recibidas,
                aceptadas=aceptadas,
                rechazadas=rechazadas,
                pendientes=max(orden.cantidad - anterior - aceptadas, 0),
            )
            self._recepciones[evento_clave] = recepcion
            self._stock[orden.material] = self._stock.get(orden.material, 0) + aceptadas
            return recepcion

    def _recepciones_pendientes(self, orden_id: str) -> int:
        return sum(r.aceptadas for r in self._recepciones.values() if r.orden_id == orden_id)

    def devolver(self, empresa_id: str, material: str, cantidad: int) -> str:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._stock[material] = self._stock.get(material, 0) - cantidad
            return "devolucion registrada; sin abono financiero ni cambio de contrato"

    def crear_observacion(self, empresa_id: str, item: str, reportante: str) -> Observacion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            obs = Observacion(
                id=self._nuevo_id("OBS"),
                item=item,
                reportante=reportante,
                estado="abierta",
            )
            self._observaciones[obs.id] = obs
            return obs

    def cerrar_observacion(self, empresa_id: str, obs_id: str, actor: str) -> Observacion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            obs = self._observaciones[obs_id]
            if actor != "inspector":
                raise AccesoDenegado("el reportante no puede cerrar la observacion")
            cerrada = replace(obs, estado="cerrada")
            self._observaciones[obs_id] = cerrada
            return cerrada

    def proponer_solucion(self, empresa_id: str, obs_id: str, solucion: str) -> Observacion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            obs = self._observaciones[obs_id]
            return replace(self._observaciones[obs_id], estado="por_validar", solucion=solucion)

    def adjuntar_comentario_ia(self, empresa_id: str, texto: str) -> str:
        self._exigir_empresa(empresa_id)
        return "comentario no oficial: no modifica presupuesto ni programa"

    def consultar_como_comercial(self, empresa_comercial_id: str) -> None:
        if empresa_comercial_id != self._empresa.id:
            raise AccesoDenegado(SIN_CONVENIO)

    def _exigir_empresa(self, empresa_id: str) -> None:
        if empresa_id != self._empresa.id:
            raise AccesoDenegado(EMPRESA_DESCONOCIDA)

    def _nuevo_id(self, prefijo: str) -> str:
        return f"{prefijo}-SINT-{next(self._ids):04d}"


def constructora_sintetica() -> ServicioConstructora:
    return ServicioConstructora()
