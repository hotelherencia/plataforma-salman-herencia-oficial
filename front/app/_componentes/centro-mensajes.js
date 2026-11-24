'use client'

import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from 'react'

const ContextoMensajes = createContext(null)

const MAX_TOASTS = 3
const DURACION_DEFECTO_MS = 5500

function focoEnContenedor(nodo) {
  if (!nodo) return []
  return Array.from(
    nodo.querySelectorAll(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  )
}

/**
 * Componente en línea unificado para avisos persistentes en pantalla.
 * Garantiza mismo formato, icono, borde izquierdo y roles ARIA en toda la app.
 */
export function AvisoLinea({ tipo = 'info', texto, children, className = '' }) {
  const contenido = children ?? texto
  if (!contenido) return null
  if (tipo === 'error') {
    return (
      <p role="alert" className={`alerta ${className}`.trim()}>
        {contenido}
      </p>
    )
  }
  if (tipo === 'exito') {
    return (
      <p role="status" className={`aviso-ok ${className}`.trim()}>
        {contenido}
      </p>
    )
  }
  if (tipo === 'aviso') {
    return (
      <p role="status" className={`aviso ${className}`.trim()}>
        {contenido}
      </p>
    )
  }
  return (
    <p role="status" className={`aviso-info ${className}`.trim()}>
      {contenido}
    </p>
  )
}

function DialogoModal({ solicitud, alResolver }) {
  const [valor, setValor] = useState(solicitud.valorInicial || '')
  const [errorCampo, setErrorCampo] = useState('')
  const panelRef = useRef(null)
  const campoRef = useRef(null)
  const cancelarRef = useRef(null)
  const idTitulo = useId()
  const idDesc = useId()
  const idCampo = useId()
  const idError = useId()

  useEffect(() => {
    setValor(solicitud.valorInicial || '')
    setErrorCampo('')
  }, [solicitud])

  useEffect(() => {
    const previo = document.activeElement
    const destinoFoco = solicitud.modo === 'texto' ? campoRef.current : cancelarRef.current
    destinoFoco?.focus?.()

    function manejarTecla(ev) {
      if (ev.key === 'Escape') {
        ev.preventDefault()
        alResolver(solicitud.modo === 'texto' ? null : false)
        return
      }
      if (ev.key === 'Tab') {
        const elementos = focoEnContenedor(panelRef.current)
        if (!elementos.length) return
        const primero = elementos[0]
        const ultimo = elementos[elementos.length - 1]
        if (ev.shiftKey && document.activeElement === primero) {
          ev.preventDefault()
          ultimo.focus()
        } else if (!ev.shiftKey && document.activeElement === ultimo) {
          ev.preventDefault()
          primero.focus()
        }
      }
    }

    document.addEventListener('keydown', manejarTecla)
    return () => {
      document.removeEventListener('keydown', manejarTecla)
      previo?.focus?.()
    }
  }, [solicitud, alResolver])

  function enviar(ev) {
    ev.preventDefault()
    if (solicitud.modo === 'texto') {
      const limpio = valor.trim()
      const minimo = Number(solicitud.minCaracteres || 0)
      if (minimo > 0 && limpio.length < minimo) {
        setErrorCampo(
          solicitud.mensajeMinimo || `Escribe al menos ${minimo} caracteres para continuar.`
        )
        campoRef.current?.focus?.()
        return
      }
      alResolver(limpio)
      return
    }
    alResolver(true)
  }

  const esPeligro = solicitud.variante === 'peligro'

  return (
    <div
      className="dialogo-fondo"
      role="presentation"
      onMouseDown={(ev) => {
        if (ev.target === ev.currentTarget) {
          alResolver(solicitud.modo === 'texto' ? null : false)
        }
      }}
    >
      <div
        ref={panelRef}
        className={`dialogo-modal${esPeligro ? ' dialogo-peligro' : ''}`}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        aria-describedby={idDesc}
      >
        <div className="dialogo-cabecera">
          <h2 id={idTitulo} className="dialogo-titulo">
            {solicitud.titulo || 'Confirmar operación'}
          </h2>
          <button
            type="button"
            className="dialogo-cerrar"
            aria-label="Cerrar diálogo"
            onClick={() => alResolver(solicitud.modo === 'texto' ? null : false)}
          >
            ×
          </button>
        </div>

        <form onSubmit={enviar} className="dialogo-cuerpo">
          <p id={idDesc} className="dialogo-mensaje">
            {solicitud.mensaje}
          </p>

          {solicitud.modo === 'texto' && (
            <label className="campo" htmlFor={idCampo}>
              <span className="campo-etiqueta">{solicitud.etiqueta || 'Detalle'}</span>
              <textarea
                ref={campoRef}
                id={idCampo}
                className="entrada"
                rows={3}
                value={valor}
                placeholder={solicitud.placeholder || ''}
                maxLength={solicitud.maxCaracteres || 300}
                aria-invalid={errorCampo ? 'true' : undefined}
                aria-describedby={errorCampo ? idError : undefined}
                onChange={(ev) => {
                  setValor(ev.target.value)
                  if (errorCampo) setErrorCampo('')
                }}
              />
              {errorCampo && (
                <span id={idError} className="error-campo" role="alert">
                  {errorCampo}
                </span>
              )}
            </label>
          )}

          <div className="dialogo-acciones">
            <button
              ref={cancelarRef}
              type="button"
              className="boton-secundario"
              onClick={() => alResolver(solicitud.modo === 'texto' ? null : false)}
            >
              {solicitud.textoCancelar || 'Cancelar'}
            </button>
            <button
              type="submit"
              className={esPeligro ? 'boton-primario boton-peligro-solido' : 'boton-primario'}
            >
              {solicitud.textoConfirmar || 'Confirmar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ToastItem({ item, alCerrar }) {
  const pausadoRef = useRef(false)

  useEffect(() => {
    const ms = item.duracionMs ?? DURACION_DEFECTO_MS
    if (ms <= 0) return undefined
    const timer = setInterval(() => {
      if (!pausadoRef.current) alCerrar(item.id)
    }, ms)
    return () => clearInterval(timer)
  }, [item.id, item.duracionMs, alCerrar])

  const esError = item.tipo === 'error'
  const claseTipo =
    item.tipo === 'exito'
      ? 'toast-exito'
      : item.tipo === 'error'
        ? 'toast-error'
        : item.tipo === 'aviso'
          ? 'toast-aviso'
          : 'toast-info'

  return (
    <div
      className={`toast ${claseTipo}`}
      role={esError ? 'alert' : 'status'}
      onMouseEnter={() => { pausadoRef.current = true }}
      onMouseLeave={() => { pausadoRef.current = false }}
      onFocus={() => { pausadoRef.current = true }}
      onBlur={() => { pausadoRef.current = false }}
    >
      <span className="toast-texto">{item.texto}</span>
      <button
        type="button"
        className="toast-cerrar"
        aria-label="Cerrar notificación"
        onClick={() => alCerrar(item.id)}
      >
        ×
      </button>
    </div>
  )
}

export function ProveedorMensajes({ children }) {
  const [dialogo, setDialogo] = useState(null)
  const [toasts, setToasts] = useState([])
  const resolverRef = useRef(null)

  const cerrarToast = useCallback((id) => {
    setToasts((prev) => prev.filter((item) => item.id !== id))
  }, [])

  const notificar = useCallback(({ tipo = 'info', texto, duracionMs = DURACION_DEFECTO_MS } = {}) => {
    const limpio = String(texto || '').trim()
    if (!limpio) return
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    setToasts((prev) => {
      const sinDuplicado = prev.filter((item) => item.texto !== limpio || item.tipo !== tipo)
      return [...sinDuplicado.slice(-(MAX_TOASTS - 1)), { id, tipo, texto: limpio, duracionMs }]
    })
  }, [])

  const notificarExito = useCallback((texto, duracionMs) => {
    notificar({ tipo: 'exito', texto, duracionMs })
  }, [notificar])

  const notificarError = useCallback((texto, duracionMs = 7500) => {
    notificar({ tipo: 'error', texto, duracionMs })
  }, [notificar])

  const notificarAviso = useCallback((texto, duracionMs) => {
    notificar({ tipo: 'aviso', texto, duracionMs })
  }, [notificar])

  const confirmar = useCallback((opciones) => {
    const cfg = typeof opciones === 'string' ? { mensaje: opciones } : (opciones || {})
    return new Promise((resolve) => {
      if (resolverRef.current) resolverRef.current(false)
      resolverRef.current = resolve
      setDialogo({
        modo: 'confirmar',
        titulo: cfg.titulo || 'Confirmar operación',
        mensaje: cfg.mensaje || '¿Confirmas esta acción?',
        textoConfirmar: cfg.textoConfirmar || 'Confirmar',
        textoCancelar: cfg.textoCancelar || 'Cancelar',
        variante: cfg.variante || 'primario',
      })
    })
  }, [])

  const solicitarTexto = useCallback((opciones) => {
    const cfg = typeof opciones === 'string' ? { mensaje: opciones } : (opciones || {})
    return new Promise((resolve) => {
      if (resolverRef.current) resolverRef.current(null)
      resolverRef.current = resolve
      setDialogo({
        modo: 'texto',
        titulo: cfg.titulo || 'Ingresar detalle',
        mensaje: cfg.mensaje || '',
        etiqueta: cfg.etiqueta || 'Motivo',
        placeholder: cfg.placeholder || '',
        valorInicial: cfg.valorInicial || '',
        minCaracteres: cfg.minCaracteres ?? 0,
        maxCaracteres: cfg.maxCaracteres ?? 300,
        mensajeMinimo: cfg.mensajeMinimo || '',
        textoConfirmar: cfg.textoConfirmar || 'Confirmar',
        textoCancelar: cfg.textoCancelar || 'Cancelar',
        variante: cfg.variante || 'primario',
      })
    })
  }, [])

  const resolverDialogo = useCallback((resultado) => {
    const resolver = resolverRef.current
    resolverRef.current = null
    setDialogo(null)
    if (resolver) resolver(resultado)
  }, [])

  return (
    <ContextoMensajes.Provider
      value={{
        confirmar,
        solicitarTexto,
        notificar,
        notificarExito,
        notificarError,
        notificarAviso,
      }}
    >
      {children}
      {dialogo && <DialogoModal solicitud={dialogo} alResolver={resolverDialogo} />}
      {toasts.length > 0 && (
        <div className="toast-pila" aria-live="polite" aria-label="Notificaciones del sistema">
          {toasts.map((item) => (
            <ToastItem key={item.id} item={item} alCerrar={cerrarToast} />
          ))}
        </div>
      )}
    </ContextoMensajes.Provider>
  )
}

export function useMensajes() {
  const ctx = useContext(ContextoMensajes)
  if (ctx) return ctx
  return {
    confirmar: async () => false,
    solicitarTexto: async () => null,
    notificar: () => {},
    notificarExito: () => {},
    notificarError: () => {},
    notificarAviso: () => {},
  }
}
