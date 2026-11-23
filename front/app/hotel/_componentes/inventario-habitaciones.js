'use client'

import Link from 'next/link'
import { useState } from 'react'
import { clp } from '../../../lib/api'
import { esAdminHotel, gestionaRecepcion } from '../../../lib/roles'
import { fechaATexto, plural } from '../../../lib/formato'
import { nombreTipo } from '../../reservar/continuidad'
import { BarraContextual, SelectorFila } from './barra-contextual'

/**
 * Capa del módulo Hotel — inventario operativo de habitaciones (pura, sin
 * fetch): usa selección por fila + barra contextual única (sin repetir
 * botones en las 17 habitaciones).
 */

const ETIQUETA_OPERATIVO = {
  disponible: 'Disponible',
  ocupada: 'Ocupada',
  bloqueada: 'Bloqueada',
  fuera_de_servicio: 'Fuera de servicio',
}

const ETIQUETA_PREPARACION = {
  limpia: 'Limpia',
  sucia: 'Sucia',
  en_limpieza: 'En limpieza',
  inspeccionada: 'Inspeccionada',
}

export function InventarioHabitaciones({ habitaciones, rol, alLimpiar, alCambiarMantenimiento }) {
  const puedeLimpiar = gestionaRecepcion(rol)
  const puedeMantenimiento = esAdminHotel(rol)
  const [seleccionadaId, setSeleccionadaId] = useState(null)

  const activa = habitaciones.find((h) => h.habitacion_id === seleccionadaId) || null
  const hayLimpiezaPendiente = activa ? (activa.limpieza_pendiente || activa.estado_preparacion === 'sucia') : false

  return (
    <>
      <p className="reservas-total">{plural(habitaciones.length, 'habitación', 'habitaciones')}</p>

      <BarraContextual
        titulo="Acciones de habitación"
        seleccionado={Boolean(activa)}
        resumen={activa ? `Habitación ${activa.habitacion_id} · ${nombreTipo(activa.tipo)}` : ''}
        detalle={activa ? `${ETIQUETA_OPERATIVO[activa.estado_operativo] || activa.estado_operativo} · ${ETIQUETA_PREPARACION[activa.estado_preparacion] || activa.estado_preparacion}` : ''}
        placeholder="Selecciona una habitación para abrir su ficha, completar limpieza o gestionar mantenimiento."
        alLimpiar={() => setSeleccionadaId(null)}
      >
        {activa && (
          <>
            <Link href={`/hotel/habitaciones/${activa.habitacion_id}`} className="boton-primario">
              Abrir ficha
            </Link>
            {puedeLimpiar && hayLimpiezaPendiente && (
              <button type="button" className="boton-secundario" onClick={() => alLimpiar(activa.habitacion_id)}>
                Completar limpieza
              </button>
            )}
            {puedeMantenimiento && (
              <button
                type="button"
                className="boton-secundario"
                onClick={() => alCambiarMantenimiento(activa.habitacion_id, !activa.mantenimiento)}
              >
                {activa.mantenimiento ? 'Cerrar mantenimiento' : 'Abrir mantenimiento'}
              </button>
            )}
          </>
        )}
      </BarraContextual>

      <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Inventario de habitaciones (desliza para ver todas las columnas)">
        <ul className="reservas-lista" role="table">
          <li className="inventario-encabezado" role="row">
            <span role="columnheader"><span className="sr-only">Elegir</span></span>
            <span role="columnheader">Habitación</span>
            <span role="columnheader">Tipo</span>
            <span role="columnheader">Cap.</span>
            <span role="columnheader">Estado</span>
            <span role="columnheader">Preparación</span>
            <span role="columnheader">Mantenimiento</span>
            <span role="columnheader">Precio hoy</span>
          </li>
          {habitaciones.map((h) => (
            <FilaHabitacion
              key={h.habitacion_id}
              habitacion={h}
              seleccionada={activa?.habitacion_id === h.habitacion_id}
              alElegir={() => setSeleccionadaId(h.habitacion_id)}
            />
          ))}
        </ul>
      </div>
    </>
  )
}

export function FilaHabitacion({ habitacion: h, seleccionada = false, alElegir }) {
  return (
    <li
      className="inventario-fila fila-seleccionable"
      role="row"
      data-seleccionada={seleccionada ? 'true' : 'false'}
      onClick={alElegir}
    >
      <span role="cell">
        <SelectorFila
          nombreGrupo="habitacion-activa"
          elegido={seleccionada}
          etiqueta={`Seleccionar habitación ${h.habitacion_id}`}
          alElegir={alElegir}
        />
      </span>
      <span role="cell" className="reserva-id">
        <Link
          href={`/hotel/habitaciones/${h.habitacion_id}`}
          title="Abrir ficha: datos, precio, reservas e historial"
          onClick={(e) => e.stopPropagation()}
        >
          {h.habitacion_id}
        </Link>
      </span>
      <span role="cell" className="reserva-celda">{nombreTipo(h.tipo)}</span>
      <span role="cell" className="reserva-celda">{h.capacidad}</span>
      <span role="cell" className={`reserva-estado estado-${h.estado_operativo}`}>
        {ETIQUETA_OPERATIVO[h.estado_operativo] || h.estado_operativo}
      </span>
      <span role="cell" className={`reserva-estado preparacion-${h.estado_preparacion}`}>
        {ETIQUETA_PREPARACION[h.estado_preparacion] || h.estado_preparacion}
      </span>
      <span role="cell" className={`reserva-estado ${h.mantenimiento ? 'estado-cancelada' : 'estado-finalizada'}`}>
        {h.mantenimiento
          ? `En mantenimiento${h.mantenimiento_desde ? ` desde ${fechaATexto(h.mantenimiento_desde)}` : ''}${h.mantenimiento_hasta ? ` hasta ${fechaATexto(h.mantenimiento_hasta)}` : ''}`
          : 'Activa'}
      </span>
      <span role="cell" className="reserva-tarifa">
        {h.tarifa_vigente_hoy_clp ? `${clp(h.tarifa_vigente_hoy_clp)}/noche` : 'Sin precio hoy'}
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
