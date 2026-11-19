'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, useClaveOperacion } from '../../../lib/api'
import Subnav from '../_componentes/subnav'
import { CampoDocumento, SelectorUnidad } from '../_componentes/campos-recepcion'
import { validarDocumento } from '../../../lib/documento'
import { SUBNAV_RESERVAS } from '../../../lib/menu-hotel'

export default function Reserva() {
  // V1-ISSUE-35: sin defaults inválidos; si viene de la oferta u otra
  // pantalla, la query precarga habitación y fechas.
  const [campos, setCampos] = useState({
    habitacion_id: '',
    inicio: '',
    fin: '',
    hora_llegada: '',
    hora_salida: '',
    nombre: '',
    personas: '2',
    documento_tipo: 'rut',
    documento: '',
  })

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setCampos((c) => ({
      ...c,
      habitacion_id: params.get('habitacion_id') || c.habitacion_id,
      inicio: params.get('inicio') || c.inicio,
      fin: params.get('fin') || c.fin,
      hora_llegada: params.get('hora_llegada') || c.hora_llegada,
      hora_salida: params.get('hora_salida') || c.hora_salida,
    }))
  }, [])
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [clave, renovarClave] = useClaveOperacion()

  async function confirmar(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[campos.inicio, 'Desde'], [campos.fin, 'Hasta'], [campos.habitacion_id, 'Habitación'], [campos.nombre, 'Nombre del huésped']])
    if (falta) { setError(falta); return }
    // #367: el documento es obligatorio y se valida antes de enviar.
    const doc = validarDocumento(campos.documento_tipo, campos.documento)
    if (!doc.ok) { setError(doc.error); return }
    try {
      const r = await api('/hotel/reservas', {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {
          habitacion_id: campos.habitacion_id,
          inicio: campos.inicio,
          fin: campos.fin,
          personas: Number(campos.personas) || undefined,
          huesped: { nombre: campos.nombre, documento: doc.valor, documento_tipo: campos.documento_tipo },
          ...(campos.hora_llegada ? { hora_llegada: campos.hora_llegada } : {}),
          ...(campos.hora_salida ? { hora_salida: campos.hora_salida } : {}),
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
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  function nuevaOperacion() {
    setSalida(null)
    setError('')
    renovarClave()
  }

  return (
    <MarcoHotel titulo="Reservar">
      <Subnav items={SUBNAV_RESERVAS} />
      <section className="tarjeta">
        <form className="formulario" onSubmit={confirmar}>
          <Campo etiqueta="Desde" type="date" value={campos.inicio} onChange={(e) => setCampos({ ...campos, inicio: e.target.value })} />
          <Campo etiqueta="Hasta" type="date" value={campos.fin} onChange={(e) => setCampos({ ...campos, fin: e.target.value })} />
          <Campo etiqueta="Personas" type="number" min="1" max="30" value={campos.personas} onChange={(e) => setCampos({ ...campos, personas: e.target.value })} />
          <SelectorUnidad
            inicio={campos.inicio}
            fin={campos.fin}
            personas={campos.personas}
            valor={campos.habitacion_id}
            incluir={campos.habitacion_id || undefined}
            alCambiar={(id) => setCampos((c) => ({ ...c, habitacion_id: id }))}
          />
          <Campo etiqueta="Hora de llegada" type="time" value={campos.hora_llegada} onChange={(e) => setCampos({ ...campos, hora_llegada: e.target.value })} />
          <Campo etiqueta="Hora de salida" type="time" value={campos.hora_salida} onChange={(e) => setCampos({ ...campos, hora_salida: e.target.value })} />
          <Campo etiqueta="Huésped" value={campos.nombre} onChange={(e) => setCampos({ ...campos, nombre: e.target.value })} />
          <CampoDocumento
            tipo={campos.documento_tipo}
            numero={campos.documento}
            alCambiar={({ tipo, numero }) => setCampos((c) => ({ ...c, documento_tipo: tipo, documento: numero }))}
          />
          <button type="submit" className="boton-primario">Confirmar reserva</button>
        </form>
      </section>
      <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{clave}</code></span>
      <button onClick={nuevaOperacion} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
