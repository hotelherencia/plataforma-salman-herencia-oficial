'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'
import { api, mensajeDeError, useSesion } from '../../lib/api'
import { gestionaRecepcion } from '../../lib/roles'

/* HerencIA — Ayuda del sistema, solo lectura: explica pantallas y políticas, no ejecuta nada
   y no ve reservas, huéspedes ni caja. Aparece únicamente en /hotel para recepción y administración. */

export function visibleAsistente(ruta, sesion) {
  return Boolean(ruta && ruta.startsWith('/hotel') && sesion?.fase === 'ok' && gestionaRecepcion(sesion.usuario?.rol))
}

function AvatarHerencIA() {
  return (
    <span className="ayuda-asistente__avatar" aria-hidden="true">
      ✨
    </span>
  )
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
      setError('No pude consultar a HerencIA. Intenta de nuevo.')
    } finally {
      setCargando(false)
    }
  }

  return (
    <aside className="ayuda-asistente" aria-label="HerencIA — Ayuda del sistema">
      {abierto && (
        <div id="ayuda-asistente-panel" className="tarjeta ayuda-asistente__panel">
          <div className="ayuda-asistente__cabecera">
            <div className="ayuda-asistente__identidad">
              <AvatarHerencIA />
              <div>
                <strong className="ayuda-asistente__nombre">HerencIA</strong>
                <span className="ayuda-asistente__sub">Asistente del hotel</span>
              </div>
            </div>
            <button
              type="button"
              className="boton-fantasma ayuda-asistente__cerrar"
              aria-label="Cerrar HerencIA"
              onClick={() => setAbierto(false)}
            >
              ✕
            </button>
          </div>
          <p className="ayuda-asistente__nota">
            Solo explica cómo usar el sistema y las políticas. No ve reservas ni datos de huéspedes.
          </p>
          <form className="ayuda-asistente__form" onSubmit={preguntar}>
            <label className="campo">
              <span className="campo-etiqueta">¿Qué necesitas saber?</span>
              <textarea
                className="entrada"
                rows={3}
                maxLength={500}
                value={pregunta}
                placeholder="Ej.: ¿Cómo registro un convenio o un cierre de caja?"
                onChange={(e) => setPregunta(e.target.value)}
              />
            </label>
            <div className="ayuda-asistente__acciones">
              <button type="submit" className="boton-primario" disabled={cargando}>
                {cargando ? 'Pensando…' : 'Preguntar'}
              </button>
            </div>
          </form>
          {error && <p role="alert" className="alerta">{error}</p>}
          {respuesta && <p role="status" className="ayuda-asistente__respuesta">{respuesta}</p>}
        </div>
      )}
      <button
        type="button"
        className="ayuda-asistente__boton"
        aria-expanded={abierto}
        aria-controls="ayuda-asistente-panel"
        onClick={() => setAbierto((v) => !v)}
      >
        <AvatarHerencIA />
        <span>{abierto ? 'Cerrar HerencIA' : 'HerencIA'}</span>
      </button>
    </aside>
  )
}
