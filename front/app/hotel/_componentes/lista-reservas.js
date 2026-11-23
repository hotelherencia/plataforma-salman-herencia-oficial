'use client'

import Link from 'next/link'
import { useState } from 'react'
import FormularioEdicion from './formulario-edicion'
import { BarraContextual, SelectorFila } from './barra-contextual'
import { clp } from '../../../lib/api'
import { plural } from '../../../lib/formato'

/**
 * Capa del módulo Hotel — búsqueda de reservas (pura, sin fetch): recibe
 * solo props y dibuja la respuesta de GET /hotel/reservas tal cual la envía
 * la API. Usa selección de reserva activa + barra contextual única (sin
 * repetir botones de acción en cada fila).
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

export function ListaReservas({ reservas, total, alActualizar }) {
  const [seleccionadaId, setSeleccionadaId] = useState(null)
  const [editando, setEditando] = useState(false)
  const [aviso, setAviso] = useState('')

  const activa = reservas.find((r) => r.reserva_id === seleccionadaId) || null

  function elegir(reservaId) {
    setAviso('')
    if (seleccionadaId !== reservaId) {
      setSeleccionadaId(reservaId)
      setEditando(false)
    }
  }

  return (
    <>
      <p className="reservas-total">{plural(total, 'reserva encontrada', 'reservas encontradas')}</p>
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      <BarraContextual
        titulo="Acciones de reserva"
        seleccionado={Boolean(activa)}
        resumen={activa ? `${activa.huesped_nombre} · ${activa.habitacion_id}` : ''}
        detalle={activa ? `${activa.reserva_id} · Llegada ${fechaChile(activa.inicio)} · Salida ${fechaChile(activa.fin)} · ${ETIQUETA_ESTADO[activa.estado] || activa.estado}` : ''}
        placeholder="Selecciona una reserva de la lista para abrir su ficha o editar los datos del huésped."
        alLimpiar={() => { setSeleccionadaId(null); setEditando(false) }}
      >
        {activa && (
          <>
            <Link href={`/hotel/reservas/${activa.reserva_id}`} className="boton-primario">
              Ver ficha y cuenta
            </Link>
            <button
              type="button"
              className="boton-secundario"
              aria-expanded={editando}
              onClick={() => setEditando((v) => !v)}
            >
              {editando ? 'Cerrar edición' : 'Editar huésped'}
            </button>
          </>
        )}
      </BarraContextual>

      {activa && editando && (
        <div className="reserva-edicion" style={{ marginBottom: '0.75rem' }}>
          <FormularioEdicion
            key={activa.reserva_id}
            ruta={`/hotel/reservas/${encodeURIComponent(activa.reserva_id)}/huesped`}
            tituloAria={`Editar huésped de ${activa.reserva_id}`}
            inicial={{ nombre: activa.huesped_nombre || '', documento: '', documento_tipo: 'rut' }}
            campos={[
              { nombre: 'nombre', etiqueta: 'Nombre del huésped', requerido: true },
              { nombre: 'documento_tipo', etiqueta: 'Tipo de documento', tipo: 'select', opciones: [['rut', 'RUT'], ['pasaporte', 'Pasaporte']] },
              { nombre: 'documento', etiqueta: 'Documento (opcional si no cambia)' },
            ]}
            armar={(v) => ({
              nombre: v.nombre.trim(),
              documento: v.documento.trim() || null,
              documento_tipo: v.documento.trim() ? v.documento_tipo : null,
            })}
            alGuardar={() => {
              setEditando(false)
              setAviso(`Reserva ${activa.reserva_id} actualizada correctamente.`)
              if (typeof alActualizar === 'function') alActualizar()
            }}
            alCancelar={() => setEditando(false)}
          />
        </div>
      )}

      <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Listado de reservas (desliza para ver todas las columnas)">
        <ul className="reservas-lista" role="table">
          <EncabezadoReservas />
          {reservas.map((r) => (
            <FilaReserva
              key={r.reserva_id}
              reserva={r}
              seleccionada={activa?.reserva_id === r.reserva_id}
              alElegir={() => elegir(r.reserva_id)}
            />
          ))}
        </ul>
      </div>
    </>
  )
}

export function EncabezadoReservas() {
  return (
    <li className="reserva-encabezado" role="row">
      <span role="columnheader"><span className="sr-only">Elegir</span></span>
      <span role="columnheader">Reserva</span>
      <span role="columnheader">Huésped</span>
      <span role="columnheader">Habitación</span>
      <span role="columnheader">Llegada y Salida</span>
      <span role="columnheader">Estado</span>
      <span role="columnheader">Precio</span>
    </li>
  )
}

export function FilaReserva({ reserva, seleccionada = false, alElegir }) {
  return (
    <li
      className="reserva-fila fila-seleccionable"
      role="row"
      data-seleccionada={seleccionada ? 'true' : 'false'}
      onClick={alElegir}
    >
      <span role="cell" className="reserva-sel">
        <SelectorFila
          nombreGrupo="reserva-activa"
          elegido={seleccionada}
          etiqueta={`Seleccionar reserva ${reserva.reserva_id} de ${reserva.huesped_nombre}`}
          alElegir={alElegir}
        />
      </span>
      <span role="cell" className="reserva-id">
        <Link href={`/hotel/reservas/${reserva.reserva_id}`} title="Ver detalle y cuenta" onClick={(e) => e.stopPropagation()}>
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
      <span role="cell" className="reserva-estado-celda">
        <span className={`reserva-estado estado-${reserva.estado}`}>
          {ETIQUETA_ESTADO[reserva.estado] || reserva.estado}
        </span>
      </span>
      <span role="cell" className="reserva-tarifa">
        {clp(reserva.tarifa_noche_aceptada_clp)}<span className="reserva-por-noche"> / noche</span>
      </span>
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
