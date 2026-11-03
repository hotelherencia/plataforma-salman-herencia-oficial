'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, SalidaJson, Campo, useClaveOperacion, useSesion } from '../../../lib/api'
import { InventarioHabitaciones, InventarioVacio } from '../_componentes/inventario-habitaciones'

export default function Habitaciones() {
  const sesion = useSesion()
  const [habitaciones, setHabitaciones] = useState(null)
  const [alta, setAlta] = useState({ habitacion_id: '', tipo: 'doble', capacidad: 2 })
  const [tarifa, setTarifa] = useState({ habitacion_id: '', fecha_desde: '', fecha_hasta: '', tarifa_noche_clp: 50000 })
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [claveAlta, renovarClaveAlta] = useClaveOperacion()
  const [claveTarifa, renovarClaveTarifa] = useClaveOperacion()
  const [claveLimpieza, renovarClaveLimpieza] = useClaveOperacion()
  const [claveMantenimiento, renovarClaveMantenimiento] = useClaveOperacion()

  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const esAdmin = rol === 'administrador'

  const cargarInventario = useCallback(async () => {
    try {
      const r = await api('/hotel/habitaciones')
      if (r.estado === 200) setHabitaciones(r.datos.habitaciones)
      else setHabitaciones([])
    } catch {
      setHabitaciones([])
    }
  }, [])

  useEffect(() => {
    if (sesion.fase === 'ok') cargarInventario()
  }, [sesion.fase, cargarInventario])

  async function postear(ruta, cuerpo, clave, alExito, e, metodo = 'POST') {
    e.preventDefault()
    setError('')
    setSalida(null)
    try {
      const r = await api(ruta, { metodo, cuerpo, claveIdempotencia: clave })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setSalida(r.datos)
        alExito()
        cargarInventario()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  async function accionInventario(ruta, cuerpo, clave, renovar) {
    setError('')
    setSalida(null)
    try {
      const r = await api(ruta, { metodo: 'POST', cuerpo, claveIdempotencia: clave })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setSalida(r.datos)
        renovar()
        cargarInventario()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  const limpiar = (habitacionId) =>
    accionInventario(`/hotel/habitaciones/${habitacionId}/limpieza`, {}, claveLimpieza, renovarClaveLimpieza)
  const cambiarMantenimiento = (habitacionId, abrir) =>
    accionInventario(`/hotel/habitaciones/${habitacionId}/mantenimiento`, { abierto: abrir }, claveMantenimiento, renovarClaveMantenimiento)

  return (
    <MarcoHotel titulo="Habitaciones, tarifas y operación">
      <section className="tarjeta">
        <h2>Inventario de habitaciones</h2>
        {habitaciones === null ? (
          <p className="estado">Cargando inventario…</p>
        ) : habitaciones.length === 0 ? (
          <InventarioVacio />
        ) : (
          <InventarioHabitaciones
            habitaciones={habitaciones}
            rol={rol}
            alLimpiar={limpiar}
            alCambiarMantenimiento={cambiarMantenimiento}
          />
        )}
        {(rol === 'recepcion' || esAdmin) && (
          <p className="nota-clave nota-tecnica">
            Claves de operación (reintenta con la misma para no duplicar) — limpieza: <code>{claveLimpieza}</code>
            {esAdmin && <> · mantenimiento: <code>{claveMantenimiento}</code></>}
          </p>
        )}
      </section>

      {esAdmin && (
        <>
          <section className="tarjeta">
            <h2>Alta o cambio de habitación</h2>
            <form
              className="formulario"
              onSubmit={(e) =>
                postear(`/hotel/habitaciones/${alta.habitacion_id}`, { tipo: alta.tipo, capacidad: Number(alta.capacidad) }, claveAlta, renovarClaveAlta, e, 'PUT')
              }
            >
              <Campo etiqueta="Habitación" value={alta.habitacion_id} onChange={(e) => setAlta({ ...alta, habitacion_id: e.target.value })} />
              <Campo etiqueta="Tipo" value={alta.tipo} onChange={(e) => setAlta({ ...alta, tipo: e.target.value })} />
              <Campo etiqueta="Capacidad" type="number" min="1" value={alta.capacidad} onChange={(e) => setAlta({ ...alta, capacidad: e.target.value })} />
              <button type="submit" className="boton-primario">Guardar habitación</button>
            </form>
            <p className="nota-clave nota-tecnica">Clave: <code>{claveAlta}</code></p>
          </section>

          <section className="tarjeta">
            <h2>Tarifa por fecha</h2>
            <form
              className="formulario"
              onSubmit={(e) =>
                postear(
                  '/hotel/tarifas',
                  {
                    habitacion_id: tarifa.habitacion_id,
                    fecha_desde: tarifa.fecha_desde,
                    fecha_hasta: tarifa.fecha_hasta,
                    tarifa_noche_clp: Number(tarifa.tarifa_noche_clp),
                  },
                  claveTarifa,
                  renovarClaveTarifa,
                  e,
                  'PUT'
                )
              }
            >
              <Campo etiqueta="Habitación" value={tarifa.habitacion_id} onChange={(e) => setTarifa({ ...tarifa, habitacion_id: e.target.value })} />
              <Campo etiqueta="Desde" type="date" value={tarifa.fecha_desde} onChange={(e) => setTarifa({ ...tarifa, fecha_desde: e.target.value })} />
              <Campo etiqueta="Hasta" type="date" value={tarifa.fecha_hasta} onChange={(e) => setTarifa({ ...tarifa, fecha_hasta: e.target.value })} />
              <Campo etiqueta="Tarifa por noche (CLP)" type="number" min="1" value={tarifa.tarifa_noche_clp} onChange={(e) => setTarifa({ ...tarifa, tarifa_noche_clp: e.target.value })} />
              <button type="submit" className="boton-primario">Guardar tarifa</button>
            </form>
            <p className="nota-clave nota-tecnica">Clave: <code>{claveTarifa}</code></p>
          </section>
        </>
      )}

      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
