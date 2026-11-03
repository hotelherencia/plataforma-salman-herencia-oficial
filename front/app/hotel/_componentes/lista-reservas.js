'use client'

import Link from 'next/link'

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
  confirmada: 'confirmada',
  en_estadia: 'en estadía',
  finalizada: 'finalizada',
  cancelada: 'cancelada',
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
      <span role="columnheader">Fechas</span>
      <span role="columnheader">Estado</span>
      <span role="columnheader">Tarifa</span>
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
      <span role="cell" className="reserva-huesped">{reserva.huesped_nombre}</span>
      <span role="cell" className="reserva-celda">{reserva.habitacion_id}</span>
      <span role="cell" className="reserva-celda reserva-fechas">{reserva.inicio} → {reserva.fin}</span>
      <span role="cell" className={`reserva-estado estado-${reserva.estado}`}>
        {ETIQUETA_ESTADO[reserva.estado] || reserva.estado}
      </span>
      <span role="cell" className="reserva-tarifa">${reserva.tarifa_noche_aceptada_clp}/noche</span>
      {reserva.huesped_documento && (
        <span role="cell" className="reserva-documento">doc. {reserva.huesped_documento}</span>
      )}
    </li>
  )
}

export function ReservasVacias() {
  return (
    <div className="oferta-vacia">
      <p className="oferta-vacia-titulo">Sin resultados para esos filtros</p>
      <p className="oferta-vacia-texto">Los filtros se combinan con Y: probá aflojar fecha, estado o texto.</p>
    </div>
  )
}
