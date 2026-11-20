'use client'

import { useState } from 'react'
import { api, mensajeDeError } from '../../../lib/api'

/** Formulario de edición en línea, compartido por leads, solicitudes, clientes y la ficha de la
 *  reserva. `campos`: [{ nombre, etiqueta, tipo?, requerido?, opciones? }]; `tipo: 'select'` usa
 *  `opciones: [[valor, etiqueta]]`, `'checkbox'` envía un booleano. `ruta`: PUT del recurso.
 *  `armar(valores)`: cuerpo a enviar (por defecto, los valores; vacíos opcionales → null, números →
 *  Number). El PUT es idempotente por construcción: repetirlo no cambia nada, no necesita clave. */
export function cuerpoPorDefecto(campos, valores) {
  return Object.fromEntries(campos.map((c) => {
    const v = valores[c.nombre]
    if (c.tipo === 'checkbox') return [c.nombre, Boolean(v)]
    if (c.tipo === 'number') return [c.nombre, v === '' || v == null ? null : Number(v)]
    const texto = String(v ?? '').trim()
    return [c.nombre, texto === '' && !c.requerido ? null : texto]
  }))
}

export default function FormularioEdicion({ campos, inicial, ruta, armar, alGuardar, alCancelar }) {
  const [valores, setValores] = useState(() =>
    Object.fromEntries(campos.map((c) => [c.nombre, inicial[c.nombre] ?? (c.tipo === 'checkbox' ? false : '')])))
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function guardar(e) {
    e.preventDefault()
    setError('')
    for (const c of campos) {
      if (c.requerido && !String(valores[c.nombre] ?? '').trim()) { setError(`${c.etiqueta} es obligatorio.`); return }
    }
    const cuerpo = armar ? armar(valores) : cuerpoPorDefecto(campos, valores)
    setEnviando(true)
    try {
      const r = await api(ruta, { metodo: 'PUT', cuerpo })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else alGuardar(r.datos)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={guardar} aria-label="Editar registro">
      {campos.map((c) => (
        <label className="campo" key={c.nombre}>
          <span className="campo-etiqueta">{c.etiqueta}</span>
          {c.tipo === 'select' ? (
            <select className="entrada" value={valores[c.nombre]} onChange={(e) => setValores({ ...valores, [c.nombre]: e.target.value })}>
              {c.opciones.map(([valor, etiqueta]) => <option key={valor} value={valor}>{etiqueta}</option>)}
            </select>
          ) : c.tipo === 'checkbox' ? (
            <input type="checkbox" checked={Boolean(valores[c.nombre])} onChange={(e) => setValores({ ...valores, [c.nombre]: e.target.checked })} />
          ) : (
            <input
              className="entrada"
              type={c.tipo || 'text'}
              value={valores[c.nombre]}
              onChange={(e) => setValores({ ...valores, [c.nombre]: e.target.value })}
            />
          )}
        </label>
      ))}
      {error && <p role="alert" className="alerta">{error}</p>}
      <div className="acciones-fila">
        <button type="submit" className="boton-primario" disabled={enviando}>Guardar cambios</button>
        <button type="button" className="boton-secundario" onClick={alCancelar}>Cancelar</button>
      </div>
    </form>
  )
}
