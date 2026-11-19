'use client'

import { useEffect, useRef, useState } from 'react'

import { traducirDetalle, traducirFormula } from './mensajes.js'
import { etiquetaRol } from './roles.js'

// Contención: si el build no inyecta API_BASE_URL, el proxy same-origin /api
// es el contrato de producción (Vercel → Railway). Vacío rompía /sesion.
const BASE = (process.env.API_BASE_URL || '/api').replace(/\/$/, '')
const SESION_TIMEOUT_MS = 12000

export class ApiCaida extends Error {}

/** URL absoluta de la API para recursos binarios (imágenes, descargas). */
export function urlApi(ruta) {
  return BASE + ruta
}

/** Cliente HTTP del front: solo habla con API_BASE_URL y jamás calcula negocio. */
export async function api(ruta, { metodo = 'GET', cuerpo, claveIdempotencia, cabeceras: extra, timeoutMs } = {}) {
  const cabeceras = { ...(extra || {}) }
  let cuerpoSerializado
  if (cuerpo !== undefined) {
    cabeceras['Content-Type'] = 'application/json'
    cuerpoSerializado = JSON.stringify(cuerpo)
  }
  if (claveIdempotencia) cabeceras['Idempotency-Key'] = claveIdempotencia
  const ac = typeof AbortController !== 'undefined' ? new AbortController() : null
  const ms = timeoutMs ?? (ruta === '/sesion' && metodo === 'GET' ? SESION_TIMEOUT_MS : undefined)
  const timer = ms && ac ? setTimeout(() => ac.abort(), ms) : null
  let respuesta
  try {
    respuesta = await fetch(BASE + ruta, {
      method: metodo,
      headers: cabeceras,
      body: cuerpoSerializado,
      credentials: 'include',
      signal: ac ? ac.signal : undefined,
    })
  } catch (error) {
    throw new ApiCaida('la API no responde')
  } finally {
    if (timer) clearTimeout(timer)
  }
  const texto = await respuesta.text()
  let datos = {}
  try {
    datos = texto ? JSON.parse(texto) : {}
  } catch {
    datos = { detalle: texto }
  }
  return { estado: respuesta.status, datos }
}

// Estado de sesión compartido (V1-ISSUE-37): BarraNav, MarcoHotel y la página
// montaban useSesion() cada uno y disparaban 2–3 GET /sesion por carga, con
// fallos transitorios que tumbaran la página a «API no disponible». Aquí hay
// una sola fuente: la primera petición se deduplica en vuelo y el resultado
// se comparte con todos los suscriptos; login/logout/2FA fuerzan un refresco.
let cacheSesion = { fase: 'cargando', usuario: null, motivo: null }
let promesaSesion = null
const oyentesSesion = new Set()

function publicarSesion() {
  oyentesSesion.forEach((oyente) => oyente(cacheSesion))
}

/** Mensaje legible cuando la API rechaza la cookie de sesión. */
export function mensajeMotivoSesion(motivo) {
  const mapa = {
    sesion_empresa_ajena:
      'Tu sesión no coincide con la empresa activa del servidor (configuración de despliegue). Vuelve a entrar; si persiste, el operador debe revisar EMPRESA_TITULAR en el servicio.',
    'sesión inválida o vencida': 'Tu sesión expiró o fue revocada. Vuelve a iniciar sesión.',
    'sin sesión': null,
  }
  // Presencia de la clave y no `||`: 'sin sesión' mapea a null a propósito (visitante que aún
  // no entra) y `||` lo convertía en «No se pudo abrir la sesión (sin sesión)».
  if (motivo && Object.prototype.hasOwnProperty.call(mapa, motivo)) return mapa[motivo]
  return motivo ? `No se pudo abrir la sesión (${motivo}).` : null
}

export function refrescarSesion() {
  if (!promesaSesion) {
    promesaSesion = api('/sesion')
      .then((r) => {
        // 401/403 sin sid usable = fuera (pantalla de acceso). Solo caídas
        // de red/timeout marcan «API no disponible». El `motivo` (detail)
        // evita que el operador/usuario tenga que adivinar por el 401 genérico.
        const motivo = typeof r.datos?.detail === 'string' ? r.datos.detail : null
        if (r.estado === 200) cacheSesion = { fase: 'ok', usuario: r.datos, motivo: null }
        else if (r.estado === 401 || r.estado === 403) {
          cacheSesion = { fase: 'fuera', usuario: null, motivo }
        } else cacheSesion = { fase: 'caida', usuario: null, motivo }
      })
      .catch(() => {
        cacheSesion = { fase: 'caida', usuario: null, motivo: 'api_caida' }
      })
      .finally(() => {
        promesaSesion = null
        publicarSesion()
      })
  }
  return promesaSesion.then(() => cacheSesion)
}

export function useSesion() {
  const [sesion, setSesion] = useState(cacheSesion)
  useEffect(() => {
    oyentesSesion.add(setSesion)
    if (cacheSesion.fase === 'cargando') refrescarSesion()
    else setSesion(cacheSesion)
    return () => oyentesSesion.delete(setSesion)
  }, [])
  return sesion
}

/**
 * Clave de idempotencia estable (spec-front-v1 «Idempotencia en el cliente»):
 * nace al montar el formulario, se muestra antes del primer envío, sobrevive
 * errores de red y 4xx/5xx, y solo se reemplaza tras un 2xx (o con
 * «Nueva operación»). Si el usuario cambia el cuerpo y reintenta con la clave
 * vieja, la API responde 409 y la clave se conserva: no se acuña en silencio.
 */
export function useClaveOperacion() {
  const [clave, setClave] = useState(() => crypto.randomUUID())
  const renovar = () => setClave(crypto.randomUUID())
  return [clave, renovar]
}

/** V1-ISSUE-13: ante un rechazo definitivo (4xx) la clave se renueva para que
 *  corregir la causa y reintentar no devuelva la respuesta guardada bajo la
 *  misma clave. Los errores de red no pasan por aquí: la clave se conserva
 *  para reintentar la misma operación sin duplicar. */
export function alRechazar(estado, renovar) {
  if (estado >= 400 && estado < 500) renovar()
}

/** Marco común: con API caída muestra error y ninguna operación se confirma. */
export function MarcoHotel({ children, titulo }) {
  const sesion = useSesion()
  if (sesion.fase === 'cargando')
    return (
      <main className="pagina">
        <p className="estado">Cargando…</p>
      </main>
    )
  if (sesion.fase === 'caida')
    return (
      <main className="pagina">
        <h1>{titulo}</h1>
        <p role="alert" className="alerta">
          La API no está disponible: nada se puede leer ni confirmar.
        </p>
      </main>
    )
  if (sesion.fase === 'fuera')
    return (
      <main className="pagina">
        <h1>{titulo}</h1>
        <p>
          Sesión cerrada. <a href="/login">Inicia sesión</a>.
        </p>
      </main>
    )
  return (
    <main className="pagina">
      <header className="pagina-cabecera">
        <h1>{titulo}</h1>
        <p className="operador">
          Operando como {sesion.usuario.usuario} · {etiquetaRol(sesion.usuario.rol)}
        </p>
      </header>
      {children}
    </main>
  )
}

/** Devuelve un mensaje si falta algún campo obligatorio, o null si está completo.
 *  Evita llamar a la API con identificadores vacíos (404 crudos). */
export function camposFaltantes(pares) {
  const faltan = pares
    .filter(([valor]) => valor === undefined || valor === null || String(valor).trim() === '')
    .map(([, etiqueta]) => etiqueta)
  return faltan.length ? `Falta completar: ${faltan.join(', ')}.` : null
}

/** Interpreta el cuerpo de error de la API en texto legible. Los `detail` de
 *  negocio ya vienen en español; los códigos técnicos se traducen y las
 *  validaciones 422 (detail como arreglo) se listan en línea. */
export function mensajeDeError(datos, estado) {
  if (estado === 404) return 'No existe ese recurso: revisa el identificador ingresado.'
  const detalle = datos && datos.detail
  if (typeof detalle === 'string') {
    return traducirDetalle(detalle)
  }
  if (typeof datos?.error === 'string') return datos.error
  if (Array.isArray(detalle))
    return detalle
      .map((d) => {
        if (!d || typeof d !== 'object') return String(d)
        const campo = Array.isArray(d.loc) && d.loc.length > 1 ? `${d.loc[d.loc.length - 1]}: ` : ''
        return `${campo}${d.msg || JSON.stringify(d)}`
      })
      .join(' · ')
  if (estado === 401) return 'Sesión expirada. Inicia sesión de nuevo.'
  if (estado === 403) return 'Sin permisos para esta operación.'
  if (estado === 429) return 'Demasiados intentos. Espera unos minutos.'
  if (estado === 503) return 'Servicio no configurado en el servidor.'
  if (estado >= 500) return 'Error interno del servidor. Intenta más tarde.'
  return `Error ${estado}`
}

/** Resumen legible de la confirmación según la forma del payload; null si no
 *  reconoce la operación (cae en el texto genérico). */
export function resumenConfirmacion(datos) {
  if (!datos || typeof datos !== 'object') return null
  // Entrega 1A: alta por lote y tipos de habitación.
  if (datos.tipo_id && Array.isArray(datos.habitaciones) && typeof datos.creadas === 'number') {
    const ids = datos.habitaciones
    const rango = ids.length > 1 ? `${ids[0]} a ${ids[ids.length - 1]}` : ids[0]
    const precio = datos.precio_base_clp ? ` · cotizan ${clp(datos.precio_base_clp)}/noche (base del tipo)` : ' · sin precio base: aún no se ofrecen'
    return `${datos.creadas} habitación(es) creada(s): ${rango}${precio}`
  }
  if (datos.tipo && datos.cambios && datos.tipo.tipo_id) {
    const cambios = Object.entries(datos.cambios).map(([campo, [antes, despues]]) => {
      const fmt = (v) => (campo === 'precio_base_clp' ? (v ? clp(v) : 'sin precio') : String(v))
      const nombre = { precio_base_clp: 'precio base', capacidad_base: 'capacidad', nombre: 'nombre', activo: 'activo', orden: 'orden' }[campo] || campo
      return `${nombre} ${fmt(antes)} → ${fmt(despues)}`
    })
    return `Tipo ${datos.tipo.nombre}: ${cambios.length ? cambios.join(' · ') : 'sin cambios'}`
  }
  if (datos.tipo_id && datos.nombre && typeof datos.capacidad_base === 'number') {
    return `Tipo ${datos.nombre} creado (${datos.tipo_id})${datos.precio_base_clp ? ` · precio base ${clp(datos.precio_base_clp)}` : ' · sin precio base'}`
  }
  if (datos.pago_id) {
    const monto = typeof datos.monto_clp === 'number' ? ` de $${datos.monto_clp}` : ''
    return `Pago ${datos.pago_id}${monto}: estado «${datos.estado}»`
  }
  // Entrega 1A.2: precio propio, excepciones por fecha y tasa de IVA.
  if (datos.habitacion_id && 'precio_propio_clp' in datos && datos.cambios) {
    return datos.precio_propio_clp
      ? `Habitación ${datos.habitacion_id}: precio propio ${clp(datos.precio_propio_clp)} con IVA`
      : `Habitación ${datos.habitacion_id}: sin precio propio, hereda el precio base del tipo`
  }
  if (datos.excepcion_id) {
    const alcance = datos.tipo_id && !datos.habitacion_id ? `del tipo ${datos.tipo_id}` : `de ${datos.habitacion_id}`
    if (datos.activa === false) return `Excepción ${alcance} retirada (${datos.fecha_desde} → ${datos.fecha_hasta}); queda en el historial`
    const precio = datos.precio_clp ? `${clp(datos.precio_clp)} con IVA` : 'sin venta'
    return `Excepción ${alcance}: ${precio} (${datos.fecha_desde} → ${datos.fecha_hasta})`
  }
  if (datos.iva && datos.iva.porcentaje !== undefined && Object.keys(datos).length === 1) {
    return `Tasa de IVA: ${String(datos.iva.porcentaje).replace('.', ',')} %. Los precios con IVA no cambian.`
  }
  // Solicitud web (#346/#347): la respuesta trae habitacion_id y tipo, así que
  // debe resolverse antes que los resúmenes de habitación (antes mostraba
  // «Habitación …: tipo, capacidad undefined» al convertir).
  if (datos.solicitud_id && datos.estado === 'convertida' && datos.reserva_id) {
    return `Solicitud ${datos.solicitud_id} convertida en la reserva ${datos.reserva_id}${datos.habitacion_id ? ` · Habitación ${datos.habitacion_id}` : ''}`
  }
  if (datos.solicitud_id && datos.estado === 'rechazada') {
    return `Solicitud ${datos.solicitud_id} rechazada`
  }
  if (datos.habitacion_id && typeof datos.en_servicio === 'boolean') {
    if (!datos.cambio) return `Habitación ${datos.habitacion_id}: sin cambios (${datos.en_servicio ? 'en servicio' : 'fuera de servicio'})`
    return datos.en_servicio
      ? `Habitación ${datos.habitacion_id}: reincorporada a la operación`
      : `Habitación ${datos.habitacion_id}: retirada de operación (${datos.motivo})`
  }
  if (datos.habitacion_id && typeof datos.creada === 'boolean') {
    if (datos.creada) return `Habitación ${datos.habitacion_id} dada de alta: ${datos.tipo}, capacidad ${datos.capacidad}`
    const cambios = Object.entries(datos.cambios || {}).map(([campo, [antes, despues]]) => `${campo} ${antes} → ${despues}`)
    return `Habitación ${datos.habitacion_id}: ${cambios.length ? cambios.join(' · ') : 'sin cambios'}`
  }
  if (datos.habitacion_id && datos.estado_preparacion) {
    const tareas = typeof datos.tareas_completadas === 'number' ? ` · ${datos.tareas_completadas} tarea(s) de limpieza cerrada(s)` : ''
    return `Habitación ${datos.habitacion_id}: preparación «${datos.estado_preparacion}»${tareas}`
  }
  if (datos.habitacion_id && datos.tipo) {
    return `Habitación ${datos.habitacion_id}: ${datos.tipo}, capacidad ${datos.capacidad}`
  }
  if (datos.cargo_id && typeof datos.monto_clp === 'number') {
    return `Cargo de ${clp(datos.monto_clp)} registrado (${datos.concepto || 'consumo'})`
  }
  if (datos.reverso_id && typeof datos.monto_clp === 'number') {
    return `Reverso contable de ${clp(datos.monto_clp)} aplicado`
  }
  if (datos.producto_id && datos.nombre) {
    return `Producto «${datos.nombre}» guardado (${clp(datos.precio_unitario_clp || 0)})`
  }
  if (datos.solicitud_id && datos.tipo) {
    return `Solicitud ${datos.solicitud_id} registrada para tipo «${datos.tipo}»`
  }
  if (datos.reserva_id && datos.codigo && datos.huesped) {
    return `Reserva ${datos.codigo} confirmada para ${datos.huesped.nombre || 'huésped'}${datos.habitacion_id ? ` · Habitación ${datos.habitacion_id}` : ''}`
  }
  if (datos.reserva_id && datos.estado === 'cancelada' && Array.isArray(datos.reversos)) {
    const totalReversado = datos.reversos.reduce((s, r) => s + (r.monto_clp || 0), 0)
    const txtReversos = datos.reversos.length
      ? `${datos.reversos.length} reverso(s) aplicado(s) (${clp(totalReversado)})`
      : 'sin cargos previos por reversar'
    const txtPenalidad =
      typeof datos.penalidad_clp === 'number' && datos.penalidad_clp > 0
        ? ` · penalidad fuera de plazo: ${clp(datos.penalidad_clp)}`
        : ' · sin penalidad (dentro de plazo)'
    const txtReembolso =
      datos.reembolso === 'no configurado'
        ? ' · reembolso por pasarela no configurado (sin devolución automática)'
        : ''
    return `Reserva ${datos.reserva_id}: estado «cancelada» · ${txtReversos}${txtPenalidad}${txtReembolso}`
  }
  if (datos.reserva_id && datos.estado === 'en_casa') return `Check-in confirmado para reserva ${datos.reserva_id}: huésped en casa`
  if (datos.reserva_id && datos.estado === 'terminada') return `Check-out confirmado para reserva ${datos.reserva_id}: habitación liberada`
  if (datos.reserva_id && datos.estado) return `Reserva ${datos.reserva_id}: estado «${datos.estado}»`
  if (datos.reserva_id) return `Reserva ${datos.reserva_id}: operación registrada`
  if (typeof datos.sesiones_revocadas === 'number') return `Usuario ${datos.id}: ${datos.sesiones_revocadas} sesión(es) revocada(s)`
  if (datos.id && datos.estado) return `Usuario ${datos.id}: ${datos.estado}`
  if (datos.id && datos.nombre) return `Usuario ${datos.nombre} (${datos.id}): rol ${datos.rol}, ${datos.activo ? 'activo' : 'inactivo'}`
  if (datos.usuario) return `Usuario ${datos.usuario}: operación registrada`
  return null
}

export function SalidaJson({ datos }) {
  if (!datos) return null
  const resumen = resumenConfirmacion(datos)
  return (
    <div className="confirmacion-operacion-contenedor" role="status">
      <span className="confirmacion-icono" aria-hidden="true">✓</span>
      <div className="confirmacion-cuerpo">
        <p className="operacion-confirmada">{resumen || 'Operación confirmada exitosamente'}</p>
      </div>
    </div>
  )
}

export function Campo({ etiqueta, ...props }) {
  return (
    <label className="campo">
      <span className="campo-etiqueta">{etiqueta}</span>
      <input className="entrada" {...props} />
    </label>
  )
}

/** Campo de clave con «Mostrar/Ocultar» (#350). Vuelve a ocultarse al
 *  enviar el formulario que lo contiene. */
export function CampoClave({ etiqueta, autoComplete = 'current-password', ...props }) {
  const [visible, setVisible] = useState(false)
  const ref = useRef(null)
  useEffect(() => {
    const formulario = ref.current?.closest('form')
    if (!formulario) return undefined
    const ocultar = () => setVisible(false)
    formulario.addEventListener('submit', ocultar)
    return () => formulario.removeEventListener('submit', ocultar)
  }, [])
  return (
    <label className="campo" ref={ref}>
      <span className="campo-etiqueta">{etiqueta}</span>
      <span className="campo-clave">
        <input className="entrada" type={visible ? 'text' : 'password'} autoComplete={autoComplete} {...props} />
        <button
          type="button"
          className="boton-ver-clave"
          aria-pressed={visible}
          aria-label={visible ? 'Ocultar clave' : 'Mostrar clave'}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? 'Ocultar' : 'Mostrar'}
        </button>
      </span>
    </label>
  )
}

export function CampoSelect({ etiqueta, children, ...props }) {
  return (
    <label className="campo">
      <span className="campo-etiqueta">{etiqueta}</span>
      <select className="entrada" {...props}>
        {children}
      </select>
    </label>
  )
}

/** Pesos chilenos para mostrar montos que ya calculó la API. */
export function clp(monto) {
  if (monto === null || monto === undefined) return '—'
  return `$${Number(monto).toLocaleString('es-CL')}`
}

/** Definición declarada por la API para un indicador (spec-hotel-operacion-v1 §4):
 *  el front explica las fórmulas en lenguaje de negocio claro para el operador (#381). */
export function Definicion({ indicador }) {
  if (!indicador) return null
  const textoFormula = traducirFormula(indicador.formula) || indicador.formula
  return (
    <details className="definicion">
      <summary>Cómo se calcula</summary>
      <dl>
        <dt>Fórmula</dt>
        <dd>{textoFormula}</dd>
        {indicador.unidad && (
          <>
            <dt>Unidad</dt>
            <dd>{indicador.unidad}</dd>
          </>
        )}
        {indicador.fuente && (
          <>
            <dt>Fuente</dt>
            <dd>{indicador.fuente === 'registro de estadías' ? 'Registro operativo de estadías' : indicador.fuente}</dd>
          </>
        )}
        {indicador.limitaciones && (
          <>
            <dt>Limitaciones</dt>
            <dd>{indicador.limitaciones}</dd>
          </>
        )}
      </dl>
    </details>
  )
}
