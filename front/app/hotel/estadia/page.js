'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, useClaveOperacion, useSesion } from '../../../lib/api'

export default function Estadia() {
  const sesion = useSesion()

    // V1-ISSUE-35: precarga del detalle de reserva («Siguiente paso»).
    useEffect(() => {
      const r = new URLSearchParams(window.location.search).get('reserva_id')
      if (r) setReservaId(r)
    }, [])
  const [reservaId, setReservaId] = useState('')
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [claveEntrada, renovarClaveEntrada] = useClaveOperacion()
  const [claveCancela, renovarClaveCancela] = useClaveOperacion()
  const [claveCargo, renovarClaveCargo] = useClaveOperacion()
  const [cargo, setCargo] = useState({ reserva_id: '', concepto: 'minibar', monto_clp: '5000' })
  const [enviando, setEnviando] = useState(false)

  // spec-api-v1: la cancelación la ejecutan recepción o administrador. La
  // acción se oculta a otros roles (la API igual la rechazaría con 403).
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeCancelar = rol === 'recepcion' || rol === 'administrador'

  async function checkIn(e) {
    e.preventDefault()
    setEnviando(true)
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
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClaveEntrada)
      }
      else {
        setSalida(r.datos)
        renovarClaveEntrada()
      }
    } catch {
      setError('La API no está disponible')
    } finally {
      setEnviando(false)
    }
  }

  async function cancelar(e) {
    e.preventDefault()
    setEnviando(true)
    if (!window.confirm('¿Cancelar esta reserva? Se reversan los cargos sin pagar y, fuera de plazo, se carga la primera noche.')) return
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
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClaveCancela)
      }
      else {
        setSalida(r.datos)
        renovarClaveCancela()
      }
    } catch {
      setError('La API no está disponible')
    } finally {
      setEnviando(false)
    }
  }

  async function asentarCargo(e) {
    e.preventDefault()
    setEnviando(true)
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
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClaveCargo)
      }
      else {
        setSalida(r.datos)
        renovarClaveCargo()
      }
    } catch {
      setError('La API no está disponible')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <MarcoHotel titulo="Estadía: entrada, cancelación y cargos">
      <section className="tarjeta">
        <h2>Check-in (entrada a la estadía)</h2>
        <form className="formulario" onSubmit={checkIn}>
          <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
          <button type="submit" className="boton-primario" disabled={enviando}>{enviando ? "Procesando…" : "Registrar entrada"}</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveEntrada}</code></p>
      </section>
      {puedeCancelar && (
        <section className="tarjeta">
          <h2>Cancelar reserva (recepción o administrador)</h2>
          <form className="formulario" onSubmit={cancelar}>
            <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
            <button type="submit" className="boton-primario" disabled={enviando}>{enviando ? "Procesando…" : "Cancelar reserva"}</button>
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
          <button type="submit" className="boton-primario" disabled={enviando}>{enviando ? "Procesando…" : "Asentar cargo"}</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveCargo}</code></p>
      </section>
      <button onClick={() => { setSalida(null); setError(''); renovarClaveEntrada(); renovarClaveCancela(); renovarClaveCargo() }} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
