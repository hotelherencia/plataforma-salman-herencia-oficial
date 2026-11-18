import { test } from 'node:test'
import assert from 'node:assert/strict'
import { clasificarPago } from '../lib/caja.js'

test('#365: clasifica pago total, parcial y en exceso', () => {
  assert.deepEqual(clasificarPago(100, 100), { tipo: 'total', diferencia: 0 })
  assert.deepEqual(clasificarPago(60, 100), { tipo: 'parcial', diferencia: 40 })
  assert.deepEqual(clasificarPago(130, 100), { tipo: 'exceso', diferencia: 30 })
  assert.deepEqual(clasificarPago(50, -20), { tipo: 'exceso', diferencia: 50 })
  assert.equal(clasificarPago('', 100), null)
  assert.equal(clasificarPago(10, null), null)
})
