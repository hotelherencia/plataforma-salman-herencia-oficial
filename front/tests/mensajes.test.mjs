// Mensajes del canal público (fix-e2e): ningún detalle técnico llega al visitante.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { traducirDetalle } from '../lib/mensajes.js'

test('503 de servicio anterior se traduce a un mensaje con salida por WhatsApp', () => {
  const m = traducirDetalle('canal público temporalmente no disponible')
  assert.match(m, /WhatsApp/)
  assert.doesNotMatch(m, /canal público/)
})

test('403 de captcha se traduce a un mensaje accionable', () => {
  const m = traducirDetalle('no se pudo verificar el envío')
  assert.match(m, /Recarga la página/)
})

test('detalle ya amable pasa sin cambios', () => {
  const d = 'No pudimos recibir tu solicitud en este momento. Escríbenos por WhatsApp al +56 9 5649 1501 o inténtalo de nuevo más tarde.'
  assert.equal(traducirDetalle(d), d)
})

test('claves heredadas de Object.prototype no se traducen', () => {
  assert.equal(traducirDetalle('constructor'), 'constructor')
})
