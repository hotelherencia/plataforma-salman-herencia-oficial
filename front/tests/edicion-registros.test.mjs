import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { gestionaClientes } from '../lib/roles.js'
import { SECCIONES, seccionesVisibles } from '../lib/menu-hotel.js'

describe('edición de registros (clientes)', () => {
  it('gestionaClientes: recepción, caja y administración del hotel; no aseo ni admin de plataforma', () => {
    for (const rol of ['recepcion', 'caja', 'administrador', 'admin_hotel']) assert.equal(gestionaClientes(rol), true, rol)
    for (const rol of ['aseo', 'admin_plataforma', undefined]) assert.equal(gestionaClientes(rol), false, String(rol))
  })

  it('el menú muestra Clientes solo a quien puede gestionarlos y no al rol aseo', () => {
    assert.ok(SECCIONES[0].items.some((i) => i.nombre === 'Clientes'))
    const nombres = (vis) => seccionesVisibles(vis).flatMap((s) => s.items.map((i) => i.nombre))
    assert.ok(nombres({ puedeVerAgente: true, puedeVerUsuarios: false, puedeVerClientes: true }).includes('Clientes'))
    assert.ok(!nombres({ puedeVerAgente: true, puedeVerUsuarios: false, puedeVerClientes: false }).includes('Clientes'))
    assert.deepEqual(nombres({ puedeVerAgente: false, puedeVerUsuarios: false, soloAseo: true }), ['Aseo'])
  })
})
