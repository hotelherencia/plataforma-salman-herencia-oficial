'use client'

/**
 * Capa del módulo Hotel — inventario operativo de habitaciones (pura, sin
 * fetch): dibuja GET /hotel/habitaciones tal cual la envía la API y emite las
 * acciones de fila hacia la página (que las ejecuta con su clave de
 * idempotencia). Las reglas de visibilidad vienen del contrato: limpieza la
 * completan recepción o administrador; el mantenimiento, solo administrador.
 */

const ETIQUETA_OPERATIVO = {
  disponible: 'disponible',
  ocupada: 'ocupada',
  bloqueada: 'bloqueada',
  fuera_de_servicio: 'fuera de servicio',
}

const ETIQUETA_PREPARACION = {
  limpia: 'limpia',
  sucia: 'sucia',
  inspeccionada: 'inspeccionada',
}

export function InventarioHabitaciones({ habitaciones, rol, alLimpiar, alCambiarMantenimiento }) {
  const puedeLimpiar = rol === 'recepcion' || rol === 'administrador'
  const puedeMantenimiento = rol === 'administrador'
  return (
    <>
      <p className="reservas-total">{habitaciones.length} habitación(es)</p>
      <ul className="reservas-lista">
        <li className="inventario-encabezado" aria-hidden="true">
          <span>Habitación</span>
          <span>Tipo</span>
          <span>Cap.</span>
          <span>Estado</span>
          <span>Preparación</span>
          <span>Mantenimiento</span>
          <span>Tarifa ref.</span>
          <span>Acciones</span>
        </li>
        {habitaciones.map((h) => (
          <FilaHabitacion
            key={h.habitacion_id}
            habitacion={h}
            puedeLimpiar={puedeLimpiar}
            puedeMantenimiento={puedeMantenimiento}
            alLimpiar={alLimpiar}
            alCambiarMantenimiento={alCambiarMantenimiento}
          />
        ))}
      </ul>
    </>
  )
}

export function FilaHabitacion({ habitacion: h, puedeLimpiar, puedeMantenimiento, alLimpiar, alCambiarMantenimiento }) {
  const hayLimpiezaPendiente = h.limpieza_pendiente || h.estado_preparacion === 'sucia'
  return (
    <li className="inventario-fila">
      <span className="reserva-id">{h.habitacion_id}</span>
      <span className="reserva-celda">{h.tipo}</span>
      <span className="reserva-celda">{h.capacidad}</span>
      <span className={`reserva-estado estado-${h.estado_operativo}`}>
        {ETIQUETA_OPERATIVO[h.estado_operativo] || h.estado_operativo}
      </span>
      <span className={`reserva-estado preparacion-${h.estado_preparacion}`}>
        {ETIQUETA_PREPARACION[h.estado_preparacion] || h.estado_preparacion}
      </span>
      <span className={`reserva-estado ${h.mantenimiento ? 'estado-cancelada' : 'estado-finalizada'}`}>
        {h.mantenimiento ? 'en mantenimiento' : 'activa'}
      </span>
      <span className="reserva-tarifa">{h.tarifa_noche_clp > 0 ? `$${h.tarifa_noche_clp}/noche` : 'sin tarifa'}</span>
      <span className="inventario-acciones">
        {puedeLimpiar && hayLimpiezaPendiente && (
          <button type="button" className="boton-fantasma" onClick={() => alLimpiar(h.habitacion_id)}>
            Completar limpieza
          </button>
        )}
        {puedeMantenimiento && (
          <button
            type="button"
            className="boton-fantasma"
            onClick={() => alCambiarMantenimiento(h.habitacion_id, !h.mantenimiento)}
          >
            {h.mantenimiento ? 'Cerrar mantenimiento' : 'Abrir mantenimiento'}
          </button>
        )}
      </span>
    </li>
  )
}

export function InventarioVacio() {
  return (
    <div className="oferta-vacia">
      <p className="oferta-vacia-titulo">Todavía no hay habitaciones</p>
      <p className="oferta-vacia-texto">Da de alta la primera unidad con el formulario de abajo.</p>
    </div>
  )
}
