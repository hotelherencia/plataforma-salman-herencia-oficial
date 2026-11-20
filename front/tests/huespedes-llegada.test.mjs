import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { SECCIONES } from '../lib/menu-hotel.js'

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..')
const fuente = (...p) => readFileSync(join(raiz, ...p), 'utf8')

describe('PR A: huéspedes y ocupación real en Llegada', () => {
  it('mantiene el menú lateral sin ítems nuevos y conserva el vocabulario Llegada/Salida', () => {
    const nombres = SECCIONES.flatMap((s) => s.items.map((i) => i.nombre))
    assert.ok(nombres.includes('Llegada'))
    assert.ok(nombres.includes('Salida'))
    assert.ok(!nombres.includes('Huéspedes'))
  })

  it('Configuración -> Políticas incluye recargo_persona_extra_clp, edad_nino_hasta y recargo_nino', () => {
    const t = fuente('app/hotel/configuracion/page.js')
    assert.match(t, /recargo_persona_extra_clp/)
    assert.match(t, /edad_nino_hasta/)
    assert.match(t, /recargo_nino/)
  })

  it('la ficha de reserva y la pantalla de Llegada incluyen la pestaña Huéspedes', () => {
    const res = fuente('app/hotel/reservas/[id]/page.js')
    const est = fuente('app/hotel/estadia/page.js')
    const comp = fuente('app/hotel/_componentes/pestana-huespedes.js')
    assert.match(res, /PestanaHuespedes/)
    assert.match(res, /Huéspedes/)
    assert.match(est, /PestanaHuespedes/)
    assert.match(est, /Huéspedes/)
    assert.match(comp, /\/ocupacion/)
    assert.match(comp, /\/huespedes/)
    assert.doesNotMatch(comp, /check-in|check-out/i)
  })
})
