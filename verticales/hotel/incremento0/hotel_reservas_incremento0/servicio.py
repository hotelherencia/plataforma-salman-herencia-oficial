import itertools
import threading
from datetime import date

from .dominio import (
    EstadoReserva,
    Huesped,
    OfertaDisponible,
    Reserva,
    ResultadoReserva,
    UnidadHabitacion,
)
from .empresa import EMPRESA_FIJA, Empresa
from .puertos import PuertosVacios

SIN_CUPO = "sin cupo"
UNIDAD_INEXISTENTE = "unidad inexistente"
EMPRESA_DESCONOCIDA = "empresa desconocida"


class AccesoDenegado(Exception):
    pass


class ServicioReservaLocal:
    def __init__(
        self,
        empresa: Empresa = EMPRESA_FIJA,
        unidades: tuple[UnidadHabitacion, ...] = (),
        puertos: PuertosVacios | None = None,
    ) -> None:
        self._empresa = empresa
        self._unidades = tuple(unidades)
        self._puertos = puertos if puertos is not None else PuertosVacios()
        self._reservas: list[Reserva] = []
        self._contador = itertools.count(1)
        self._cerrojo = threading.Lock()

    @property
    def empresa(self) -> Empresa:
        return self._empresa

    def consultar_disponibilidad(
        self,
        empresa_id: str,
        fecha_inicio: date,
        fecha_fin: date,
        cantidad_huespedes: int,
    ) -> list[OfertaDisponible]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return [
                OfertaDisponible(unidad, fecha_inicio, fecha_fin)
                for unidad in self._unidades
                if unidad.tipo.capacidad >= cantidad_huespedes
                and self._disponible(unidad.id, fecha_inicio, fecha_fin)
            ]

    def reservar(
        self,
        empresa_id: str,
        unidad_id: str,
        fecha_inicio: date,
        fecha_fin: date,
        huesped: Huesped,
    ) -> ResultadoReserva:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            if unidad_id not in {u.id for u in self._unidades}:
                return self._rechazar(unidad_id, empresa_id, fecha_inicio, fecha_fin, huesped, UNIDAD_INEXISTENTE)
            if not self._disponible(unidad_id, fecha_inicio, fecha_fin):
                return self._rechazar(unidad_id, empresa_id, fecha_inicio, fecha_fin, huesped, SIN_CUPO)
            reserva = Reserva(
                id=f"RSV-SINT-{next(self._contador):04d}",
                empresa_id=empresa_id,
                unidad_id=unidad_id,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                huesped=huesped,
                estado=EstadoReserva.CONFIRMADA,
            )
            self._reservas.append(reserva)
            return ResultadoReserva(confirmada=True, reserva=reserva)

    def reservas_confirmadas(self, empresa_id: str) -> list[Reserva]:
        self._exigir_empresa(empresa_id)
        with self._cerrojo:
            return [r for r in self._reservas if r.estado is EstadoReserva.CONFIRMADA]

    def _exigir_empresa(self, empresa_id: str) -> None:
        if empresa_id != self._empresa.id:
            raise AccesoDenegado(EMPRESA_DESCONOCIDA)

    def _disponible(self, unidad_id: str, fecha_inicio: date, fecha_fin: date) -> bool:
        return all(
            not (
                r.unidad_id == unidad_id
                and r.estado is EstadoReserva.CONFIRMADA
                and fecha_inicio < r.fecha_fin
                and fecha_fin > r.fecha_inicio
            )
            for r in self._reservas
        )

    def _rechazar(self, unidad_id, empresa_id, fecha_inicio, fecha_fin, huesped, motivo) -> ResultadoReserva:
        reserva = Reserva(
            id=f"RSV-SINT-{next(self._contador):04d}",
            empresa_id=empresa_id,
            unidad_id=unidad_id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            huesped=huesped,
            estado=EstadoReserva.RECHAZADA,
            motivo_rechazo=motivo,
        )
        return ResultadoReserva(confirmada=False, reserva=reserva, motivo=motivo)


def hotel_sintetico_con_una_unidad() -> ServicioReservaLocal:
    from .dominio import TipoHabitacion

    doble = TipoHabitacion(id="TIPO-SINT-DOBLE", nombre="Doble sintética", capacidad=2)
    unidad = UnidadHabitacion(id="HAB-SINT-101", tipo=doble)
    return ServicioReservaLocal(unidades=(unidad,))
