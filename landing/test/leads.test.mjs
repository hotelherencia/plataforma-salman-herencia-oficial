/** Tests de las utilidades puras del formulario de contacto (leads.js). */
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { decidirClave, mapearCuerpo, mensajePara, problemaConsulta } from '../js/leads.js'

test('mapearCuerpo mapea los names del formulario histórico a snake_case', () => {
  const cuerpo = mapearCuerpo({
    nombre: '  Ana Pérez ',
    correo: ' ana@example.test ',
    telefono: ' +56 9 5555 5555 ',
    huespedes: '3',
    check_in: '2026-12-10',
    check_out: '2026-12-12',
    mensaje: ' Viajamos con un bebé ',
  })
  assert.deepEqual(cuerpo, {
    nombre: 'Ana Pérez',
    correo: 'ana@example.test',
    telefono: '+56 9 5555 5555',
    huespedes: 3,
    check_in: '2026-12-10',
    check_out: '2026-12-12',
    mensaje: 'Viajamos con un bebé',
  })
})

test('mapearCuerpo acepta los names del sitio real y no los copia al cuerpo', () => {
  const cuerpo = mapearCuerpo({
    name: '  Ana Pérez ',
    email: ' ana@example.test ',
    phone: ' +56 9 5555 5555 ',
    guests: '3',
    checkin: '2026-12-10',
    checkout: '2026-12-12',
    message: ' Viajamos con un bebé ',
    _subject: 'no debe viajar',
  })
  assert.deepEqual(cuerpo, {
    nombre: 'Ana Pérez',
    correo: 'ana@example.test',
    telefono: '+56 9 5555 5555',
    huespedes: 3,
    check_in: '2026-12-10',
    check_out: '2026-12-12',
    mensaje: 'Viajamos con un bebé',
  })
  assert.equal('name' in cuerpo, false)
  assert.equal('email' in cuerpo, false)
  assert.equal('message' in cuerpo, false)
})

test('mapearCuerpo deja opcionales en null cuando el campo viene vacío', () => {
  const cuerpo = mapearCuerpo({
    nombre: 'Ana',
    correo: 'ana@example.test',
    telefono: '123',
    huespedes: '',
    check_in: '',
    check_out: '',
    mensaje: '',
  })
  assert.equal(cuerpo.huespedes, null)
  assert.equal(cuerpo.check_in, null)
  assert.equal(cuerpo.check_out, null)
  assert.equal(cuerpo.mensaje, null)
})

test('problemaConsulta acepta el cuerpo del sitio y rechaza la salida anterior', () => {
  const valido = mapearCuerpo({
    name: 'Ana',
    email: 'ana@example.test',
    phone: '+56 9 5555 5555',
    guests: '2',
    checkin: '2026-12-10',
    checkout: '2026-12-12',
  })
  assert.equal(problemaConsulta(valido), null)
  const invertido = { ...valido, check_in: '2026-12-12', check_out: '2026-12-10' }
  assert.match(problemaConsulta(invertido), /posterior/)
})

test('problemaConsulta rechaza un teléfono corto y un correo sin formato', () => {
  const base = mapearCuerpo({ name: 'Ana', email: 'ana@example.test', phone: '+56 9 5555 5555' })
  assert.match(problemaConsulta({ ...base, telefono: '123' }), /8 y 15/)
  assert.match(problemaConsulta({ ...base, correo: 'ana' }), /correo/)
})

test('decidirClave conserva la clave solo cuando el resultado no llegó', () => {
  assert.equal(decidirClave(201), 'renovar')
  assert.equal(decidirClave(200), 'renovar')
  assert.equal(decidirClave(422), 'renovar')
  assert.equal(decidirClave(429), 'renovar')
  assert.equal(decidirClave(0), 'conservar')
  assert.equal(decidirClave(503), 'conservar')
})

test('mensajePara distingue éxito, freno, validación y fallo genérico', () => {
  assert.match(mensajePara(201), /Consulta enviada/)
  assert.match(mensajePara(200), /Consulta enviada/) // reintento idempotente
  assert.match(mensajePara(429), /espera un minuto/i)
  assert.match(mensajePara(422), /Revisa los datos/)
  assert.match(mensajePara(503), /No se pudo enviar/)
  assert.match(mensajePara(0), /No se pudo enviar/)
})
