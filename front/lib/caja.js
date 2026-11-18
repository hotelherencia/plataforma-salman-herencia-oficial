// Reglas puras de caja (#365), sin JSX para probarlas con node --test.

/** Clasifica el pago frente al saldo: total, parcial (queda saldo) o exceso. */
export function clasificarPago(monto, saldo) {
  const m = Number(monto)
  if (!Number.isFinite(m) || m <= 0 || saldo === null || saldo === undefined) return null
  if (m === saldo) return { tipo: 'total', diferencia: 0 }
  if (m < saldo) return { tipo: 'parcial', diferencia: saldo - m }
  return { tipo: 'exceso', diferencia: m - Math.max(saldo, 0) }
}
