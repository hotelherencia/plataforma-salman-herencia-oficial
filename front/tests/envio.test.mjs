// Envío de /reservar (fix-forms): node --test front/tests/
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { conCodigo, enviarSolicitud, mensajeSolicitud, nuevoCodigoEnvio, obtenerToken } from '../app/reservar/envio.js'

const traducir = (datos, estado) => (typeof datos?.detail === 'string' ? datos.detail : `Error ${estado}`)
const sinEspera = async () => {}

function tokens() {
  let n = 0
  const emitidos = []
  return {
    emitidos,
    token: async () => {
      n += 1
      const t = `tok-reserva-${n}-${'x'.repeat(30)}`
      emitidos.push(t)
      return t
    },
  }
}

function servidor(pasos) {
  const llamadas = []
  let i = 0
  return {
    llamadas,
    pedir: async (cabeceras) => {
      llamadas.push(cabeceras)
      const paso = pasos[Math.min(i, pasos.length - 1)]
      i += 1
      if (paso === 'red') throw new Error('la API no responde')
      return paso
    },
  }
}

test('red caída: reintenta una vez con token nuevo; X-Request-Id lleva el código y el intento', async () => {
  const t = tokens()
  const s = servidor(['red', { estado: 201, datos: { solicitud_id: 'SOL-1' } }])
  const r = await enviarSolicitud({ pedir: s.pedir, token: t.token, esperar: sinEspera })
  assert.equal(r.tipo, 'respuesta')
  assert.equal(r.estado, 201)
  assert.equal(s.llamadas.length, 2)
  assert.notEqual(s.llamadas[0]['X-Recaptcha-Token'], s.llamadas[1]['X-Recaptcha-Token'])
  assert.equal(s.llamadas[0]['X-Request-Id'], `${r.codigo}-1`)
  assert.equal(s.llamadas[1]['X-Request-Id'], `${r.codigo}-2`)
})

test('502/503/504 (Railway desplegando) se reintentan; 4xx no', async () => {
  for (const estado of [502, 503, 504]) {
    const s = servidor([{ estado, datos: {} }, { estado: 200, datos: { reintento: true } }])
    const r = await enviarSolicitud({ pedir: s.pedir, token: tokens().token, esperar: sinEspera })
    assert.equal(r.estado, 200)
    assert.equal(s.llamadas.length, 2)
  }
  for (const estado of [403, 409, 422, 429]) {
    const s = servidor([{ estado, datos: { detail: 'x' } }, { estado: 201, datos: {} }])
    const r = await enviarSolicitud({ pedir: s.pedir, token: tokens().token, esperar: sinEspera })
    assert.equal(r.estado, estado)
    assert.equal(s.llamadas.length, 1)
  }
})

test('reCAPTCHA bloqueado: no se envía nada y el mensaje lo explica con código', async () => {
  const s = servidor([{ estado: 201, datos: {} }])
  const ventana = { setInterval, clearInterval }
  let bloqueado = false
  setTimeout(() => { bloqueado = true }, 10)
  const r = await enviarSolicitud({
    pedir: s.pedir,
    token: () => obtenerToken(ventana, 'clave', 'reserva', { bloqueado: () => bloqueado, pasoMs: 2 }),
    esperar: sinEspera,
  })
  assert.equal(r.tipo, 'captcha_bloqueado')
  assert.equal(s.llamadas.length, 0)
  const m = mensajeSolicitud(r, traducir)
  assert.match(m, /bloqueador/)
  assert.match(m, /Firefox/)
  assert.match(m, /WhatsApp/)
  assert.match(m, /\(código [A-Z2-9]{8}\)$/)
})

test('grecaptcha listo: obtenerToken usa la acción reserva y entrega el token', async () => {
  const acciones = []
  const ventana = {
    grecaptcha: { ready: (fn) => fn(), execute: async (_c, { action }) => { acciones.push(action); return 'k'.repeat(40) } },
    setInterval, clearInterval,
  }
  assert.equal(await obtenerToken(ventana, 'clave', 'reserva'), 'k'.repeat(40))
  assert.deepEqual(acciones, ['reserva'])
  ventana.grecaptcha.execute = async () => { throw new Error('x') }
  await assert.rejects(obtenerToken(ventana, 'clave', 'reserva'), (e) => e.causa === 'recaptcha')
})

test('mensajes específicos en español con código para cada falla', () => {
  const c = 'ABCD2345'
  const casos = [
    [{ tipo: 'red', codigo: c }, /No pudimos conectar con el servidor/],
    [{ tipo: 'respuesta', estado: 502, datos: { detalle: '<html>' }, codigo: c }, /problema de nuestro lado/],
    [{ tipo: 'respuesta', estado: 500, datos: {}, codigo: c }, /problema de nuestro lado/],
    [{ tipo: 'respuesta', estado: 503, datos: { detail: 'Canal no disponible por ahora.' }, codigo: c }, /Canal no disponible/],
    [{ tipo: 'respuesta', estado: 403, datos: {}, codigo: c }, /No pudimos verificar el envío/],
    [{ tipo: 'respuesta', estado: 429, datos: {}, codigo: c }, /demasiados intentos/],
    [{ tipo: 'respuesta', estado: 409, datos: { detail: 'no hay cupo' }, codigo: c }, /no hay cupo/],
  ]
  for (const [resultado, patron] of casos) {
    const m = mensajeSolicitud(resultado, traducir)
    assert.match(m, patron)
    assert.ok(m.endsWith(`(código ${c})`), m)
  }
  assert.match(nuevoCodigoEnvio(), /^[A-Z2-9]{8}$/)
  assert.equal(conCodigo('Hola.', ''), 'Hola.')
})

test('page.js pide el token al enviar, avisa si el script falla y conserva la clave ante red/5xx', () => {
  const page = readFileSync(new URL('../app/reservar/page.js', import.meta.url), 'utf8')
  assert.match(page, /script\.onerror = \(\) => \{\s*recaptchaBloqueado = true/)
  assert.match(page, /token: \(\) => tokenRecaptcha\('reserva'\)/)
  assert.match(page, /if \(resultado\.tipo === 'respuesta'\) alRechazar\(resultado\.estado, renovarClave\)/)
})
