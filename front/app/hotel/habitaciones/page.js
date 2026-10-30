'use client'

import { useState } from 'react'
import { api, MarcoHotel, SalidaJson, Campo, CampoSelect, useClaveOperacion } from '../../../lib/api'

export default function Habitaciones() {
  const [hab, setHab] = useState({ habitacion_id: 'HAB-101', tipo: 'doble', capacidad: '2' })
  const [tarifa, setTarifa] = useState({
    habitacion_id: 'HAB-101',
    fecha_desde: '2026-01-01',
    fecha_hasta: '2027-12-31',
    tarifa_noche_clp: '50000',
  })
  const [limpiezaId, setLimpiezaId] = useState('HAB-SINT-101')
  const [mantenimiento, setMantenimiento] = useState({ habitacion_id: 'HAB-SINT-101', abrir: 'true' })
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [claveHab, renovarClaveHab] = useClaveOperacion()
  const [claveTarifa, renovarClaveTarifa] = useClaveOperacion()
  const [claveLimpieza, renovarClaveLimpieza] = useClaveOperacion()
  const [claveMantenimiento, renovarClaveMantenimiento] = useClaveOperacion()

  async function enviar(ruta, cuerpo, clave, alExito, e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    try {
      const r = await api(ruta, { metodo: 'PUT', cuerpo, claveIdempotencia: clave })
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else {
        setSalida(r.datos)
        alExito()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  async function postear(ruta, cuerpo, clave, alExito, e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    try {
      const r = await api(ruta, { metodo: 'POST', cuerpo, claveIdempotencia: clave })
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else {
        setSalida(r.datos)
        alExito()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Habitaciones, tarifas y operación (administrador)">
      <section className="tarjeta">
        <h2>Alta o cambio de habitación</h2>
        <form className="formulario" onSubmit={(e) => enviar(`/hotel/habitaciones/${hab.habitacion_id}`, { tipo: hab.tipo, capacidad: Number(hab.capacidad) }, claveHab, renovarClaveHab, e)}>
          <Campo etiqueta="Habitación" value={hab.habitacion_id} onChange={(e) => setHab({ ...hab, habitacion_id: e.target.value })} />
          <Campo etiqueta="Tipo" value={hab.tipo} onChange={(e) => setHab({ ...hab, tipo: e.target.value })} />
          <Campo etiqueta="Capacidad" type="number" value={hab.capacidad} onChange={(e) => setHab({ ...hab, capacidad: e.target.value })} />
          <button type="submit" className="boton-primario">Guardar habitación</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveHab}</code></p>
      </section>
      <section className="tarjeta">
        <h2>Tarifa por fecha</h2>
        <form className="formulario" onSubmit={(e) => enviar('/hotel/tarifas', { ...tarifa, tarifa_noche_clp: Number(tarifa.tarifa_noche_clp) }, claveTarifa, renovarClaveTarifa, e)}>
          <Campo etiqueta="Habitación" value={tarifa.habitacion_id} onChange={(e) => setTarifa({ ...tarifa, habitacion_id: e.target.value })} />
          <Campo etiqueta="Desde" type="date" value={tarifa.fecha_desde} onChange={(e) => setTarifa({ ...tarifa, fecha_desde: e.target.value })} />
          <Campo etiqueta="Hasta" type="date" value={tarifa.fecha_hasta} onChange={(e) => setTarifa({ ...tarifa, fecha_hasta: e.target.value })} />
          <Campo etiqueta="Tarifa por noche (CLP)" type="number" value={tarifa.tarifa_noche_clp} onChange={(e) => setTarifa({ ...tarifa, tarifa_noche_clp: e.target.value })} />
          <button type="submit" className="boton-primario">Guardar tarifa</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveTarifa}</code></p>
      </section>
      <section className="tarjeta">
        <h2>Completar limpieza (recepción o administrador)</h2>
        <form className="formulario" onSubmit={(e) => postear(`/hotel/habitaciones/${limpiezaId}/limpieza`, {}, claveLimpieza, renovarClaveLimpieza, e)}>
          <Campo etiqueta="Habitación" value={limpiezaId} onChange={(e) => setLimpiezaId(e.target.value)} />
          <button type="submit" className="boton-primario">Completar limpieza</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveLimpieza}</code></p>
      </section>
      <section className="tarjeta">
        <h2>Mantenimiento (solo administrador)</h2>
        <form className="formulario" onSubmit={(e) => postear(`/hotel/habitaciones/${mantenimiento.habitacion_id}/mantenimiento`, { abierto: mantenimiento.abrir === 'true' }, claveMantenimiento, renovarClaveMantenimiento, e)}>
          <Campo etiqueta="Habitación" value={mantenimiento.habitacion_id} onChange={(e) => setMantenimiento({ ...mantenimiento, habitacion_id: e.target.value })} />
          <CampoSelect etiqueta="Estado" value={mantenimiento.abrir} onChange={(e) => setMantenimiento({ ...mantenimiento, abrir: e.target.value })}>
            <option value="true">Abrir mantenimiento</option>
            <option value="false">Cerrar mantenimiento</option>
          </CampoSelect>
          <button type="submit" className="boton-primario">Aplicar mantenimiento</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveMantenimiento}</code></p>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
