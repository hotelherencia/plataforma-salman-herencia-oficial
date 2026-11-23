import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  etiquetaPreparacion,
  progresoSubtareas,
  resumirAtencion,
} from '../lib/operacion-corte1.js'
import { SECCIONES } from '../lib/menu-hotel.js'

describe('Corte 1 operativo (#415, #416, #417)', () => {
  it('#416: etiquetaPreparacion expone «En limpieza» y progresoSubtareas bloquea cierre con obligatorias pendientes', () => {
    assert.equal(etiquetaPreparacion('en_limpieza'), 'En limpieza')
    assert.equal(etiquetaPreparacion('sucia'), 'Sucia')
    assert.equal(etiquetaPreparacion('limpia'), 'Limpia')

    const pendiente = progresoSubtareas([
      { subtarea_id: 'S1', obligatoria: true, completada: true },
      { subtarea_id: 'S2', obligatoria: true, completada: false },
      { subtarea_id: 'S3', obligatoria: false, completada: false },
    ])
    assert.deepEqual(pendiente, {
      total: 3,
      completadas: 1,
      obligatoriasPendientes: 1,
      puedeCerrar: false,
    })

    const listo = progresoSubtareas([
      { subtarea_id: 'S1', obligatoria: true, completada: true },
      { subtarea_id: 'S2', obligatoria: true, completada: true },
      { subtarea_id: 'S3', obligatoria: false, completada: false },
    ])
    assert.equal(listo.puedeCerrar, true)
    assert.equal(listo.obligatoriasPendientes, 0)
  })

  it('#417: resumirAtencion agrupa las 5 categorías con enlaces directos y sin vocabulario check-in/check-out', () => {
    const res = resumirAtencion({
      total: 5,
      llegadas_atrasadas: [{ reserva_id: 'RSV-1', huesped_nombre: 'Ana', habitacion_id: 'HAB-01', fecha: '2026-11-20', enlace: '/hotel/reservas/RSV-1' }],
      salidas_atrasadas: [{ reserva_id: 'RSV-2', huesped_nombre: 'Luis', habitacion_id: 'HAB-02', fecha: '2026-11-21', enlace: '/hotel/reservas/RSV-2' }],
      incidencias_abiertas: [{ incidencia_id: 'INC-1', habitacion_id: 'HAB-03', area: 'habitacion', titulo: 'Fuga baño', gravedad: 'alta', bloquea_disponibilidad: true, enlace: '/hotel/habitaciones/HAB-03' }],
      limpiezas_por_verificar: [{ tarea_id: 'TSK-1', habitacion_id: 'HAB-04', completada_por: 'aseo1', enlace: '/hotel/aseo' }],
      productos_bajo_stock: [{ producto_id: 'PRD-1', nombre: 'Agua', stock_actual: 0, stock_minimo: 5, nivel: 'sin_stock', enlace: '/hotel/productos' }],
    })
    assert.equal(res.total, 5)
    assert.deepEqual(res.grupos.map((g) => g.id), [
      'llegadas_atrasadas',
      'salidas_atrasadas',
      'incidencias_abiertas',
      'limpiezas_por_verificar',
      'productos_bajo_stock',
    ])
    assert.equal(res.grupos[2].items[0].bloquea, true)
    assert.equal(res.grupos[2].items[0].href, '/hotel/habitaciones/HAB-03')
    const texto = JSON.stringify(res)
    assert.doesNotMatch(texto, /check-?in|check-?out/i)
  })

  it('regla de menú y vocabulario: sin ítems nuevos en menu-hotel.js y sin check-in/check-out en las vistas tocadas', () => {
    const items = SECCIONES.flatMap((s) => s.items.map((i) => i.href))
    assert.equal(items.length, 14)
    assert.ok(!items.includes('/hotel/incidencias'))
    assert.ok(!items.includes('/hotel/tareas'))
    for (const rel of [
      '../app/hotel/panel/page.js',
      '../app/hotel/aseo/page.js',
      '../app/hotel/habitaciones/[id]/page.js',
      '../lib/operacion-corte1.js',
    ]) {
      const src = readFileSync(new URL(rel, import.meta.url), 'utf8')
      assert.doesNotMatch(src, /check-?in|check-?out/i, `${rel} no debe usar check-in ni check-out`)
    }
  })
})
