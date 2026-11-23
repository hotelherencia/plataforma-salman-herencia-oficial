import test from 'node:test'
import assert from 'node:assert/strict'
import { variacion, flechaVariacion, mesAnterior, alertasDueno } from '../lib/resumen-dueno.js'

test('variación contra el mes anterior', () => {
  assert.equal(variacion(120, 100), 20)
  assert.equal(variacion(80, 100), -20)
  assert.equal(variacion(5, 0), null)
  assert.equal(variacion(null, 100), null)
  assert.match(flechaVariacion(20), /▲ 20 %/)
  assert.match(flechaVariacion(-5), /▼ 5 %/)
  assert.equal(flechaVariacion(null), 'sin base para comparar')
})
test('mes anterior con cambio de año', () => {
  assert.deepEqual(mesAnterior('2026-11-01'), { desde: '2026-10-01', hasta: '2026-11-01' })
  assert.deepEqual(mesAnterior('2027-01-01'), { desde: '2026-12-01', hasta: '2027-01-01' })
})
test('alertas solo las que existen y en orden', () => {
  assert.deepEqual(alertasDueno({}), [])
  const a = alertasDueno({ atencionTotal: 2, cxcVencidoClp: 50000, sugerenciasNuevas: 1 })
  assert.deepEqual(a.map((x) => x.clave), ['cxc', 'atencion', 'sug'])
})
