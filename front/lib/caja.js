// Reglas puras de caja (#365), sin JSX para probarlas con node --test.
import { rutValido } from './contabilidad.js'

/** Clasifica el pago frente al saldo: total, parcial (queda saldo) o exceso. */
export function clasificarPago(monto, saldo) {
  const m = Number(monto)
  if (!Number.isFinite(m) || m <= 0 || saldo === null || saldo === undefined) return null
  if (m === saldo) return { tipo: 'total', diferencia: 0 }
  if (m < saldo) return { tipo: 'parcial', diferencia: saldo - m }
  return { tipo: 'exceso', diferencia: m - Math.max(saldo, 0) }
}

// --- Fase 1 contable (2026-11-19): turnos, medios, arqueo y cierre diario ---

export const MEDIOS = [
  ['efectivo', 'Efectivo'],
  ['debito', 'Tarjeta de débito'],
  ['credito', 'Tarjeta de crédito'],
  ['transferencia', 'Transferencia'],
]

const NOMBRES_MEDIO = Object.fromEntries([...MEDIOS, ['no_informado', 'Sin medio informado']])

export function nombreMedio(medio) {
  return NOMBRES_MEDIO[medio] || 'Sin medio informado'
}

export const DOCUMENTOS = [
  ['boleta', 'Boleta'],
  ['factura', 'Factura'],
  ['sin_documento', 'Sin documento (p. ej. abono que se documenta después)'],
]

const NOMBRES_DOCUMENTO = { boleta: 'Boleta', factura: 'Factura', sin_documento: 'Sin documento', pendiente: 'Por indicar' }

export function nombreDocumento(tipo) {
  return NOMBRES_DOCUMENTO[tipo] || 'Por indicar'
}

const NOMBRES_MOVIMIENTO = { cobro: 'Cobro', reverso_cobro: 'Reverso de cobro', retiro_deposito: 'Retiro para depósito' }

export function nombreMovimiento(tipo) {
  return NOMBRES_MOVIMIENTO[tipo] || tipo
}

export const esTarjeta = (medio) => medio === 'debito' || medio === 'credito'

/** Suma del arqueo: { '20000': 2, '500': 3 } → 41500. Ignora vacíos. */
export function totalArqueo(conteo) {
  return Object.entries(conteo || {}).reduce((suma, [valor, cantidad]) => {
    const n = Number(cantidad)
    return Number.isInteger(n) && n > 0 ? suma + Number(valor) * n : suma
  }, 0)
}

/** Conteo para la API: solo cantidades enteras mayores que cero. */
export function arqueoParaApi(conteo) {
  return Object.fromEntries(
    Object.entries(conteo || {})
      .map(([valor, cantidad]) => [String(valor), Number(cantidad)])
      .filter(([, n]) => Number.isInteger(n) && n > 0),
  )
}

/** PCI: true si el texto parece un número completo de tarjeta (12+ dígitos). */
export function pareceNumeroDeTarjeta(texto) {
  return (String(texto || '').match(/\d[\d\s-]{11,}\d/g) || []).some((t) => t.replace(/\D/g, '').length >= 12)
}

/** Diferencia de cuadratura en palabras: sobrante, faltante o cuadra. */
export function textoDiferencia(diferencia) {
  const d = Number(diferencia) || 0
  if (d === 0) return 'Cuadra'
  const monto = `$${Math.abs(d).toLocaleString('es-CL')}`
  return d > 0 ? `Sobrante de ${monto}` : `Faltante de ${monto}`
}

/** Valida en el navegador los datos del pago antes de enviarlos (la API
 *  vuelve a validar). Devuelve el mensaje de error o null. */
export function validarDatosPago({ medio, codigo, ultimos4, documento, receptor }) {
  if (!medio) return 'Elige el medio de pago.'
  if (esTarjeta(medio)) {
    if (!String(codigo || '').trim()) return 'Anota el código de autorización del voucher.'
    if (ultimos4 && !/^\d{4}$/.test(ultimos4)) return 'Los últimos 4 dígitos de la tarjeta son exactamente 4 números.'
  }
  if ([codigo, ultimos4].some(pareceNumeroDeTarjeta)) {
    return 'No anotes el número completo de la tarjeta: solo los últimos 4 dígitos y el código de autorización.'
  }
  if (documento === 'factura') {
    const faltan = [['rut', 'RUT'], ['razon_social', 'razón social'], ['giro', 'giro'], ['direccion', 'dirección'], ['comuna', 'comuna']]
      .filter(([k]) => !String(receptor?.[k] || '').trim()).map(([, n]) => n)
    if (faltan.length) return `Para la factura falta: ${faltan.join(', ')}.`
    if (!rutValido(receptor.rut)) return 'El RUT no es válido: revisa el número y el dígito verificador.'
  }
  return null
}
