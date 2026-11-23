'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError } from '../../../lib/api'
import { fechaHora } from '../../../lib/formato'

const ROLES = [
  ['recepcion', 'Recepción'],
  ['caja', 'Caja'],
  ['aseo', 'Aseo'],
  ['admin_hotel', 'Administración'],
]

function clave(prefijo) {
  return `${prefijo}-${crypto.randomUUID().slice(0, 12)}`
}

/** #418: comunicados internos con confirmación de lectura. `puedePublicar` = administración. */
export default function Comunicados({ puedePublicar = false }) {
  const [lista, setLista] = useState(null)
  const [error, setError] = useState('')
  const [titulo, setTitulo] = useState('')
  const [cuerpo, setCuerpo] = useState('')
  const [roles, setRoles] = useState([])
  const [lecturas, setLecturas] = useState({})

  const cargar = useCallback(async () => {
    try {
      const r = await api('/hotel/comunicados')
      if (r.estado === 200) setLista(r.datos)
    } catch {
      /* el bloque es secundario: sin red, no se muestra */
    }
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar])

  async function accion(ruta, prefijo) {
    setError('')
    const r = await api(ruta, { metodo: 'POST', claveIdempotencia: clave(prefijo), cuerpo: {} })
    if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
    await cargar()
  }

  async function publicar(e) {
    e.preventDefault()
    setError('')
    if (titulo.trim().length < 3 || cuerpo.trim().length < 3) return setError('Escribe un título y un mensaje.')
    const r = await api('/hotel/comunicados', {
      metodo: 'POST',
      claveIdempotencia: clave('com'),
      cuerpo: { titulo: titulo.trim(), cuerpo: cuerpo.trim(), roles },
    })
    if (r.estado >= 400) return setError(mensajeDeError(r.datos, r.estado))
    setTitulo('')
    setCuerpo('')
    setRoles([])
    cargar()
  }

  async function verLecturas(id) {
    const r = await api(`/hotel/comunicados/${id}/lecturas`)
    if (r.estado === 200) setLecturas((l) => ({ ...l, [id]: r.datos }))
  }

  if (!lista || (lista.comunicados.length === 0 && !puedePublicar)) return null
  return (
    <section className="tarjeta" aria-label="Comunicados" data-comunicados>
      <h2>Comunicados {lista.sin_leer > 0 && <span className="insignia">{lista.sin_leer}</span>}</h2>
      {error && <p role="alert" className="alerta">{error}</p>}
      {lista.comunicados.length === 0 && <p className="estado">No hay comunicados vigentes.</p>}
      <ul className="lista-simple">
        {lista.comunicados.map((c) => (
          <li key={c.id}>
            <strong>{c.titulo}</strong> <span className="estado-pct">{fechaHora(c.creado_en)} · {c.creado_por}</span>
            <p>{c.cuerpo}</p>
            {c.leido ? (
              <span className="estado">Leído</span>
            ) : (
              <button type="button" className="boton-primario" onClick={() => accion(`/hotel/comunicados/${c.id}/lectura`, 'lec')}>
                Confirmar lectura
              </button>
            )}
            {puedePublicar && (
              <>
                {' '}
                <button type="button" className="boton-fantasma" onClick={() => verLecturas(c.id)}>Quién lo leyó</button>
                <button type="button" className="boton-fantasma" onClick={() => accion(`/hotel/comunicados/${c.id}/archivo`, 'arc')}>Archivar</button>
                {lecturas[c.id] && (
                  <p className="estado" data-lecturas>
                    Leyeron: {lecturas[c.id].leyeron.map((x) => x.usuario).join(', ') || 'nadie aún'}.
                    {' '}Faltan: {lecturas[c.id].faltan.map((x) => x.usuario).join(', ') || 'nadie'}.
                  </p>
                )}
              </>
            )}
          </li>
        ))}
      </ul>
      {puedePublicar && (
        <form className="formulario" onSubmit={publicar}>
          <h3 className="subtitulo">Nuevo comunicado</h3>
          <label className="campo">Título
            <input value={titulo} maxLength={120} onChange={(e) => setTitulo(e.target.value)} />
          </label>
          <label className="campo">Mensaje
            <textarea value={cuerpo} maxLength={4000} rows={3} onChange={(e) => setCuerpo(e.target.value)} />
          </label>
          <fieldset>
            <legend>Para (sin marcar = todo el personal)</legend>
            {ROLES.map(([valor, texto]) => (
              <label key={valor} className="campo-check">
                <input
                  type="checkbox"
                  checked={roles.includes(valor)}
                  onChange={(e) => setRoles(e.target.checked ? [...roles, valor] : roles.filter((x) => x !== valor))}
                />
                {texto}
              </label>
            ))}
          </fieldset>
          <button type="submit" className="boton-primario">Publicar</button>
        </form>
      )}
    </section>
  )
}
