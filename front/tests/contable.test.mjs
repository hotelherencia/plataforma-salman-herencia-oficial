import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  arqueoParaApi, nombreDocumento, nombreMedio, pareceNumeroDeTarjeta, textoDiferencia, totalArqueo, validarDatosPago,
} from '../lib/caja.js'
import { aCsv, errorRango, parametrosRango, sufijoRango } from '../lib/exportacion.js'
import { PESTANAS_CAJA } from '../lib/menu-hotel.js'

test('arqueo: suma por denominación e ignora vacíos o negativos', () => {
  assert.equal(totalArqueo({ 20000: 2, 500: '3', 100: '', 50: -1 }), 41500)
  assert.deepEqual(arqueoParaApi({ 20000: '2', 1000: '', 10: '0' }), { 20000: 2 })
})

test('diferencia de cuadratura en palabras', () => {
  assert.equal(textoDiferencia(0), 'Cuadra')
  assert.equal(textoDiferencia(1500), 'Sobrante de $1.500')
  assert.equal(textoDiferencia(-5000), 'Faltante de $5.000')
})

test('PCI: detecta números completos de tarjeta y no confunde códigos cortos', () => {
  assert.ok(pareceNumeroDeTarjeta('4111 1111 1111 1111'))
  assert.ok(pareceNumeroDeTarjeta('4111-1111-1111-1111'))
  assert.ok(!pareceNumeroDeTarjeta('A1B2C3'))
  assert.ok(!pareceNumeroDeTarjeta('4321'))
})

test('validación del pago: tarjeta exige código; factura exige receptor', () => {
  assert.match(validarDatosPago({ medio: 'debito' }), /código de autorización/)
  assert.match(validarDatosPago({ medio: 'credito', codigo: 'X1', ultimos4: '12' }), /4 números/)
  assert.match(validarDatosPago({ medio: 'credito', codigo: '4111111111111111' }), /número completo/)
  assert.match(validarDatosPago({ medio: 'transferencia', documento: 'factura', receptor: { rut: '1-9' } }), /razón social/)
  assert.equal(validarDatosPago({ medio: 'efectivo', documento: 'boleta' }), null)
})

test('nombres en castellano para medios y documentos', () => {
  assert.equal(nombreMedio('debito'), 'Tarjeta de débito')
  assert.equal(nombreMedio('no_informado'), 'Sin medio informado')
  assert.equal(nombreDocumento('pendiente'), 'Por indicar')
})

test('pestañas de Caja (sin ítem de menú nuevo)', () => {
  assert.deepEqual(PESTANAS_CAJA.map(([id]) => id), ['dia', 'turno', 'movimientos', 'depositos', 'cierre'])
})

test('exportación por rango: validación, parámetros y nombre de archivo', () => {
  assert.equal(errorRango('2026-11-10', '2026-11-01'), 'La fecha «desde» debe ser anterior o igual a «hasta».')
  assert.equal(errorRango('2026-11-01', ''), null)
  assert.equal(parametrosRango('2026-11-01', '2026-11-19').toString(), 'desde=2026-11-01&hasta=2026-11-19')
  assert.equal(parametrosRango('', '2026-11-19').toString(), 'hasta=2026-11-19&todos=true')
  assert.equal(sufijoRango('2026-11-01', ''), 'desde-2026-11-01')
  assert.equal(sufijoRango('', ''), 'todo')
  assert.equal(aCsv([['a', 'b"c']]), '\uFEFF"a","b""c"')
})
