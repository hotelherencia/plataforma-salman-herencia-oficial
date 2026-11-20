import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { construirTablaUnica, aCsv } from '../lib/exportacion.js'

describe('exportacion en formato unico (SPEC-02)', () => {
  it('incluye encabezado institucional, emision, filtros, separador y filas normalizadas', () => {
    const tabla = construirTablaUnica({
      titulo: 'Reservas',
      filtros: 'estado confirmada',
      columnas: ['Reserva', 'Huésped', 'Activo'],
      filas: [['RSV-1', 'Ana Pérez', true], ['RSV-2', null, false]],
      emitidoEn: '20/11/2026 11:40',
    })
    assert.deepEqual(tabla[0], ['Hotel Herencia', 'Reservas'])
    assert.deepEqual(tabla[1], ['Emitido el', '20/11/2026 11:40'])
    assert.deepEqual(tabla[2], ['Filtros aplicados', 'estado confirmada'])
    assert.deepEqual(tabla[3], [])
    assert.deepEqual(tabla[4], ['Reserva', 'Huésped', 'Activo'])
    assert.deepEqual(tabla[5], ['RSV-1', 'Ana Pérez', 'Sí'])
    assert.deepEqual(tabla[6], ['RSV-2', '', 'No'])
    const csv = aCsv(tabla)
    assert.ok(csv.startsWith('\uFEFF"Hotel Herencia","Reservas"'))
  })
})
