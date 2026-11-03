'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, camposFaltantes, mensajeDeError, MarcoHotel, SalidaJson, Campo, useClaveOperacion, useSesion } from '../../../lib/api'
import { InventarioHabitaciones, InventarioVacio } from '../_componentes/inventario-habitaciones'

/**
 * Inventario y alta de habitaciones (spec-hotel-operacion-v1 §2). El alta
 * envía `If-None-Match: *`: si el id ya existe la API responde 409 y nada se
 * sobrescribe. Editar tipo/capacidad, registrar tarifas y retirar de
 * operación se hacen en la ficha de cada habitación (/hotel/habitaciones/[id]).
 */
export default function Habitaciones() {
  const sesion = useSesion()
  const [habitaciones, setHabitaciones] = useState(null)
  const [alta, setAlta] = useState({ habitacion_id: '', tipo: 'doble', capacidad: 2 })
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [claveAlta, renovarClaveAlta] = useClaveOperacion()
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

  async function darDeAlta(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[alta.habitacion_id, 'Habitación'], [alta.tipo, 'Tipo']])
    if (falta) return setError(falta)
    try {
      const r = await api(`/hotel/habitaciones/${encodeURIComponent(alta.habitacion_id.trim())}`, {
        metodo: 'PUT',
        cuerpo: { tipo: alta.tipo, capacidad: Number(alta.capacidad) },
        claveIdempotencia: claveAlta,
        cabeceras: { 'If-None-Match': '*' },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setSalida(r.datos)
        renovarClaveAlta()
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
        <p className="nota-clave">
          Abre la <strong>ficha</strong> de una habitación para ver sus tarifas, reservas e historial
          {esAdmin ? ', editar sus datos, registrar una tarifa nueva o retirarla de operación' : ''}.
        </p>
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
        <section className="tarjeta">
          <h2>Nueva habitación</h2>
          <p className="nota-clave">
            Solo crea: si el identificador ya existe se rechaza sin tocar la habitación. Nace disponible y limpia, y no
            se ofrece hasta que tenga tarifa (regístrala en su ficha).
          </p>
          <form className="formulario" onSubmit={darDeAlta}>
            <Campo etiqueta="Habitación" value={alta.habitacion_id} placeholder="p. ej. HAB-201" onChange={(e) => setAlta({ ...alta, habitacion_id: e.target.value })} />
            <Campo etiqueta="Tipo" value={alta.tipo} onChange={(e) => setAlta({ ...alta, tipo: e.target.value })} />
            <Campo etiqueta="Capacidad" type="number" min="1" max="30" value={alta.capacidad} onChange={(e) => setAlta({ ...alta, capacidad: e.target.value })} />
            <button type="submit" className="boton-primario">Dar de alta</button>
          </form>
          <p className="nota-clave nota-tecnica">Clave: <code>{claveAlta}</code></p>
        </section>
      )}

      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
