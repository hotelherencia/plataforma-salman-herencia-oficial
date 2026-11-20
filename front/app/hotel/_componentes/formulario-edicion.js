'use client'

import { useId, useRef, useState } from 'react'
import { api, mensajeDeError } from '../../../lib/api'

const PATRON_CORREO = /^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$/

/** Formulario de edición en línea, compartido por leads, solicitudes, clientes y la ficha de la
 *  reserva. `campos`: [{ nombre, etiqueta, tipo?, requerido?, opciones?, validar? }]; `tipo: 'select'` usa
 *  `opciones: [[valor, etiqueta]]`, `'checkbox'` envía un booleano. `ruta`: PUT/POST del recurso.
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

/** Valida los campos del formulario antes de enviar y devuelve un mapa `{ [nombre]: mensaje }`. */
export function validarCampos(campos, valores) {
  const errores = {}
  for (const c of campos) {
    const v = valores[c.nombre]
    const texto = String(v ?? '').trim()
    if (c.requerido && c.tipo !== 'checkbox' && !texto) {
      errores[c.nombre] = `${c.etiqueta} es obligatorio.`
      continue
    }
    if (c.tipo === 'email' && texto && !PATRON_CORREO.test(texto)) {
      errores[c.nombre] = `${c.etiqueta} debe tener un formato de correo válido.`
      continue
    }
    if (c.tipo === 'number' && texto !== '' && Number.isNaN(Number(texto))) {
      errores[c.nombre] = `${c.etiqueta} debe ser un número válido.`
      continue
    }
    if (typeof c.validar === 'function') {
      const msg = c.validar(v, valores)
      if (msg) errores[c.nombre] = msg
    }
  }
  return errores
}

export default function FormularioEdicion({
  campos,
  inicial,
  ruta,
  metodo = 'PUT',
  claveIdempotencia,
  etiquetaGuardar = 'Guardar cambios',
  tituloAria = 'Editar registro',
  armar,
  alGuardar,
  alErrorEstado,
  alCancelar,
}) {
  const prefijoId = useId()
  const [valores, setValores] = useState(() =>
    Object.fromEntries(campos.map((c) => [c.nombre, inicial[c.nombre] ?? (c.tipo === 'checkbox' ? false : '')])))
  const [erroresCampo, setErroresCampo] = useState({})
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const refs = useRef({})
  const refAlerta = useRef(null)

  function enfocarElemento(el) {
    if (!el) return
    if (typeof el.scrollIntoView === 'function') el.scrollIntoView({ block: 'center', behavior: 'smooth' })
    if (typeof el.focus === 'function') el.focus({ preventScroll: true })
  }

  function cambiar(nombre, valor) {
    setValores((prev) => ({ ...prev, [nombre]: valor }))
    setErroresCampo((prev) => (prev[nombre] ? { ...prev, [nombre]: undefined } : prev))
  }

  async function guardar(e) {
    e.preventDefault()
    setError('')
    const errores = validarCampos(campos, valores)
    setErroresCampo(errores)
    const primeroConError = campos.find((c) => errores[c.nombre])
    if (primeroConError) {
      setError(errores[primeroConError.nombre])
      requestAnimationFrame(() => enfocarElemento(refs.current[primeroConError.nombre]))
      return
    }
    const cuerpo = armar ? armar(valores) : cuerpoPorDefecto(campos, valores)
    setEnviando(true)
    try {
      const opciones = { metodo, cuerpo }
      if (claveIdempotencia) opciones.claveIdempotencia = claveIdempotencia
      const r = await api(ruta, opciones)
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        if (typeof alErrorEstado === 'function') alErrorEstado(r.estado)
        requestAnimationFrame(() => enfocarElemento(refAlerta.current))
      } else {
        alGuardar(r.datos)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
      requestAnimationFrame(() => enfocarElemento(refAlerta.current))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="formulario" onSubmit={guardar} aria-label={tituloAria} noValidate>
      {campos.map((c) => {
        const msgError = erroresCampo[c.nombre]
        const idError = `${prefijoId}-err-${c.nombre}`
        const propsA11y = {
          ref: (el) => { refs.current[c.nombre] = el },
          'aria-invalid': msgError ? 'true' : undefined,
          'aria-describedby': msgError ? idError : undefined,
          required: Boolean(c.requerido),
        }
        return (
          <label className="campo" key={c.nombre}>
            <span className="campo-etiqueta">
              {c.etiqueta}{c.requerido ? ' *' : ''}
            </span>
            {c.tipo === 'select' ? (
              <select
                className="entrada"
                value={valores[c.nombre]}
                onChange={(e) => cambiar(c.nombre, e.target.value)}
                {...propsA11y}
              >
                {c.opciones.map(([valor, etiqueta]) => <option key={valor} value={valor}>{etiqueta}</option>)}
              </select>
            ) : c.tipo === 'checkbox' ? (
              <input
                type="checkbox"
                checked={Boolean(valores[c.nombre])}
                onChange={(e) => cambiar(c.nombre, e.target.checked)}
                {...propsA11y}
              />
            ) : (
              <input
                className="entrada"
                type={c.tipo || 'text'}
                placeholder={c.placeholder}
                value={valores[c.nombre]}
                onChange={(e) => cambiar(c.nombre, e.target.value)}
                {...propsA11y}
              />
            )}
            {msgError && <span id={idError} className="error-campo">{msgError}</span>}
          </label>
        )
      })}
      {error && <p role="alert" className="alerta" tabIndex={-1} ref={refAlerta}>{error}</p>}
      <div className="acciones-fila">
        <button type="submit" className="boton-primario" disabled={enviando} aria-busy={enviando || undefined}>
          {enviando ? 'Guardando…' : etiquetaGuardar}
        </button>
        <button type="button" className="boton-secundario" onClick={alCancelar}>Cancelar</button>
      </div>
    </form>
  )
}
