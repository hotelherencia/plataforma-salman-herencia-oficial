import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const equipo = readFileSync(new URL('../app/hotel/equipo/page.js', import.meta.url), 'utf8')
const panel = readFileSync(new URL('../app/hotel/panel/page.js', import.meta.url), 'utf8')
const menu = readFileSync(new URL('../lib/menu-hotel.js', import.meta.url), 'utf8')

describe('Corte 2 Operativo (#418 parte 2): turnos, biblioteca, sugerencias y activos preventivos', () => {
  it('conecta turnos semanales, biblioteca, buzón y activos preventivos sin agregar ítems al menú lateral', () => {
    assert.ok(equipo.includes('/hotel/equipo/turnos'))
    assert.ok(equipo.includes('/hotel/equipo/biblioteca'))
    assert.ok(equipo.includes('/hotel/equipo/sugerencias'))
    assert.ok(equipo.includes('/hotel/activos'))
    assert.ok(panel.includes('/hotel/equipo'))
    assert.ok(!menu.includes('/hotel/equipo'))
  })

  it('respeta vocabulario y plurales escritos sin (s)/(es)', () => {
    assert.ok(!/\w\(s\)|\w\(es\)/i.test(equipo))
    assert.ok(!/check-in|check-out/i.test(equipo))
    assert.ok(equipo.includes('plural('))
  })
})
