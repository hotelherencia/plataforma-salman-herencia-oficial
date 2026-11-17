// Tipos de habitación y alta por lote (entrega 1A). Módulo puro, sin JSX,
// para probarlo con node --test. La API decide y valida; aquí solo se arma
// la vista previa que ve la administración antes de confirmar.

export const MAX_LOTE = 100
export const PATRON_ID_TIPO = /^[a-z0-9][a-z0-9_]{0,49}$/
export const PATRON_PREFIJO = /^[A-Za-z0-9][A-Za-z0-9_-]{0,19}$/

/** Código del tipo a partir del nombre: «Matrimonial +1» → «matrimonial_1». */
export function codigoDesdeNombre(nombre) {
  return String(nombre || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 50)
}

/** Identificadores que creará el lote, igual que la API: prefijo + número con ceros. */
export function idsDelLote(prefijo, desde, cantidad, digitos) {
  const n = Number(cantidad)
  const inicio = Number(desde)
  const d = Number(digitos)
  if (!Number.isInteger(n) || n < 1 || !Number.isInteger(inicio) || inicio < 0 || !Number.isInteger(d) || d < 1) return []
  return Array.from({ length: Math.min(n, MAX_LOTE) }, (_, i) => `${prefijo}${String(inicio + i).padStart(d, '0')}`)
}

/** Siguiente número libre después del mayor existente con ese prefijo (HAB-17 → 18). */
export function siguienteNumero(idsExistentes, prefijo) {
  let mayor = 0
  for (const id of idsExistentes || []) {
    if (!id.startsWith(prefijo)) continue
    const resto = id.slice(prefijo.length)
    if (/^\d+$/.test(resto)) mayor = Math.max(mayor, Number(resto))
  }
  return mayor + 1
}

/** Texto corto de la vista previa: «HAB-18, HAB-19 … HAB-27 (10)». */
export function resumenIds(ids) {
  if (!ids.length) return ''
  if (ids.length <= 4) return ids.join(', ')
  return `${ids[0]}, ${ids[1]} … ${ids[ids.length - 1]} (${ids.length})`
}

/** Valida el formulario del lote; devuelve el mensaje de error o null. */
export function validarLote({ tipoId, cantidad, prefijo, desde, digitos }, idsExistentes = []) {
  if (!tipoId) return 'Elige el tipo de las habitaciones nuevas.'
  const n = Number(cantidad)
  if (!Number.isInteger(n) || n < 1 || n > MAX_LOTE) return `La cantidad va de 1 a ${MAX_LOTE}.`
  if (!PATRON_PREFIJO.test(prefijo || '')) return 'El prefijo admite letras, números, guion y guion bajo (máx. 20).'
  if (!Number.isInteger(Number(desde)) || Number(desde) < 0) return 'El número inicial debe ser 0 o mayor.'
  const d = Number(digitos)
  if (!Number.isInteger(d) || d < 1 || d > 5) return 'Los dígitos van de 1 a 5.'
  const existentes = new Set(idsExistentes)
  const repetidas = idsDelLote(prefijo, desde, n, d).filter((id) => existentes.has(id))
  if (repetidas.length) return `Ya existen: ${resumenIds(repetidas)}. Cambia el número inicial.`
  return null
}

/** De dónde sale el precio de hoy de una habitación (origen que envía la API). */
export function etiquetaOrigen(origen) {
  if (origen === 'tipo') return 'hereda la base'
  if (origen === 'habitacion') return 'precio propio'
  if (origen === 'tarifa') return 'tarifa por fechas'
  return 'sin precio hoy'
}

/** Monto ingresado en el formulario → entero positivo o null (vacío = sin precio). */
export function montoONulo(valor) {
  const limpio = String(valor ?? '').replace(/[.$\s]/g, '')
  if (limpio === '') return null
  const n = Number(limpio)
  return Number.isInteger(n) && n > 0 ? n : NaN
}
