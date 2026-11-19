// Exportación de leads y contactos por fecha o rango (2026-11-19). Puro, sin JSX.

/** CSV con comillas dobles escapadas y BOM para que Excel lea tildes. */
export function aCsv(filas) {
  const celda = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  return '\uFEFF' + filas.map((f) => f.map(celda).join(',')).join('\n')
}

/** Valida el rango «desde/hasta» (aaaa-mm-dd, ambos opcionales). */
export function errorRango(desde, hasta) {
  if (desde && hasta && desde > hasta) return 'La fecha «desde» debe ser anterior o igual a «hasta».'
  return null
}

/** Parámetros de consulta del rango; sin «desde» pide todos (sin el corte de la bandeja). */
export function parametrosRango(desde, hasta) {
  const q = new URLSearchParams()
  if (desde) q.set('desde', desde)
  if (hasta) q.set('hasta', hasta)
  if (!desde) q.set('todos', 'true')
  return q
}

/** Sufijo del nombre de archivo: «2026-11-01_a_2026-11-19», «desde-…», «hasta-…» o «todo». */
export function sufijoRango(desde, hasta) {
  if (desde && hasta) return `${desde}_a_${hasta}`
  if (desde) return `desde-${desde}`
  if (hasta) return `hasta-${hasta}`
  return 'todo'
}
