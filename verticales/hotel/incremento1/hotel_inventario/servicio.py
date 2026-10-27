import itertools
import threading
from dataclasses import replace
from datetime import date, datetime, time, timedelta

from .dominio import (
    ESTADOS_VENDIBLES,
    Cargo,
    Establecimiento,
    EstadoDevolucion,
    EstadoReserva,
    EstadoTarea,
    EstadoUnidad,
    Huesped,
    AccionRegistrada,
    Aprobacion,
    ExtraHotel,
    Liquidacion,
    LineaExtra,
    OfertaVigente,
    Pago,
    PedidoHabitacion,
    PropuestaCambio,
    PropuestaUpsell,
    ProyeccionPublica,
    ReglaCantidad,
    Reserva,
    ResultadoBorrador,
    ResultadoPedido,
    SolicitudDevolucion,
    TransferenciaHumana,
    ResultadoCancelacion,
    ResultadoReserva,
    TareaOperativa,
    TipoCargo,
    Unidad,
)
from .empresa import EMPRESA_FIJA, Empresa
from .puertos import PuertosVacios

SIN_CUPO = "sin cupo"
UNIDAD_INEXISTENTE = "unidad inexistente"
ESTADO_NO_VENDIBLE = "estado no vendible"
EMPRESA_DESCONOCIDA = "empresa desconocida"
TAREA_INEXISTENTE = "tarea inexistente"

# Propuesta técnica (README del incremento 1): cancelación gratuita hasta 48 h
# antes de la llegada; la llegada se toma a la hora de check-in fijada abajo.
LIMITE_CANCELACION_GRATUITA = timedelta(hours=48)
HORA_LLEGADA = time(15, 0)
POLITICA_CANCELACION = (
    "cancelación gratuita hasta 48 horas antes de la llegada; "
    "después se carga la primera noche"
)
VIGENCIA_OFERTA = timedelta(minutes=15)


class AccesoDenegado(Exception):
    pass


class ReservaNoCancelable(Exception):
    pass


class CargoNoReversible(Exception):
    pass


class CheckInNoPermitido(Exception):
    pass


class NocheNoAsentable(Exception):
    pass


class CheckOutNoPermitido(Exception):
    pass


class CheckInIncompleto(Exception):
    pass


ROLES_DOCUMENTO = frozenset({"recepcion", "administrador"})


class ServicioHotelInventario:
    def __init__(
        self,
        establecimiento: Establecimiento,
        unidades: tuple[Unidad, ...],
        empresa: Empresa = EMPRESA_FIJA,
        puertos: PuertosVacios | None = None,
        extras: tuple[ExtraHotel, ...] = (),
    ) -> None:
        if establecimiento.empresa_id != empresa.id:
            raise ValueError("el establecimiento pertenece a otra empresa")
        if any(u.establecimiento_id != establecimiento.id for u in unidades):
            raise ValueError("una unidad no pertenece al establecimiento")
        self._empresa = empresa
        self._establecimiento = establecimiento
        self._unidades: dict[str, Unidad] = {u.id: u for u in unidades}
        self._reservas: dict[str, Reserva] = {}
        self._cargos: list[Cargo] = []
        self._tareas: dict[str, TareaOperativa] = {}
        self._ingresos_incompletos: dict[str, str] = {}
        self._accesos_documento: list[tuple[str, str]] = []
        self._evidencia: list[tuple[str, str, str]] = []
        self._pagos: list[Pago] = []
        self._liquidaciones: dict[str, Liquidacion] = {}
        self._pedidos: list[PedidoHabitacion] = []
        self._devoluciones: dict[str, SolicitudDevolucion] = {}
        self._extras: dict[str, ExtraHotel] = {e.id: e for e in extras}
        self._tarifas_aceptadas: dict[str, int] = {}
        self._borradores: list[tuple[str, str]] = []
        self._registro: list[AccionRegistrada] = []
        self._aprobaciones: dict[str, Aprobacion] = {}
        self._aprobaciones_usadas: set[str] = set()
        self._upsells: dict[str, PropuestaUpsell] = {}
        self._conversiones_upsell = 0
        self._transferencias: dict[str, TransferenciaHumana] = {}
        self._firmas: dict[str, str] = {}
        # Los puertos quedan guardados y no se invocan: el servicio no habla con
        # PMS, canal, pago ni documento tributario en el incremento 1.
        self._puertos = puertos if puertos is not None else PuertosVacios()
        self._ids = itertools.count(1)
        self._cerrojo = threading.Lock()

    @property
    def empresa(self) -> Empresa:
        return self._empresa

    def consultar_disponibilidad(
        self,
        empresa_id: str,
        inicio: date,
        fin: date,
        personas: int,
    ) -> list[Unidad]:
        self._exigir_empresa(empresa_id)
        self._exigir_rango(inicio, fin)
        with self._cerrojo:
            return [
                u
                for u in self._unidades.values()
                if u.capacidad >= personas
                and self._vendible(u)
                and self._libre(u.id, inicio, fin)
            ]

    def consultar_oferta(
        self,
        empresa_id: str,
        inicio: date,
        fin: date,
        personas: int,
        ahora: datetime,
    ) -> list[OfertaVigente]:
        self._exigir_empresa(empresa_id)
        self._exigir_rango(inicio, fin)
        with self._cerrojo:
            unidades = [
                u
                for u in self._unidades.values()
                if u.capacidad >= personas
                and self._vendible(u)
                and self._libre(u.id, inicio, fin)
            ]
            return [
                OfertaVigente(
                    unidad_id=u.id,
                    tarifa_noche_clp=u.tarifa_noche_clp,
                    politica_cancelacion=POLITICA_CANCELACION,
                    emitida_en=ahora,
                    vigente_hasta=ahora + VIGENCIA_OFERTA,
                    inicio=inicio,
                    fin=fin,
                )
                for u in unidades
            ]

    def datos_reserva(self, empresa_id: str, reserva_id: str, solicitante: str) -> Reserva:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if solicitante != f"huesped:{reserva_id}":
                self._evidencia.append(("consulta_reserva", reserva_id, "consulta ajena"))
                raise AccesoDenegado("consulta ajena")
            reserva = self._reservas.get(reserva_id)
            if reserva is None:
                raise ValueError("reserva inexistente")
            return reserva

    def pedir_cambio(
        self, empresa_id: str, reserva_id: str, solicitante: str, descripcion: str
    ) -> ResultadoBorrador:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if solicitante != f"huesped:{reserva_id}":
                self._evidencia.append(("pedir_cambio", reserva_id, "consulta ajena"))
                raise AccesoDenegado("consulta ajena")
            if reserva_id not in self._reservas:
                raise ValueError("reserva inexistente")
            self._borradores.append((reserva_id, descripcion))
            self._registro.append(
                AccionRegistrada(
                    fuente="pedir_cambio",
                    regla="sin permiso de mutación: borrador y escalado",
                    actor=solicitante,
                    resultado="escalado",
                    cuando=datetime.now(),
                )
            )
            return ResultadoBorrador(
                aplicado=False,
                escalado=True,
                motivo="sin permiso de mutación: queda borrador y escala",
            )

    def registrar_accion(
        self,
        empresa_id: str,
        fuente: str,
        regla: str,
        actor: str,
        resultado: str,
        cuando: datetime,
        datos: dict | None = None,
    ) -> AccionRegistrada:
        self._exigir_empresa(empresa_id)
        if datos and datos.get("documento"):
            raise ValueError("dato personal completo en el registro")
        with self._cerrojo:
            entrada = AccionRegistrada(
                fuente=fuente, regla=regla, actor=actor, resultado=resultado, cuando=cuando
            )
            self._registro.append(entrada)
            return entrada

    def registro_acciones(self, empresa_id: str) -> tuple[AccionRegistrada, ...]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return tuple(self._registro)

    def proyeccion_publica(
        self, empresa_id: str, inicio: date, fin: date, personas: int
    ) -> list[ProyeccionPublica]:
        self._exigir_empresa(empresa_id)
        self._exigir_rango(inicio, fin)
        with self._cerrojo:
            return [
                ProyeccionPublica(unidad_id=u.id, capacidad=u.capacidad)
                for u in self._unidades.values()
                if u.capacidad >= personas and self._vendible(u) and self._libre(u.id, inicio, fin)
            ]

    def modificar_desde_proyeccion(self, empresa_id: str, operacion: str, parametros: dict) -> None:
        self._exigir_empresa(empresa_id)
        raise AccesoDenegado("la proyección pública es de solo lectura")

    def ejecutar_sin_aprobacion(self, empresa_id: str, monto_clp: int, ahora: datetime) -> str:
        self._exigir_empresa(empresa_id)
        if monto_clp > self._monto_max_autonomo():
            self._evidencia.append(("accion", "-", "fuera de politica"))
            raise AccesoDenegado("fuera de política: requiere aprobación humana")
        return "ejecutada dentro de política"

    def autorizar_accion(
        self,
        empresa_id: str,
        descripcion: str,
        parametros: dict,
        monto_clp: int,
        ahora: datetime,
        vigencia_minutos: int,
    ) -> Aprobacion:
        self._exigir_empresa(empresa_id)
        aprobacion = Aprobacion(
            id=self._nuevo_id("APR"),
            descripcion=descripcion,
            parametros=tuple(sorted(parametros.items())),
            monto_clp=monto_clp,
            vigente_hasta=ahora + timedelta(minutes=vigencia_minutos),
        )
        self._aprobaciones[aprobacion.id] = aprobacion
        return aprobacion

    def ejecutar_accion_aprobada(
        self, empresa_id: str, aprobacion_id: str, parametros: dict, ahora: datetime
    ) -> str:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            aprobacion = self._aprobaciones.get(aprobacion_id)
            if (
                aprobacion is None
                or aprobacion_id in self._aprobaciones_usadas
                or ahora > aprobacion.vigente_hasta
                or tuple(sorted(parametros.items())) != aprobacion.parametros
            ):
                self._evidencia.append(("accion", aprobacion_id, "aprobacion invalidada"))
                raise AccesoDenegado("aprobación inválida: parámetros, vigencia o uso")
            self._aprobaciones_usadas.add(aprobacion_id)
            self._registro.append(
                AccionRegistrada(
                    fuente="ejecutar_accion",
                    regla="aprobación vigente y parámetros exactos",
                    actor="servicio",
                    resultado="ok",
                    cuando=ahora,
                )
            )
            return "ejecutada bajo aprobación"

    def _monto_max_autonomo(self) -> int:
        return 0

    def ofrecer_upsell(
        self, empresa_id: str, reserva_id: str, extra_id: str, ahora: datetime
    ) -> PropuestaUpsell:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado is not EstadoReserva.HOSPEDADA:
                raise ValueError("la reserva no está hospedada")
            extra = self._extras.get(extra_id)
            if extra is None:
                raise ValueError("extra inexistente")
            upsell = PropuestaUpsell(
                id=self._nuevo_id("UPS"),
                reserva_id=reserva_id,
                extra_id=extra_id,
                descripcion=f"Upsell: {extra.nombre}",
                monto_clp=extra.precio_clp,
                link=f"https://pago.sintetico.local/upsell/{reserva_id}/{extra_id}",
                creada_en=ahora,
            )
            self._upsells[upsell.id] = upsell
            return upsell

    def contabilizar_conversion(self, empresa_id: str, upsell_id: str) -> int:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            upsell = self._upsells.get(upsell_id)
            if upsell is None:
                raise ValueError("upsell inexistente")
            pagado = any(
                p.reserva_id == upsell.reserva_id and p.clave == f"upsell:{upsell_id}"
                for p in self._pagos
            )
            if pagado:
                self._conversiones_upsell += 1
            return self._conversiones_upsell

    def confirmar_con_oferta(
        self, empresa_id: str, oferta: OfertaVigente, huesped: Huesped, ahora: datetime
    ) -> ResultadoReserva:
        self._exigir_empresa(empresa_id)
        if ahora > oferta.vigente_hasta:
            with self._cerrojo:
                pendiente = Reserva(
                    id=self._nuevo_id("RSV"),
                    empresa_id=self._empresa.id,
                    unidad_id=oferta.unidad_id,
                    inicio=ahora.date(),
                    fin=ahora.date(),
                    huesped=huesped,
                    estado=EstadoReserva.PENDIENTE,
                    motivo="oferta sin vigencia: pendiente, sin prometer cupo",
                )
                self._reservas[pendiente.id] = pendiente
                transferencia = TransferenciaHumana(
                    id=self._nuevo_id("TRF"),
                    reserva_id=pendiente.id,
                    receptor="recepcion",
                    estado="transferida",
                    resuelto=False,
                )
                self._transferencias[transferencia.id] = transferencia
                return ResultadoReserva(
                    confirmada=False,
                    reserva=pendiente,
                    motivo="oferta sin vigencia: pendiente, sin prometer cupo",
                )
        return self.reservar(empresa_id, oferta.unidad_id, oferta.inicio, oferta.fin, huesped)

    def transferencias(self, empresa_id: str) -> list[TransferenciaHumana]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return list(self._transferencias.values())

    def derivar_a_recepcion(self, empresa_id: str, referencia: str, resumen: str) -> TransferenciaHumana:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            transferencia = TransferenciaHumana(
                id=self._nuevo_id("TRF"),
                reserva_id=referencia,
                receptor="recepcion",
                estado="transferida",
                resuelto=False,
            )
            self._transferencias[transferencia.id] = transferencia
            self._registro.append(
                AccionRegistrada(
                    fuente="concierge",
                    regla="derivación con resumen mínimo",
                    actor="concierge",
                    resultado=f"escalado: {resumen}",
                    cuando=datetime.now(),
                )
            )
            return transferencia

    def reservas_pagadas(self, empresa_id: str) -> list[str]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            pagadas = set()
            for pago in self._pagos:
                saldo = self._saldo_sin_exigir(pago.reserva_id)
                if saldo <= 0:
                    pagadas.add(pago.reserva_id)
            return sorted(pagadas)

    def _saldo_sin_exigir(self, reserva_id: str) -> int:
        devoluciones = sum(
            s.monto_clp
            for s in self._devoluciones.values()
            if s.reserva_id == reserva_id and s.estado is EstadoDevolucion.EFECTUADA
        )
        cargos = sum(
            c.monto_clp if c.tipo is TipoCargo.CARGO else -c.monto_clp
            for c in self._cargos
            if c.reserva_id == reserva_id
        )
        pagos = sum(p.monto_clp for p in self._pagos if p.reserva_id == reserva_id)
        return cargos - pagos + devoluciones

    def reservar(
        self,
        empresa_id: str,
        unidad_id: str,
        inicio: date,
        fin: date,
        huesped: Huesped,
    ) -> ResultadoReserva:
        self._exigir_empresa(empresa_id)
        self._exigir_rango(inicio, fin)
        with self._cerrojo:
            unidad = self._unidades.get(unidad_id)
            if unidad is None:
                return self._rechazar(unidad_id, inicio, fin, huesped, UNIDAD_INEXISTENTE)
            if not self._vendible(unidad):
                return self._rechazar(unidad_id, inicio, fin, huesped, ESTADO_NO_VENDIBLE)
            if not self._libre(unidad_id, inicio, fin):
                return self._rechazar(unidad_id, inicio, fin, huesped, SIN_CUPO)
            reserva = Reserva(
                id=self._nuevo_id("RSV"),
                empresa_id=self._empresa.id,
                unidad_id=unidad_id,
                inicio=inicio,
                fin=fin,
                huesped=huesped,
                estado=EstadoReserva.CONFIRMADA,
            )
            self._reservas[reserva.id] = reserva
            return ResultadoReserva(confirmada=True, reserva=reserva)

    def cambiar_estado_unidad(self, empresa_id: str, unidad_id: str, estado: EstadoUnidad) -> Unidad:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            unidad = self._unidades.get(unidad_id)
            if unidad is None:
                raise ValueError(UNIDAD_INEXISTENTE)
            actualizada = replace(unidad, estado=estado)
            self._unidades[unidad_id] = actualizada
            return actualizada

    def cancelar(self, empresa_id: str, reserva_id: str, ahora: datetime) -> ResultadoCancelacion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado is not EstadoReserva.CONFIRMADA:
                raise ReservaNoCancelable(reserva_id)
            cancelada = replace(reserva, estado=EstadoReserva.CANCELADA)
            self._reservas[reserva_id] = cancelada
            llegada = datetime.combine(reserva.inicio, HORA_LLEGADA)
            if llegada - ahora >= LIMITE_CANCELACION_GRATUITA:
                return ResultadoCancelacion(reserva=cancelada, cargo=None)
            tarifa = self._tarifa_de_reserva(reserva_id)
            cargo = self._asentar(
                reserva_id, TipoCargo.CARGO, "Cancelación fuera de plazo: primera noche", tarifa
            )
            return ResultadoCancelacion(reserva=cancelada, cargo=cargo)

    ESTADOS_CON_CUENTA_ABIERTA = (EstadoReserva.CONFIRMADA, EstadoReserva.HOSPEDADA)

    def solicitar_devolucion(self, empresa_id: str, reserva_id: str, monto_clp: int) -> SolicitudDevolucion:
        self._exigir_empresa(empresa_id)
        if monto_clp <= 0:
            raise ValueError("el monto debe ser positivo")
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None:
                raise ValueError("reserva inexistente")
            pagado = sum(p.monto_clp for p in self._pagos if p.reserva_id == reserva_id)
            devuelto = sum(
                s.monto_clp
                for s in self._devoluciones.values()
                if s.reserva_id == reserva_id and s.estado is EstadoDevolucion.EFECTUADA
            )
            if monto_clp > pagado - devuelto:
                raise ValueError("el monto supera lo pagado sin devolver")
            solicitud = SolicitudDevolucion(
                id=self._nuevo_id("DEV"),
                reserva_id=reserva_id,
                monto_clp=monto_clp,
                estado=EstadoDevolucion.PENDIENTE,
            )
            self._devoluciones[solicitud.id] = solicitud
            return solicitud

    def autorizar_devolucion(
        self, empresa_id: str, solicitud_id: str, aprobador: str
    ) -> SolicitudDevolucion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            solicitud = self._devoluciones.get(solicitud_id)
            if solicitud is None or solicitud.estado is not EstadoDevolucion.PENDIENTE:
                raise ValueError("solicitud no autorizable")
            autorizada = replace(solicitud, estado=EstadoDevolucion.AUTORIZADA, aprobador=aprobador)
            self._devoluciones[solicitud_id] = autorizada
            return autorizada

    def ejecutar_devolucion(
        self, empresa_id: str, solicitud_id: str, operacion_confirmada: bool
    ) -> SolicitudDevolucion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            solicitud = self._devoluciones.get(solicitud_id)
            if solicitud is None or solicitud.estado is not EstadoDevolucion.AUTORIZADA:
                raise ValueError("solicitud no ejecutable")
            if not operacion_confirmada:
                return solicitud
            efectuada = replace(solicitud, estado=EstadoDevolucion.EFECTUADA)
            self._devoluciones[solicitud_id] = efectuada
            return efectuada

    def devoluciones(self, empresa_id: str, reserva_id: str) -> tuple[SolicitudDevolucion, ...]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return tuple(s for s in self._devoluciones.values() if s.reserva_id == reserva_id)

    def previsualizar_cambio(
        self, empresa_id: str, reserva_id: str, tarifa_nueva_clp: int
    ) -> PropuestaCambio:
        self._exigir_empresa(empresa_id)
        if tarifa_nueva_clp <= 0:
            raise ValueError("la tarifa debe ser positiva")
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado not in self.ESTADOS_CON_CUENTA_ABIERTA:
                raise ValueError("la reserva no admite cambios")
            noches = (reserva.fin - reserva.inicio).days
            actual = self._tarifa_de_reserva(reserva_id)
            return PropuestaCambio(
                reserva_id=reserva_id,
                tarifa_actual_clp=actual,
                tarifa_nueva_clp=tarifa_nueva_clp,
                noches=noches,
                diferencia_total_clp=(tarifa_nueva_clp - actual) * noches,
            )

    def aplicar_cambio(
        self,
        empresa_id: str,
        reserva_id: str,
        propuesta: PropuestaCambio,
        aceptacion: bool,
    ) -> PropuestaCambio:
        self._exigir_empresa(empresa_id)
        if propuesta.reserva_id != reserva_id:
            raise ValueError("la propuesta pertenece a otra reserva")
        if not aceptacion:
            raise ValueError("cambio no aceptado")
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado not in self.ESTADOS_CON_CUENTA_ABIERTA:
                raise ValueError("la reserva no admite cambios")
            actual = self._tarifa_de_reserva(reserva_id)
            if (
                propuesta.diferencia_total_clp != 0
                and actual == propuesta.tarifa_nueva_clp
                and any(
                    c.referencia == f"cambio:{propuesta.tarifa_nueva_clp}" for c in self._cargos
                )
            ):
                return propuesta
            if propuesta.tarifa_actual_clp != actual:
                raise ValueError("propuesta obsoleta: la tarifa cambió")
            if propuesta.diferencia_total_clp == 0:
                raise ValueError("sin diferencia que aplicar")
            self._asentar(
                reserva_id,
                TipoCargo.CARGO,
                "Ajuste de tarifa",
                propuesta.diferencia_total_clp,
                referencia=f"cambio:{propuesta.tarifa_nueva_clp}",
            )
            self._tarifas_aceptadas[reserva_id] = propuesta.tarifa_nueva_clp
            return propuesta

    def _tarifa_de_reserva(self, reserva_id: str) -> int:
        reserva = self._reservas[reserva_id]
        unidad = self._unidades[reserva.unidad_id]
        return self._tarifas_aceptadas.get(reserva_id, unidad.tarifa_noche_clp)

    def agregar_extra(
        self,
        empresa_id: str,
        reserva_id: str,
        extra_id: str,
        personas: int,
        noches: int,
    ) -> LineaExtra:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado not in self.ESTADOS_CON_CUENTA_ABIERTA:
                raise ValueError("la reserva no admite extras")
            extra = self._extras.get(extra_id)
            if extra is None:
                raise ValueError("extra inexistente")
            if extra.regla is ReglaCantidad.POR_PERSONA_NOCHE:
                cantidad = personas * noches
                regla_visible = f"{extra.nombre}: {personas} personas × {noches} noches = {cantidad}"
            else:
                cantidad = 1
                regla_visible = f"{extra.nombre}: 1 por estadía"
            monto = cantidad * extra.precio_clp
            self._asentar(reserva_id, TipoCargo.CARGO, f"Extra: {extra.nombre}", monto, referencia=f"extra:{extra.id}")
            return LineaExtra(
                extra_id=extra.id,
                nombre=extra.nombre,
                cantidad=cantidad,
                monto_clp=monto,
                regla_visible=regla_visible,
            )

    def asentar_cargo(
        self,
        empresa_id: str,
        reserva_id: str,
        concepto: str,
        monto_clp: int,
        clave: str | None = None,
    ) -> Cargo:
        self._exigir_empresa(empresa_id)
        if monto_clp <= 0:
            raise ValueError("el monto debe ser positivo")
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado not in self.ESTADOS_CON_CUENTA_ABIERTA:
                raise ReservaNoCancelable(reserva_id)
            if clave is not None:
                existente = next(
                    (
                        c
                        for c in self._cargos
                        if c.reserva_id == reserva_id and c.referencia == f"clave:{clave}"
                    ),
                    None,
                )
                if existente is not None:
                    return existente
                return self._asentar(reserva_id, TipoCargo.CARGO, concepto, monto_clp, referencia=f"clave:{clave}")
            return self._asentar(reserva_id, TipoCargo.CARGO, concepto, monto_clp)

    def registrar_pago(
        self, empresa_id: str, reserva_id: str, monto_clp: int, clave: str | None = None
    ) -> Pago:
        self._exigir_empresa(empresa_id)
        if monto_clp <= 0:
            raise ValueError("el monto debe ser positivo")
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None:
                raise ValueError("reserva inexistente")
            if clave is not None:
                existente = next((p for p in self._pagos if p.reserva_id == reserva_id and p.clave == clave), None)
                if existente is not None:
                    return existente
            pago = Pago(id=self._nuevo_id("PGO"), reserva_id=reserva_id, monto_clp=monto_clp, clave=clave)
            self._pagos.append(pago)
            return pago

    def pagos(self, empresa_id: str, reserva_id: str) -> tuple[Pago, ...]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return tuple(p for p in self._pagos if p.reserva_id == reserva_id)

    def liquidacion(self, empresa_id: str, reserva_id: str) -> Liquidacion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            liquidada = self._liquidaciones.get(reserva_id)
            if liquidada is None:
                raise ValueError("la reserva no tiene liquidación")
            return liquidada

    def _liquidar(self, reserva_id: str) -> Liquidacion:
        total_cargos = sum(
            c.monto_clp if c.tipo is TipoCargo.CARGO else -c.monto_clp
            for c in self._cargos
            if c.reserva_id == reserva_id
        )
        total_pagos = sum(p.monto_clp for p in self._pagos if p.reserva_id == reserva_id)
        total_devoluciones = sum(
            s.monto_clp
            for s in self._devoluciones.values()
            if s.reserva_id == reserva_id and s.estado is EstadoDevolucion.EFECTUADA
        )
        liquidada = Liquidacion(
            reserva_id=reserva_id,
            total_cargos_clp=total_cargos - total_devoluciones,
            total_pagos_clp=total_pagos,
            saldo_clp=total_cargos - total_pagos + total_devoluciones,
        )
        self._liquidaciones[reserva_id] = liquidada
        return liquidada

    def pedir_a_habitacion(
        self,
        empresa_id: str,
        reserva_id: str,
        items: tuple[str, ...],
        clave: str | None = None,
    ) -> ResultadoPedido:
        self._exigir_empresa(empresa_id)
        if not items:
            raise ValueError("el pedido no tiene ítems")
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado is not EstadoReserva.HOSPEDADA:
                raise ValueError("la reserva no está hospedada")
            if clave is not None:
                existente = next(
                    (p for p in self._pedidos if p.reserva_id == reserva_id and p.clave == clave),
                    None,
                )
                if existente is not None:
                    return ResultadoPedido(confirmado=True, pedido=existente)
            respuesta = self._puertos.pedidos.hacer_pedido(
                {"reserva_id": reserva_id, "items": items}
            )
            if not respuesta.aceptado:
                return ResultadoPedido(confirmado=False, pedido=None, motivo="servicio no disponible")
            pedido = PedidoHabitacion(
                id=self._nuevo_id("PDH"),
                reserva_id=reserva_id,
                items=tuple(items),
                comanda_id=respuesta.comanda_id or "",
                clave=clave,
            )
            self._pedidos.append(pedido)
            self._asentar(
                reserva_id,
                TipoCargo.CARGO,
                "Pedido a habitación",
                respuesta.monto_clp or 0,
                referencia=f"pedido:{pedido.comanda_id}",
            )
            return ResultadoPedido(confirmado=True, pedido=pedido)

    def pedidos(self, empresa_id: str, reserva_id: str) -> tuple[PedidoHabitacion, ...]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return tuple(p for p in self._pedidos if p.reserva_id == reserva_id)

    def marcar_entregado(self, empresa_id: str, reserva_id: str, pedido_id: str) -> PedidoHabitacion:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            pedido = next(
                (p for p in self._pedidos if p.id == pedido_id and p.reserva_id == reserva_id),
                None,
            )
            if pedido is None:
                raise ValueError("pedido inexistente")
            entregado = replace(pedido, entregado=True)
            self._pedidos = [entregado if p.id == pedido_id else p for p in self._pedidos]
            return entregado

    def servicio_entregado(self, empresa_id: str, reserva_id: str, pedido_id: str) -> bool:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            pedido = next(
                (p for p in self._pedidos if p.id == pedido_id and p.reserva_id == reserva_id),
                None,
            )
            if pedido is None:
                raise ValueError("pedido inexistente")
            return pedido.entregado

    def reversar_cargo(self, empresa_id: str, cargo_id: str) -> Cargo:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            original = next((c for c in self._cargos if c.id == cargo_id), None)
            if original is None:
                raise CargoNoReversible("cargo inexistente")
            if original.tipo is TipoCargo.REVERSO:
                raise CargoNoReversible("un reverso no se revierte")
            if any(c.tipo is TipoCargo.REVERSO and c.referencia == cargo_id for c in self._cargos):
                raise CargoNoReversible("cargo ya reversado")
            return self._asentar(
                original.reserva_id,
                TipoCargo.REVERSO,
                f"Reverso de {cargo_id}",
                original.monto_clp,
                referencia=cargo_id,
            )

    def cuenta(self, empresa_id: str, reserva_id: str) -> tuple[Cargo, ...]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return tuple(c for c in self._cargos if c.reserva_id == reserva_id)

    def saldo_clp(self, empresa_id: str, reserva_id: str) -> int:
        devoluciones = sum(
            s.monto_clp
            for s in self.devoluciones(empresa_id, reserva_id)
            if s.estado is EstadoDevolucion.EFECTUADA
        )
        return (
            sum(
                c.monto_clp if c.tipo is TipoCargo.CARGO else -c.monto_clp
                for c in self.cuenta(empresa_id, reserva_id)
            )
            - sum(p.monto_clp for p in self.pagos(empresa_id, reserva_id))
            + devoluciones
        )

    def reservas_confirmadas(self, empresa_id: str) -> list[Reserva]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return [r for r in self._reservas.values() if r.estado is EstadoReserva.CONFIRMADA]

    def check_in(
        self, empresa_id: str, reserva_id: str, ahora: datetime, firma_registro: str | None = None
    ) -> Reserva:
        if empresa_id != self._empresa.id:
            self._evidencia.append(("check_in", reserva_id, EMPRESA_DESCONOCIDA))
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado is not EstadoReserva.CONFIRMADA:
                raise CheckInNoPermitido(reserva_id)
            llegada = datetime.combine(reserva.inicio, HORA_LLEGADA)
            if ahora < llegada:
                raise CheckInNoPermitido("aún no es hora de llegada")
            if not reserva.huesped.documento:
                motivo = "ingreso incompleto: documento faltante; deriva a recepción"
                self._ingresos_incompletos[reserva_id] = motivo
                raise CheckInIncompleto(motivo)
            unidad = self._unidades[reserva.unidad_id]
            if unidad.mantenimiento:
                self._evidencia.append(("check_in", reserva_id, "mantenimiento abierto"))
                raise CheckInNoPermitido("mantenimiento abierto")
            if unidad.estado in (EstadoUnidad.BLOQUEADA, EstadoUnidad.FUERA_DE_SERVICIO):
                raise CheckInNoPermitido("unidad no disponible para entrada")
            if unidad.estado is EstadoUnidad.SUCIA:
                raise CheckInNoPermitido("unidad no preparada")
            hospedada = replace(reserva, estado=EstadoReserva.HOSPEDADA)
            self._reservas[reserva_id] = hospedada
            self._unidades[unidad.id] = replace(unidad, estado=EstadoUnidad.OCUPADA)
            if firma_registro is not None:
                self._firmas[reserva_id] = firma_registro
            self._asentar(
                reserva_id,
                TipoCargo.CARGO,
                "Noche",
                self._tarifa_de_reserva(reserva_id),
                referencia=f"noche:{reserva.inicio.isoformat()}",
            )
            return hospedada

    def asentar_noche(
        self, empresa_id: str, reserva_id: str, noche: date, ahora: datetime
    ) -> Cargo:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado is not EstadoReserva.HOSPEDADA:
                raise NocheNoAsentable(reserva_id)
            if not (reserva.inicio < noche < reserva.fin):
                raise NocheNoAsentable("noche fuera de rango")
            referencia = f"noche:{noche.isoformat()}"
            if any(c.reserva_id == reserva_id and c.referencia == referencia for c in self._cargos):
                raise NocheNoAsentable("noche ya asentada")
            tarifa = self._tarifa_de_reserva(reserva_id)
            return self._asentar(reserva_id, TipoCargo.CARGO, "Noche", tarifa, referencia=referencia)

    def check_out(self, empresa_id: str, reserva_id: str, ahora: datetime) -> Reserva:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None or reserva.estado is not EstadoReserva.HOSPEDADA:
                raise CheckOutNoPermitido(reserva_id)
            salida = replace(reserva, estado=EstadoReserva.SALIDA)
            self._reservas[reserva_id] = salida
            unidad = self._unidades[reserva.unidad_id]
            self._unidades[unidad.id] = replace(unidad, estado=EstadoUnidad.SUCIA)
            tarea = TareaOperativa(
                id=self._nuevo_id("TSK"),
                empresa_id=self._empresa.id,
                unidad_id=unidad.id,
                tipo="limpieza",
                estado=EstadoTarea.PENDIENTE,
            )
            self._tareas[tarea.id] = tarea
            self._liquidar(reserva_id)
            return salida

    def completar_tarea(self, empresa_id: str, tarea_id: str) -> TareaOperativa:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            tarea = self._tareas.get(tarea_id)
            if tarea is None or tarea.estado is not EstadoTarea.PENDIENTE:
                raise ValueError(TAREA_INEXISTENTE)
            completada = replace(tarea, estado=EstadoTarea.COMPLETADA)
            self._tareas[tarea_id] = completada
            unidad = self._unidades.get(tarea.unidad_id)
            if unidad is not None and unidad.estado is EstadoUnidad.SUCIA:
                self._unidades[unidad.id] = replace(unidad, estado=EstadoUnidad.LIMPIA)
            return completada

    def tareas(self, empresa_id: str) -> list[TareaOperativa]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return list(self._tareas.values())

    def ingresos_incompletos(self, empresa_id: str) -> dict[str, str]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return dict(self._ingresos_incompletos)

    def documento_huesped(self, empresa_id: str, reserva_id: str, rol: str) -> str | None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            reserva = self._reservas.get(reserva_id)
            if reserva is None:
                raise ValueError("reserva inexistente")
            if rol not in ROLES_DOCUMENTO:
                raise AccesoDenegado("rol no autorizado")
            self._accesos_documento.append((reserva_id, rol))
            return reserva.huesped.documento

    def accesos_documento(self, empresa_id: str) -> list[tuple[str, str]]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return list(self._accesos_documento)

    def firma_de_registro(self, empresa_id: str, reserva_id: str, rol: str) -> str:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if rol not in ROLES_DOCUMENTO:
                raise AccesoDenegado("rol no autorizado")
            if reserva_id not in self._firmas:
                raise ValueError("la reserva no tiene firma de registro")
            self._accesos_documento.append((reserva_id, f"firma:{rol}"))
            return self._firmas[reserva_id]

    def abrir_mantenimiento(self, empresa_id: str, unidad_id: str) -> Unidad:
        return self._fijar_mantenimiento(empresa_id, unidad_id, True)

    def cerrar_mantenimiento(self, empresa_id: str, unidad_id: str) -> Unidad:
        return self._fijar_mantenimiento(empresa_id, unidad_id, False)

    def evidencia_denegaciones(self, empresa_id: str) -> list[tuple[str, str, str]]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return list(self._evidencia)

    def _fijar_mantenimiento(self, empresa_id: str, unidad_id: str, abierto: bool) -> Unidad:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            unidad = self._unidades.get(unidad_id)
            if unidad is None:
                raise ValueError(UNIDAD_INEXISTENTE)
            actualizada = replace(unidad, mantenimiento=abierto)
            self._unidades[unidad_id] = actualizada
            if abierto:
                tarea = TareaOperativa(
                    id=self._nuevo_id("TSK"),
                    empresa_id=self._empresa.id,
                    unidad_id=unidad_id,
                    tipo="mantenimiento",
                    estado=EstadoTarea.PENDIENTE,
                )
                self._tareas[tarea.id] = tarea
            else:
                for tarea in self._tareas.values():
                    if (
                        tarea.unidad_id == unidad_id
                        and tarea.tipo == "mantenimiento"
                        and tarea.estado is EstadoTarea.PENDIENTE
                    ):
                        self._tareas[tarea.id] = replace(tarea, estado=EstadoTarea.COMPLETADA)
            return actualizada

    def _exigir_empresa(self, empresa_id: str) -> None:
        if empresa_id != self._empresa.id:
            raise AccesoDenegado(EMPRESA_DESCONOCIDA)

    @staticmethod
    def _exigir_rango(inicio: date, fin: date) -> None:
        if fin <= inicio:
            raise ValueError("el rango debe terminar después de empezar")

    def _nuevo_id(self, prefijo: str) -> str:
        return f"{prefijo}-SINT-{next(self._ids):04d}"

    @staticmethod
    def _vendible(unidad: Unidad) -> bool:
        return unidad.estado in ESTADOS_VENDIBLES and not unidad.mantenimiento

    def _libre(self, unidad_id: str, inicio: date, fin: date) -> bool:
        ocupantes = (EstadoReserva.CONFIRMADA, EstadoReserva.HOSPEDADA)
        return not any(
            r.unidad_id == unidad_id
            and r.estado in ocupantes
            and inicio < r.fin
            and fin > r.inicio
            for r in self._reservas.values()
        )

    def _rechazar(self, unidad_id, inicio, fin, huesped, motivo) -> ResultadoReserva:
        reserva = Reserva(
            id=self._nuevo_id("RSV"),
            empresa_id=self._empresa.id,
            unidad_id=unidad_id,
            inicio=inicio,
            fin=fin,
            huesped=huesped,
            estado=EstadoReserva.RECHAZADA,
            motivo=motivo,
        )
        self._reservas[reserva.id] = reserva
        return ResultadoReserva(confirmada=False, reserva=reserva, motivo=motivo)

    def _asentar(self, reserva_id, tipo, concepto, monto, referencia=None) -> Cargo:
        cargo = Cargo(
            id=self._nuevo_id("CGO"),
            reserva_id=reserva_id,
            tipo=tipo,
            concepto=concepto,
            monto_clp=monto,
            referencia=referencia,
        )
        self._cargos.append(cargo)
        return cargo


def hotel_sintetico() -> ServicioHotelInventario:
    establecimiento = Establecimiento(
        id="EST-SINT-001", empresa_id=EMPRESA_FIJA.id, nombre="Establecimiento sintético"
    )
    unidades = (
        Unidad("HAB-SINT-101", establecimiento.id, 2, 50_000, EstadoUnidad.LIMPIA),
        Unidad("HAB-SINT-102", establecimiento.id, 2, 50_000, EstadoUnidad.SUCIA),
        Unidad("HAB-SINT-103", establecimiento.id, 4, 90_000, EstadoUnidad.INSPECCIONADA),
        Unidad("HAB-SINT-104", establecimiento.id, 2, 50_000, EstadoUnidad.BLOQUEADA),
        Unidad("HAB-SINT-105", establecimiento.id, 2, 50_000, EstadoUnidad.FUERA_DE_SERVICIO),
    )
    return ServicioHotelInventario(establecimiento, unidades)


def hotel_con_extras() -> ServicioHotelInventario:
    establecimiento = Establecimiento(
        id="EST-SINT-001", empresa_id=EMPRESA_FIJA.id, nombre="Establecimiento sintético"
    )
    unidad = Unidad("HAB-SINT-101", establecimiento.id, 2, 50_000, EstadoUnidad.LIMPIA)
    extras = (
        ExtraHotel("EXT-DESAYUNO", "Desayuno", 5_000, ReglaCantidad.POR_PERSONA_NOCHE),
        ExtraHotel("EXT-BOTELLA", "Botella de bienvenida", 15_000, ReglaCantidad.POR_ESTADIA),
    )
    return ServicioHotelInventario(establecimiento, (unidad,), extras=extras)


def servicio_con_una_unidad(puertos: PuertosVacios | None = None) -> ServicioHotelInventario:
    establecimiento = Establecimiento(
        id="EST-SINT-001", empresa_id=EMPRESA_FIJA.id, nombre="Establecimiento sintético"
    )
    unidad = Unidad("HAB-SINT-101", establecimiento.id, 2, 50_000, EstadoUnidad.LIMPIA)
    return ServicioHotelInventario(establecimiento, (unidad,), puertos=puertos)
