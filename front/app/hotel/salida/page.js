'use client'

import { useState } from 'react'
import { api, alRechazar, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, useClaveOperacion } from '../../../lib/api'

export default function SalidaPage() {
  const [reservaId, setReservaId] = useState('')
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [clave, renovarClave] = useClaveOperacion()

  async function checkOut(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[reservaId, 'ID de la reserva']])
    if (falta) { setError(falta); return }
    try {
      const r = await api(`/hotel/reservas/${reservaId}/salida`, {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {},
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
      } else {
        setSalida(r.datos)
        renovarClave()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Check-out (salida y liquidación)">
      <section className="tarjeta">
        <form className="formulario" onSubmit={checkOut}>
          <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
          <button type="submit" className="boton-primario">Liquidar cuenta</button>
        </form>
      </section>
      <p className="nota-clave">Clave de idempotencia (reintenta con la misma para no duplicar): <code>{clave}</code></p>
      <button onClick={() => { setSalida(null); setError(''); renovarClave() }} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
