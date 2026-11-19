// Reglas puras de contabilidad (fase 2.1), sin JSX para probarlas con node --test.

/** RUT como lo guarda el servidor: solo números y dígito verificador, sin puntos ni guion. */
export function limpiarRut(texto) {
  return String(texto || '').replace(/[.\s-]/g, '').toUpperCase()
}

function digitoVerificador(cuerpo) {
  let suma = 0
  let factor = 2
  for (const d of String(cuerpo).split('').reverse()) {
    suma += Number(d) * factor
    factor = factor === 7 ? 2 : factor + 1
  }
  const resto = 11 - (suma % 11)
  return resto === 11 ? '0' : resto === 10 ? 'K' : String(resto)
}

export function rutValido(texto) {
  const limpio = limpiarRut(texto)
  if (!/^\d{7,8}[0-9K]$/.test(limpio)) return false
  return digitoVerificador(limpio.slice(0, -1)) === limpio.slice(-1)
}

/** `123456785` → `12.345.678-5` (solo para mostrar). */
export function formatearRut(clave) {
  const limpio = limpiarRut(clave)
  if (!/^\d{7,8}[0-9K]$/.test(limpio)) return ''
  const cuerpo = limpio.slice(0, -1).replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${cuerpo}-${limpio.slice(-1)}`
}

const ROTULOS = {
  cargo: 'Cargo',
  reverso: 'Reverso de cargo',
  pago: 'Pago',
  reverso_pago: 'Reverso de pago',
  cargo_directo: 'Cargo directo (sin habitación)',
  egreso_operacional: 'Egreso operacional',
  reverso_directo: 'Reverso directo',
}

export function rotuloMovimiento(tipo) {
  return ROTULOS[tipo] || 'Movimiento'
}

/** Qué decirle a recepción sobre lo que falta por pagar. */
export function saldoVisible(saldo) {
  const p = Number(saldo?.pendiente_clp || 0)
  if (p > 0) return { texto: 'Pendiente de pago', monto: p, tono: 'pendiente' }
  if (p < 0) return { texto: 'Saldo a favor del cliente', monto: -p, tono: 'favor' }
  return { texto: 'Cuenta saldada', monto: 0, tono: 'saldada' }
}
