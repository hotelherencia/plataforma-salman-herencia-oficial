'use client'

import Link from 'next/link'
import { Fragment, useState } from 'react'
import FormularioEdicion from './formulario-edicion'
import { clp } from '../../../lib/api'
import { plural } from '../../../lib/formato'

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

export function ListaReservas({ reservas, total, alActualizar }) {
  const [editandoId, setEditandoId] = useState(null)
  const [aviso, setAviso] = useState('')
  return (
    <>
      <p className="reservas-total">{plural(total, 'reserva encontrada', 'reservas encontradas')}</p>
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      <ul className="reservas-lista" role="table">
        <EncabezadoReservas />
        {reservas.map((r) => (
          <Fragment key={r.reserva_id}>
            <FilaReserva
              reserva={r}
              editando={editandoId === r.reserva_id}
              onToggleEditar={() => { setAviso(''); setEditandoId(editandoId === r.reserva_id ? null : r.reserva_id) }}
            />
            {editandoId === r.reserva_id && (
              <li className="reserva-edicion" role="row" style={{ gridColumn: '1 / -1', padding: '0.5rem 0' }}>
                <FormularioEdicion
                  ruta={`/hotel/reservas/${encodeURIComponent(r.reserva_id)}/huesped`}
                  tituloAria={`Editar huésped de ${r.reserva_id}`}
                  inicial={{ nombre: r.huesped_nombre || '', documento: '', documento_tipo: 'rut' }}
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
                    setEditandoId(null)
                    setAviso(`Reserva ${r.reserva_id} actualizada correctamente.`)
                    if (typeof alActualizar === 'function') alActualizar()
                  }}
                  alCancelar={() => setEditandoId(null)}
                />
              </li>
            )}
          </Fragment>
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
      <span role="columnheader">Acciones</span>
    </li>
  )
}

export function FilaReserva({ reserva, editando = false, onToggleEditar }) {
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
      <span role="cell" className="acciones-fila">
        {typeof onToggleEditar === 'function' && (
          <button type="button" className="boton-secundario" onClick={onToggleEditar}>
            {editando ? 'Cerrar' : 'Editar'}
          </button>
        )}
        <Link href={`/hotel/reservas/${reserva.reserva_id}`} className="boton-fantasma">Ficha</Link>
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
