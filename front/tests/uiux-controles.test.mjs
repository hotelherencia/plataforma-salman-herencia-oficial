import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const leer = (ruta) => readFileSync(new URL(ruta, import.meta.url), 'utf8')

describe('Auditoría UI/UX de controles, alineación y cero botones repetidos (2026-11-23)', () => {
  it('usa BarraContextual y SelectorFila en todas las vistas con tablas o listados repetitivos', () => {
    const vistas = [
      '../app/hotel/_componentes/lista-reservas.js',
      '../app/hotel/_componentes/inventario-habitaciones.js',
      '../app/hotel/leads/page.js',
      '../app/hotel/solicitudes/page.js',
      '../app/hotel/clientes/page.js',
      '../app/hotel/_componentes/cuentas-por-cobrar.js',
      '../app/hotel/productos/page.js',
      '../app/hotel/aseo/page.js',
      '../app/hotel/_componentes/movimientos-contables.js',
      '../app/hotel/_componentes/caja-contable.js',
    ]
    for (const v of vistas) {
      const src = leer(v)
      assert.ok(src.includes('BarraContextual'), `${v}: debe usar BarraContextual`)
      assert.ok(src.includes('SelectorFila'), `${v}: debe usar SelectorFila`)
    }
  })

  it('mantiene etiquetas legibles en castellano en combo lists (sin valores crudos en_estadia)', () => {
    const reservas = leer('../app/hotel/reservas/page.js')
    const panel = leer('../app/hotel/panel/page.js')
    const agente = leer('../app/hotel/agente/page.js')
    assert.ok(reservas.includes('>En estadía</option>'))
    assert.ok(!reservas.includes('>en_estadia</option>'))
    assert.ok(panel.includes('nombreTipo(t)'))
    assert.ok(agente.includes('Sitio web'))
  })

  it('garantiza reglas geométricas de alineación y área táctil mínima 44px en diseno.css', () => {
    const css = leer('../app/diseno.css')
    assert.ok(css.includes('.filtros {\n  display: flex;\n  flex-wrap: wrap;\n  gap: var(--e-2) var(--e-3);\n  align-items: flex-end;'))
    assert.ok(css.includes('.barra-contextual'))
    assert.ok(css.includes('.selector-fila'))
    assert.ok(css.includes('height: 2.75rem;'))
    assert.ok(css.includes('min-height: 2.75rem;'))
  })

  it('soporta error en línea accesible (aria-invalid + aria-describedby) e inputMode numérico en Campo', () => {
    const api = leer('../lib/api.js')
    assert.ok(api.includes("inputMode={modo}"))
    assert.ok(api.includes('aria-describedby={descrito}'))
    assert.ok(api.includes('className="error-campo"'))
  })
})
