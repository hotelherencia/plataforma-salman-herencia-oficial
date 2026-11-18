'use client'

import { useEffect, useState } from 'react'
import { api, clp } from '../../../lib/api'
import { nombreTipo } from '../../reservar/continuidad'
import { validarDocumento } from '../../../lib/documento'

/** Documento obligatorio con tipo (#367): RUT validado o pasaporte. */
export function CampoDocumento({ tipo, numero, alCambiar, obligatorio = true }) {
  const revision = numero ? validarDocumento(tipo, numero) : null
  return (
    <fieldset className="grupo-documento">
      <legend className="campo-etiqueta">Documento del huésped{obligatorio ? ' (obligatorio)' : ''}</legend>
      <label className="campo">
        <span className="campo-etiqueta">Tipo de documento</span>
        <select className="entrada" value={tipo} onChange={(e) => alCambiar({ tipo: e.target.value, numero })}>
          <option value="rut">RUT</option>
          <option value="pasaporte">Pasaporte</option>
        </select>
      </label>
      <label className="campo">
        <span className="campo-etiqueta">Número de documento</span>
        <input
          className="entrada"
          value={numero}
          aria-invalid={revision && !revision.ok ? 'true' : undefined}
          placeholder={tipo === 'rut' ? '12.345.678-5' : 'AB1234567'}
          onChange={(e) => alCambiar({ tipo, numero: e.target.value })}
        />
      </label>
      {revision && !revision.ok && <p className="alerta" role="alert">{revision.error}</p>}
    </fieldset>
  )
}

/**
 * Selector de habitación con disponibilidad real (#367, #360, #361): lista las
 * unidades libres en el rango según /hotel/oferta. `incluir` agrega la unidad
 * actual de la reserva (la oferta la excluye porque la ocupa la misma reserva).
 */
export function SelectorUnidad({ etiqueta = 'Habitación', inicio, fin, personas, valor, alCambiar, incluir }) {
  const [items, setItems] = useState([])
  const [estado, setEstado] = useState('')

  useEffect(() => {
    if (!inicio || !fin || fin <= inicio) {
      setItems([])
      setEstado('Elige las fechas para ver las habitaciones libres.')
      return undefined
    }
    let cancelado = false
    setEstado('Buscando habitaciones libres…')
    const q = new URLSearchParams({ inicio, fin, personas: String(Math.max(1, Number(personas) || 1)) })
    api(`/hotel/oferta?${q}`)
      .then((r) => {
        if (cancelado) return
        const lista = r.estado === 200 ? r.datos.oferta || [] : []
        setItems(lista)
        setEstado(lista.length ? '' : 'No hay habitaciones libres con tarifa en ese rango.')
      })
      .catch(() => { if (!cancelado) setEstado('La API no está disponible.') })
    return () => { cancelado = true }
  }, [inicio, fin, personas])

  const grupos = {}
  for (const item of items) (grupos[item.tipo] ||= []).push(item)

  return (
    <label className="campo">
      <span className="campo-etiqueta">{etiqueta}</span>
      <select className="entrada" value={valor || ''} onChange={(e) => alCambiar(e.target.value)}>
        <option value="">{estado || 'Elige una habitación'}</option>
        {incluir && !items.some((i) => i.habitacion_id === incluir) && (
          <option value={incluir}>{incluir} (actual)</option>
        )}
        {Object.entries(grupos).map(([tipo, lista]) => (
          <optgroup key={tipo} label={nombreTipo(tipo)}>
            {lista.map((i) => (
              <option key={i.habitacion_id} value={i.habitacion_id}>
                {i.habitacion_id} · hasta {i.capacidad} · {clp(i.total_clp)} total
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </label>
  )
}
