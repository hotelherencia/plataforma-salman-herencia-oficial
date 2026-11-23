import test from 'node:test'
import assert from 'node:assert/strict'
import { rangoSemana, rangoMes, porcentajeNoche, resumenSerie, puntosLinea } from '../lib/panel-serie.js'

test('semana de lunes a lunes', () => {
  assert.deepEqual(rangoSemana('2026-11-23'), { desde: '2026-11-23', hasta: '2026-11-30' }) // lunes
  assert.deepEqual(rangoSemana('2026-11-29'), { desde: '2026-11-23', hasta: '2026-11-30' }) // domingo
})
test('mes y cambio de año', () => {
  assert.deepEqual(rangoMes('2026-11-23'), { desde: '2026-11-01', hasta: '2026-12-01' })
  assert.deepEqual(rangoMes('2026-12-05'), { desde: '2026-12-01', hasta: '2027-01-01' })
})
test('porcentaje y resumen', () => {
  assert.equal(porcentajeNoche({ unidades: 10, ocupadas_estadias: 3, reservadas: 5 }), 50)
  assert.equal(porcentajeNoche({ unidades: 0, reservadas: 1 }), null)
  const r = resumenSerie([
    { fecha: '2026-11-23', unidades: 10, ocupadas_estadias: 2, reservadas: 4 },
    { fecha: '2026-11-24', unidades: 10, ocupadas_estadias: null, reservadas: 8 },
    { fecha: '2026-11-25', unidades: 10, ocupadas_estadias: null, reservadas: 0 },
  ])
  assert.equal(r.promedio, 40)
  assert.equal(r.pico.fecha, '2026-11-24')
  assert.equal(r.valle.fecha, '2026-11-25')
  assert.equal(resumenSerie([]), null)
  assert.equal(puntosLinea(r.puntos)[0].x, 0)
  assert.equal(puntosLinea(r.puntos)[2].x, 100)
})
