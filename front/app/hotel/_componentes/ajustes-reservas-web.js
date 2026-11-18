'use client'

import { useEffect, useState } from 'react'
import { api, mensajeDeError, Campo } from '../../../lib/api'

function clave() {
  return `aj-${crypto.randomUUID().slice(0, 12)}`
}

/**
 * Reservas web (#348): tope de solicitudes por cliente (correo o teléfono)
 * en un período. Lo edita la administración del hotel.
 */
export default function AjustesReservasWeb() {
  const [tope, setTope] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    api('/hotel/ajustes')
      .then((r) => (r.estado === 200 ? setTope(r.datos.ajustes.tope_solicitudes_cliente) : setError(mensajeDeError(r.datos, r.estado))))
      .catch(() => setError('La API no está disponible'))
  }, [])

  async function guardar(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const cuerpo = { activo: tope.activo, max_solicitudes: Number(tope.max_solicitudes), dias: Number(tope.dias) }
    try {
      const r = await api('/hotel/ajustes/tope_solicitudes_cliente', { metodo: 'PUT', cuerpo, claveIdempotencia: clave() })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setTope(r.datos.valor)
        setAviso('Tope guardado.')
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <section className="tarjeta">
      <h2>Tope de solicitudes por cliente</h2>
      <p className="nota-clave">
        Un mismo cliente (mismo correo o teléfono) puede dejar como máximo este número de solicitudes de reserva
        en el período. Las rechazadas no cuentan. Frena el abuso sin bloquear habitaciones.
      </p>
      {!tope && !error && <p className="estado">Cargando…</p>}
      {tope && (
        <form className="formulario" onSubmit={guardar}>
          <label className="campo-check">
            <input type="checkbox" checked={tope.activo} onChange={(e) => setTope({ ...tope, activo: e.target.checked })} />
            Tope activo
          </label>
          <Campo etiqueta="Máximo de solicitudes por cliente" type="number" min="1" max="100" value={tope.max_solicitudes}
            onChange={(e) => setTope({ ...tope, max_solicitudes: e.target.value })} />
          <Campo etiqueta="Período (días)" type="number" min="1" max="365" value={tope.dias}
            onChange={(e) => setTope({ ...tope, dias: e.target.value })} />
          <button type="submit" className="boton-primario">Guardar</button>
        </form>
      )}
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
    </section>
  )
}
