'use client'

import { useEffect, useState } from 'react'

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
  return mapa[motivo] || (motivo ? `No se pudo abrir la sesión (${motivo}).` : null)
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
          Operando como {sesion.usuario.usuario} · {sesion.usuario.rol}
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
    const traducciones = {
      codigo_totp_requerido: 'Ingresa el código del autenticador.',
      sesion_empresa_ajena:
        'La sesión no pertenece a la empresa activa del servidor. Revisa EMPRESA_TITULAR / redeploy.',
      'sesión inválida o vencida': 'Sesión expirada o revocada. Inicia sesión de nuevo.',
      'sin sesión': 'No hay sesión activa.',
    }
    return traducciones[detalle] || detalle
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
  if (datos.pago_id) {
    const monto = typeof datos.monto_clp === 'number' ? ` de $${datos.monto_clp}` : ''
    return `Pago ${datos.pago_id}${monto}: estado «${datos.estado}»`
  }
  if (datos.tarifa_id) {
    return `Tarifa ${datos.habitacion_id}: $${datos.tarifa_noche_clp}/noche (${datos.fecha_desde} → ${datos.fecha_hasta})`
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
    <div>
      <p className="operacion-confirmada">{resumen || 'Operación confirmada por el servidor'}</p>
      <details className="json-detalle">
        <summary>Ver detalle técnico</summary>
        <pre className="json-panel">{JSON.stringify(datos, null, 2)}</pre>
      </details>
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
 *  el front no reescribe fórmulas, las muestra tal como llegan. */
export function Definicion({ indicador }) {
  if (!indicador) return null
  return (
    <details className="definicion">
      <summary>Cómo se calcula</summary>
      <dl>
        <dt>Fórmula</dt>
        <dd>{indicador.formula}</dd>
        <dt>Unidad</dt>
        <dd>{indicador.unidad}</dd>
        <dt>Fuente</dt>
        <dd>{indicador.fuente}</dd>
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
