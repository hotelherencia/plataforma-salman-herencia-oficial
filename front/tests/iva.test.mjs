import { test } from 'node:test'
import assert from 'node:assert/strict'
import { aConIva, aumentar, desglose, netoDesdePrecio, precioDesdeNeto } from '../lib/iva.js'

// Mismos vectores que servicio/tests/test_precio_unico_1a2.py.
const VECTORES_IVA = [
  [55000, 19, 46218, 8782],
  [47000, 19, 39496, 7504],
  [65000, 19, 54622, 10378],
  [119, 19, 100, 19],
  [1, 19, 1, 0],
  [100000, 0, 100000, 0],
  [55000, 19.5, 46025, 8975],
]
const VECTORES_NETO = [[50000, 19, 59500], [46218, 19, 54999], [46219, 19, 55001], [100, 19, 119], [1, 19, 1], [46025, 19.5, 55000]]

test('desglose con IVA → neto + IVA igual que el servidor', () => {
  for (const [precio, tasa, neto, iva] of VECTORES_IVA) {
    assert.deepEqual(desglose(precio, tasa), { conIva: precio, neto, iva })
  }
  for (let p = 1; p <= 200000; p += 997) {
    const d = desglose(p, 19)
    assert.equal(d.neto + d.iva, p)
  }
  assert.equal(desglose(null, 19), null)
})

test('neto ingresado → precio con IVA guardado', () => {
  for (const [neto, tasa, precio] of VECTORES_NETO) assert.equal(precioDesdeNeto(neto, tasa), precio)
  assert.equal(aConIva(50000, 'neto', 19), 59500)
  assert.equal(aConIva(55000, 'con_iva', 19), 55000)
  assert.equal(aConIva(null, 'neto', 19), null)
  assert.equal(netoDesdePrecio(59500, 19), 50000)
})

test('calculadora: aumento sobre el neto o sobre el precio final', () => {
  // +10 % sobre el final: 55.000 → 60.500 con IVA.
  assert.deepEqual(aumentar(55000, 10, 'final', 19), { conIva: 60500, neto: 50840, iva: 9660 })
  // +10 % sobre el neto: 50.000 neto → 55.000 neto → 65.450 con IVA.
  assert.deepEqual(aumentar(59500, 10, 'neto', 19), { conIva: 65450, neto: 55000, iva: 10450 })
  assert.deepEqual(aumentar(55000, 0, 'final', 19), desglose(55000, 19))
  assert.deepEqual(aumentar(55000, -10, 'final', 19), { conIva: 49500, neto: 41597, iva: 7903 })
  assert.equal(aumentar(55000, 'x', 'final', 19), null)
})
