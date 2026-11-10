/**
 * Utilidades puras del formulario de contacto (spec-api-v1 «Contacto y leads
 * de la landing», V1-ISSUE-20 punto 8: formulario propio, Formspree
 * retirado). Sin dependencias de DOM: las mismas funciones corren en el
 * navegador (formulario) y en Node (tests, `node --test landing/test/`).
 */
import { validarRango } from './reserva.js'

/**
 * El formulario postea a `{API_URL}/publico/leads` (spec del contrato): los
 * campos usan snake_case y las fechas viajan como YYYY-MM-DD o null; el
 * HTML del sitio real usa name, email, phone, guests, checkin, checkout y
 * message. El marcador anterior usaba nombre, correo, telefono, huespedes,
 * check-in y check-out. El mapeo vive aquí y queda probado; el cuerpo que
 * sale hacia la API sigue en snake_case.
 */
function textoPresente(datos, ...claves) {
  for (const clave of claves) {
    if (datos[clave] == null) continue
    const limpio = String(datos[clave]).trim()
    if (limpio !== '') return limpio
  }
  return ''
}

export function mapearCuerpo(datos) {
  const huespedes = textoPresente(datos, 'huespedes', 'guests')
  const checkIn = textoPresente(datos, 'check_in', 'checkin', 'check-in')
  const checkOut = textoPresente(datos, 'check_out', 'checkout', 'check-out')
  return {
    nombre: textoPresente(datos, 'nombre', 'name'),
    correo: textoPresente(datos, 'correo', 'email'),
    telefono: textoPresente(datos, 'telefono', 'phone'),
    huespedes: huespedes === '' ? null : Number(huespedes),
    check_in: checkIn || null,
    check_out: checkOut || null,
    mensaje: textoPresente(datos, 'mensaje', 'message') || null,
  }
}

/** Mensaje de estado legible según el código HTTP de /publico/leads. */
export function mensajePara(estadoHttp) {
  if (estadoHttp === 201 || estadoHttp === 200) {
    return 'Consulta enviada. Responderemos a la brevedad.'
  }
  if (estadoHttp === 429) {
    return 'Recibimos demasiados intentos; espera un minuto e inténtalo de nuevo.'
  }
  if (estadoHttp === 422) {
    return 'Revisa los datos del formulario e inténtalo de nuevo.'
  }
  return 'No se pudo enviar. Inténtalo por teléfono o WhatsApp.'
}

const CORREO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

/** Misma regla que `_validar` del servicio: null si el cuerpo puede enviarse. */
export function problemaConsulta(cuerpo) {
  if (!cuerpo.nombre || cuerpo.nombre.length > 200) return 'El nombre es obligatorio.'
  if (!cuerpo.correo || cuerpo.correo.length > 320 || !CORREO.test(cuerpo.correo)) {
    return 'El correo debe tener formato de correo.'
  }
  const telefono = cuerpo.telefono || ''
  const digitos = telefono.replace(/\D/g, '')
  if (!telefono || telefono.length > 40 || digitos.length < 8 || digitos.length > 15) {
    return 'El teléfono debe incluir entre 8 y 15 dígitos.'
  }
  if (cuerpo.huespedes != null && (!Number.isInteger(cuerpo.huespedes) || cuerpo.huespedes < 1 || cuerpo.huespedes > 30)) {
    return 'Los huéspedes deben estar entre 1 y 30.'
  }
  const tieneLlegada = Boolean(cuerpo.check_in)
  const tieneSalida = Boolean(cuerpo.check_out)
  if (tieneLlegada !== tieneSalida) return 'Indica la llegada y la salida, o ninguna.'
  if (tieneLlegada) {
    const fechas = validarRango(cuerpo.check_in, cuerpo.check_out, cuerpo.huespedes || 1)
    if (fechas) return fechas
  }
  if (cuerpo.mensaje && cuerpo.mensaje.length > 2000) return 'El mensaje es demasiado largo.'
  return null
}

/**
 * La clave de idempotencia se conserva solo cuando la red no confirmó el
 * resultado (0 o 5xx), para reintentar sin crear otro lead. Un 2xx o un 4xx
 * ya quedó decidido: la siguiente consulta usa otra clave.
 */
export function decidirClave(estadoHttp) {
  if (estadoHttp >= 200 && estadoHttp < 300) return 'renovar'
  if (estadoHttp >= 400 && estadoHttp < 500) return 'renovar'
  return 'conservar'
}
