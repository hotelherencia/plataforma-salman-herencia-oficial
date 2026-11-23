'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError } from '../../../lib/api'
import { ETIQUETA_AREA, ETIQUETA_PRIORIDAD, etiqueta, progresoSubtareas } from '../../../lib/operacion-etiquetas'

const AREAS = Object.entries(ETIQUETA_AREA)
const PRIORIDADES = Object.entries(ETIQUETA_PRIORIDAD)

function clave(prefijo) {
  return `${prefijo}-${crypto.randomUUID().slice(0, 12)}`
}

/** #416: tareas con checklist; la tarea no se cierra hasta marcar las subtareas obligatorias. */
export function Checklists({ habitacionId, puedeCrear }) {
  const [items, setItems] = useState(null)
  const [plantillas, setPlantillas] = useState([])
  const [error, setError] = useState('')
  const [nueva, setNueva] = useState({ titulo: '', area: 'general', plantilla_id: '' })

  const cargar = useCallback(async () => {
    const q = new URLSearchParams({ estado: 'pendiente' })
    if (habitacionId) q.set('habitacion_id', habitacionId)
    try {
      const [t, p] = await Promise.all([api(`/hotel/tareas?${q}`), api('/hotel/checklists/plantillas')])
      if (t.estado === 200) setItems(t.datos.items)
      else setError(mensajeDeError(t.datos, t.estado))
      if (p.estado === 200) setPlantillas(p.datos.items)
    } catch {
      setError('No se pudo conectar con el servidor.')
    }
  }, [habitacionId])

  useEffect(() => {
    cargar()
  }, [cargar])

  async function enviar(ruta, cuerpo) {
    setError('')
    const r = await api(ruta, { metodo: 'POST', claveIdempotencia: clave('tar'), cuerpo })
    if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
    else cargar()
    return r
  }

  const marcar = (t, s) => enviar(`/hotel/tareas/${t.tarea_id}/subtareas/${s.subtarea_id}/marcado`, { hecha: !s.hecha })
  const cerrar = (t) => enviar(`/hotel/tareas/${t.tarea_id}/cierre`, {})
  async function crear(e) {
    e.preventDefault()
    if (nueva.titulo.trim().length < 2) return setError('Escribe el título de la tarea.')
    const r = await enviar('/hotel/tareas', {
      titulo: nueva.titulo.trim(), area: nueva.area, habitacion_id: habitacionId || null,
      plantilla_id: nueva.plantilla_id || null,
    })
    if (r.estado < 400) setNueva({ titulo: '', area: 'general', plantilla_id: '' })
  }

  return (
    <section className="tarjeta" aria-label="Tareas y checklists" data-checklists>
      <h3 className="subtitulo">Tareas y checklists {items ? `(${items.length})` : ''}</h3>
      {error && <p role="alert" className="alerta">{error}</p>}
      {items && items.length === 0 && <p className="estado">Sin tareas pendientes.</p>}
      <ul className="lista-simple">
        {(items || []).map((t) => (
          <li key={t.tarea_id}>
            <strong>{t.titulo}</strong> · {etiqueta(ETIQUETA_PRIORIDAD, t.prioridad)}{t.vence ? ` · vence ${t.vence}` : ''}{t.responsable ? ` · ${t.responsable}` : ''}
            {t.progreso.total > 0 && ` · ${progresoSubtareas(t.subtareas).hechas}/${t.progreso.total}`}
            <ul className="lista-simple">
              {t.subtareas.map((s) => (
                <li key={s.subtarea_id}>
                  <label className="campo-check">
                    <input type="checkbox" checked={s.hecha} onChange={() => marcar(t, s)} />
                    {s.texto}{s.obligatoria ? '' : ' (opcional)'}
                  </label>
                </li>
              ))}
            </ul>
            {puedeCrear && (
              <div className="acciones-aseo">
                <select className="entrada" aria-label={`Prioridad de ${t.titulo}`} value={t.prioridad}
                  onChange={(e) => enviar(`/hotel/tareas/${t.tarea_id}/actualizacion`, { prioridad: e.target.value })}>
                  {PRIORIDADES.map(([v, x]) => <option key={v} value={v}>{x}</option>)}
                </select>
                <input className="entrada" aria-label={`Responsable de ${t.titulo}`} placeholder="Responsable"
                  defaultValue={t.responsable || ''}
                  onBlur={(e) => e.target.value.trim() && e.target.value.trim() !== (t.responsable || '') &&
                    enviar(`/hotel/tareas/${t.tarea_id}/actualizacion`, { responsable: e.target.value.trim() })} />
                <input className="entrada" aria-label={`Agregar subtarea a ${t.titulo}`} placeholder="Agregar subtarea y Enter"
                  onKeyDown={(e) => {
                    if (e.key !== 'Enter') return
                    e.preventDefault()
                    const texto = e.currentTarget.value.trim()
                    if (texto.length < 2) return
                    e.currentTarget.value = ''
                    enviar(`/hotel/tareas/${t.tarea_id}/subtareas`, { texto, obligatoria: true })
                  }} />
              </div>
            )}
            <button type="button" className="boton-secundario" disabled={t.obligatorias_pendientes > 0} onClick={() => cerrar(t)}>
              {t.obligatorias_pendientes > 0 ? `Faltan ${t.obligatorias_pendientes} obligatorias` : 'Completar tarea'}
            </button>
          </li>
        ))}
      </ul>
      {puedeCrear && (
        <form className="formulario" onSubmit={crear} aria-label="Nueva tarea">
          <label className="campo">
            <span className="campo-etiqueta">Nueva tarea</span>
            <input className="entrada" value={nueva.titulo} onChange={(e) => setNueva({ ...nueva, titulo: e.target.value })} />
          </label>
          <label className="campo">
            <span className="campo-etiqueta">Área</span>
            <select className="entrada" value={nueva.area} onChange={(e) => setNueva({ ...nueva, area: e.target.value })}>
              {AREAS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
            </select>
          </label>
          {plantillas.length > 0 && (
            <label className="campo">
              <span className="campo-etiqueta">Checklist</span>
              <select className="entrada" value={nueva.plantilla_id} onChange={(e) => setNueva({ ...nueva, plantilla_id: e.target.value })}>
                <option value="">Sin checklist</option>
                {plantillas.map((p) => <option key={p.plantilla_id} value={p.plantilla_id}>{p.nombre}</option>)}
              </select>
            </label>
          )}
          <button type="submit" className="boton-primario">Crear tarea</button>
        </form>
      )}
    </section>
  )
}
