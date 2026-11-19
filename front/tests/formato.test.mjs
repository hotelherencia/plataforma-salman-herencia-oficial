// Segunda pasada UI/UX (2026-11-19): formato chileno, plurales escritos, barra
// lateral a todo el alto, menú compacto en tablet y aviso de reCAPTCHA.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { decimal, fechaATexto, fechaDesdeTexto, mascaraFecha, plural, porcentaje } from '../lib/formato.js'

const raiz = new URL('..', import.meta.url).pathname
const leer = (p) => readFileSync(join(raiz, p), 'utf8')

function archivos(dir) {
  return readdirSync(join(raiz, dir)).flatMap((n) => {
    const r = join(dir, n)
    return statSync(join(raiz, r)).isDirectory() ? archivos(r) : /\.(js|jsx)$/.test(n) ? [r] : []
  })
}

test('porcentajes y decimales con coma chilena', () => {
  assert.equal(porcentaje(0), '0,0 %')
  assert.equal(porcentaje(0.1234), '12,3 %')
  assert.equal(porcentaje(1), '100,0 %')
  assert.equal(porcentaje(null), 'sin muestra')
  assert.equal(decimal(2.5), '2,5')
})

test('plurales escritos, nunca «(s)» ni «(es)»', () => {
  assert.equal(plural(1, 'solicitud', 'solicitudes'), '1 solicitud')
  assert.equal(plural(3, 'solicitud', 'solicitudes'), '3 solicitudes')
  assert.equal(plural(0, 'noche'), '0 noches')
  assert.equal(plural(1, 'noche'), '1 noche')
  const culpables = [...archivos('app'), ...archivos('lib')].filter((f) => {
    const s = leer(f).split('\n').filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l)).join('\n')
    return /(?<![.\wáéíóúñ])[a-záéíóúñ]+\((s|es)\)/i.test(s)
  })
  assert.deepEqual(culpables, [])
})

test('fechas dd/mm/aaaa: se escriben, se validan y salen como aaaa-mm-dd', () => {
  assert.equal(fechaDesdeTexto('19/11/2026'), '2026-11-19')
  assert.equal(fechaDesdeTexto('1/2/2026'), '2026-02-01')
  assert.equal(fechaDesdeTexto('19112026'), '2026-11-19')
  assert.equal(fechaDesdeTexto('2026-11-19'), '2026-11-19')
  assert.equal(fechaDesdeTexto('31/02/2026'), null)
  assert.equal(fechaDesdeTexto('11/19/2026'), null, 'el orden estadounidense no se acepta')
  assert.equal(fechaATexto('2026-11-19'), '19/11/2026')
  assert.equal(fechaATexto(''), '')
  assert.equal(mascaraFecha('1911'), '19/11')
  assert.equal(mascaraFecha('19112026'), '19/11/2026')
  assert.equal(mascaraFecha('19/112'), '19/11/2')
  assert.equal(mascaraFecha('19/'), '19/', 'borrar no reinserta barras')
})

test('todo campo de fecha pasa por el campo chileno (sin <input type="date"> suelto)', () => {
  const api = leer('lib/api.js')
  assert.match(api, /if \(props\.type === 'date'\) return <CampoFecha/)
  assert.match(api, /placeholder="dd\/mm\/aaaa"/)
  const sueltos = archivos('app').filter((f) => /<input[^>]*type="date"/.test(leer(f)))
  assert.deepEqual(sueltos, [])
})

test('barra lateral: fondo a todo el alto y menú fijo; ≤1024 px pasa al botón Menú', () => {
  const barra = leer('app/barra.jsx')
  const diseno = leer('app/diseno.css')
  const globals = leer('app/globals.css')
  assert.match(barra, /<aside className="barra">\s*{[^}]*}\s*<div className="barra-fija">/)
  assert.match(diseno, /\.barra-fija {[^}]*position: sticky;[^}]*height: 100dvh;/)
  assert.match(diseno, /\.barra {[^}]*align-self: stretch;[^}]*min-height: 100dvh;/)
  assert.match(globals, /@media \(max-width: 1024px\) {\s*\.aplicacion {\s*flex-direction: column;\s*}\s*[^@]*\.barra {\s*display: none;/)
  assert.match(barra, /className="boton-menu-icono"/)
  assert.match(barra, /src={LOGO\.hojaSvg}/)
})

test('indicadores: sin porcentajes con punto ni «x (y noches)» en la cifra', () => {
  const panel = leer('app/hotel/panel/page.js')
  assert.doesNotMatch(panel, /toFixed\(1\)/)
  assert.doesNotMatch(panel, /noches\)`/)
  assert.match(panel, /Ocupación \(estadías reales\)/)
})

test('reCAPTCHA: sello oculto solo con el aviso de Google junto al envío', () => {
  assert.match(leer('app/diseno.css'), /\.grecaptcha-badge {\s*visibility: hidden !important;/)
  const reservar = leer('app/reservar/page.js')
  const aviso = reservar.match(/<p className="recaptcha-aviso">[\s\S]*?<\/p>/)
  assert.ok(aviso)
  assert.match(aviso[0], /policies\.google\.com\/privacy/)
  assert.match(aviso[0], /policies\.google\.com\/terms/)
  assert.ok(reservar.indexOf('recaptcha-aviso') < reservar.lastIndexOf('</form>'))
})

test('logo del acceso nítido en pantallas de alta densidad', () => {
  assert.match(leer('app/login/pantalla.jsx'), /srcSet={`\${LOGO\.h128} 1x, \${LOGO\.h256} 2x`}/)
})

test('cabeceras de noches en dd/mm (nunca mm-dd)', async () => {
  const { fechaCorta } = await import('../lib/formato.js')
  assert.equal(fechaCorta('2026-11-19'), '19/11')
  for (const f of ['app/hotel/ocupacion/page.js', 'app/hotel/panel/page.js']) assert.doesNotMatch(leer(f), /\.slice\(5\)/, f)
})
