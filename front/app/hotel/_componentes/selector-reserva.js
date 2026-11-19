'use client'

import { useEffect, useState } from 'react'
import { api, clp } from '../../../lib/api'
import { fechaATexto } from '../../../lib/formato'

/**
 * Selector de reserva (#356, #364): nunca un ID escrito a mano.
 * - `fijo`: la reserva llegó precargada (?reserva_id= o desde el detalle) y se
 *   muestra solo lectura; «Cambiar reserva» la libera a propósito.
 * - Sin reserva: buscador por huésped, habitación o código, filtrado por
 *   `estados` (por defecto, cuentas abiertas).
 */
export function SelectorReserva({ etiqueta = 'Reserva', valor, alCambiar, fijo = false, alLiberar, estados = ['confirmada', 'en_estadia'] }) {
  const [texto, setTexto] = useState('')
  const [opciones, setOpciones] = useState([])
  const [buscando, setBuscando] = useState(false)

  useEffect(() => {
    if (fijo && valor) return undefined
    let cancelado = false
    const t = setTimeout(async () => {
      setBuscando(true)
      try {
        const q = new URLSearchParams()
        if (texto.trim()) q.set('texto', texto.trim())
        const r = await api(`/hotel/reservas?${q}`)
        if (!cancelado && r.estado === 200) {
          setOpciones((r.datos.reservas || []).filter((x) => estados.includes(x.estado)).slice(0, 50))
        }
      } catch {
        if (!cancelado) setOpciones([])
      } finally {
        if (!cancelado) setBuscando(false)
      }
    }, 250)
    return () => {
      cancelado = true
      clearTimeout(t)
    }
    // estados es una lista literal estable por pantalla
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [texto, fijo, valor])

  if (fijo && valor) {
    return (
      <div className="campo" data-reserva-fija>
        <span className="campo-etiqueta">{etiqueta}</span>
        <span className="reserva-fija">
          <code>{valor}</code>
          {alLiberar && (
            <button type="button" className="boton-fantasma" onClick={alLiberar}>
              Cambiar reserva
            </button>
          )}
        </span>
      </div>
    )
  }

  return (
    <div className="selector-reserva">
      <label className="campo">
        <span className="campo-etiqueta">Buscar {etiqueta.toLowerCase()} (huésped, habitación o código)</span>
        <input className="entrada" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Ej.: Pérez o 104" />
      </label>
      <label className="campo">
        <span className="campo-etiqueta">{etiqueta}</span>
        <select className="entrada" value={valor || ''} onChange={(e) => alCambiar(e.target.value)}>
          <option value="">{buscando ? 'Buscando…' : opciones.length ? 'Elige una reserva' : 'Sin coincidencias'}</option>
          {opciones.map((o) => (
            <option key={o.reserva_id} value={o.reserva_id}>
              {o.huesped_nombre} · hab. {o.habitacion_id} · {fechaATexto(o.inicio)} → {fechaATexto(o.fin)} · {o.reserva_id}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}

/** Ficha de la reserva elegida: huésped, habitación, fechas y cuenta (#364). */
export function FichaReserva({ detalle }) {
  if (!detalle) return null
  const { cuenta } = detalle
  return (
    <div className="ficha-reserva" aria-label="Reserva elegida">
      <p>
        <strong>{detalle.huesped_nombre}</strong> · habitación {detalle.habitacion_id} ({detalle.tipo_habitacion}) ·{' '}
        {fechaATexto(detalle.inicio)} → {fechaATexto(detalle.fin)}
      </p>
      <p className="nota-clave">
        Cargos netos {clp(cuenta.cargos_netos_clp)} · Pagado {clp(cuenta.pagado_clp)} · Saldo{' '}
        <strong>{clp(cuenta.saldo_clp)}</strong>
      </p>
    </div>
  )
}

/** Carga el detalle de una reserva (o null) cada vez que cambia el id. */
export function useDetalleReserva(reservaId, version = 0) {
  const [detalle, setDetalle] = useState(null)
  useEffect(() => {
    const limpio = (reservaId || '').trim()
    if (!/^RSV-[A-Za-z0-9_-]+$/.test(limpio)) {
      setDetalle(null)
      return undefined
    }
    let cancelado = false
    api(`/hotel/reservas/${encodeURIComponent(limpio)}`)
      .then((r) => { if (!cancelado) setDetalle(r.estado === 200 ? r.datos : null) })
      .catch(() => { if (!cancelado) setDetalle(null) })
    return () => { cancelado = true }
  }, [reservaId, version])
  return detalle
}
