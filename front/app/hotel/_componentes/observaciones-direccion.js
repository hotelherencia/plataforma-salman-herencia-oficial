'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, useClaveOperacion } from '../../../lib/api'
import { fechaHora } from '../../../lib/formato'
import { esDueno } from '../../../lib/roles'

/* Observaciones del dueño a la administración. El dueño escribe y cierra; la administración
   responde. Nadie más las ve. Una sola lista y un solo formulario (sin botones por fila salvo el
   estado que corresponde a cada rol). */

const ESTADO = { abierta: 'abierta', respondida: 'respondida', cerrada: 'cerrada' }

export default function ObservacionesDireccion({ rol }) {
  const dueno = esDueno(rol)
  const [lista, setLista] = useState(null)
  const [texto, setTexto] = useState('')
  const [referencia, setReferencia] = useState('')
  const [respuestas, setRespuestas] = useState({})
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  const [clave, renovar] = useClaveOperacion()

  useEffect(() => {
    let vivo = true
    api('/hotel/observaciones').then((r) => { if (vivo && r.estado === 200) setLista(r.datos) }).catch(() => {})
    return () => { vivo = false }
  }, [version])

  async function enviar(ruta, cuerpo) {
    setError('')
    const r = await api(ruta, { metodo: 'POST', claveIdempotencia: clave, ...(cuerpo ? { cuerpo } : {}) })
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); alRechazar(r.estado, renovar); return false }
    renovar()
    setVersion((v) => v + 1)
    return true
  }

  async function dejar(e) {
    e.preventDefault()
    if (texto.trim().length < 3) { setError('Escribe la observación (mínimo 3 letras).'); return }
    if (await enviar('/hotel/observaciones', { texto: texto.trim(), ...(referencia.trim() ? { referencia: referencia.trim() } : {}) })) {
      setTexto('')
      setReferencia('')
    }
  }

  if (!lista) return null
  return (
    <section className="tarjeta" aria-label="Observaciones del dueño">
      <h2>Observaciones del dueño{lista.abiertas > 0 ? ` · ${lista.abiertas} sin responder` : ''}</h2>
      {dueno && (
        <form className="formulario" onSubmit={dejar}>
          <label className="campo">
            <span className="campo-etiqueta">Observación para la administración</span>
            <textarea className="entrada" rows="3" maxLength={1000} value={texto} onChange={(e) => setTexto(e.target.value)} />
          </label>
          <label className="campo">
            <span className="campo-etiqueta">Se refiere a (opcional)</span>
            <input className="entrada" maxLength={120} value={referencia} onChange={(e) => setReferencia(e.target.value)} placeholder="Pantalla o dato, por ejemplo Caja del lunes" />
          </label>
          <button type="submit" className="boton-primario">Dejar observación</button>
        </form>
      )}
      {error && <p role="alert" className="alerta">{error}</p>}
      {lista.observaciones.length === 0 ? (
        <p className="estado estado-vacio">Sin observaciones.</p>
      ) : (
        <ul className="lista-simple">
          {lista.observaciones.map((o) => (
            <li key={o.id}>
              <strong>{ESTADO[o.estado]}</strong> · {fechaHora(o.creado_en)}{o.referencia ? ` · ${o.referencia}` : ''}
              <div>{o.texto}</div>
              {o.respuesta && <div className="nota-clave">Respuesta de {o.respondida_por}: {o.respuesta}</div>}
              {!dueno && o.estado !== 'cerrada' && (
                <div className="acciones-fila">
                  <input className="entrada" placeholder="Responder" aria-label={`Responder observación ${o.id}`} value={respuestas[o.id] || ''}
                    onChange={(e) => setRespuestas({ ...respuestas, [o.id]: e.target.value })} />
                  <button type="button" className="boton-secundario" onClick={async () => {
                    if (!(respuestas[o.id] || '').trim()) { setError('Escribe la respuesta.'); return }
                    if (await enviar(`/hotel/observaciones/${o.id}/respuesta`, { respuesta: respuestas[o.id].trim() })) setRespuestas({ ...respuestas, [o.id]: '' })
                  }}>Responder</button>
                </div>
              )}
              {dueno && o.estado === 'respondida' && (
                <button type="button" className="boton-secundario" onClick={() => enviar(`/hotel/observaciones/${o.id}/cierre`)}>Dar por cerrada</button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
