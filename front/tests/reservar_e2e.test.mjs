import test from 'node:test'
import assert from 'node:assert/strict'
import { contactoEstructurado, erroresContacto, errorCorreo, errorDocumento, errorTelefono } from '../app/reservar/continuidad.js'

test('E2E formulario /reservar: exige 3 campos obligatorios (nombre, correo, teléfono); RUT/pasaporte es opcional', () => {
  const vacio = erroresContacto('', '', '', '')
  assert.ok(vacio.nombre, 'Debe exigir nombre')
  assert.ok(vacio.contacto, 'Debe exigir correo')
  assert.ok(vacio.telefono, 'Debe exigir teléfono')
  assert.equal(vacio.documento, undefined, 'RUT o pasaporte es opcional (#414)')

  const soloCorreo = erroresContacto('Ana Pérez', 'ana@ejemplo.cl', '', '')
  assert.equal(soloCorreo.nombre, undefined)
  assert.equal(soloCorreo.contacto, undefined)
  assert.ok(soloCorreo.telefono, 'Debe rechazar si falta teléfono aunque haya correo')
  assert.equal(soloCorreo.documento, undefined)

  const valido = erroresContacto('Ana Pérez', 'ana@ejemplo.cl', '+56 9 8765 4321', '12.345.678-9')
  assert.deepEqual(valido, {})
})

test('E2E formulario /reservar: protege contra formatos inválidos o abuso de longitud', () => {
  assert.ok(errorTelefono('123'), 'Rechaza teléfono muy corto')
  assert.ok(errorTelefono('1'.repeat(35)), 'Rechaza teléfono excesivamente largo')
  assert.ok(errorCorreo('sin-arroba'), 'Rechaza correo inválido')
  assert.ok(errorDocumento('12'), 'Rechaza documento muy corto')
  assert.ok(errorDocumento('A'.repeat(35)), 'Rechaza documento excesivamente largo')
})

test('E2E envío /publico/solicitudes: procesa payload completo con idempotencia y token anti-abuso', async () => {
  let capturado = null
  const fetchMock = async (url, opts) => {
    capturado = { url, opts, body: JSON.parse(opts.body) }
    return {
      status: 201,
      ok: true,
      json: async () => ({ solicitud_id: 'SOL-E2E-001', estado: 'pendiente' }),
    }
  }

  const nombre = 'Carlos Muñoz'
  const correo = 'carlos@hotelherencia.cl'
  const telefono = '+56912345678'
  const documento = '15.234.567-K'
  const errores = erroresContacto(nombre, correo, telefono, documento)
  assert.deepEqual(errores, {})

  const res = await fetchMock('/publico/solicitudes', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': 'e2e-key-001',
      'X-Recaptcha-Token': 'token-valido',
    },
    body: JSON.stringify({
      tipo: 'matrimonial',
      inicio: '2026-12-01',
      fin: '2026-12-03',
      personas: 2,
      huesped_nombre: nombre,
      huesped_contacto: `${correo} · Tel: ${telefono} · Doc: ${documento}`,
    }),
  })

  assert.equal(res.status, 201)
  assert.equal(capturado.body.huesped_nombre, 'Carlos Muñoz')
  assert.match(capturado.body.huesped_contacto, /carlos@hotelherencia\.cl/)
  assert.match(capturado.body.huesped_contacto, /\+56912345678/)
  assert.match(capturado.body.huesped_contacto, /15\.234\.567-K/)
  assert.ok(capturado.opts.headers['Idempotency-Key'], 'Debe incluir Idempotency-Key contra envíos duplicados')
  assert.ok(capturado.opts.headers['X-Recaptcha-Token'], 'Debe incluir token reCAPTCHA contra abuso automatizado')
})

test('#414: contacto estructurado omite «Doc» cuando no hay documento', () => {
  assert.equal(contactoEstructurado('a@b.cl', '+56987654321', ''), 'a@b.cl · Tel: +56987654321')
  assert.equal(contactoEstructurado('a@b.cl', '+56987654321', ' 12.345.678-9 '), 'a@b.cl · Tel: +56987654321 · Doc: 12.345.678-9')
})
