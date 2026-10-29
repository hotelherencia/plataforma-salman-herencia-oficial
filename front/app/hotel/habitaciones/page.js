'use client'

import { useState } from 'react'
import { api, MarcoHotel, SalidaJson, Campo } from '../../../lib/api'

export default function Habitaciones() {
  const [hab, setHab] = useState({ habitacion_id: 'HAB-101', tipo: 'doble', capacidad: '2' })
  const [tarifa, setTarifa] = useState({
    habitacion_id: 'HAB-101',
    fecha_desde: '2026-01-01',
    fecha_hasta: '2027-12-31',
    tarifa_noche_clp: '50000',
  })
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [claveUsada, setClaveUsada] = useState('')

  async function enviar(ruta, cuerpo, e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const clave = crypto.randomUUID()
    setClaveUsada(clave)
    try {
      const r = await api(ruta, { metodo: 'PUT', cuerpo, claveIdempotencia: clave })
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else setSalida(r.datos)
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Habitaciones y tarifas (administrador)">
      <section className="tarjeta">
        <h2>Alta o cambio de habitación</h2>
        <form className="formulario" onSubmit={(e) => enviar(`/hotel/habitaciones/${hab.habitacion_id}`, { tipo: hab.tipo, capacidad: Number(hab.capacidad) }, e)}>
          <Campo etiqueta="Habitación" value={hab.habitacion_id} onChange={(e) => setHab({ ...hab, habitacion_id: e.target.value })} />
          <Campo etiqueta="Tipo" value={hab.tipo} onChange={(e) => setHab({ ...hab, tipo: e.target.value })} />
          <Campo etiqueta="Capacidad" type="number" value={hab.capacidad} onChange={(e) => setHab({ ...hab, capacidad: e.target.value })} />
          <button type="submit" className="boton-primario">Guardar habitación</button>
        </form>
      </section>
      <section className="tarjeta">
        <h2>Tarifa por fecha</h2>
        <form className="formulario" onSubmit={(e) => enviar('/hotel/tarifas', { ...tarifa, tarifa_noche_clp: Number(tarifa.tarifa_noche_clp) }, e)}>
          <Campo etiqueta="Habitación" value={tarifa.habitacion_id} onChange={(e) => setTarifa({ ...tarifa, habitacion_id: e.target.value })} />
          <Campo etiqueta="Desde" type="date" value={tarifa.fecha_desde} onChange={(e) => setTarifa({ ...tarifa, fecha_desde: e.target.value })} />
          <Campo etiqueta="Hasta" type="date" value={tarifa.fecha_hasta} onChange={(e) => setTarifa({ ...tarifa, fecha_hasta: e.target.value })} />
          <Campo etiqueta="Tarifa por noche (CLP)" type="number" value={tarifa.tarifa_noche_clp} onChange={(e) => setTarifa({ ...tarifa, tarifa_noche_clp: e.target.value })} />
          <button type="submit" className="boton-primario">Guardar tarifa</button>
        </form>
      </section>
      {claveUsada && <p className="nota-clave">Clave de idempotencia: <code>{claveUsada}</code></p>}
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
