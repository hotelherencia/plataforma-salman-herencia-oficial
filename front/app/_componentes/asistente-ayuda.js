'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'
import { api, mensajeDeError, useSesion } from '../../lib/api'
import { gestionaRecepcion } from '../../lib/roles'

/* Ayuda del sistema, solo lectura: explica pantallas y políticas, no ejecuta nada y no ve reservas,
   huéspedes ni caja. Aparece únicamente en /hotel para recepción y administración. */

export function visibleAsistente(ruta, sesion) {
  return Boolean(ruta && ruta.startsWith('/hotel') && sesion?.fase === 'ok' && gestionaRecepcion(sesion.usuario?.rol))
}

export default function AsistenteAyuda() {
  const ruta = usePathname()
  const sesion = useSesion()
  const [abierto, setAbierto] = useState(false)
  const [pregunta, setPregunta] = useState('')
  const [respuesta, setRespuesta] = useState('')
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  if (!visibleAsistente(ruta, sesion)) return null

  async function preguntar(e) {
    e.preventDefault()
    if (pregunta.trim().length < 2 || cargando) return
    setCargando(true)
    setError('')
    setRespuesta('')
    try {
      const r = await api('/hotel/asistente', { metodo: 'POST', cuerpo: { pregunta: pregunta.trim() } })
      if (r.estado === 200) setRespuesta(r.datos.respuesta)
      else setError(mensajeDeError(r.datos, r.estado))
    } catch {
      setError('No pude consultar la ayuda. Intenta de nuevo.')
    } finally {
      setCargando(false)
    }
  }

  return (
    <aside className="ayuda-asistente" aria-label="Ayuda del sistema">
      <button type="button" className="boton ayuda-asistente__boton" aria-expanded={abierto}
        aria-controls="ayuda-asistente-panel" onClick={() => setAbierto((v) => !v)}>
        {abierto ? 'Cerrar ayuda' : 'Ayuda'}
      </button>
      {abierto && (
        <div id="ayuda-asistente-panel" className="tarjeta ayuda-asistente__panel">
          <p className="nota">Solo explica cómo usar el sistema y las políticas. No ve reservas ni datos de huéspedes.</p>
          <form onSubmit={preguntar}>
            <label>
              ¿Qué necesitas saber?
              <textarea rows={3} maxLength={500} value={pregunta} onChange={(e) => setPregunta(e.target.value)} />
            </label>
            <button type="submit" className="boton" disabled={cargando}>{cargando ? 'Consultando…' : 'Preguntar'}</button>
          </form>
          {error && <p role="alert" className="alerta">{error}</p>}
          {respuesta && <p role="status" className="ayuda-asistente__respuesta">{respuesta}</p>}
        </div>
      )}
    </aside>
  )
}
