import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  SECCIONES, PESTANAS_CONFIGURACION, itemActivo, seccionesVisibles, rutaInicio, hayOperacionActiva,
} from '../lib/menu-hotel.js'

describe('menú del hotel (entrega 1A.3)', () => {
  it('agrupa en operación diaria, configuración y plataforma, sin entradas sueltas de precios o políticas', () => {
    const ids = SECCIONES.map((s) => s.id)
    assert.deepEqual(ids, ['operacion', 'configuracion', 'plataforma'])
    const nombres = SECCIONES.flatMap((s) => s.items.map((i) => i.nombre))
    assert.ok(nombres.includes('Reservas'))
    assert.ok(nombres.includes('Solicitudes y leads'))
    assert.ok(nombres.includes('Configuración'))
    assert.ok(nombres.includes('Llegada'))
    assert.ok(nombres.includes('Caja y pagos'))
    assert.ok(!nombres.includes('Tipos, habitaciones y precios'))
    assert.ok(!nombres.includes('Nueva reserva'))
    assert.ok(!nombres.includes('Políticas y registro'))
    assert.deepEqual(PESTANAS_CONFIGURACION.map(([id]) => id), ['tipos', 'precios', 'politicas', 'faq', 'reservas_web', 'correo', 'avisos', 'caja'])
  })

  it('resalta Reservas en oferta, nueva y ficha, sin confundir /hotel/reserva con /hotel/reservas', () => {
    const reservas = SECCIONES[0].items.find((i) => i.nombre === 'Reservas')
    assert.equal(itemActivo('/hotel/reservas', reservas), true)
    assert.equal(itemActivo('/hotel/reservas/RSV-1', reservas), true)
    assert.equal(itemActivo('/hotel/reserva', reservas), true)
    assert.equal(itemActivo('/hotel/oferta', reservas), true)
    assert.equal(itemActivo('/hotel/habitaciones', reservas), false)
  })

  it('oculta Agente y Usuarios según el rol', () => {
    const recepcion = seccionesVisibles({ puedeVerAgente: true, puedeVerUsuarios: false })
    assert.ok(recepcion.some((s) => s.items.some((i) => i.nombre === 'Agente')))
    assert.ok(!recepcion.some((s) => s.id === 'plataforma'))
    const soloPlataforma = seccionesVisibles({ puedeVerAgente: false, puedeVerUsuarios: true })
    assert.ok(!soloPlataforma.some((s) => s.items.some((i) => i.nombre === 'Agente')))
    assert.ok(soloPlataforma.some((s) => s.id === 'plataforma'))
    assert.equal(hayOperacionActiva('/hotel/tipos', { puedeVerAgente: true, puedeVerUsuarios: true }), true)
    assert.equal(hayOperacionActiva('/hotel/configuracion', { puedeVerAgente: false, puedeVerUsuarios: false }), true)
  })

  it('#362: el rol aseo solo ve Aseo; caja no lo ve', () => {
    const aseo = seccionesVisibles({ puedeVerAgente: false, puedeVerUsuarios: false, puedeVerAseo: true, soloAseo: true })
    assert.deepEqual(aseo.flatMap((s) => s.items.map((i) => i.href)), ['/hotel/aseo'])
    const caja = seccionesVisibles({ puedeVerAgente: false, puedeVerUsuarios: false, puedeVerAseo: false })
    assert.ok(!caja.some((s) => s.items.some((i) => i.href === '/hotel/aseo')))
  })

  it('#455: lista exacta de enlaces por rol', () => {
    const enlaces = (rol, extra = {}) => seccionesVisibles({
      puedeVerAgente: ['administrador', 'admin_hotel', 'recepcion'].includes(rol),
      puedeVerUsuarios: ['administrador', 'admin_hotel', 'admin_plataforma'].includes(rol),
      puedeVerAseo: ['administrador', 'admin_hotel', 'recepcion', 'aseo'].includes(rol),
      puedeVerClientes: ['administrador', 'admin_hotel', 'recepcion', 'caja'].includes(rol),
      soloAseo: rol === 'aseo', rol, ...extra,
    }).flatMap((s) => s.items.map((i) => i.href))
    const base = ['/hotel/panel', '/hotel/ocupacion', '/hotel/habitaciones', '/hotel/aseo', '/hotel/reservas',
      '/hotel/solicitudes', '/hotel/agente', '/hotel/clientes', '/hotel/estadia', '/hotel/salida', '/hotel/caja',
      '/hotel/configuracion', '/hotel/productos']
    assert.deepEqual(enlaces('admin_hotel'), [...base, '/hotel/usuarios'])  // valida cambios de rol
    assert.deepEqual(enlaces('administrador'), [...base, '/hotel/usuarios'])
    assert.deepEqual(enlaces('recepcion'), base)
    assert.deepEqual(enlaces('caja'), ['/hotel/panel', '/hotel/ocupacion', '/hotel/reservas', '/hotel/clientes', '/hotel/caja', '/hotel/productos'])
    assert.deepEqual(enlaces('aseo'), ['/hotel/aseo'])
    // Dueño: lee todo lo de consulta, no opera (sin Llegada, Salida, Aseo, Agente, Clientes, Usuarios).
    assert.deepEqual(enlaces('dueno'), ['/hotel/panel', '/hotel/ocupacion', '/hotel/habitaciones', '/hotel/reservas',
      '/hotel/solicitudes', '/hotel/caja', '/hotel/configuracion', '/hotel/productos'])
    assert.deepEqual(enlaces('admin_plataforma'), ['/hotel/panel', '/hotel/productos', '/hotel/usuarios'])
  })

  it('#455: pantalla de inicio por rol', () => {
    assert.equal(rutaInicio('aseo'), '/hotel/aseo')
    assert.equal(rutaInicio('caja'), '/hotel/caja')
    assert.equal(rutaInicio('recepcion'), '/hotel/panel')
    assert.equal(rutaInicio('admin_hotel'), '/hotel/panel')
    assert.equal(rutaInicio(null), '/hotel/panel')
  })
})
