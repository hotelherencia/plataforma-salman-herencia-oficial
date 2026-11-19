'use client'

import Link from 'next/link'
import { clp } from '../../../lib/api'

/**
 * Capa del módulo Hotel — búsqueda de reservas (pura, sin fetch): recibe
 * solo props y dibuja la respuesta de GET /hotel/reservas tal cual la envía
 * la API. El `huesped_documento` solo viene en el ítem cuando la API lo
 * incluye (roles recepcion/administrador): aquí no se decide, solo se muestra.
 * Presentación adaptada a mano desde «Records Table» de @theshanelevine
 * (21st.dev, id 23604): filas alineadas a columnas, líneas de rejilla
 * explícitas y pastillas de estado de paleta contenida.
 */

const ETIQUETA_ESTADO = {
  confirmada: 'Confirmada',
  en_estadia: 'En estadía',
  finalizada: 'Finalizada',
  cancelada: 'Cancelada',
}

// 2026-11-10 → «10/11/2026»: el formato de fecha que se lee en Chile.
export function fechaChile(iso) {
  if (typeof iso !== 'string') return ''
  const [a, m, d] = iso.slice(0, 10).split('-')
  return a && m && d ? `${d}/${m}/${a}` : iso
}

export function ListaReservas({ reservas, total }) {
  return (
    <>
      <p className="reservas-total">{total} reserva(s) encontrada(s)</p>
      <ul className="reservas-lista" role="table">
        <EncabezadoReservas />
        {reservas.map((r) => (
          <FilaReserva key={r.reserva_id} reserva={r} />
        ))}
      </ul>
    </>
  )
}

export function EncabezadoReservas() {
  return (
    <li className="reserva-encabezado" role="row">
      <span role="columnheader">Reserva</span>
      <span role="columnheader">Huésped</span>
      <span role="columnheader">Habitación</span>
      <span role="columnheader">Llegada y Salida</span>
      <span role="columnheader">Estado</span>
      <span role="columnheader">Precio</span>
    </li>
  )
}

export function FilaReserva({ reserva }) {
  return (
    <li className="reserva-fila" role="row">
      <span role="cell" className="reserva-id">
        <Link href={`/hotel/reservas/${reserva.reserva_id}`} title="Ver detalle y cuenta">
          {reserva.reserva_id}
        </Link>
      </span>
      <span role="cell" className="reserva-huesped">
        {reserva.huesped_nombre}
        {reserva.huesped_documento && (
          <span className="reserva-documento">Doc. {reserva.huesped_documento}</span>
        )}
      </span>
      <span role="cell" className="reserva-celda">{reserva.habitacion_id}</span>
      <span role="cell" className="reserva-celda reserva-fechas">
        <span className="reserva-fecha-rotulo">Llegada</span> {fechaChile(reserva.inicio)}
        <br />
        <span className="reserva-fecha-rotulo">Salida</span> {fechaChile(reserva.fin)}
      </span>
      <span role="cell">
        <span className={`reserva-estado estado-${reserva.estado}`}>
          {ETIQUETA_ESTADO[reserva.estado] || reserva.estado}
        </span>
      </span>
      <span role="cell" className="reserva-tarifa">{clp(reserva.tarifa_noche_aceptada_clp)}<span className="reserva-por-noche"> / noche</span></span>
    </li>
  )
}

export function ReservasVacias() {
  return (
    <div className="oferta-vacia">
      <p className="oferta-vacia-titulo">Sin resultados para esos filtros</p>
      <p className="oferta-vacia-texto">Los filtros se combinan con Y: prueba ampliar las fechas o quitar el estado o el texto.</p>
    </div>
  )
}
