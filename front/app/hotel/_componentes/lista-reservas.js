'use client'

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
      <ul className="reservas-lista">
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
    <li className="reserva-encabezado" aria-hidden="true">
      <span>Reserva</span>
      <span>Huésped</span>
      <span>Habitación</span>
      <span>Fechas</span>
      <span>Estado</span>
      <span>Tarifa</span>
    </li>
  )
}

export function FilaReserva({ reserva }) {
  return (
    <li className="reserva-fila">
      <span className="reserva-id">{reserva.reserva_id}</span>
      <span className="reserva-huesped">{reserva.huesped_nombre}</span>
      <span className="reserva-celda">{reserva.habitacion_id}</span>
      <span className="reserva-celda reserva-fechas">{reserva.inicio} → {reserva.fin}</span>
      <span className={`reserva-estado estado-${reserva.estado}`}>
        {ETIQUETA_ESTADO[reserva.estado] || reserva.estado}
      </span>
      <span className="reserva-tarifa">${reserva.tarifa_noche_aceptada_clp}/noche</span>
      {reserva.huesped_documento && (
        <span className="reserva-documento">doc. {reserva.huesped_documento}</span>
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
