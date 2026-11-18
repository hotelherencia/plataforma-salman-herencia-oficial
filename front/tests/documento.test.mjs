import { test } from 'node:test'
import assert from 'node:assert/strict'
import { validarDocumento, digitoVerificador } from '../lib/documento.js'

test('#367: RUT válido se normaliza; dígito incorrecto se rechaza', () => {
  assert.equal(digitoVerificador('12345678'), '5')
  assert.equal(digitoVerificador('11111111'), '1')
  assert.deepEqual(validarDocumento('rut', '123456785'), { ok: true, valor: '12.345.678-5' })
  assert.equal(validarDocumento('rut', '12.345.678-9').ok, false)
  assert.equal(validarDocumento('rut', 'abc').ok, false)
})

test('#367: pasaporte y documento vacío', () => {
  assert.deepEqual(validarDocumento('pasaporte', 'ab 123456'), { ok: true, valor: 'AB123456' })
  assert.equal(validarDocumento('pasaporte', 'A-1').ok, false)
  assert.equal(validarDocumento('rut', '').ok, false)
})
