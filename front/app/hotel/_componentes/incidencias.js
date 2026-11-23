'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError } from '../../../lib/api'
import { fotoLigera } from '../../../lib/imagen'
import { ETIQUETA_ESTADO_INCIDENCIA, ETIQUETA_GRAVEDAD, etiqueta } from '../../../lib/operacion-etiquetas'

const GRAVEDADES = Object.entries(ETIQUETA_GRAVEDAD)

function clave(prefijo) {
  return `${prefijo}-${crypto.randomUUID().slice(0, 12)}`
}

/** #415: reporte rápido desde el móvil, con foto y bloqueo opcional de la habitación. */
export function ReporteIncidencia({ habitacionId, alGuardar }) {
  const [habitacion, setHabitacion] = useState(habitacionId || '')
  const [descripcion, setDescripcion] = useState('')
  const [gravedad, setGravedad] = useState('media')
  const [bloquea, setBloquea] = useState(false)
  const [foto, setFoto] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    if (descripcion.trim().length < 3) return setError('Describe el problema (mínimo 3 caracteres).')
    if (!habitacion.trim()) return setError('Indica la habitación.')
    setEnviando(true)
    try {
      const r = await api('/hotel/incidencias', {
        metodo: 'POST',
        claveIdempotencia: clave('inc'),
        cuerpo: { habitacion_id: habitacion.trim(), descripcion: descripcion.trim(), gravedad, bloquea_disponibilidad: bloquea },
      })
      if (r.estado >= 400) return setError(mensajeDeError(r.datos, r.estado))
      let mensaje = `Incidencia ${r.datos.incidencia_id} registrada.`
      if (foto) {
        try {
          const contenido = await fotoLigera(foto)
          const f = await api(`/hotel/incidencias/${r.datos.incidencia_id}/evidencias`, {
            metodo: 'POST',
            claveIdempotencia: clave('evd'),
            cuerpo: { mime: 'image/jpeg', contenido_base64: contenido },
          })
          if (f.estado >= 400) mensaje += ` La foto no se pudo subir: ${mensajeDeError(f.datos, f.estado)}`
        } catch {
          mensaje += ' La foto no se pudo procesar; la incidencia quedó sin foto.'
        }
      }
      if (r.datos.bloqueo_activo) mensaje += ' La habitación quedó fuera de la venta.'
      setAviso(mensaje)
      setDescripcion('')
      setBloquea(false)
      setFoto(null)
      alGuardar?.()
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={enviar} aria-label="Reportar incidencia" data-reporte-incidencia>
      <h3 className="subtitulo">Reportar incidencia</h3>
      {!habitacionId && (
        <label className="campo">
          <span className="campo-etiqueta">Habitación</span>
          <input className="entrada" value={habitacion} onChange={(e) => setHabitacion(e.target.value)} placeholder="HAB-01" />
        </label>
      )}
      <label className="campo">
        <span className="campo-etiqueta">¿Qué pasó?</span>
        <textarea className="entrada" rows={3} maxLength={1000} value={descripcion} onChange={(e) => setDescripcion(e.target.value)} />
      </label>
      <label className="campo">
        <span className="campo-etiqueta">Gravedad</span>
        <select className="entrada" value={gravedad} onChange={(e) => setGravedad(e.target.value)}>
          {GRAVEDADES.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
        </select>
      </label>
      <label className="campo">
        <span className="campo-etiqueta">Foto (opcional)</span>
        <input className="entrada" type="file" accept="image/*" capture="environment" onChange={(e) => setFoto(e.target.files?.[0] || null)} />
      </label>
      <label className="campo-check">
        <input type="checkbox" checked={bloquea} onChange={(e) => setBloquea(e.target.checked)} />
        Bloquear la habitación para la venta
      </label>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      <button type="submit" className="boton-primario" disabled={enviando}>{enviando ? 'Enviando…' : 'Registrar incidencia'}</button>
    </form>
  )
}

/** #415: incidencias abiertas (de una habitación o de todo el hotel) con cierre para recepción y administración. */
export function ListaIncidencias({ habitacionId, puedeCerrar, version }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')

  const cargar = useCallback(async () => {
    const q = new URLSearchParams({ estado: 'abiertas' })
    if (habitacionId) q.set('habitacion_id', habitacionId)
    try {
      const r = await api(`/hotel/incidencias?${q}`)
      if (r.estado === 200) setItems(r.datos.items)
      else setError(mensajeDeError(r.datos, r.estado))
    } catch {
      setError('No se pudo conectar con el servidor.')
    }
  }, [habitacionId])

  useEffect(() => {
    cargar()
  }, [cargar, version])

  async function cambiar(i, ruta, cuerpo) {
    setError('')
    const r = await api(`/hotel/incidencias/${i.incidencia_id}/${ruta}`, { metodo: 'POST', claveIdempotencia: clave('inc'), cuerpo })
    if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
    else cargar()
  }

  return (
    <section className="tarjeta" aria-label="Incidencias abiertas" data-incidencias>
      <h3 className="subtitulo">Incidencias abiertas {items ? `(${items.length})` : ''}</h3>
      {error && <p role="alert" className="alerta">{error}</p>}
      {items && items.length === 0 && <p className="estado">Sin incidencias abiertas.</p>}
      <ul className="lista-simple">
        {(items || []).map((i) => (
          <li key={i.incidencia_id}>
            <strong>{i.habitacion_id || i.area}</strong> · {etiqueta(ETIQUETA_GRAVEDAD, i.gravedad)} · {etiqueta(ETIQUETA_ESTADO_INCIDENCIA, i.estado)}
            {i.bloqueo_activo && ' · bloquea la habitación'}
            {i.evidencias > 0 && ` · ${i.evidencias} foto${i.evidencias > 1 ? 's' : ''}`}
            <br />
            {i.descripcion}
            <div className="acciones-aseo">
              {i.estado === 'abierta' && (
                <button type="button" className="boton-fantasma" onClick={() => cambiar(i, 'actualizacion', { estado: 'en_curso' })}>
                  En curso
                </button>
              )}
              {puedeCerrar && (
                <button type="button" className="boton-secundario" onClick={() => cambiar(i, 'cierre', {})}>Cerrar</button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
