/** Tests de las utilidades puras del formulario de contacto (leads.js). */
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { mapearCuerpo, mensajePara } from '../js/leads.js'

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

test('mensajePara distingue éxito, freno, validación y fallo genérico', () => {
  assert.match(mensajePara(201), /Consulta enviada/)
  assert.match(mensajePara(200), /Consulta enviada/) // reintento idempotente
  assert.match(mensajePara(429), /espera un minuto/i)
  assert.match(mensajePara(422), /Revisa los datos/)
  assert.match(mensajePara(503), /No se pudo enviar/)
  assert.match(mensajePara(0), /No se pudo enviar/)
})
