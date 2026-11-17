// IVA de los precios del hotel (entrega 1A.2). Módulo puro, sin JSX.
//
// Regla única, idéntica a servicio/iva.py (mismos vectores de prueba):
// - La fuente de verdad es el precio CON IVA en pesos enteros.
// - neto = redondeo medio-arriba(precio × 100 / (100 + tasa)); IVA = precio − neto.
// - Desde un neto: precio = redondeo medio-arriba(neto × (100 + tasa) / 100);
//   el neto se vuelve a derivar de ese precio (puede diferir en $1).
// Aritmética entera (tasa en milésimas de punto) para no depender de
// decimales de punto flotante.

export const TASA_POR_DEFECTO = 19

function milesimas(tasa) {
  return Math.round(Number(tasa) * 1000)
}

function dividirMedioArriba(a, b) {
  return Math.floor((2 * a + b) / (2 * b))
}

export function netoDesdePrecio(precioConIva, tasa = TASA_POR_DEFECTO) {
  return dividirMedioArriba(precioConIva * 100000, 100000 + milesimas(tasa))
}

export function precioDesdeNeto(neto, tasa = TASA_POR_DEFECTO) {
  return dividirMedioArriba(neto * (100000 + milesimas(tasa)), 100000)
}

/** {conIva, neto, iva} de un precio con IVA, o null sin precio. */
export function desglose(precioConIva, tasa = TASA_POR_DEFECTO) {
  if (precioConIva === null || precioConIva === undefined || Number.isNaN(precioConIva)) return null
  const neto = netoDesdePrecio(precioConIva, tasa)
  return { conIva: precioConIva, neto, iva: precioConIva - neto }
}

/** Monto ingresado → precio con IVA a guardar (en: 'con_iva' | 'neto'). */
export function aConIva(monto, en, tasa = TASA_POR_DEFECTO) {
  if (monto === null || monto === undefined || Number.isNaN(monto)) return monto
  return en === 'neto' ? precioDesdeNeto(monto, tasa) : monto
}

/**
 * Calculadora «¿y si subo X %?»: aplica el porcentaje sobre el neto o sobre
 * el precio final y devuelve el desglose resultante (el precio con IVA
 * redondeado a peso es lo que se guardaría).
 */
export function aumentar(precioConIva, porcentaje, sobre = 'final', tasa = TASA_POR_DEFECTO) {
  const pct = Number(porcentaje)
  if (!Number.isFinite(pct) || precioConIva === null || precioConIva === undefined) return null
  const factorMil = Math.round((100 + pct) * 1000)
  if (factorMil < 0) return null
  if (sobre === 'neto') {
    const neto = dividirMedioArriba(netoDesdePrecio(precioConIva, tasa) * factorMil, 100000)
    return desglose(precioDesdeNeto(neto, tasa), tasa)
  }
  return desglose(dividirMedioArriba(precioConIva * factorMil, 100000), tasa)
}

/** «19» o «19,5» para mostrar la tasa. */
export function tasaTexto(tasa) {
  return String(tasa).replace('.', ',')
}
