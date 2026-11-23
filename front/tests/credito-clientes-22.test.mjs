import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { SECCIONES } from '../lib/menu-hotel.js'

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..')
const fuente = (...p) => readFileSync(join(raiz, ...p), 'utf8')

describe('Contable 2.2 (#392): políticas de crédito y cuentas por cobrar', () => {
  it('mantiene el menú lateral sin ítems nuevos', () => {
    const nombres = SECCIONES.flatMap((s) => s.items.map((i) => i.nombre))
    assert.ok(nombres.includes('Clientes'))
    assert.ok(!nombres.includes('Cuentas por cobrar'))
  })

  it('Clientes y Salida integran las 3 políticas de crédito, CxC por tramos y PCI sin CVV', () => {
    const cli = fuente('app/hotel/clientes/page.js')
    const cxc = fuente('app/hotel/_componentes/cuentas-por-cobrar.js')
    const sal = fuente('app/hotel/salida/page.js')
    assert.match(cli, /credito_autorizado/)
    assert.match(cli, /garantia_salida/)
    assert.match(cli, /pago_al_registrarse/)
    assert.match(cli, /CuentasPorCobrar/)
    assert.match(cxc, /0 a 30 días/)
    assert.match(cxc, /31 a 60 días/)
    assert.match(cxc, /61 a 90 días/)
    assert.match(cxc, /Más de 90 días/)
    assert.match(sal, /\/salida-credito/)
    assert.doesNotMatch(cxc, /check-in|check-out/i)
  })
})
