import itertools
import threading
from dataclasses import replace
from datetime import datetime, timedelta

from .dominio import (
    ESTADOS_VENDIBLES,
    Cargo,
    CuentaEstadia,
    EstadoReserva,
    Huesped,
    OfertaDisponible,
    Reserva,
    ResultadoReserva,
    UnidadHabitacion,
)
from .empresa import EMPRESA_FIJA, ESTABLECIMIENTO_FIJO, Empresa, Establecimiento
from .puertos import PuertosVacios

SIN_CUPO = "sin cupo"
UNIDAD_INEXISTENTE = "unidad inexistente"
EMPRESA_DESCONOCIDA = "empresa desconocida"
ESTABLECIMIENTO_DESCONOCIDO = "establecimiento desconocido"
RESERVA_INEXISTENTE = "reserva inexistente"
CARGO_INEXISTENTE = "cargo inexistente"
CARGO_NO_REVERSIBLE = "cargo no reversible"
CANCELACION_TARDIA = "cancelacion_tardia"
HORAS_CANCELACION_GRATUITA = 48


class AccesoDenegado(Exception):
    pass


class ServicioHotelLocal:
    def __init__(
        self,
        empresa: Empresa = EMPRESA_FIJA,
        establecimientos: tuple[Establecimiento, ...] = (ESTABLECIMIENTO_FIJO,),
        unidades: tuple[UnidadHabitacion, ...] = (),
        puertos: PuertosVacios | None = None,
    ) -> None:
        self._empresa = empresa
        self._establecimientos = tuple(establecimientos)
        self._unidades = tuple(unidades)
        self._puertos = puertos if puertos is not None else PuertosVacios()
        self._reservas: list[Reserva] = []
        self._cuentas: list[CuentaEstadia] = []
        self._cargos: list[Cargo] = []
        self._contador = itertools.count(1)
        self._cerrojo = threading.Lock()

    def consultar_disponibilidad(
        self,
        empresa_id: str,
        establecimiento_id: str,
        inicio: datetime,
        fin: datetime,
        cantidad_huespedes: int,
    ) -> list[OfertaDisponible]:
        self._exigir_empresa_y_establecimiento(empresa_id, establecimiento_id)
        with self._cerrojo:
            return [
                OfertaDisponible(unidad, inicio, fin)
                for unidad in self._unidades
                if unidad.establecimiento_id == establecimiento_id
                and unidad.estado in ESTADOS_VENDIBLES
                and unidad.tipo.capacidad >= cantidad_huespedes
                and self._disponible(unidad.id, inicio, fin)
            ]

    def reservar(
        self,
        empresa_id: str,
        establecimiento_id: str,
        unidad_id: str,
        inicio: datetime,
        fin: datetime,
        llegada: datetime,
        huesped: Huesped,
    ) -> ResultadoReserva:
        self._exigir_empresa_y_establecimiento(empresa_id, establecimiento_id)
        with self._cerrojo:
            empresa_duena = self._empresa.id
            candidatas = {u.id for u in self._unidades if u.establecimiento_id == establecimiento_id}
            if unidad_id not in candidatas:
                return self._rechazar(establecimiento_id, unidad_id, empresa_duena, inicio, fin, llegada, huesped, UNIDAD_INEXISTENTE)
            unidad = next(u for u in self._unidades if u.id == unidad_id)
            if unidad.estado not in ESTADOS_VENDIBLES or not self._disponible(unidad_id, inicio, fin):
                return self._rechazar(establecimiento_id, unidad_id, empresa_duena, inicio, fin, llegada, huesped, SIN_CUPO)
            reserva = Reserva(
                id=f"RSV-SINT-{next(self._contador):04d}",
                empresa_id=empresa_duena,
                establecimiento_id=establecimiento_id,
                unidad_id=unidad_id,
                inicio=inicio,
                fin=fin,
                llegada=llegada,
                huesped=huesped,
                estado=EstadoReserva.CONFIRMADA,
            )
            self._reservas.append(reserva)
            self._cuentas.append(
                CuentaEstadia(
                    id=f"CTA-SINT-{next(self._contador):04d}",
                    empresa_id=empresa_duena,
                    reserva_id=reserva.id,
                )
            )
            return ResultadoReserva(confirmada=True, reserva=reserva)

    def cancelar(self, empresa_id: str, reserva_id: str, ahora: datetime) -> Reserva:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            reserva = self._buscar_reserva(reserva_id)
            limite = reserva.llegada - timedelta(hours=HORAS_CANCELACION_GRATUITA)
            reserva = replace(reserva, estado=EstadoReserva.CANCELADA)
            self._reservas = [reserva if r.id == reserva_id else r for r in self._reservas]
            if ahora > limite:
                cuenta = self._cuenta_de_reserva(reserva_id)
                unidad = next(u for u in self._unidades if u.id == reserva.unidad_id)
                self._asentar_cargo(
                    cuenta.id,
                    CANCELACION_TARDIA,
                    unidad.tipo.tarifa_noche_clp,
                )
            return reserva

    def asentar_cargo(self, empresa_id: str, cuenta_id: str, concepto: str, monto_clp: int) -> Cargo:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return self._asentar_cargo(cuenta_id, concepto, monto_clp)

    def revertir_cargo(self, empresa_id: str, cargo_id: str) -> Cargo:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            original = self._buscar_cargo(cargo_id)
            if original.cargo_origen_id is not None:
                raise ValueError(CARGO_NO_REVERSIBLE)
            ya_reversado = any(c.cargo_origen_id == cargo_id for c in self._cargos)
            if ya_reversado:
                raise ValueError(CARGO_NO_REVERSIBLE)
            return self._asentar_cargo(
                original.cuenta_id,
                f"reverso:{original.concepto}",
                -original.monto_clp,
                cargo_origen_id=original.id,
            )

    def cargos_de_cuenta(self, empresa_id: str, cuenta_id: str) -> list[Cargo]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return [c for c in self._cargos if c.cuenta_id == cuenta_id]

    def saldo_cuenta(self, empresa_id: str, cuenta_id: str) -> int:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return sum(c.monto_clp for c in self._cargos if c.cuenta_id == cuenta_id)

    def cambiar_estado_unidad(self, empresa_id: str, unidad_id: str, estado) -> None:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            ids = {u.id for u in self._unidades}
            if unidad_id not in ids:
                raise ValueError(UNIDAD_INEXISTENTE)
            self._unidades = tuple(
                replace(u, estado=estado) if u.id == unidad_id else u
                for u in self._unidades
            )

    def _asentar_cargo(self, cuenta_id: str, concepto: str, monto_clp: int, cargo_origen_id: str | None = None) -> Cargo:
        cuenta = next((c for c in self._cuentas if c.id == cuenta_id), None)
        if cuenta is None:
            raise ValueError(CARGO_INEXISTENTE)
        cargo = Cargo(
            id=f"CARGO-SINT-{next(self._contador):04d}",
            empresa_id=self._empresa.id,
            cuenta_id=cuenta_id,
            concepto=concepto,
            monto_clp=monto_clp,
            cargo_origen_id=cargo_origen_id,
        )
        self._cargos.append(cargo)
        return cargo

    def _buscar_reserva(self, reserva_id: str) -> Reserva:
        reserva = next((r for r in self._reservas if r.id == reserva_id), None)
        if reserva is None:
            raise ValueError(RESERVA_INEXISTENTE)
        return reserva

    def _buscar_cargo(self, cargo_id: str) -> Cargo:
        cargo = next((c for c in self._cargos if c.id == cargo_id), None)
        if cargo is None:
            raise ValueError(CARGO_INEXISTENTE)
        return cargo

    def _cuenta_de_reserva(self, reserva_id: str) -> CuentaEstadia:
        return next(c for c in self._cuentas if c.reserva_id == reserva_id)

    def _exigir_empresa(self, empresa_id: str) -> None:
        if empresa_id != self._empresa.id:
            raise AccesoDenegado(EMPRESA_DESCONOCIDA)

    def _exigir_empresa_y_establecimiento(self, empresa_id: str, establecimiento_id: str) -> None:
        self._exigir_empresa(empresa_id)
        conocidos = {e.id for e in self._establecimientos if e.empresa_id == self._empresa.id}
        if establecimiento_id not in conocidos:
            raise AccesoDenegado(ESTABLECIMIENTO_DESCONOCIDO)

    def _disponible(self, unidad_id: str, inicio: datetime, fin: datetime) -> bool:
        return all(
            not (
                r.unidad_id == unidad_id
                and r.estado is EstadoReserva.CONFIRMADA
                and inicio < r.fin
                and fin > r.inicio
            )
            for r in self._reservas
        )

    def _rechazar(self, establecimiento_id, unidad_id, empresa_id, inicio, fin, llegada, huesped, motivo) -> ResultadoReserva:
        reserva = Reserva(
            id=f"RSV-SINT-{next(self._contador):04d}",
            empresa_id=empresa_id,
            establecimiento_id=establecimiento_id,
            unidad_id=unidad_id,
            inicio=inicio,
            fin=fin,
            llegada=llegada,
            huesped=huesped,
            estado=EstadoReserva.RECHAZADA,
            motivo_rechazo=motivo,
        )
        return ResultadoReserva(confirmada=False, reserva=reserva, motivo=motivo)


def hotel_sintetico_con_una_unidad() -> ServicioHotelLocal:
    from .dominio import EstadoUnidad, TipoHabitacion

    doble = TipoHabitacion(id="TIPO-SINT-DOBLE", nombre="Doble sintética", capacidad=2, tarifa_noche_clp=60000)
    unidad = UnidadHabitacion(
        id="HAB-SINT-101",
        tipo=doble,
        establecimiento_id=ESTABLECIMIENTO_FIJO.id,
        estado=EstadoUnidad.SUCIA,
    )
    return ServicioHotelLocal(unidades=(unidad,))
