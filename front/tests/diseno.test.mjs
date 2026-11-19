// Sistema de diseño de la plataforma (UI/UX 2026-11-19): tokens con
// contraste AA, una sola capa de componentes, fuentes propias, tablas
// accesibles con teclado y vocabulario Llegada/Salida en pantalla.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const raiz = new URL('..', import.meta.url).pathname
const leer = (p) => readFileSync(join(raiz, p), 'utf8')
const diseno = leer('app/diseno.css')

function tokens(css) {
  const bloque = css.match(/:root\s*{([\s\S]*?)\n}/)[1]
  const t = {}
  for (const [, nombre, valor] of bloque.matchAll(/--([\w-]+):\s*([^;]+);/g)) t[nombre] = valor.trim()
  return t
}

function luminancia(hex) {
  const h = hex.replace('#', '')
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function contraste(a, b) {
  const [x, y] = [luminancia(a), luminancia(b)].sort((m, n) => n - m)
  return (x + 0.05) / (y + 0.05)
}

function archivos(dir) {
  return readdirSync(join(raiz, dir)).flatMap((n) => {
    const rel = join(dir, n)
    if (statSync(join(raiz, rel)).isDirectory()) return archivos(rel)
    return /\.(js|jsx)$/.test(n) ? [rel] : []
  })
}

test('la capa de diseño se carga después de globals.css', () => {
  const layout = leer('app/layout.js')
  const g = layout.indexOf("import './globals.css'")
  const d = layout.indexOf("import './diseno.css'")
  assert.ok(g >= 0 && d > g, 'diseno.css debe importarse justo después de globals.css')
})

test('los pares de texto y fondo del sistema cumplen WCAG AA (4,5:1)', () => {
  const t = tokens(diseno)
  const pares = [
    ['c-tinta', 'c-fondo'], ['c-tinta', 'c-superficie'], ['c-tinta-2', 'c-fondo'],
    ['c-tinta-2', 'c-superficie'], ['c-tinta-2', 'c-superficie-2'], ['c-tinta-3', 'c-superficie'],
    ['c-verde', 'c-superficie'], ['c-verde', 'c-verde-suave'], ['c-terracota', 'c-superficie-2'],
    ['c-terracota', 'c-terracota-suave'], ['c-exito', 'c-exito-fondo'], ['c-aviso', 'c-aviso-fondo'],
    ['c-error', 'c-error-fondo'], ['c-info', 'c-info-fondo'],
  ]
  for (const [texto, fondo] of pares) {
    const r = contraste(t[texto], t[fondo])
    assert.ok(r >= 4.5, `${texto} sobre ${fondo}: ${r.toFixed(2)}:1`)
  }
  // Botón primario: texto blanco sobre verde de marca.
  assert.ok(contraste('#ffffff', t['c-verde']) >= 4.5)
})

test('el sistema define escalas completas de tipografía, espacio, radios y sombras', () => {
  const t = tokens(diseno)
  for (const n of ['t-xs', 't-sm', 't-base', 't-md', 't-lg', 't-xl', 't-2xl', 't-3xl']) assert.ok(t[n], n)
  for (const n of ['e-1', 'e-2', 'e-3', 'e-4', 'e-6', 'e-8']) assert.ok(t[n], n)
  for (const n of ['r-sm', 'r-md', 'r-lg', 'r-pill', 's-1', 's-2', 's-3']) assert.ok(t[n], n)
  // Los nombres antiguos apuntan al sistema: no hay dos paletas en paralelo.
  for (const n of ['papel', 'tinta', 'tinta-suave', 'linea', 'radio', 'sombra']) {
    assert.match(t[n], /^var\(--/, `--${n} debe ser un alias del sistema`)
  }
})

test('sin fuentes externas: la CSP sólo permite fuentes propias', () => {
  for (const css of [diseno, leer('app/globals.css')]) {
    assert.doesNotMatch(css, /fonts\.(googleapis|gstatic)\.com|@import\s+url\(http/i)
  }
})

test('toda tabla desplazable se puede recorrer con teclado y tiene nombre', () => {
  for (const archivo of archivos('app')) {
    const src = leer(archivo)
    for (const m of src.matchAll(/<div className="(tabla-contenedor|rejilla-ocupacion)"([^>]*)>/g)) {
      assert.match(m[2], /tabIndex=\{0\}/, `${archivo}: ${m[1]} sin tabIndex`)
      assert.match(m[2], /role="region"/, `${archivo}: ${m[1]} sin role=region`)
      assert.match(m[2], /aria-label="[^"]+"/, `${archivo}: ${m[1]} sin nombre`)
    }
  }
})

test('pantallas y mensajes dicen Llegada y Salida, no check-in ni check-out', () => {
  // Sólo textos: literales y texto JSX (no identificadores como checkOut()).
  const textos = (src) => [
    ...src.matchAll(/'[^'\n]*'|"[^"\n]*"|`[^`]*`/g),
    ...src.matchAll(/>([^<>{}();=]*)</g),
  ].map((m) => m[0])
  for (const archivo of ['app/hotel/salida/page.js', 'app/hotel/estadia/page.js', 'app/hotel/panel/page.js',
    'app/hotel/ocupacion/page.js', 'app/hotel/reservas/[id]/page.js']) {
    const sinComentarios = leer(archivo).replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')
    for (const t of textos(sinComentarios)) assert.doesNotMatch(t, /\bcheck-?(in|out)\b/i, `${archivo}: ${t}`)
  }
  const api = leer('lib/api.js')
  assert.match(api, /Llegada registrada para la reserva/)
  assert.match(api, /Salida registrada para la reserva/)
  assert.doesNotMatch(api, /Check-(in|out) confirmado/)
})

test('la barra lateral no muestra identificadores internos y agrupa los módulos en preparación', () => {
  const barra = leer('app/barra.jsx')
  assert.doesNotMatch(barra, /usuario\.empresa_id/)
  assert.doesNotMatch(barra, /className="nav-cerrado"/)
  assert.match(barra, /Próximamente:/)
})

test('el panel muestra la situación de hoy antes de los filtros del periodo', () => {
  const panel = leer('app/hotel/panel/page.js')
  const hoy = panel.indexOf('aria-label="Situación de hoy"')
  const filtros = panel.indexOf('className="panel-filtros"')
  assert.ok(hoy > 0 && filtros > hoy)
  assert.doesNotMatch(panel, /Fecha de corte del servidor/)
})
