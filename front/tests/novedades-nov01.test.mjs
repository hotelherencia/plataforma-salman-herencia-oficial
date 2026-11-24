import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const comp = readFileSync(new URL('../app/hotel/_componentes/libro-novedades.js', import.meta.url), 'utf8')
const panel = readFileSync(new URL('../app/hotel/panel/page.js', import.meta.url), 'utf8')
const menu = readFileSync(new URL('../lib/menu-hotel.js', import.meta.url), 'utf8')

describe('SPEC-NOV-01 (#448): Libro de novedades, estacionamiento y conteos', () => {
  it('integra LibroNovedades en Panel sin agregar ítems al menú lateral y usa BarraContextual', () => {
    assert.ok(panel.includes('LibroNovedades'))
    assert.ok(comp.includes('/hotel/novedades'))
    assert.ok(comp.includes('/hotel/estacionamiento/asignacion'))
    assert.ok(comp.includes('/hotel/novedades/conteos'))
    assert.ok(comp.includes('BarraContextual'))
    assert.ok(comp.includes('SelectorFila'))
    assert.ok(!menu.includes('Novedades'))
    assert.ok(!menu.includes('Estacionamiento'))
  })

  it('usa plurales escritos sin (s)/(es) y vocabulario Llegada/Salida', () => {
    assert.ok(!/\w\(s\)|\w\(es\)/i.test(comp))
    assert.ok(!/check-in|check-out/i.test(comp))
    assert.ok(comp.includes('plural('))
  })
})
