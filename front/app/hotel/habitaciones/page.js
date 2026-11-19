'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, alRechazar, camposFaltantes, mensajeDeError, MarcoHotel, SalidaJson, Campo, useClaveOperacion, useSesion } from '../../../lib/api'
import { InventarioHabitaciones, InventarioVacio } from '../_componentes/inventario-habitaciones'
import { esAdminHotel, gestionaRecepcion } from '../../../lib/roles'

/**
 * Inventario y alta de habitaciones (spec-hotel-operacion-v1 §2). El alta
 * envía `If-None-Match: *`: si el id ya existe la API responde 409 y nada se
 * sobrescribe. Editar tipo/capacidad y retirar de operación se hacen en la
 * ficha de cada habitación (/hotel/habitaciones/[id]). Los precios se definen
 * solo en «Tipos, habitaciones y precios» (/hotel/tipos, entrega 1A.2).
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
  const esAdmin = esAdminHotel(rol)

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
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClaveAlta)
      }
      else {
        setSalida(r.datos)
        renovarClaveAlta()
        cargarInventario()
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  async function accionInventario(ruta, cuerpo, clave, renovar) {
    setError('')
    setSalida(null)
    try {
      const r = await api(ruta, { metodo: 'POST', cuerpo, claveIdempotencia: clave })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovar)
      } else {
        setSalida(r.datos)
        renovar()
        cargarInventario()
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  const limpiar = (habitacionId) =>
    accionInventario(`/hotel/habitaciones/${habitacionId}/limpieza`, {}, claveLimpieza, renovarClaveLimpieza)
  // #349: abrir mantenimiento pide el rango; solo en esas fechas sale del cupo.
  const [pedirMant, setPedirMant] = useState(null)
  const cambiarMantenimiento = (habitacionId, abrir) => {
    if (abrir) {
      setPedirMant({ habitacion_id: habitacionId, desde: new Date().toLocaleDateString('sv-SE'), hasta: '' })
      return
    }
    accionInventario(`/hotel/habitaciones/${habitacionId}/mantenimiento`, { abierto: false }, claveMantenimiento, renovarClaveMantenimiento)
  }
  function confirmarMantenimiento(e) {
    e.preventDefault()
    const { habitacion_id, desde, hasta } = pedirMant
    if (!desde) { setError('Indica desde cuándo rige el mantenimiento.'); return }
    if (hasta && hasta <= desde) { setError('«Hasta» debe ser posterior a «Desde».'); return }
    accionInventario(
      `/hotel/habitaciones/${habitacion_id}/mantenimiento`,
      { abierto: true, desde, ...(hasta ? { hasta } : {}) },
      claveMantenimiento,
      renovarClaveMantenimiento,
    )
    setPedirMant(null)
  }

  return (
    <MarcoHotel titulo="Estado de habitaciones">
      {pedirMant && (
        <section className="tarjeta">
          <form className="formulario" onSubmit={confirmarMantenimiento} aria-label="Abrir mantenimiento">
            <h2>Mantenimiento de {pedirMant.habitacion_id}</h2>
            <Campo etiqueta="Desde" type="date" value={pedirMant.desde} onChange={(e) => setPedirMant({ ...pedirMant, desde: e.target.value })} />
            <Campo etiqueta="Hasta (sin incluir; vacío = solo hasta hoy)" type="date" value={pedirMant.hasta} onChange={(e) => setPedirMant({ ...pedirMant, hasta: e.target.value })} />
            <p className="nota-clave">La habitación sale de la venta solo en esas fechas; fuera de ellas sigue disponible. La limpieza nunca la quita de la venta.</p>
            <button type="submit" className="boton-primario">Abrir mantenimiento</button>
            <button type="button" className="boton-fantasma" onClick={() => setPedirMant(null)}>Cancelar</button>
          </form>
        </section>
      )}
      <section className="tarjeta">
        <h2>Inventario de habitaciones</h2>
        <p className="nota-clave">
          Abre la <strong>ficha</strong> de una habitación para ver su precio, reservas e historial
          {esAdmin ? ', editar sus datos o retirarla de operación' : ''}. Los precios se cambian en{' '}
          <a href="/hotel/tipos">Tipos, habitaciones y precios</a>.
        </p>
        {habitaciones === null ? (
          <p className="estado" role="status" aria-busy="true">Cargando inventario…</p>
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
        {gestionaRecepcion(rol) && (
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
            Solo crea: si el identificador ya existe se rechaza sin tocar la habitación. Nace disponible y limpia, y
            cotiza con el precio base de su tipo (o queda sin precio si el tipo no lo tiene). Para crear varias de una
            vez, usa <a href="/hotel/tipos">Tipos, habitaciones y precios</a>.
          </p>
          <form className="formulario" onSubmit={darDeAlta}>
            <Campo etiqueta="Habitación" value={alta.habitacion_id} placeholder="p. ej. HAB-201" onChange={(e) => setAlta({ ...alta, habitacion_id: e.target.value })} />
            <Campo etiqueta="Tipo" value={alta.tipo} onChange={(e) => setAlta({ ...alta, tipo: e.target.value })} />
            <Campo etiqueta="Capacidad" type="number" min="1" max="30" value={alta.capacidad} onChange={(e) => setAlta({ ...alta, capacidad: e.target.value })} />
            <button type="submit" className="boton-primario">Dar de alta</button>
          </form>
          <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveAlta}</code></span>
        </section>
      )}

      <button onClick={() => { setSalida(null); setError(''); renovarClaveAlta(); renovarClaveLimpieza(); renovarClaveMantenimiento() }} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
