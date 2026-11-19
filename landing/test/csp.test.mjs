/**
 * La landing la sirve un Apache estático. Si su política de seguridad (CSP) no deja pasar a Google reCAPTCHA ni
 * a la API de la plataforma, el formulario de contacto falla sin que ninguna otra prueba lo note (el E2E sirve la
 * landing sin cabeceras). Esta prueba fija la política que el sitio necesita y que `.htaccess` publica.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { PLATAFORMA_URL } from '../js/config.js'

const AQUI = dirname(fileURLToPath(import.meta.url))
const LANDING = join(AQUI, '..')
const POLITICA = readFileSync(join(LANDING, 'hosting', 'csp.txt'), 'utf8').trim()
const HTACCESS = readFileSync(join(LANDING, '.htaccess'), 'utf8')
const INDEX = readFileSync(join(LANDING, 'index.html'), 'utf8')

function directivas(texto) {
  const salida = new Map()
  for (const parte of texto.split(';')) {
    const [nombre, ...fuentes] = parte.trim().split(/\s+/)
    if (nombre) salida.set(nombre, fuentes)
  }
  return salida
}
const D = directivas(POLITICA)
// Un recurso se permite con su directiva, o con default-src si la directiva no está.
const fuentesDe = (directiva) => D.get(directiva) ?? D.get('default-src') ?? []

test('la política deja cargar el script de reCAPTCHA y abrir su marco', () => {
  assert.ok(fuentesDe('script-src').includes('https://www.google.com'), 'api.js sale de www.google.com')
  assert.ok(fuentesDe('script-src').includes('https://www.gstatic.com'), 'recaptcha__es.js sale de gstatic')
  assert.ok(fuentesDe('frame-src').includes('https://www.google.com'))
  assert.ok(fuentesDe('frame-src').includes('https://recaptcha.google.com'))
})

test('la política deja enviar el formulario a la API de la plataforma y a reCAPTCHA', () => {
  const origen = new URL(PLATAFORMA_URL).origin
  assert.ok(fuentesDe('connect-src').includes(origen), `connect-src debe incluir ${origen}`)
  assert.ok(fuentesDe('connect-src').includes('https://www.google.com'))
})

test('la política deja cargar las tipografías de Google que usa el sitio', () => {
  assert.ok(fuentesDe('style-src').includes('https://fonts.googleapis.com'))
  assert.ok(fuentesDe('font-src').includes('https://fonts.gstatic.com'))
})

test('los scripts y estilos en línea de index.html están permitidos', () => {
  const enLinea = [...INDEX.matchAll(/<script(?![^>]*\b(?:src=|type="application\/ld\+json")[^>]*>)[^>]*>/g)]
  assert.ok(enLinea.length > 0, 'index.html tiene scripts en línea (el módulo de arranque)')
  assert.ok(fuentesDe('script-src').includes("'unsafe-inline'"))
  assert.ok(fuentesDe('style-src').includes("'unsafe-inline'"))
})

test('todo origen externo que carga index.html está cubierto por la política', () => {
  const externos = new Set()
  for (const m of INDEX.matchAll(/<(?:script|link)[^>]+(?:src|href)="(https:\/\/[^"]+)"[^>]*>/g)) {
    if (/rel="(?:canonical|alternate|preconnect)"/.test(m[0])) continue
    externos.add(new URL(m[1]).origin)
  }
  const permitidos = new Set([...fuentesDe('style-src'), ...fuentesDe('script-src'), ...fuentesDe('font-src')])
  for (const origen of externos) assert.ok(permitidos.has(origen), `${origen} no está permitido por la política`)
})

test('la política no abre de más', () => {
  assert.ok(!/\*/.test(POLITICA.replace(/'self'/g, '')), 'sin comodines')
  assert.ok(!POLITICA.includes("'unsafe-eval'"))
  assert.deepEqual(D.get('object-src'), ["'none'"])
  assert.deepEqual(D.get('frame-ancestors'), ["'none'"])
  assert.deepEqual(D.get('base-uri'), ["'self'"])
})

test('.htaccess publica exactamente esa política', () => {
  assert.ok(HTACCESS.includes(`Header always set Content-Security-Policy "${POLITICA}"`), '.htaccess y hosting/csp.txt divergen')
})
