import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { SECCIONES } from '../lib/menu-hotel.js'

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..')
const fuente = (...p) => readFileSync(join(raiz, ...p), 'utf8')

describe('PR B (RES-007): titular con varias habitaciones', () => {
  it('mantiene el menú lateral sin ítems nuevos y conserva vocabulario Llegada/Salida', () => {
    const nombres = SECCIONES.flatMap((s) => s.items.map((i) => i.nombre))
    assert.ok(nombres.includes('Llegada'))
    assert.ok(nombres.includes('Salida'))
    assert.ok(!nombres.includes('Grupos'))
  })

  it('/hotel/reserva permite crear grupos multi-habitación vía POST /hotel/grupos', () => {
    const t = fuente('app/hotel/reserva/page.js')
    assert.match(t, /\/hotel\/grupos/)
    assert.match(t, /Varias habitaciones/)
    assert.match(t, /titular_aloja/)
    assert.doesNotMatch(t, /check-in|check-out/i)
  })

  it('ficha de reserva, pantalla de Llegada y BloqueGrupo integran /hotel/grupos sin anglicismos', () => {
    const res = fuente('app/hotel/reservas/[id]/page.js')
    const est = fuente('app/hotel/estadia/page.js')
    const bloq = fuente('app/hotel/_componentes/bloque-grupo.js')
    assert.match(res, /BloqueGrupo/)
    assert.match(est, /BloqueGrupo/)
    assert.match(bloq, /\/hotel\/grupos\//)
    assert.match(bloq, /\/entrada/)
    assert.match(bloq, /\/reservas/)
    assert.doesNotMatch(bloq, /check-in|check-out/i)
  })
})
