'use client'

import { useState } from 'react'
import { api, MarcoHotel, SalidaJson, Campo } from '../../../lib/api'

export default function Reserva() {
  const [campos, setCampos] = useState({
    habitacion_id: 'HAB-SINT-102',
    inicio: '2026-12-10',
    fin: '2026-12-12',
    nombre: 'Huésped Web',
  })
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [clave, setClave] = useState('')

  async function confirmar(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const nuevaClave = crypto.randomUUID()
    setClave(nuevaClave)
    try {
      const r = await api('/hotel/reservas', {
        metodo: 'POST',
        claveIdempotencia: nuevaClave,
        cuerpo: {
          habitacion_id: campos.habitacion_id,
          inicio: campos.inicio,
          fin: campos.fin,
          huesped: { nombre: campos.nombre },
        },
      })
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else setSalida(r.datos)
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Reservar">
      <section className="tarjeta">
        <form className="formulario" onSubmit={confirmar}>
          <Campo etiqueta="Habitación" value={campos.habitacion_id} onChange={(e) => setCampos({ ...campos, habitacion_id: e.target.value })} />
          <Campo etiqueta="Desde" type="date" value={campos.inicio} onChange={(e) => setCampos({ ...campos, inicio: e.target.value })} />
          <Campo etiqueta="Hasta" type="date" value={campos.fin} onChange={(e) => setCampos({ ...campos, fin: e.target.value })} />
          <Campo etiqueta="Huésped" value={campos.nombre} onChange={(e) => setCampos({ ...campos, nombre: e.target.value })} />
          <button type="submit" className="boton-primario">Confirmar reserva</button>
        </form>
      </section>
      {clave && <p className="nota-clave">Clave de idempotencia (reintenta con la misma para no duplicar): <code>{clave}</code></p>}
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
      {salida && (
        <a
          className="boton-primario enlace-salida"
          target="_blank"
          rel="noopener noreferrer"
          href={`https://wa.me/56956491501?text=${encodeURIComponent(
            `Reserva ${salida.reserva_id} confirmada: habitación ${salida.habitacion_id}, del ${salida.inicio} al ${salida.fin}. Huésped: ${campos.nombre}.`
          )}`}
        >
          Avisar por WhatsApp
        </a>
      )}
    </MarcoHotel>
  )
}
