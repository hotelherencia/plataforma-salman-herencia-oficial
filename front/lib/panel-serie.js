// Lectura amigable de la serie de ocupación por noche (panel operativo).
// No recalcula indicadores oficiales: solo resume y dibuja lo que entrega la API.

function sumar(iso, dias) {
  const d = new Date(`${iso}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + dias)
  return d.toISOString().slice(0, 10)
}

/** Lunes de la semana de `iso` y el lunes siguiente (hasta sin incluir). */
export function rangoSemana(iso) {
  const dow = new Date(`${iso}T12:00:00Z`).getUTCDay() // 0 = domingo
  const lunes = sumar(iso, -((dow + 6) % 7))
  return { desde: lunes, hasta: sumar(lunes, 7) }
}

/** Primer día del mes de `iso` y el primer día del mes siguiente. */
export function rangoMes(iso) {
  const [a, m] = iso.split('-').map(Number)
  const sig = m === 12 ? `${a + 1}-01-01` : `${a}-${String(m + 1).padStart(2, '0')}-01`
  return { desde: `${iso.slice(0, 7)}-01`, hasta: sig }
}

/** % de unidades comprometidas (en casa + reservadas) en una noche de la serie. */
export function porcentajeNoche(noche) {
  const max = noche.unidades || 0
  if (!max) return null
  const oc = noche.ocupadas_estadias ?? 0
  const res = Math.max(0, (noche.reservadas || 0) - oc)
  return Math.min(100, Math.round(((oc + res) / max) * 100))
}

export function resumenSerie(serie) {
  const pts = (serie || []).map((n) => ({ fecha: n.fecha, pct: porcentajeNoche(n) })).filter((p) => p.pct !== null)
  if (!pts.length) return null
  const promedio = Math.round(pts.reduce((a, p) => a + p.pct, 0) / pts.length)
  const pico = pts.reduce((a, p) => (p.pct > a.pct ? p : a))
  const valle = pts.reduce((a, p) => (p.pct < a.pct ? p : a))
  return { promedio, pico, valle, puntos: pts }
}

/** Puntos del SVG (viewBox 0..100 x 0..100, el 100% arriba). */
export function puntosLinea(puntos) {
  const n = puntos.length
  return puntos.map((p, i) => ({
    x: n === 1 ? 50 : (i / (n - 1)) * 100,
    y: 100 - p.pct,
    ...p,
  }))
}
