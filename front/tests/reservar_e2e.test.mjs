import test from 'node:test'
import assert from 'node:assert/strict'
import {
  erroresContacto, errorCorreo, errorDocumento, errorTelefono, leerParametros, validarRango,
} from '../app/reservar/continuidad.js'

test('E2E formulario /reservar (#414): exige nombre, correo y teléfono; RUT/pasaporte es opcional', () => {
  const vacio = erroresContacto('', '', '', '')
  assert.ok(vacio.nombre, 'Debe exigir nombre')
  assert.ok(vacio.contacto, 'Debe exigir correo')
  assert.ok(vacio.telefono, 'Debe exigir teléfono')
  assert.equal(vacio.documento, undefined, 'RUT/pasaporte debe ser opcional en la solicitud pública')

  const soloCorreo = erroresContacto('Ana Pérez', 'ana@ejemplo.cl', '', '')
  assert.equal(soloCorreo.nombre, undefined)
  assert.equal(soloCorreo.contacto, undefined)
  assert.ok(soloCorreo.telefono, 'Debe rechazar si falta teléfono aunque haya correo')
  assert.equal(soloCorreo.documento, undefined)

  const sinDocumento = erroresContacto('Ana Pérez', 'ana@ejemplo.cl', '+56 9 8765 4321', '')
  assert.deepEqual(sinDocumento, {})

  const conDocumento = erroresContacto('Ana Pérez', 'ana@ejemplo.cl', '+56 9 8765 4321', '12.345.678-9')
  assert.deepEqual(conDocumento, {})
})

test('E2E formulario /reservar: protege contra formatos inválidos o abuso de longitud', () => {
  assert.ok(errorTelefono('123'), 'Rechaza teléfono muy corto')
  assert.ok(errorTelefono('1'.repeat(35)), 'Rechaza teléfono excesivamente largo')
  assert.ok(errorCorreo('sin-arroba'), 'Rechaza correo inválido')
  assert.equal(errorDocumento(''), undefined, 'Documento vacío es válido (opcional)')
  assert.ok(errorDocumento('12'), 'Si se ingresa documento, rechaza valores muy cortos')
  assert.ok(errorDocumento('A'.repeat(35)), 'Si se ingresa documento, rechaza valores excesivamente largos')
})

test('E2E flujo único (#414): barra landing (3 campos) → /reservar → POST /publico/solicitudes sin doble formulario ni RUT obligatorio', async () => {
  // 1. Llega directo desde la barra rápida de 3 campos de la landing (sin lead previo ni PII en URL)
  const queryLanding = new URLSearchParams('llegada=2026-12-01&salida=2026-12-03&personas=2')
  const parametros = leerParametros(queryLanding)
  assert.equal(parametros.inicio, '2026-12-01')
  assert.equal(parametros.fin, '2026-12-03')
  assert.equal(parametros.personas, '2')
  assert.equal(parametros.ref, '')
  assert.deepEqual(parametros.avisos, [])
  assert.equal(validarRango(parametros.inicio, parametros.fin, parametros.personas, '2026-11-23'), null)

  // 2. Completa solo los 3 datos de contacto mínimos (sin RUT/pasaporte)
  const nombre = 'Carlos Muñoz'
  const correo = 'carlos@hotelherencia.cl'
  const telefono = '+56912345678'
  const documento = ''
  const errores = erroresContacto(nombre, correo, telefono, documento)
  assert.deepEqual(errores, {})

  let capturado = null
  const fetchMock = async (url, opts) => {
    capturado = { url, opts, body: JSON.parse(opts.body) }
    return {
      status: 201,
      ok: true,
      json: async () => ({ solicitud_id: 'SOL-E2E-001', estado: 'recibida' }),
    }
  }

  const contactoFinal = documento.trim()
    ? `${correo} · Tel: ${telefono} · Doc: ${documento.trim()}`
    : `${correo} · Tel: ${telefono}`

  const res = await fetchMock('/publico/solicitudes', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': 'e2e-key-001',
      'X-Recaptcha-Token': 'token-valido',
    },
    body: JSON.stringify({
      tipo: 'matrimonial',
      inicio: parametros.inicio,
      fin: parametros.fin,
      personas: Number(parametros.personas),
      huesped_nombre: nombre,
      huesped_contacto: contactoFinal,
    }),
  })

  assert.equal(res.status, 201)
  assert.equal(capturado.body.huesped_nombre, 'Carlos Muñoz')
  assert.equal(capturado.body.huesped_contacto, 'carlos@hotelherencia.cl · Tel: +56912345678')
  assert.doesNotMatch(capturado.body.huesped_contacto, /Doc:/)
  assert.ok(capturado.opts.headers['Idempotency-Key'], 'Debe incluir Idempotency-Key contra envíos duplicados')
  assert.ok(capturado.opts.headers['X-Recaptcha-Token'], 'Debe incluir token reCAPTCHA contra abuso automatizado')
})
