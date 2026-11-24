'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError } from '../../../lib/api'
import { fechaCorta } from '../../../lib/formato'

const CATEGORIAS = [
  ['mobiliario', 'Mobiliario'],
  ['electrico', 'Eléctrico'],
  ['climatizacion', 'Climatización'],
  ['sanitario', 'Sanitario'],
  ['electronico', 'Electrónico'],
  ['otro', 'Otro'],
]

function clave(prefijo) {
  return `${prefijo}-${crypto.randomUUID().slice(0, 12)}`
}

/** #418: mantenciones preventivas por vencer y alta de activos. `puedeGestionar` = recepción o administración. */
export default function Mantenciones({ puedeGestionar = false }) {
  const [lista, setLista] = useState(null)
  const [activos, setActivos] = useState([])
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [activo, setActivo] = useState({ habitacion_id: '', nombre: '', categoria: 'otro' })
  const [plan, setPlan] = useState({ activo_id: '', descripcion: '', cada_dias: '90' })

  const cargar = useCallback(async () => {
    try {
      const r = await api('/hotel/mantenciones?dentro_de_dias=14')
      if (r.estado === 200) setLista(r.datos.mantenciones)
      if (puedeGestionar) {
        const a = await api('/hotel/activos')
        if (a.estado === 200) setActivos(a.datos.activos)
      }
    } catch {
      /* bloque secundario */
    }
  }, [puedeGestionar])

  useEffect(() => {
    cargar()
  }, [cargar])

  async function enviar(ruta, cuerpo, prefijo, mensaje) {
    setError('')
    setAviso('')
    const r = await api(ruta, { metodo: 'POST', claveIdempotencia: clave(prefijo), cuerpo })
    if (r.estado >= 400) {
      setError(mensajeDeError(r.datos, r.estado))
      return false
    }
    setAviso(mensaje)
    await cargar()
    return true
  }

  if (lista === null || (lista.length === 0 && !puedeGestionar)) return null
  return (
    <section className="tarjeta" aria-label="Mantención preventiva" data-mantenciones>
      <h2>Mantención preventiva {lista.length > 0 && <span className="insignia">{lista.length}</span>}</h2>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      {lista.length === 0 && <p className="estado">Nada por vencer en los próximos 14 días.</p>}
      <ul className="lista-simple">
        {lista.map((m) => (
          <li key={m.plan_id}>
            {m.vencida ? <strong>Vencida</strong> : 'Vence'} {fechaCorta(m.proxima)} · {m.activo} ({m.habitacion_id || m.area}): {m.descripcion}{' '}
            <button type="button" className="boton-primario" onClick={() => enviar(`/hotel/mantenciones/${m.plan_id}/realizada`, {}, 'mre', 'Mantención registrada.')}>
              Marcar hecha hoy
            </button>
          </li>
        ))}
      </ul>
      {puedeGestionar && (
        <>
          <form
            className="formulario"
            onSubmit={async (e) => {
              e.preventDefault()
              if (activo.nombre.trim().length < 2 || !activo.habitacion_id.trim()) return setError('Indica la habitación y el nombre del activo.')
              if (await enviar('/hotel/activos', { habitacion_id: activo.habitacion_id.trim(), nombre: activo.nombre.trim(), categoria: activo.categoria }, 'act', 'Activo agregado.')) setActivo({ ...activo, nombre: '' })
            }}
          >
            <h3 className="subtitulo">Agregar activo a una habitación</h3>
            <label className="campo">Habitación
              <input value={activo.habitacion_id} onChange={(e) => setActivo({ ...activo, habitacion_id: e.target.value })} />
            </label>
            <label className="campo">Activo
              <input value={activo.nombre} maxLength={80} onChange={(e) => setActivo({ ...activo, nombre: e.target.value })} />
            </label>
            <label className="campo">Tipo
              <select value={activo.categoria} onChange={(e) => setActivo({ ...activo, categoria: e.target.value })}>
                {CATEGORIAS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
              </select>
            </label>
            <button type="submit" className="boton-primario">Agregar activo</button>
          </form>
          {activos.length > 0 && (
            <form
              className="formulario"
              onSubmit={async (e) => {
                e.preventDefault()
                if (!plan.activo_id || plan.descripcion.trim().length < 3) return setError('Elige el activo y describe la mantención.')
                if (await enviar(`/hotel/activos/${plan.activo_id}/plan`, { descripcion: plan.descripcion.trim(), cada_dias: Number(plan.cada_dias) }, 'mpl', 'Plan de mantención creado.')) setPlan({ ...plan, descripcion: '' })
              }}
            >
              <h3 className="subtitulo">Programar mantención periódica</h3>
              <label className="campo">Activo
                <select value={plan.activo_id} onChange={(e) => setPlan({ ...plan, activo_id: e.target.value })}>
                  <option value="">(elige)</option>
                  {activos.filter((a) => a.estado !== 'de_baja').map((a) => (
                    <option key={a.id} value={a.id}>{a.habitacion_id || a.area} · {a.nombre}</option>
                  ))}
                </select>
              </label>
              <label className="campo">Qué se hace
                <input value={plan.descripcion} maxLength={200} onChange={(e) => setPlan({ ...plan, descripcion: e.target.value })} />
              </label>
              <label className="campo">Cada cuántos días
                <input type="number" min="1" max="1830" value={plan.cada_dias} onChange={(e) => setPlan({ ...plan, cada_dias: e.target.value })} />
              </label>
              <button type="submit" className="boton-primario">Programar</button>
            </form>
          )}
        </>
      )}
    </section>
  )
}
