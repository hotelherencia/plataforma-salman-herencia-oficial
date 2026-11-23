import test from 'node:test'
import assert from 'node:assert/strict'
import { bytesDeBase64, escalaMaxima, MAX_BYTES_FOTO } from '../lib/imagen.js'

test('escalaMaxima reduce el lado mayor y nunca amplía', () => {
  assert.equal(escalaMaxima(4000, 3000, 1280), 0.32)
  assert.equal(escalaMaxima(800, 600, 1280), 1)
})

test('bytesDeBase64 coincide con el tamaño real y el tope cabe en el cuerpo HTTP', () => {
  const crudo = Buffer.alloc(1000, 7)
  assert.equal(bytesDeBase64(crudo.toString('base64')), 1000)
  assert.ok(Math.ceil((MAX_BYTES_FOTO * 4) / 3) < 256 * 1024)
})
