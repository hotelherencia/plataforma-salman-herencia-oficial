import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { SECCIONES } from '../lib/menu-hotel.js'

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..')
const fuente = (...p) => readFileSync(join(raiz, ...p), 'utf8')

describe('Contabilidad 2.3, 2.4 y 2.5 (#393, #394, #395 / KPI-002)', () => {
  it('mantiene el menú lateral sin ítems nuevos', () => {
    const nombres = SECCIONES.flatMap((s) => s.items.map((i) => i.nombre))
    assert.ok(nombres.includes('Panel'))
    assert.ok(nombres.includes('Caja y pagos'))
    assert.ok(!nombres.includes('Cierre mensual'))
  })

  it('el Panel muestra ADR y RevPAR reales con «sin muestra» cuando son null', () => {
    const panel = fuente('app/hotel/panel/page.js')
    assert.match(panel, /clave="adr_clp"/)
    assert.match(panel, /clave="revpar_clp"/)
    assert.match(panel, /clave="ingreso_alojamiento_clp"/)
    assert.match(panel, /=== null \? 'sin muestra'/)
  })

  it('Cierre integra Cuadratura diaria (2.3) y Cierre mensual con exportación CSV (2.4)', () => {
    const caja = fuente('app/hotel/_componentes/caja-contable.js')
    const comp = fuente('app/hotel/_componentes/contable-mensual.js')
    assert.match(caja, /ContableMensual/)
    assert.match(comp, /\/hotel\/contabilidad\/cuadratura-diaria/)
    assert.match(comp, /\/hotel\/contabilidad\/cierre-mensual/)
    assert.match(comp, /exportar\.csv/)
    assert.doesNotMatch(comp, /check-in|check-out/i)
  })
})
