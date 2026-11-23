import test from 'node:test'
import assert from 'node:assert/strict'
import { etiqueta, ETIQUETA_GRAVEDAD, progresoSubtareas, resumirAtencion } from '../lib/operacion-etiquetas.js'

test('etiquetas: valor conocido y desconocido', () => {
  assert.equal(etiqueta(ETIQUETA_GRAVEDAD, 'critica'), 'Crítica')
  assert.equal(etiqueta(ETIQUETA_GRAVEDAD, 'rara'), 'rara')
  assert.equal(etiqueta(ETIQUETA_GRAVEDAD, null), '')
})

test('resumirAtencion: vacío y con varios grupos', () => {
  assert.equal(resumirAtencion({ total: 0 }), 'Todo al día')
  const a = { total: 3, llegadas_atrasadas: [{}], incidencias_abiertas: [{}, {}] }
  assert.equal(resumirAtencion(a), '1 llegada atrasada, 2 incidencias abiertas')
})

test('progresoSubtareas cuenta obligatorias pendientes', () => {
  const p = progresoSubtareas([
    { hecha: true, obligatoria: true }, { hecha: false, obligatoria: true }, { hecha: false, obligatoria: false },
  ])
  assert.deepEqual(p, { hechas: 1, total: 3, faltanObligatorias: 1, porcentaje: 33 })
  assert.equal(progresoSubtareas([]).porcentaje, 0)
})
