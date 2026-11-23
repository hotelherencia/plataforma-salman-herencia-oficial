import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const comp = readFileSync(new URL('../app/hotel/_componentes/conciliacion-bancaria-tributaria.js', import.meta.url), 'utf8')
const libro = readFileSync(new URL('../app/hotel/_componentes/movimientos-contables.js', import.meta.url), 'utf8')
const menu = readFileSync(new URL('../lib/menu-hotel.js', import.meta.url), 'utf8')

describe('Contable 2.6 y 2.7: Conciliación bancaria y borrador F29 (#396, #397)', () => {
  it('integra conciliación bancaria y borrador F29 en el libro contable sin tocar el menú lateral', () => {
    assert.ok(libro.includes('ConciliacionBancariaTributaria'))
    assert.ok(comp.includes('/hotel/contabilidad/cartolas/vista-previa'))
    assert.ok(comp.includes('/hotel/contabilidad/cartolas'))
    assert.ok(comp.includes('/hotel/contabilidad/conciliacion-bancaria/emparejar'))
    assert.ok(comp.includes('/hotel/contabilidad/comisiones-medios'))
    assert.ok(comp.includes('/hotel/contabilidad/tributario?anio='))
    assert.ok(comp.includes('/hotel/contabilidad/tributario/exportar.csv'))
    assert.ok(!menu.includes('Conciliación'))
    assert.ok(!menu.includes('F29'))
  })

  it('usa plurales escritos sin (s)/(es) y sin jerga en inglés', () => {
    assert.ok(!/\(s\)|\(es\)/i.test(comp))
    assert.ok(!/check-in|check-out/i.test(comp))
    assert.ok(comp.includes('plural('))
  })
})
