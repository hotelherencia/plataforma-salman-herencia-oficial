/**
 * E2E del canal público — V1-ISSUE-23 y V1-ISSUE-24 (spec-api-v1 «Canal
 * público»): un visitante sin sesión llega desde la landing (deep link con
 * fechas y personas), ve la disponibilidad que decide el servidor, envía una
 * solicitud idempotente y recepción la convierte en reserva con trazabilidad.
 *
 * Navegador real (Chromium) contra front y API locales, datos 100 %
 * sintéticos. Cada mutación se verifica releyendo el estado por la API.
 *
 * Uso: cd e2e && FRONT_URL=http://127.0.0.1:3000 API_URL=http://127.0.0.1:8080 node e2e-reserva-publica.mjs
 */

import { chromium } from 'playwright'
import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONT = process.env.FRONT_URL || 'http://127.0.0.1:3000'
const API = process.env.API_URL || 'http://127.0.0.1:8080'
const ADMIN = ['admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123']
const RUN = Date.now().toString(36)
const K = (nombre) => `${nombre}-${RUN}`
const AQUI = dirname(fileURLToPath(import.meta.url))

function isoLocal(fecha) {
  const d = new Date(fecha)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dia = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${dia}`
}

function sumarDias(fecha, dias) {
  const d = new Date(`${fecha}T00:00:00`)
  d.setDate(d.getDate() + dias)
  return isoLocal(d)
}

async function api(metodo, ruta, { cuerpo, clave, cookie, cabeceras = {} } = {}) {
  const h = { ...cabeceras }
  if (cuerpo !== undefined) h['Content-Type'] = 'application/json'
  if (clave) h['Idempotency-Key'] = clave
  if (cookie) h.Cookie = cookie
  const r = await fetch(API + ruta, { method: metodo, headers: h, body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined })
  const texto = await r.text()
  let datos = {}
  try {
    datos = texto ? JSON.parse(texto) : {}
  } catch {
    datos = { detalle: texto }
  }
  return { estado: r.status, datos, cookie: (r.headers.get('set-cookie') || '').split(';')[0] }
}

async function loginApi(usuario, clave) {
  const r = await api('POST', '/sesion', { cuerpo: { usuario, clave } })
  if (r.estado !== 200) throw new Error(`login API falló para ${usuario}: ${r.estado}`)
  return r.cookie
}

function esperar(condicion, mensaje) {
  if (!condicion) throw new Error(mensaje)
}

const resultados = []
async function caso(id, ruta, flujo, rol, esperado, fn) {
  let observado = ''
  let estado = 'APROBADO'
  try {
    observado = (await fn()) || 'según lo esperado'
  } catch (error) {
    estado = 'FALLIDO'
    observado = `excepción: ${error.message}`
  }
  resultados.push({ id, ruta, flujo, rol, esperado, observado, estado })
  console.log(`${estado === 'APROBADO' ? '✓' : '✗'} [${id}] ${ruta} · ${flujo} · ${rol} → ${estado}`)
  if (estado === 'FALLIDO') console.log(`    esperado: ${esperado}\n    observado: ${observado}`)
}

const carpeta = join(AQUI, '..', 'capturas', `e2e-${isoLocal(new Date())}`)
mkdirSync(carpeta, { recursive: true })
let evidenciaN = 0
async function evidencia(page, nombre) {
  evidenciaN += 1
  const archivo = join(carpeta, `${String(evidenciaN).padStart(2, '0')}-${nombre}.png`)
  await page.screenshot({ path: archivo })
  return `capturas/e2e-${isoLocal(new Date())}/${String(evidenciaN).padStart(2, '0')}-${nombre}.png`
}

const HOY = isoLocal(new Date())
const MANANA = sumarDias(HOY, 1)
const EN_3 = sumarDias(HOY, 3)
const EN_5 = sumarDias(HOY, 5)
const EN_7 = sumarDias(HOY, 7)
const HAB = `HAB-PUB-${RUN}`

const navegador = await chromium.launch()
try {
  const cookieAdmin = await loginApi(ADMIN[0], ADMIN[1])
  // Aislamiento: habitación y tarifa propias de esta corrida.
  const alta = await api('PUT', `/hotel/habitaciones/${HAB}`, {
    cuerpo: { tipo: 'doble', capacidad: 2 }, cabeceras: { 'If-None-Match': '*' }, clave: K('alta-hab'), cookie: cookieAdmin,
  })
  esperar(alta.estado === 201 || alta.estado === 200, `alta habitación: ${alta.estado} ${JSON.stringify(alta.datos)}`)
  const tarifa = await api('PUT', '/hotel/tarifas', {
    cuerpo: { habitacion_id: HAB, fecha_desde: '2026-01-01', fecha_hasta: '2027-12-31', tarifa_noche_clp: 45000 },
    clave: K('tarifa'), cookie: cookieAdmin,
  })
  esperar(tarifa.estado === 201 || tarifa.estado === 200, `tarifa: ${tarifa.estado} ${JSON.stringify(tarifa.datos)}`)
  const recepcionUsuario = `recepcion-pub-${RUN}`
  const altaRecepcion = await api('POST', '/usuarios', {
    cuerpo: { nombre: recepcionUsuario, rol: 'recepcion', clave: 'RecepPubE2e123' },
    clave: K('alta-recep'), cookie: cookieAdmin,
  })
  esperar(altaRecepcion.estado === 201, `alta recepción: ${altaRecepcion.estado}`)
  const cookieRecepcion = await loginApi(recepcionUsuario, 'RecepPubE2e123')

  // ---------- PUB-01: deep link → disponibilidad → solicitud → bandeja → conversión ----------
  await caso('PUB-01', '/reservar', 'deep link de la landing → solicitud → recepción la convierte y la reserva queda trazable', 'visitante → recepcion', 'disponibilidad del servidor; solicitud con id; bandeja la muestra con el mismo id; conversión crea reserva confirmada', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    await page.goto(`${FRONT}/reservar?inicio=${MANANA}&fin=${EN_3}&personas=2`)
    await page.waitForSelector('.lista-opciones', { timeout: 8000 })
    const opcion = await page.locator(`.opcion:has-text("${HAB}")`).count()
    esperar(opcion > 0, `la oferta no incluye ${HAB}`)
    await page.getByRole('textbox', { name: 'Nombre' }).fill('Visitante E2E Público')
    await page.getByRole('textbox', { name: 'Correo o teléfono' }).fill('visitante.pub@example.test')
    await page.getByRole('button', { name: 'Enviar solicitud' }).click()
    await page.waitForSelector('[role=status]', { timeout: 8000 })
    const texto = await page.evaluate(() => document.querySelector('[role=status]')?.innerText || '')
    const solicitudId = (texto.match(/SOL-[a-z0-9]+/i) || [])[0]
    esperar(solicitudId, `sin número de solicitud en: ${texto.slice(0, 120)}`)
    const captura = await evidencia(page, 'pub-01-solicitud-recibida')
    await ctx.close()

    // recepción la ve en la bandeja con el mismo id y la convierte
    const ctxR = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const paginaR = await ctxR.newPage()
    await paginaR.goto(`${FRONT}/login`)
    await paginaR.getByRole('textbox', { name: 'Usuario' }).fill(recepcionUsuario)
    await paginaR.getByRole('textbox', { name: 'Clave' }).fill('RecepPubE2e123')
    await paginaR.getByRole('button', { name: 'Entrar' }).click()
    await paginaR.waitForTimeout(1800)
    await paginaR.goto(`${FRONT}/hotel/solicitudes`)
    await paginaR.waitForTimeout(1800)
    const fila = paginaR.locator(`tr:has-text("${solicitudId}")`)
    esperar((await fila.count()) > 0, `la bandeja no muestra ${solicitudId}`)
    await fila.getByRole('button', { name: 'Convertir en reserva' }).click()
    await paginaR.waitForSelector('.operacion-confirmada', { timeout: 8000 })
    const confirmacion = await paginaR.evaluate(() => document.querySelector('.operacion-confirmada')?.textContent || '')
    esperar(confirmacion.includes('convertida'), `confirmación: ${confirmacion}`)
    const detalle = await paginaR.evaluate(() => document.querySelector('.json-panel')?.textContent || '{}')
    const reservaId = (JSON.parse(detalle).reserva_id || '')
    esperar(reservaId, `sin reserva_id en ${detalle.slice(0, 160)}`)
    await evidencia(paginaR, 'pub-01-convertida')
    await ctxR.close()

    // releída por la API: solicitud convertida apunta a la reserva confirmada
    const solicitudes = await api('GET', `/hotel/solicitudes?estado=convertida`, { cookie: cookieRecepcion })
    const convertida = (solicitudes.datos.solicitudes || []).find((s) => s.solicitud_id === solicitudId)
    esperar(convertida && convertida.reserva_id === reservaId, `solicitud sin reserva_id: ${JSON.stringify(convertida)}`)
    const reserva = await api('GET', `/hotel/reservas/${reservaId}`, { cookie: cookieRecepcion })
    esperar(reserva.estado === 200 && reserva.datos.estado === 'confirmada', `reserva: ${reserva.estado} ${JSON.stringify(reserva.datos).slice(0, 120)}`)
    return `${solicitudId} → ${reservaId} (${captura})`
  })

  // ---------- PUB-02: sin cupo ----------
  await caso('PUB-02', '/reservar', 'rango sin cupo: la pantalla lo dice y la API rechaza sin persistir', 'visitante', '«No hay opciones…» en la pantalla; POST /publico/solicitudes → 409', async () => {
    const ocupante = await api('POST', '/hotel/reservas', {
      cuerpo: { habitacion_id: HAB, inicio: EN_5, fin: EN_7, huesped: { nombre: 'Ocupante E2E' } },
      clave: K('ocupante'), cookie: cookieAdmin,
    })
    esperar(ocupante.estado === 201, `no se pudo ocupar el rango: ${ocupante.estado}`)
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    await page.goto(`${FRONT}/reservar?inicio=${EN_5}&fin=${EN_7}&personas=2`)
    await page.waitForSelector('.lista-opciones', { timeout: 8000 })
    const ofreceHab = await page.locator(`.opcion:has-text("${HAB}")`).count()
    esperar(ofreceHab === 0, `${HAB} aparece pese a estar sin cupo`)
    await evidencia(page, 'pub-02-sin-cupo')
    await ctx.close()
    const directo = await api('POST', '/publico/solicitudes', {
      cuerpo: { habitacion_id: HAB, inicio: EN_5, fin: EN_7, personas: 2, huesped_nombre: 'X', huesped_contacto: 'x@x.test' },
      clave: K('pub-02'),
    })
    esperar(directo.estado === 409, `POST directo: ${directo.estado}`)
    return 'pantalla y API rechazan; nada que confirmar'
  })

  // ---------- PUB-03: doble envío no duplica ----------
  await caso('PUB-03', '/reservar', 'doble envío (misma clave del navegador) no crea dos solicitudes', 'visitante', 'una sola fila; el reintento responde 200 reintento:true', async () => {
    const nombreUnico = `Doble Clic ${RUN}`
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    // Aislamiento del cupo: PUB-01 convierte esta misma habitación en
    // MANANA..EN_3 y PUB-02 la ocupa en EN_5..EN_7. Este caso prueba la
    // idempotencia del doble envío, no el cupo: usa un rango propio libre
    // (nadie más de la corrida toca +20..+22).
    const ini = sumarDias(HOY, 20)
    const fin = sumarDias(HOY, 22)
    await page.goto(`${FRONT}/reservar?inicio=${ini}&fin=${fin}&personas=2`)
    await page.waitForSelector('.lista-opciones', { timeout: 8000 })
    await page.locator(`.opcion:has-text("${HAB}") input`).check()
    await page.getByRole('textbox', { name: 'Nombre' }).fill(nombreUnico)
    await page.getByRole('textbox', { name: 'Correo o teléfono' }).fill('doble@example.test')
    // Doble envío en la misma ráfaga (antes de que el 2xx renueve la clave):
    // dos submits del form con la misma Idempotency-Key en vuelo; el servidor
    // deduplica (200 reintento) y solo nace una solicitud.
    await page.evaluate(() => {
      const form = [...document.querySelectorAll('form')].find((f) => f.textContent.includes('Enviar solicitud'))
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
    })
    await page.waitForSelector('[role=status]', { timeout: 8000 })
    await ctx.close()
    const bandeja = await api('GET', `/hotel/solicitudes?estado=recibida`, { cookie: cookieRecepcion })
    const duplicadas = (bandeja.datos.solicitudes || []).filter((s) => s.huesped_nombre === nombreUnico)
    esperar(duplicadas.length === 1, `solicitudes del huésped: ${duplicadas.length}`)
    return '1 sola solicitud tras el doble clic'
  })

  // ---------- PUB-04: parámetros manipulados ----------
  await caso('PUB-04', '/reservar', 'parámetros de la URL inválidos: mensaje local, sin llamada de mutación', 'visitante', 'alerta de validación y sección de disponibilidad ausente', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    await page.goto(`${FRONT}/reservar?inicio=${EN_3}&fin=${MANANA}&personas=2`)
    await page.waitForSelector('[role=alert]', { timeout: 8000 })
    const alerta = await page.evaluate(() => document.querySelector('[role=alert]')?.textContent || '')
    esperar(alerta.includes('posterior'), `alerta: ${alerta}`)
    esperar((await page.locator('.lista-opciones').count()) === 0, 'se ofertó pese a fechas invertidas')
    await page.goto(`${FRONT}/reservar?inicio=${MANANA}&fin=${EN_3}&personas=99`)
    await page.waitForSelector('[role=alert]', { timeout: 8000 })
    const alerta2 = await page.evaluate(() => document.querySelector('[role=alert]')?.textContent || '')
    esperar(alerta2.includes('Personas'), `alerta2: ${alerta2}`)
    await ctx.close()
    return 'fin invertido y personas=99 rechazados en el cliente'
  })

  // ---------- PUB-05: sin sesión no hay pantalla interna ----------
  await caso('PUB-05', '/reservar', 'el visitante jamás ve el menú interno ni datos ajenos', 'anonimo', 'sin enlaces de operación en /reservar; /hotel/panel pide login', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    await page.goto(`${FRONT}/reservar`)
    await page.waitForTimeout(1500)
    const menu = await page.getByRole('link', { name: 'Panel' }).count()
    esperar(menu === 0, 'menú interno visible en la página pública')
    await page.goto(`${FRONT}/hotel/panel`)
    await page.waitForTimeout(1500)
    const loginVisible = await page.locator('.login-tarjeta').count()
    esperar(loginVisible > 0, 'la ruta interna no pidió login')
    await ctx.close()
    return 'página pública limpia y guardia intacta'
  })

  // ---------- PUB-REF: fechas sin ref → aviso (V1-ISSUE-42) ----------
  await caso('PUB-REF', '/reservar', 'URL solo con fechas: campos vacíos y aviso de consulta previa ausente', 'visitante', '[data-aviso-sin-ref] visible; Nombre y contacto vacíos; sin PII en la URL', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    await page.goto(`${FRONT}/reservar?inicio=${MANANA}&fin=${EN_3}&personas=2`)
    await page.waitForSelector('.lista-opciones', { timeout: 8000 })
    const aviso = page.locator('[data-aviso-sin-ref]')
    esperar((await aviso.count()) === 1, 'falta el aviso sin ref')
    const textoAviso = await aviso.innerText()
    esperar(textoAviso.includes('consulta previa'), `aviso inesperado: ${textoAviso.slice(0, 120)}`)
    const nombre = await page.getByRole('textbox', { name: 'Nombre' }).inputValue()
    const contacto = await page.getByRole('textbox', { name: 'Correo o teléfono' }).inputValue()
    esperar(nombre === '' && contacto === '', `contacto precargado sin ref: «${nombre}» / «${contacto}»`)
    const url = page.url()
    esperar(!/[?&](nombre|correo|telefono|email|phone)=/i.test(url), `PII en URL: ${url}`)
    await evidencia(page, 'pub-ref-aviso-sin-ref')
    await ctx.close()
    return 'aviso sin ref + campos vacíos'
  })

  // ---------- BAN-01: rechazo con motivo ----------
  await caso('BAN-01', '/hotel/solicitudes', 'recepción rechaza con motivo; la conversión posterior es 409', 'recepcion', 'estado rechazada + motivo; convertir → 409', async () => {
    const creada = await api('POST', '/publico/solicitudes', {
      cuerpo: { habitacion_id: HAB, inicio: sumarDias(HOY, 9), fin: sumarDias(HOY, 11), personas: 2, huesped_nombre: 'Rechazado E2E', huesped_contacto: 'r@x.test' },
      clave: K('ban-01'),
    })
    esperar(creada.estado === 201, `solicitud: ${creada.estado} ${JSON.stringify(creada.datos)}`)
    const solicitudId = creada.datos.solicitud_id
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    await page.goto(`${FRONT}/login`)
    await page.getByRole('textbox', { name: 'Usuario' }).fill(recepcionUsuario)
    await page.getByRole('textbox', { name: 'Clave' }).fill('RecepPubE2e123')
    await page.getByRole('button', { name: 'Entrar' }).click()
    await page.waitForTimeout(1800)
    await page.goto(`${FRONT}/hotel/solicitudes?estado=recibida`)
    await page.waitForTimeout(1800)
    const fila = page.locator(`tr:has-text("${solicitudId}")`)
    esperar((await fila.count()) > 0, `bandeja sin ${solicitudId}`)
    await fila.getByPlaceholder('Motivo del rechazo').fill('sin cupo real')
    await fila.getByRole('button', { name: 'Rechazar' }).click()
    await page.waitForTimeout(1800)
    const releida = await api('GET', `/hotel/solicitudes?estado=rechazada`, { cookie: cookieRecepcion })
    const rechazada = (releida.datos.solicitudes || []).find((s) => s.solicitud_id === solicitudId)
    esperar(rechazada && rechazada.estado === 'rechazada', `estado: ${JSON.stringify(rechazada)}`)
    const conversion = await api('POST', `/hotel/solicitudes/${solicitudId}/conversion`, {
      cuerpo: {}, clave: K('ban-01-conv'), cookie: cookieRecepcion,
    })
    esperar(conversion.estado === 409, `conversión sobre rechazada: ${conversion.estado}`)
    await ctx.close()
    return `rechazada con motivo; conversión ${conversion.estado}`
  })
} finally {
  await navegador.close()
}

const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
const fallidos = resultados.filter((r) => r.estado === 'FALLIDO')
console.log(`\n${aprobados}/${resultados.length} aprobados → ${join(AQUI, 'e2e-reserva-publica-resultados.json')}`)
writeFileSync(join(AQUI, 'e2e-reserva-publica-resultados.json'), JSON.stringify({ fecha: HOY, resultados }, null, 2))
if (fallidos.length > 0) process.exitCode = 1
