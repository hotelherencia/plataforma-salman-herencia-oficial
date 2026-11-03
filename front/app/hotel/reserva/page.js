'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, useClaveOperacion } from '../../../lib/api'

export default function Reserva() {
  // V1-ISSUE-35: sin defaults inválidos; si viene de la oferta u otra
  // pantalla, la query precarga habitación y fechas.
  const [campos, setCampos] = useState({
    habitacion_id: '',
    inicio: '',
    fin: '',
    nombre: '',
    documento: '',
  })

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setCampos((c) => ({
      ...c,
      habitacion_id: params.get('habitacion_id') || c.habitacion_id,
      inicio: params.get('inicio') || c.inicio,
      fin: params.get('fin') || c.fin,
    }))
  }, [])
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [clave, renovarClave] = useClaveOperacion()

  async function confirmar(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[campos.habitacion_id, 'Habitación'], [campos.inicio, 'Desde'], [campos.fin, 'Hasta'], [campos.nombre, 'Nombre del huésped']])
    if (falta) { setError(falta); return }
    try {
      const r = await api('/hotel/reservas', {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {
          habitacion_id: campos.habitacion_id,
          inicio: campos.inicio,
          fin: campos.fin,
          huesped: {
            nombre: campos.nombre,
            ...(campos.documento.trim() ? { documento: campos.documento.trim() } : {}),
          },
        },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave) // 4xx definitivo: clave nueva (V1-ISSUE-13)
      } else {
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
          <Campo etiqueta="Documento (opcional)" value={campos.documento} onChange={(e) => setCampos({ ...campos, documento: e.target.value })} />
          <button type="submit" className="boton-primario">Confirmar reserva</button>
        </form>
      </section>
      <p className="nota-clave">Clave de idempotencia (reintenta con la misma para no duplicar): <code>{clave}</code></p>
      <button onClick={nuevaOperacion} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
