// Entrega 1A: vista previa del alta por lote y formulario de tipos.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  codigoDesdeNombre, etiquetaOrigen, idsDelLote, montoONulo, resumenIds, siguienteNumero, validarLote,
} from '../lib/tipos.js'

test('el lote numera igual que la API (prefijo + número con ceros)', () => {
  assert.deepEqual(idsDelLote('HAB-', 18, 3, 2), ['HAB-18', 'HAB-19', 'HAB-20'])
  assert.deepEqual(idsDelLote('P2-', 1, 2, 3), ['P2-001', 'P2-002'])
  assert.deepEqual(idsDelLote('HAB-', 99, 2, 2), ['HAB-99', 'HAB-100'])
  assert.equal(idsDelLote('HAB-', 1, 0, 2).length, 0)
  assert.equal(idsDelLote('HAB-', 1, 500, 3).length, 100)
})

test('sugiere el número siguiente al mayor existente', () => {
  const ids = Array.from({ length: 17 }, (_, i) => `HAB-${String(i + 1).padStart(2, '0')}`)
  assert.equal(siguienteNumero([...ids, 'HAB-SINT-101'], 'HAB-'), 18)
  assert.equal(siguienteNumero([], 'HAB-'), 1)
})

test('valida el lote y avisa los identificadores que ya existen', () => {
  const base = { tipoId: 'matrimonial', cantidad: 3, prefijo: 'HAB-', desde: 16, digitos: 2 }
  assert.match(validarLote(base, ['HAB-16', 'HAB-17']), /Ya existen: HAB-16, HAB-17/)
  assert.equal(validarLote({ ...base, desde: 18 }, ['HAB-17']), null)
  assert.match(validarLote({ ...base, cantidad: 101 }), /1 a 100/)
  assert.match(validarLote({ ...base, prefijo: 'mal/prefijo' }), /prefijo/)
  assert.match(validarLote({ ...base, tipoId: '' }), /tipo/)
})

test('resumen corto de identificadores', () => {
  assert.equal(resumenIds(['A1', 'A2']), 'A1, A2')
  assert.equal(resumenIds(idsDelLote('HAB-', 18, 10, 2)), 'HAB-18, HAB-19 … HAB-27 (10)')
})

test('código del tipo desde el nombre y montos del formulario', () => {
  assert.equal(codigoDesdeNombre('Matrimonial +1'), 'matrimonial_1')
  assert.equal(codigoDesdeNombre('Suite Jardín'), 'suite_jardin')
  assert.equal(montoONulo(''), null)
  assert.equal(montoONulo('55.000'), 55000)
  assert.ok(Number.isNaN(montoONulo('-3')))
  assert.equal(etiquetaOrigen('tipo'), 'hereda la base')
  assert.equal(etiquetaOrigen(null), 'sin precio hoy')
})
