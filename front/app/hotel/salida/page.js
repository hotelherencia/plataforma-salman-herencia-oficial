'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, useClaveOperacion } from '../../../lib/api'

export default function SalidaPage() {

    // V1-ISSUE-35: precarga del detalle de reserva («Siguiente paso»).
    useEffect(() => {
      const r = new URLSearchParams(window.location.search).get('reserva_id')
      if (r) setReservaId(r)
    }, [])
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
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <MarcoHotel titulo="Salida y liquidación de la cuenta">
      <section className="tarjeta">
        <form className="formulario" onSubmit={checkOut}>
          <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
          <button type="submit" className="boton-primario">Liquidar cuenta</button>
        </form>
      </section>
      <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{clave}</code></span>
      <button onClick={() => { setSalida(null); setError(''); renovarClave() }} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
