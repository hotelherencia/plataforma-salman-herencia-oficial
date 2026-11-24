import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { gestionaRecepcion } from '../lib/roles.js'

const fuente = readFileSync(new URL('../app/_componentes/asistente-ayuda.js', import.meta.url), 'utf8')
const layout = readFileSync(new URL('../app/layout.js', import.meta.url), 'utf8')

test('la ayuda solo se ofrece a recepción y administración dentro de /hotel', () => {
  assert.match(fuente, /ruta\.startsWith\('\/hotel'\)/)
  assert.match(fuente, /gestionaRecepcion/)
  for (const rol of ['recepcion', 'admin_hotel', 'administrador']) assert.equal(gestionaRecepcion(rol), true, rol)
  for (const rol of ['caja', 'aseo', 'dueno']) assert.equal(gestionaRecepcion(rol), false, rol)
})

test('la ayuda llama solo a /hotel/asistente, sin pop-ups nativos y con controles accesibles', () => {
  assert.match(fuente, /'\/hotel\/asistente'/)
  assert.doesNotMatch(fuente, /window\.(alert|confirm|prompt)/)
  assert.doesNotMatch(fuente, /\/hotel\/reservas|\/hotel\/caja|\/hotel\/huespedes/)
  assert.match(fuente, /aria-expanded/)
  assert.match(fuente, /role="alert"/)
})

test('la ayuda está montada una sola vez en el layout', () => {
  assert.equal((layout.match(/<AsistenteAyuda \/>/g) || []).length, 1)
})

test('el asistente usa la identidad visual HerencIA', () => {
  assert.match(fuente, /HerencIA/)
})
