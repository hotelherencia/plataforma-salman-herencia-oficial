// Formato chileno para lo que ve el equipo (UI/UX 2026-11-19, segunda pasada):
// fechas dd/mm/aaaa sin depender del idioma del navegador, decimales con coma
// y plurales escritos (nunca «solicitud(es)»).

const NUMERO = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** 0.123 → «12,3 %»; null/undefined → texto alternativo. */
export function porcentaje(fraccion, sinDato = 'sin muestra') {
  if (fraccion === null || fraccion === undefined || Number.isNaN(Number(fraccion))) return sinDato
  return `${NUMERO.format(Number(fraccion) * 100)} %`
}

/** Número con un decimal y coma chilena: 2.5 → «2,5». */
export function decimal(valor) {
  return NUMERO.format(Number(valor))
}

/** plural(1, 'noche') → «1 noche»; plural(3, 'solicitud', 'solicitudes') → «3 solicitudes». */
export function plural(n, singular, pluralTexto = `${singular}s`) {
  const cantidad = Number(n) || 0
  return `${cantidad.toLocaleString('es-CL')} ${cantidad === 1 ? singular : pluralTexto}`
}

function valida(a, m, d) {
  const f = new Date(Date.UTC(a, m - 1, d))
  return f.getUTCFullYear() === a && f.getUTCMonth() === m - 1 && f.getUTCDate() === d && a >= 1900 && a <= 2200
}

const dos = (n) => String(n).padStart(2, '0')

/** Texto escrito por la persona → «aaaa-mm-dd» o null. Acepta dd/mm/aaaa,
 *  d-m-aaaa, ddmmaaaa y también aaaa-mm-dd (valor de máquina). */
export function fechaDesdeTexto(texto) {
  const t = String(texto || '').trim()
  let a, m, d
  let r = t.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/)
  if (r) [a, m, d] = [r[1], r[2], r[3]].map(Number)
  else if ((r = t.match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$/))) [d, m, a] = [r[1], r[2], r[3]].map(Number)
  else if ((r = t.match(/^(\d{2})(\d{2})(\d{4})$/))) [d, m, a] = [r[1], r[2], r[3]].map(Number)
  else return null
  return valida(a, m, d) ? `${a}-${dos(m)}-${dos(d)}` : null
}

/** «aaaa-mm-dd» → «dd/mm/aaaa» (vacío si no es fecha). */
export function fechaATexto(iso) {
  const r = String(iso || '').match(/^(\d{4})-(\d{2})-(\d{2})$/)
  return r ? `${r[3]}/${r[2]}/${r[1]}` : ''
}

/** Mientras se escribe: agrega las barras («19112026» → «19/11/2026»,
 *  «19/112» → «19/11/2»). No agrega barras al final, así borrar funciona. */
export function mascaraFecha(texto) {
  const t = String(texto || '')
  let r
  if (/^\d{3,8}$/.test(t)) {
    const dig = t
    return dig.length <= 4 ? `${dig.slice(0, 2)}/${dig.slice(2)}` : `${dig.slice(0, 2)}/${dig.slice(2, 4)}/${dig.slice(4)}`
  }
  if ((r = t.match(/^(\d{1,2})\/(\d{3,6})$/))) return `${r[1]}/${r[2].slice(0, 2)}/${r[2].slice(2)}`
  return t
}

/** «aaaa-mm-dd» → «dd/mm» para cabeceras de columnas (nunca mm-dd). */
export function fechaCorta(iso) {
  const r = String(iso || '').match(/^\d{4}-(\d{2})-(\d{2})$/)
  return r ? `${r[2]}/${r[1]}` : String(iso || '')
}
