import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..')
const fuente = (...p) => readFileSync(join(raiz, ...p), 'utf8')

describe('recargos de Llegada/Salida en la operación diaria', () => {
  it('la oferta permite indicar hora de llegada y de salida y las envía a la API', () => {
    const t = fuente('app/hotel/oferta/page.js')
    assert.match(t, /hora_llegada/)
    assert.match(t, /hora_salida/)
    assert.match(t, /Hora de llegada/)
    assert.match(t, /Hora de salida/)
  })

  it('la nueva reserva envía hora de llegada y de salida', () => {
    const t = fuente('app/hotel/reserva/page.js')
    assert.match(t, /hora_llegada/)
    assert.match(t, /hora_salida/)
    assert.match(t, /Hora de llegada/)
    assert.match(t, /Hora de salida/)
  })

  it('la tarjeta de oferta muestra recargos cuando hay llegada anticipada o salida tardía', () => {
    const t = fuente('app/hotel/_componentes/tarjeta-oferta.js')
    assert.match(t, /recargos/)
    assert.match(t, /totalRecargosClp/)
  })
})
