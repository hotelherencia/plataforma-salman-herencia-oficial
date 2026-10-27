import hashlib
import itertools
import threading
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from .empresa import EMPRESA_FIJA, Empresa

EMPRESA_DESCONOCIDA = "empresa desconocida"


class AccesoDenegado(Exception):
    pass


@dataclass(frozen=True)
class Lead:
    id: str
    canal: str
    contacto: str
    etiqueta: str = "nuevo"


@dataclass(frozen=True)
class Unidad:
    id: str
    precio_base_clp: int
    reserva_vigente: str | None = None
    promesada: bool = False


@dataclass(frozen=True)
class Cotizacion:
    id: str
    unidad_id: str
    lead_id: str
    precio_versionado_clp: int
    pie_clp: int
    financiamiento_estimado_clp: int
    version: int
    vencimiento: datetime


@dataclass(frozen=True)
class Cita:
    id: str
    lead_id: str
    cuando_utc: datetime
    zona: str
    estado: str
    referencia_anterior: str | None = None


@dataclass(frozen=True)
class Promesa:
    id: str
    unidad_id: str
    firmantes_requeridos: int
    firmas: tuple[str, ...]
    version_legal: int
    estado: str
    documento_hash: str


@dataclass(frozen=True)
class CasoPostventa:
    id: str
    descripcion: str
    clasificacion: str
    responsable: str
    estado: str
    historial: tuple[str, ...] = ()


class ServicioInmobiliaria:
    def __init__(self, empresa: Empresa = EMPRESA_FIJA) -> None:
        self._empresa = empresa
        self._leads: dict[str, Lead] = {}
        self._unidades: dict[str, Unidad] = {}
        self._cotizaciones: dict[str, Cotizacion] = {}
        self._citas: dict[str, Cita] = {}
        self._promesas: dict[str, Promesa] = {}
        self._casos: dict[str, CasoPostventa] = {}
        self._saldo_cuotas: dict[str, int] = {}
        self._pagos_cuotas: set[str] = set()
        self._documentos: dict[str, str] = {}
        self._accesos: dict[str, set[str]] = {}
        self._permisos_contacto: dict[str, bool] = {}
        self._ids = itertools.count(1)
        self._cerrojo = threading.Lock()

    @property
    def empresa(self) -> Empresa:
        return self._empresa

    def registrar_lead(self, empresa_id: str, canal: str, contacto: str) -> tuple[Lead, str]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            coincidencias = [l for l in self._leads.values() if l.contacto == contacto]
            if len(coincidencias) == 1:
                return coincidencias[0], "coincidencia sugerida: seguimiento unico"
            lead = Lead(id=self._nuevo_id("LEAD"), canal=canal, contacto=contacto)
            self._leads[lead.id] = lead
            if len(coincidencias) > 1:
                return lead, "identidad ambigua: separado para revision"
            return lead, "nuevo"

    def registrar_unidad(self, empresa_id: str, unidad_id: str, precio_base_clp: int) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._unidades[unidad_id] = Unidad(id=unidad_id, precio_base_clp=precio_base_clp)

    def calificar(self, empresa_id: str, lead_id: str, presupuesto_declarado_clp: int) -> Lead:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            lead = self._leads[lead_id]
            calificado = replace(lead, etiqueta=f"declaracion:{presupuesto_declarado_clp}")
            self._leads[lead_id] = calificado
            return calificado

    def cotizar(
        self,
        empresa_id: str,
        unidad_id: str,
        lead_id: str,
        precio_versionado_clp: int,
        pie_clp: int,
        financiamiento_estimado_clp: int,
        ahora: datetime,
        vigencia_dias: int = 7,
    ) -> Cotizacion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            version = sum(1 for c in self._cotizaciones.values() if c.unidad_id == unidad_id and c.lead_id == lead_id) + 1
            cotizacion = Cotizacion(
                id=self._nuevo_id("COT"),
                unidad_id=unidad_id,
                lead_id=lead_id,
                precio_versionado_clp=precio_versionado_clp,
                pie_clp=pie_clp,
                financiamiento_estimado_clp=financiamiento_estimado_clp,
                version=version,
                vencimiento=ahora + timedelta(days=vigencia_dias),
            )
            self._cotizaciones[cotizacion.id] = cotizacion
            return cotizacion

    def reservar_unidad(self, empresa_id: str, unidad_id: str, lead_id: str, clave: str) -> str:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            unidad = self._unidades[unidad_id]
            if unidad.reserva_vigente not in (None, lead_id):
                return "en conciliacion"
            self._unidades[unidad_id] = replace(unidad, reserva_vigente=lead_id)
            return "reservada"

    def proponer_cita(self, empresa_id: str, lead_id: str, cuando_utc: datetime, zona: str | None) -> Cita:
        self._exigir_empresa(empresa_id)
        if not zona:
            raise ValueError("zona/offset requerido")
        with self._cerrojo:
            cita = Cita(
                id=self._nuevo_id("CITA"),
                lead_id=lead_id,
                cuando_utc=cuando_utc,
                zona=zona,
                estado="pendiente",
            )
            self._citas[cita.id] = cita
            return cita

    def aceptar_cita_interesado(self, empresa_id: str, cita_id: str) -> Cita:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            cita = self._citas[cita_id]
            pendiente = replace(cita, estado="pendiente_autorizacion")
            self._citas[cita_id] = pendiente
            return pendiente

    def reprogramar_cita(self, empresa_id: str, cita_id: str, nueva_utc: datetime, zona: str) -> Cita:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            anterior = self._citas[cita_id]
            nueva = Cita(
                id=self._nuevo_id("CITA"),
                lead_id=anterior.lead_id,
                cuando_utc=nueva_utc,
                zona=zona,
                estado="pendiente_autorizacion",
                referencia_anterior=anterior.id,
            )
            self._citas[nueva.id] = nueva
            return nueva

    def crear_promesa(self, empresa_id: str, unidad_id: str, firmantes_requeridos: int, version_legal: int) -> Promesa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            documento = f"promesa-{unidad_id}-v{version_legal}"
            promesa = Promesa(
                id=self._nuevo_id("PROM"),
                unidad_id=unidad_id,
                firmantes_requeridos=firmantes_requeridos,
                firmas=(),
                version_legal=version_legal,
                estado="pendiente",
                documento_hash=self._huella(documento),
            )
            self._promesas[promesa.id] = promesa
            self._documentos[promesa.id] = documento
            return promesa

    def firmar(self, empresa_id: str, promesa_id: str, firmante: str, exitosa: bool = True) -> Promesa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            promesa = self._promesas[promesa_id]
            if not exitosa:
                return promesa
            firmas = promesa.firmas + (firmante,)
            completa = len(firmas) >= promesa.firmantes_requeridos
            actualizada = replace(
                promesa,
                firmas=firmas,
                estado="promesada" if completa else "pendiente",
            )
            self._promesas[promesa_id] = actualizada
            if completa:
                unidad = self._unidades[promesa.unidad_id]
                self._unidades[promesa.unidad_id] = replace(unidad, promesada=True)
            return actualizada

    def cambiar_documento_promesa(self, empresa_id: str, promesa_id: str, nuevo_contenido: str) -> str:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            nueva_huella = self._huella(nuevo_contenido)
            self._documentos[promesa_id] = nuevo_contenido
            return nueva_huella

    def registrar_cuota(self, empresa_id: str, deuda_id: str, monto_clp: int) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._saldo_cuotas[deuda_id] = monto_clp

    def generar_recordatorio(self, empresa_id: str, deuda_id: str) -> str:
        self._exigir_empresa(empresa_id)
        return f"borrador recordatorio: cuota {deuda_id} pendiente"

    def registrar_pago_cuota(self, empresa_id: str, deuda_id: str, monto_clp: int, clave: str) -> int:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if clave in self._pagos_cuotas:
                return self._saldo_cuotas[deuda_id]
            self._pagos_cuotas.add(clave)
            self._saldo_cuotas[deuda_id] = self._saldo_cuotas.get(deuda_id, 0) - monto_clp
            return self._saldo_cuotas[deuda_id]

    def vincular_acceso(self, empresa_id: str, cliente_id: str, unidad_id: str) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._accesos.setdefault(cliente_id, set()).add(unidad_id)

    def reasignar_acceso_corriente(self, empresa_id: str, unidad_id: str, desde: str, hacia: str) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if unidad_id in self._accesos.get(desde, set()):
                self._accesos[desde].discard(unidad_id)
            self._accesos.setdefault(hacia, set()).add(unidad_id)

    def vista_cliente(self, empresa_id: str, cliente_id: str, unidad_solicitada: str) -> set[str]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            permitidas = self._accesos.get(cliente_id, set())
            if unidad_solicitada not in permitidas:
                raise AccesoDenegado("recurso de otro cliente o empresa")
            return set(permitidas)

    def corregir_telefono(self, empresa_id: str, cliente_id: str, telefono_nuevo: str) -> str:
        self._exigir_empresa(empresa_id)
        return "telefono actualizado sin cambiar titularidades ni enviar informacion"

    def crear_caso_postventa(self, empresa_id: str, descripcion: str, urgente: bool = False) -> CasoPostventa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            texto = descripcion.lower()
            if "negar garantia" in texto or "fuera de garantia" in texto:
                clasificacion = "revision_humana"
            else:
                clasificacion = "clasificacion_provisional"
            caso = CasoPostventa(
                id=self._nuevo_id("CASO"),
                descripcion=descripcion,
                clasificacion=clasificacion,
                responsable="recepcion" if not urgente else "supervisor",
                estado="pendiente",
            )
            self._casos[caso.id] = caso
            return caso

    def registrar_intento_visita(self, empresa_id: str, caso_id: str, motivo: str) -> CasoPostventa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            caso = self._casos[caso_id]
            actualizado = replace(
                caso,
                estado="pendiente_recoordinacion",
                historial=caso.historial + (f"intento: {motivo}",),
            )
            self._casos[caso_id] = actualizado
            return actualizado

    def proponer_reparacion(self, empresa_id: str, caso_id: str, propuesta: str) -> CasoPostventa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            caso = self._casos[caso_id]
            actualizado = replace(
                caso,
                estado="por_validar",
                historial=caso.historial + (f"propuesta: {propuesta}",),
            )
            self._casos[caso_id] = actualizado
            return actualizado

    def reabrir_caso(self, empresa_id: str, caso_id: str, nueva_evidencia: str) -> CasoPostventa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            caso = self._casos[caso_id]
            actualizado = replace(
                caso,
                estado="reabierto",
                historial=caso.historial + (f"reapertura: {nueva_evidencia}",),
            )
            self._casos[caso_id] = actualizado
            return actualizado

    def retirar_permiso_contacto(self, empresa_id: str, lead_id: str) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            self._permisos_contacto[lead_id] = False

    def automatizar_seguimiento(self, empresa_id: str, lead_id: str) -> str:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if self._permisos_contacto.get(lead_id) is False:
                return "seguimiento suspendido: origen y motivo conservados"
            return "seguimiento automatico activo"

    def _huella(self, contenido: str) -> str:
        return hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:16]

    def _exigir_empresa(self, empresa_id: str) -> None:
        if empresa_id != self._empresa.id:
            raise AccesoDenegado(EMPRESA_DESCONOCIDA)

    def _nuevo_id(self, prefijo: str) -> str:
        return f"{prefijo}-SINT-{next(self._ids):04d}"


def inmobiliaria_sintetica() -> ServicioInmobiliaria:
    servicio = ServicioInmobiliaria()
    servicio.registrar_unidad(servicio.empresa.id, "U1", 80_000_000)
    servicio.registrar_unidad(servicio.empresa.id, "U2", 95_000_000)
    return servicio
