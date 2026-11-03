'use client'

import { useState } from 'react'
import { api, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, useClaveOperacion, useSesion } from '../../../lib/api'

export default function Estadia() {
  const sesion = useSesion()
  const [reservaId, setReservaId] = useState('')
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [claveEntrada, renovarClaveEntrada] = useClaveOperacion()
  const [claveCancela, renovarClaveCancela] = useClaveOperacion()
  const [claveCargo, renovarClaveCargo] = useClaveOperacion()
  const [cargo, setCargo] = useState({ reserva_id: '', concepto: 'minibar', monto_clp: '5000' })

  // spec-api-v1: la cancelación la ejecutan recepción o administrador. La
  // acción se oculta a otros roles (la API igual la rechazaría con 403).
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeCancelar = rol === 'recepcion' || rol === 'administrador'

  async function checkIn(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[reservaId, 'ID de la reserva']])
    if (falta) { setError(falta); return }
    try {
      const r = await api(`/hotel/reservas/${reservaId}/entrada`, {
        metodo: 'POST',
        claveIdempotencia: claveEntrada,
        cuerpo: {},
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setSalida(r.datos)
        renovarClaveEntrada()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  async function cancelar(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[reservaId, 'ID de la reserva']])
    if (falta) { setError(falta); return }
    try {
      const r = await api(`/hotel/reservas/${reservaId}/cancelacion`, {
        metodo: 'POST',
        claveIdempotencia: claveCancela,
        cuerpo: {},
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setSalida(r.datos)
        renovarClaveCancela()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  async function asentarCargo(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[cargo.reserva_id, 'ID de la reserva'], [cargo.monto_clp, 'Monto CLP']])
    if (falta) { setError(falta); return }
    try {
      const r = await api(`/hotel/reservas/${cargo.reserva_id}/cargos`, {
        metodo: 'POST',
        claveIdempotencia: claveCargo,
        cuerpo: { concepto: cargo.concepto, monto_clp: Number(cargo.monto_clp) },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setSalida(r.datos)
        renovarClaveCargo()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Estadía: entrada, cancelación y cargos">
      <section className="tarjeta">
        <h2>Check-in (entrada a la estadía)</h2>
        <form className="formulario" onSubmit={checkIn}>
          <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
          <button type="submit" className="boton-primario">Registrar entrada</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveEntrada}</code></p>
      </section>
      {puedeCancelar && (
        <section className="tarjeta">
          <h2>Cancelar reserva (recepción o administrador)</h2>
          <form className="formulario" onSubmit={cancelar}>
            <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
            <button type="submit" className="boton-primario">Cancelar reserva</button>
          </form>
          <p className="nota-clave">Clave: <code>{claveCancela}</code></p>
        </section>
      )}
      <section className="tarjeta">
        <h2>Asentar cargo (minibar, consumo, extra)</h2>
        <form className="formulario" onSubmit={asentarCargo}>
          <Campo etiqueta="Reserva" value={cargo.reserva_id} onChange={(e) => setCargo({ ...cargo, reserva_id: e.target.value })} />
          <Campo etiqueta="Concepto" value={cargo.concepto} onChange={(e) => setCargo({ ...cargo, concepto: e.target.value })} />
          <Campo etiqueta="Monto (CLP)" type="number" value={cargo.monto_clp} onChange={(e) => setCargo({ ...cargo, monto_clp: e.target.value })} />
          <button type="submit" className="boton-primario">Asentar cargo</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveCargo}</code></p>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
