/**
 * Tests del constructor de enlaces del CTA de reserva (CA-PUB-12,
 * V1-ISSUE-25). Corre con el runtime de Node, sin navegador:
 *
 *   node --test landing/test/reserva.test.mjs
 *
 * Las reglas de validación espejan `validar()` de `front/app/reservar/page.js`:
 * la landing y el front deben rechazar exactamente los mismos rangos.
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'

import { construirEnlaceReserva, hoyLocal, validarRango } from '../js/reserva.js'

const HOY = hoyLocal()
const MANANA = sumarDias(HOY, 1)
const EN_4 = sumarDias(HOY, 4)

function sumarDias(fecha, dias) {
  const d = new Date(`${fecha}T00:00:00`)
  d.setDate(d.getDate() + dias)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dia = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${dia}`
}

test('hoyLocal devuelve YYYY-MM-DD del día local', () => {
  assert.match(hoyLocal(), /^\d{4}-\d{2}-\d{2}$/)
})

test('validarRango acepta un rango vendible', () => {
  assert.equal(validarRango(MANANA, EN_4, 2), null)
})

test('validarRango rechaza salida anterior o igual a la llegada', () => {
  assert.match(validarRango(EN_4, MANANA, 2), /posterior/)
  assert.match(validarRango(MANANA, MANANA, 2), /posterior/)
})

test('validarRango rechaza llegada en el pasado', () => {
  const ayer = sumarDias(HOY, -1)
  assert.match(validarRango(ayer, MANANA, 2), /pasada/)
})

test('validarRango rechaza rangos mayores a 30 noches', () => {
  const en_31 = sumarDias(MANANA, 31)
  assert.match(validarRango(MANANA, en_31, 2), /30 noches/)
})

test('validarRango rechaza personas fuera de 1..30', () => {
  assert.match(validarRango(MANANA, EN_4, 0), /1 y 30/)
  assert.match(validarRango(MANANA, EN_4, 31), /1 y 30/)
  assert.match(validarRango(MANANA, EN_4, 'x'), /1 y 30/)
  assert.match(validarRango(MANANA, EN_4, 2.5), /1 y 30/)
})

test('construirEnlaceReserva arma el deep link del front público', () => {
  const enlace = construirEnlaceReserva('https://plataforma.test', MANANA, EN_4, 2)
  assert.equal(enlace, `https://plataforma.test/reservar?inicio=${MANANA}&fin=${EN_4}&personas=2`)
})

test('construirEnlaceReserva normaliza personas a entero', () => {
  const enlace = construirEnlaceReserva('https://plataforma.test', MANANA, EN_4, '02')
  assert.ok(enlace.endsWith('personas=2'), enlace)
})

test('construirEnlaceReserva rechaza el mismo rango inválido que el front', () => {
  assert.throws(() => construirEnlaceReserva('https://plataforma.test', EN_4, MANANA, 2), /posterior/)
})
