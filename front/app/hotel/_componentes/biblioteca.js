'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError } from '../../../lib/api'

const CATEGORIAS = [
  ['manual', 'Manual'],
  ['instructivo', 'Instructivo'],
  ['politica', 'Política'],
  ['otro', 'Otro'],
]
const NOMBRE = Object.fromEntries(CATEGORIAS)
const ROLES = [
  ['recepcion', 'Recepción'],
  ['caja', 'Caja'],
  ['aseo', 'Aseo'],
  ['admin_hotel', 'Administración'],
]

function clave(prefijo) {
  return `${prefijo}-${crypto.randomUUID().slice(0, 12)}`
}

/** #418: biblioteca por rol y buzón de sugerencias. `puedeAdministrar` = administración del hotel. */
export default function Biblioteca({ puedeAdministrar = false }) {
  const [docs, setDocs] = useState(null)
  const [sugerencias, setSugerencias] = useState([])
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [abierto, setAbierto] = useState(null)
  const [texto, setTexto] = useState('')
  const [nuevo, setNuevo] = useState({ titulo: '', categoria: 'manual', contenido: '', enlace: '', roles: [] })

  const cargar = useCallback(async () => {
    try {
      const r = await api('/hotel/biblioteca')
      if (r.estado === 200) setDocs(r.datos.documentos)
      if (puedeAdministrar) {
        const s = await api('/hotel/sugerencias?estado=nueva')
        if (s.estado === 200) setSugerencias(s.datos.sugerencias)
      }
    } catch {
      /* bloque secundario */
    }
  }, [puedeAdministrar])

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

  if (docs === null) return null
  return (
    <section className="tarjeta" aria-label="Biblioteca y sugerencias" data-biblioteca>
      <h2>Biblioteca del personal</h2>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      {docs.length === 0 && <p className="estado">Aún no hay documentos para tu rol.</p>}
      <ul className="lista-simple">
        {docs.map((d) => (
          <li key={d.id}>
            <strong>{d.titulo}</strong> <span className="estado-pct">{NOMBRE[d.categoria]}</span>{' '}
            {d.contenido && (
              <button type="button" className="boton-fantasma" onClick={() => setAbierto(abierto === d.id ? null : d.id)}>
                {abierto === d.id ? 'Cerrar' : 'Leer'}
              </button>
            )}
            {d.enlace && <a href={d.enlace} target="_blank" rel="noopener noreferrer">Abrir enlace</a>}
            {puedeAdministrar && (
              <button type="button" className="boton-fantasma" onClick={() => enviar(`/hotel/biblioteca/${d.id}/archivo`, {}, 'arc', 'Documento archivado.')}>Archivar</button>
            )}
            {abierto === d.id && <p style={{ whiteSpace: 'pre-wrap' }}>{d.contenido}</p>}
          </li>
        ))}
      </ul>

      <form
        className="formulario"
        onSubmit={async (e) => {
          e.preventDefault()
          if (texto.trim().length < 3) return setError('Escribe tu sugerencia.')
          if (await enviar('/hotel/sugerencias', { texto: texto.trim() }, 'sug', 'Gracias: tu sugerencia llegó a la administración.')) setTexto('')
        }}
      >
        <h3 className="subtitulo">Buzón de sugerencias</h3>
        <label className="campo">¿Qué mejorarías?
          <textarea value={texto} maxLength={1000} rows={2} onChange={(e) => setTexto(e.target.value)} />
        </label>
        <button type="submit" className="boton-primario">Enviar sugerencia</button>
      </form>

      {puedeAdministrar && sugerencias.length > 0 && (
        <div data-sugerencias>
          <h3 className="subtitulo">Sugerencias nuevas ({sugerencias.length})</h3>
          <ul className="lista-simple">
            {sugerencias.map((s) => (
              <li key={s.id}>
                <strong>{s.autor}</strong>: {s.texto}{' '}
                <button type="button" className="boton-fantasma" onClick={() => enviar(`/hotel/sugerencias/${s.id}/atencion`, {}, 'ate', 'Sugerencia marcada como atendida.')}>
                  Marcar atendida
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {puedeAdministrar && (
        <form
          className="formulario"
          onSubmit={async (e) => {
            e.preventDefault()
            const cuerpo = { titulo: nuevo.titulo.trim(), categoria: nuevo.categoria, contenido: nuevo.contenido.trim(), roles: nuevo.roles }
            if (nuevo.enlace.trim()) cuerpo.enlace = nuevo.enlace.trim()
            if (await enviar('/hotel/biblioteca', cuerpo, 'doc', 'Documento publicado.')) setNuevo({ titulo: '', categoria: 'manual', contenido: '', enlace: '', roles: [] })
          }}
        >
          <h3 className="subtitulo">Publicar documento</h3>
          <label className="campo">Título
            <input value={nuevo.titulo} maxLength={120} onChange={(e) => setNuevo({ ...nuevo, titulo: e.target.value })} />
          </label>
          <label className="campo">Tipo
            <select value={nuevo.categoria} onChange={(e) => setNuevo({ ...nuevo, categoria: e.target.value })}>
              {CATEGORIAS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
            </select>
          </label>
          <label className="campo">Contenido
            <textarea value={nuevo.contenido} maxLength={20000} rows={4} onChange={(e) => setNuevo({ ...nuevo, contenido: e.target.value })} />
          </label>
          <label className="campo">Enlace seguro (https, opcional)
            <input value={nuevo.enlace} onChange={(e) => setNuevo({ ...nuevo, enlace: e.target.value })} />
          </label>
          <fieldset>
            <legend>Para (sin marcar = todo el personal)</legend>
            {ROLES.map(([valor, nombre]) => (
              <label key={valor} className="campo-check">
                <input type="checkbox" checked={nuevo.roles.includes(valor)} onChange={(e) => setNuevo({ ...nuevo, roles: e.target.checked ? [...nuevo.roles, valor] : nuevo.roles.filter((x) => x !== valor) })} />
                {nombre}
              </label>
            ))}
          </fieldset>
          <button type="submit" className="boton-primario">Publicar</button>
        </form>
      )}
    </section>
  )
}
