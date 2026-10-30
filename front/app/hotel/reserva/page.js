'use client'

import { useState } from 'react'
import { api, MarcoHotel, SalidaJson, Campo, useClaveOperacion } from '../../../lib/api'

export default function Reserva() {
  const [campos, setCampos] = useState({
    habitacion_id: 'HAB-SINT-102',
    inicio: '2026-12-10',
    fin: '2026-12-12',
    nombre: 'Huésped Web',
  })
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [clave, renovarClave] = useClaveOperacion()

  async function confirmar(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    try {
      const r = await api('/hotel/reservas', {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {
          habitacion_id: campos.habitacion_id,
          inicio: campos.inicio,
          fin: campos.fin,
          huesped: { nombre: campos.nombre },
        },
      })
      if (r.estado >= 400) setError(JSON.stringify(r.datos)) // 409 incluido: la clave se conserva
      else {
        setSalida(r.datos)
        renovarClave() // 2xx: clave nueva para la operación siguiente
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  function nuevaOperacion() {
    setSalida(null)
    setError('')
    renovarClave()
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
      <p className="nota-clave">Clave de idempotencia (reintenta con la misma para no duplicar): <code>{clave}</code></p>
      <button onClick={nuevaOperacion} className="boton-secundario">Nueva operación</button>
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
