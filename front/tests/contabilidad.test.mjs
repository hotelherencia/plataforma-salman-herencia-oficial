import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  formatearRut, limpiarRut, rotuloMovimiento, rutValido, saldoVisible,
} from '../lib/contabilidad.js'

test('el RUT se limpia a números y dígito verificador', () => {
  assert.equal(limpiarRut('12.345.678-5'), '123456785')
  assert.equal(limpiarRut(' 7.000.013-k '), '7000013K')
  assert.equal(limpiarRut(''), '')
})

test('el RUT se valida por su dígito verificador', () => {
  assert.equal(rutValido('12.345.678-5'), true)
  assert.equal(rutValido('7000013K'), true)
  assert.equal(rutValido('12.345.678-9'), false)
  assert.equal(rutValido('abc'), false)
  assert.equal(rutValido(''), false)
})

test('el RUT se muestra con puntos y guion', () => {
  assert.equal(formatearRut('123456785'), '12.345.678-5')
  assert.equal(formatearRut('7000013K'), '7.000.013-K')
  assert.equal(formatearRut(null), '')
})

test('los movimientos se rotulan en castellano claro', () => {
  assert.equal(rotuloMovimiento('cargo'), 'Cargo')
  assert.equal(rotuloMovimiento('reverso'), 'Reverso de cargo')
  assert.equal(rotuloMovimiento('pago'), 'Pago')
  assert.equal(rotuloMovimiento('reverso_pago'), 'Reverso de pago')
  assert.equal(rotuloMovimiento('cargo_directo'), 'Cargo directo (sin habitación)')
  assert.equal(rotuloMovimiento('egreso_operacional'), 'Egreso operacional')
  assert.equal(rotuloMovimiento('reverso_directo'), 'Reverso directo')
})

test('el saldo explica si falta pagar o queda a favor', () => {
  assert.equal(saldoVisible({ pendiente_clp: 70000 }).texto, 'Pendiente de pago')
  assert.equal(saldoVisible({ pendiente_clp: 0 }).texto, 'Cuenta saldada')
  assert.equal(saldoVisible({ pendiente_clp: -3000 }).texto, 'Saldo a favor del cliente')
  assert.equal(saldoVisible({ pendiente_clp: -3000 }).monto, 3000)
})
