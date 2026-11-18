// Reglas puras de /reservar: node --test front/tests/
import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  agruparOferta, enlaceWhatsapp, erroresContacto, fechaIso, guardarReferencia, leerParametros, leerReferencia,
  elegirTipo, nombreTipo, politicaUnica, urlCanonica, validarRango,
} from '../app/reservar/continuidad.js'

const REF = 'Abc_123-xyz'.repeat(4)
const p = (q) => new URLSearchParams(q)
function almacen() {
  const m = new Map()
  return { m, getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) }
}

test('llegada/salida son canónicos; inicio/fin se aceptan como alias', () => {
  assert.deepEqual(leerParametros(p('llegada=2030-01-10&salida=2030-01-12&personas=2')).inicio, '2030-01-10')
  const alias = leerParametros(p('inicio=2030-01-10&fin=2030-01-12&personas=3'))
  assert.equal(alias.inicio, '2030-01-10')
  assert.equal(alias.fin, '2030-01-12')
  assert.equal(leerParametros(p('llegada=2030-01-11&inicio=2030-01-10')).inicio, '2030-01-11')
})

test('lista blanca: fechas imposibles, XSS, SQLi y personas fuera de rango se descartan sin reflejarse', () => {
  const r = leerParametros(p({ llegada: '<img src=x onerror=alert(1)>', salida: '2030-02-31', personas: '99', ref: "' OR 1=1 --" }))
  assert.equal(r.inicio, '')
  assert.equal(r.fin, '')
  assert.equal(r.personas, '')
  assert.equal(r.ref, '')
  assert.equal(r.avisos.length, 3)
  for (const aviso of r.avisos) assert.doesNotMatch(aviso, /img|OR 1=1|99|2030/)
})

test('fechaIso exige fechas reales', () => {
  assert.equal(fechaIso('2028-02-29'), true)
  assert.equal(fechaIso('2027-02-29'), false)
  assert.equal(fechaIso('2030-1-1'), false)
  assert.equal(fechaIso(' 2030-01-01'), false)
})

test('validarRango: salida posterior, sin pasado, tope de noches y personas', () => {
  const hoy = '2030-01-01'
  assert.equal(validarRango('2030-01-02', '2030-01-04', '2', hoy), null)
  assert.match(validarRango('2030-01-04', '2030-01-02', '2', hoy), /posterior/)
  assert.match(validarRango('2029-12-30', '2030-01-02', '2', hoy), /pasada/)
  assert.match(validarRango('2030-01-02', '2030-03-02', '2', hoy), /30 noches/)
  assert.match(validarRango('2030-01-02', '2030-01-04', '31', hoy), /Personas/)
})

test('URL canónica: sin ref, sin alias ni parámetros ajenos; null si ya es canónica', () => {
  const v = { inicio: '2030-01-10', fin: '2030-01-12', personas: '2' }
  assert.equal(urlCanonica(`https://x.cl/reservar?inicio=2030-01-10&fin=2030-01-12&personas=2&ref=${REF}&next=https://evil.example`, v),
    '/reservar?llegada=2030-01-10&salida=2030-01-12&personas=2')
  assert.equal(urlCanonica('https://x.cl/reservar?llegada=2030-01-10&salida=2030-01-12&personas=2', v), null)
})

test('referencia guardada caduca y descarta valores manipulados', () => {
  const a = almacen()
  assert.equal(guardarReferencia(a, '<script>'), false)
  assert.equal(guardarReferencia(a, REF), true)
  assert.equal(leerReferencia(a), REF)
  assert.equal(leerReferencia(a, Date.now() + 73 * 3600000), '')
  assert.equal(a.m.size, 0)
})

test('errores de contacto por campo', () => {
  assert.deepEqual(erroresContacto('', ''), { nombre: 'Escribe tu nombre.', contacto: 'Escribe un correo o un teléfono.' })
  assert.deepEqual(erroresContacto('Ana', 'ana@example.cl'), {})
  assert.deepEqual(erroresContacto('Ana', '+56 9 1234 5678'), {})
  assert.ok(erroresContacto('Ana', 'ana@').contacto)
  assert.ok(erroresContacto('Ana', '<b>123</b>').contacto)
})

test('tipos con nombre visible y oferta agrupada con política una sola vez', () => {
  assert.equal(nombreTipo('matrimonial_mas_1'), 'Matrimonial + 1')
  assert.equal(nombreTipo('suite_familiar'), 'Suite familiar')
  const pol = 'cancelación gratuita hasta 48 horas antes de la llegada; después se carga la primera noche'
  const items = [
    { habitacion_id: 'HAB-01', tipo: 'matrimonial', capacidad: 2, tarifa_noche_clp: 55000, total_clp: 110000, politica_cancelacion: pol },
    { habitacion_id: 'HAB-02', tipo: 'matrimonial', capacidad: 2, tarifa_noche_clp: 55000, total_clp: 110000, politica_cancelacion: pol },
    { habitacion_id: 'HAB-17', tipo: 'triple', capacidad: 3, tarifa_noche_clp: 65000, total_clp: 130000, politica_cancelacion: pol },
  ]
  const g = agruparOferta(items)
  assert.deepEqual(g.map((x) => [x.nombre, x.disponibles, x.capacidad, x.tipo]), [['Matrimonial', 2, 2, 'matrimonial'], ['Triple', 1, 3, 'triple']])
  // #346: el grupo no lleva número de habitación (la solicitud va por tipo)
  assert.ok(g.every((x) => !('habitacion_id' in x)))
  assert.equal(politicaUnica(items), pol)
})

test('WhatsApp con fechas y personas validadas, sin valores crudos', () => {
  const u = new URL(enlaceWhatsapp('2030-01-10', '2030-01-12', '5'))
  assert.equal(u.searchParams.get('text'), 'Hola, quiero consultar disponibilidad en Hotel Herencia para 5 personas del 2030-01-10 al 2030-01-12.')
  assert.equal(new URL(enlaceWhatsapp('<x>', "' OR 1", '99')).searchParams.get('text'), 'Hola, quiero consultar disponibilidad en Hotel Herencia.')
})

test('landinpage#1: el tipo del enlace se lee por lista blanca y queda en la URL canónica', () => {
  const p = (q) => new URLSearchParams(q)
  assert.equal(leerParametros(p('llegada=2030-01-10&salida=2030-01-12&tipo=matrimonial')).tipo, 'matrimonial')
  assert.equal(leerParametros(p('tipo=<script>')).tipo, '')
  assert.equal(leerParametros(p('tipo=HAB-01')).tipo, '')
  assert.equal(
    urlCanonica('https://x.test/reservar?inicio=2030-01-10&fin=2030-01-12&tipo=doble&ref=abc', { inicio: '2030-01-10', fin: '2030-01-12', personas: '2', tipo: 'doble' }),
    '/reservar?llegada=2030-01-10&salida=2030-01-12&personas=2&tipo=doble',
  )
})

test('landinpage#1: preselecciona el tipo con cupo; si no hay, lo dice y ofrece otros', () => {
  const grupos = [{ tipo: 'doble' }, { tipo: 'matrimonial' }]
  assert.deepEqual(elegirTipo(grupos, 'matrimonial'), { tipo: 'matrimonial', aviso: '' })
  const sinCupo = elegirTipo(grupos, 'triple')
  assert.equal(sinCupo.tipo, 'doble')
  assert.match(sinCupo.aviso, /No queda cupo en Triple/)
  assert.doesNotMatch(sinCupo.aviso, /HAB-|\d{2,}/)
  assert.deepEqual(elegirTipo(grupos, ''), { tipo: 'doble', aviso: '' })
  assert.deepEqual(elegirTipo([], 'doble'), { tipo: '', aviso: '' })
})
