import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { aplicarPreset, camposVisibles, cuerpoBuzon, formularioVacio } from '../lib/correo.js'

describe('servidores de correo (#355)', () => {
  it('el preset de Gmail llena IMAP o SMTP según el proveedor', () => {
    const imap = aplicarPreset(formularioVacio('lectura_enviados'), 'gmail')
    assert.deepEqual([imap.parametros.host, imap.parametros.puerto, imap.parametros.seguridad], ['imap.gmail.com', 993, 'ssl'])
    const smtp = aplicarPreset(formularioVacio('envio_avisos'), 'outlook')
    assert.equal(smtp.parametros.host, 'smtp.office365.com')
    assert.ok(smtp.parametros.token_url.includes('microsoftonline'))
  })

  it('muestra los campos según autenticación y propósito', () => {
    assert.deepEqual(camposVisibles('lectura_enviados', 'imap', 'clave').secretos, ['clave'])
    assert.ok(camposVisibles('lectura_enviados', 'imap', 'oauth2').parametros.includes('client_id'))
    assert.ok(!camposVisibles('lectura_enviados', 'smtp', 'clave').parametros.includes('destino'))
    assert.ok(camposVisibles('envio_avisos', 'smtp', 'clave').parametros.includes('destino'))
    assert.deepEqual(camposVisibles('lectura_enviados', 'gmail_api', 'cuenta_servicio').secretos, ['cuenta_servicio_json'])
  })

  it('no envía secretos vacíos ni campos ocultos y convierte el puerto', () => {
    const form = { ...aplicarPreset(formularioVacio(), 'zoho'), etiqueta: ' reservas ', buzon_id: 'BZN-1' }
    form.parametros = { ...form.parametros, usuario: 'r@hotel.test', puerto: '993', destino: 'no-va@hotel.test' }
    form.secretos = { clave: '', refresh_token: 'oculto' }
    const cuerpo = cuerpoBuzon(form)
    assert.equal(cuerpo.etiqueta, 'reservas')
    assert.equal(cuerpo.parametros.puerto, 993)
    assert.equal(cuerpo.parametros.destino, undefined)
    assert.deepEqual(cuerpo.secretos, {})
    assert.equal(cuerpo.proposito, undefined) // al editar, el propósito no cambia
  })
})
