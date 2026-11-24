'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'
import { api, mensajeDeError, useSesion } from '../../lib/api'
import { gestionaRecepcion } from '../../lib/roles'

/* HerencIA — Copiloto operativo interno en solo lectura: ve disponibilidad actual, pendientes
   del día, guías por pantalla y ayuda a redactar mensajes o reportes (sin exponer PII al modelo). */

export function visibleAsistente(ruta, sesion) {
  return Boolean(ruta && ruta.startsWith('/hotel') && sesion?.fase === 'ok' && gestionaRecepcion(sesion.usuario?.rol))
}

export function sugerenciasParaRuta(ruta) {
  const seccion = (ruta || '').split('/')[2] || ''
  if (seccion === 'aseo') {
    return ['¿Qué incidencias siguen abiertas?', 'Ayúdame a redactar un reporte técnico', '¿Qué habitaciones faltan por limpiar?']
  }
  if (seccion === 'caja') {
    return ['¿Cómo hago el cierre de caja?', '¿Cómo se registran convenios en caja?', '¿Qué pide el borrador F29?']
  }
  if (seccion === 'reservas' || seccion === 'reserva') {
    return ['¿Qué habitaciones están disponibles ahora?', '¿Cómo hago un upgrade a tarifa Single?', '¿Cómo funciona la reserva provisoria de empresa?']
  }
  return ['¿Qué habitaciones están disponibles ahora?', 'Resumen operativo y pendientes de hoy', 'Ayúdame a redactar respuesta a un huésped']
}

function AvatarHerencIA() {
  return (
    <span className="ayuda-asistente__avatar" aria-hidden="true">
      <img src="/logo-herencia-hoja.svg" alt="" width={20} height={20} className="ayuda-asistente__hoja" />
    </span>
  )
}

export default function AsistenteAyuda() {
  const ruta = usePathname()
  const sesion = useSesion()
  const [abierto, setAbierto] = useState(false)
  const [pregunta, setPregunta] = useState('')
  const [mensajes, setMensajes] = useState([])
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  if (!visibleAsistente(ruta, sesion)) return null

  async function enviarPregunta(textoBruto) {
    const limpio = textoBruto.trim()
    if (limpio.length < 2 || cargando) return
    setCargando(true)
    setError('')
    const historial = mensajes.slice(-4)
    try {
      const r = await api('/hotel/asistente', {
        metodo: 'POST',
        cuerpo: { pregunta: limpio, ruta, historial },
      })
      if (r.estado === 200) {
        setMensajes((prev) => [...prev, { rol: 'usuario', texto: limpio }, { rol: 'asistente', texto: r.datos.respuesta }])
        setPregunta('')
      } else {
        setError(mensajeDeError(r.datos, r.estado))
      }
    } catch {
      setError('No pude consultar a HerencIA. Intenta de nuevo.')
    } finally {
      setCargando(false)
    }
  }

  function preguntar(e) {
    e.preventDefault()
    enviarPregunta(pregunta)
  }

  const chips = sugerenciasParaRuta(ruta)

  return (
    <aside className="ayuda-asistente" aria-label="HerencIA — Asistente del hotel">
      {abierto && (
        <div id="ayuda-asistente-panel" className="tarjeta ayuda-asistente__panel">
          <div className="ayuda-asistente__cabecera">
            <div className="ayuda-asistente__identidad">
              <AvatarHerencIA />
              <div>
                <strong className="ayuda-asistente__nombre">HerencIA</strong>
                <span className="ayuda-asistente__sub">Copiloto operativo del hotel</span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
              {mensajes.length > 0 && (
                <button
                  type="button"
                  className="boton-fantasma"
                  style={{ minHeight: '2rem', padding: '0.2rem 0.55rem', fontSize: '0.78rem' }}
                  onClick={() => { setMensajes([]); setError('') }}
                >
                  Limpiar
                </button>
              )}
              <button
                type="button"
                className="boton-fantasma ayuda-asistente__cerrar"
                aria-label="Cerrar HerencIA"
                onClick={() => setAbierto(false)}
              >
                ✕
              </button>
            </div>
          </div>
          <p className="ayuda-asistente__nota">
            Consulta disponibilidad actual, pendientes del turno, guías paso a paso o pide redactar mensajes y reportes.
          </p>
          {mensajes.length === 0 && (
            <div className="ayuda-asistente__chips" aria-label="Consultas rápidas">
              {chips.map((c) => (
                <button
                  key={c}
                  type="button"
                  className="ayuda-asistente__chip"
                  disabled={cargando}
                  onClick={() => enviarPregunta(c)}
                >
                  {c}
                </button>
              ))}
            </div>
          )}
          {mensajes.length > 0 && (
            <div className="ayuda-asistente__hilo" role="log" aria-live="polite">
              {mensajes.map((m, i) => (
                <p
                  key={i}
                  className={m.rol === 'usuario' ? 'ayuda-asistente__burbuja-user' : 'ayuda-asistente__respuesta'}
                >
                  {m.texto}
                </p>
              ))}
            </div>
          )}
          <form className="ayuda-asistente__form" onSubmit={preguntar}>
            <label className="campo">
              <span className="campo-etiqueta">¿En qué te ayudo?</span>
              <textarea
                className="entrada"
                rows={2}
                maxLength={500}
                value={pregunta}
                placeholder="Ej.: ¿Qué habitaciones quedan libres hoy? o redacta una respuesta…"
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
