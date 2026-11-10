/**
 * Utilidades puras del CTA de reserva de la landing (CA-PUB-12,
 * V1-ISSUE-25). Sin dependencias de DOM: las mismas funciones corren en el
 * navegador (widget) y en Node (tests, `node --test landing/test/`).
 *
 * La validación espeja `validar()` de `front/app/reservar/page.js`: la
 * landing y el front deben rechazar exactamente los mismos rangos, para que
 * el deep link siempre llegue a un formulario que acepta lo que la landing
 * validó.
 */
export const MAX_NOCHES = 30
export const MAX_PERSONAS = 30

/** Fecha local en YYYY-MM-DD (misma regla que hoyLocal() del front). */
export function hoyLocal(fecha = new Date()) {
  const m = String(fecha.getMonth() + 1).padStart(2, '0')
  const dia = String(fecha.getDate()).padStart(2, '0')
  return `${fecha.getFullYear()}-${m}-${dia}`
}

/** Devuelve null si el rango es vendible, o un mensaje legible si no. */
export function validarRango(inicio, fin, personas) {
  if (!inicio || !fin) return 'Indica las fechas de tu estadía.'
  if (fin <= inicio) return 'La salida debe ser posterior a la llegada.'
  if (inicio < hoyLocal()) return 'La llegada no puede ser una fecha pasada.'
  if ((new Date(`${fin}T00:00:00`) - new Date(`${inicio}T00:00:00`)) / 86400000 > MAX_NOCHES)
    return `El rango supera las ${MAX_NOCHES} noches.`
  const n = Number(personas)
  if (!Number.isInteger(n) || n < 1 || n > MAX_PERSONAS) return `Personas debe estar entre 1 y ${MAX_PERSONAS}.`
  return null
}

/**
 * Deep link al front público: `{base}/reservar?inicio=…&fin=…&personas=…`.
 * Lanza Error con el mismo mensaje de validarRango si el rango no es vendible.
 */
const REFERENCIA = /^[A-Za-z0-9_-]{20,128}$/

export function construirEnlaceReserva(base, inicio, fin, personas, referencia) {
  const problema = validarRango(inicio, fin, personas)
  if (problema) throw new Error(problema)
  const raiz = String(base || '').replace(/\/+$/, '')
  let enlace = `${raiz}/reservar?inicio=${inicio}&fin=${fin}&personas=${Number(personas)}`
  if (referencia == null || referencia === '') return enlace
  if (!REFERENCIA.test(referencia)) throw new Error('La referencia de la consulta no es válida.')
  return `${enlace}&ref=${encodeURIComponent(referencia)}`
}
