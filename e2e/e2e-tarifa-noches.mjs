/**
 * E2E de V1-ISSUE-39 — regla RES-TARIFA-NOCHES (spec-hotel-operacion-v1 §2.8,
 * CA-HAB-08): desde el menú, una estadía con noches sin tarifa no aparece en
 * la Oferta y su Reserva se rechaza con la noche descubierta; con la tarifa
 * siguiente registrada en la ficha, la misma estadía se ofrece y el total
 * confirmado es el ofrecido.
 *
 * Archivo propio: no modifica e2e.mjs, e2e-operacion.mjs ni sus resultados.
 * Navegador real (Chromium) contra front y API locales, datos 100 %
 * sintéticos, ids y claves únicos por corrida. Cada mutación se verifica
 * releyendo el estado desde la API.
 *
 * Uso: cd e2e && FRONT_URL=http://127.0.0.1:3000 API_URL=http://127.0.0.1:8080 node e2e-tarifa-noches.mjs
 * Salida: consola + e2e-tarifa-noches-resultados.json; capturas en
 * ../capturas/e2e-AAAA-MM-DD/tn-NN-*.png.
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

function sumarDias(isoFecha, dias) {
  const d = new Date(`${isoFecha}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + dias)
  return d.toISOString().slice(0, 10)
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

let carpeta = null
let evidenciaN = 0
async function evidencia(page, nombre) {
  evidenciaN += 1
  const archivo = join(carpeta, `tn-${String(evidenciaN).padStart(2, '0')}-${nombre}.png`)
  await page.screenshot({ path: archivo, fullPage: true })
  return archivo
}

async function loginUi(page, [usuario, clave]) {
  await page.goto(`${FRONT}/login`)
  await page.waitForSelector('input')
  await page.getByRole('textbox', { name: 'Usuario' }).fill(usuario)
  await page.getByRole('textbox', { name: 'Clave' }).fill(clave)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await page.waitForTimeout(1800)
}

const alerta = (page) => page.evaluate(() => document.querySelector('[role=alert]')?.textContent || null)
const confirmacion = (page) => page.evaluate(() => document.querySelector('.operacion-confirmada')?.textContent || null)
const textoPagina = (page) => page.evaluate(() => document.body.innerText)

const navegador = await chromium.launch()
async function paginaDe(credenciales) {
  const ctx = await navegador.newContext({ baseURL: FRONT })
  const page = await ctx.newPage()
  await loginUi(page, credenciales)
  return page
}

async function irDesdeMenu(page, enlace, ruta) {
  await page.goto(`${FRONT}/`)
  await page.waitForTimeout(1200)
  await page.getByRole('link', { name: 'Hotel', exact: true }).first().click()
  await page.waitForTimeout(1400)
  await page.getByRole('link', { name: enlace, exact: true }).first().click()
  await page.waitForTimeout(1400)
  esperar(page.url().endsWith(ruta), `el menú llevó a ${page.url()}`)
}

try {
  // ===== Semilla sintética (por API, como el administrador) =====
  const cAdmin = await loginApi(...ADMIN)
  const RECEPCION = [`recepcion_tn_${RUN}`, 'RecepTn1234']
  const u = await api('POST', '/usuarios', { cookie: cAdmin, clave: K('u-rec'), cuerpo: { nombre: RECEPCION[0], rol: 'recepcion', clave: RECEPCION[1] } })
  esperar(u.estado === 201, `alta recepción: ${u.estado} ${JSON.stringify(u.datos)}`)
  const cRecepcion = await loginApi(...RECEPCION)

  const HOY = (await api('GET', '/hotel/indicadores', { cookie: cAdmin })).datos.fecha_corte
  carpeta = join(AQUI, '..', 'capturas', `e2e-${HOY}`)
  mkdirSync(carpeta, { recursive: true })
  const D = (n) => sumarDias(HOY, n)

  const HAB = `HAB-${RUN}-TN`
  const alta = await api('PUT', `/hotel/habitaciones/${HAB}`, { cookie: cAdmin, clave: K('alta'), cuerpo: { tipo: 'doble', capacidad: 2 }, cabeceras: { 'If-None-Match': '*' } })
  esperar(alta.estado === 200 && alta.datos.creada === true, `alta: ${alta.estado} ${JSON.stringify(alta.datos)}`)
  // tarifa de las noches 40..44 (hasta 45 sin incluir); la estadía 43→47 deja 45 y 46 sin tarifa
  const t1 = await api('PUT', '/hotel/tarifas', { cookie: cAdmin, clave: K('tar1'), cuerpo: { habitacion_id: HAB, fecha_desde: D(40), fecha_hasta: D(45), tarifa_noche_clp: 41000 } })
  esperar(t1.estado === 201, `tarifa 1: ${t1.estado} ${JSON.stringify(t1.datos)}`)
  const [INICIO, FIN] = [D(43), D(47)]

  const reservasDe = async () =>
    (await api('GET', `/hotel/reservas?habitacion_id=${encodeURIComponent(HAB)}`, { cookie: cRecepcion })).datos.reservas || []
  const ofertaApi = async () =>
    ((await api('GET', `/hotel/oferta?inicio=${INICIO}&fin=${FIN}&personas=2`, { cookie: cRecepcion })).datos.oferta || []).find((i) => i.habitacion_id === HAB)

  const recepcion = await paginaDe(RECEPCION)
  const consultarOferta = async () => {
    await recepcion.getByRole('textbox', { name: 'Desde' }).fill(INICIO)
    await recepcion.getByRole('textbox', { name: 'Hasta' }).fill(FIN)
    await recepcion.getByLabel('Personas').fill('2')
    await recepcion.getByRole('button', { name: 'Consultar oferta' }).click()
    await recepcion.waitForTimeout(1500)
  }
  const confirmarReserva = async () => {
    await recepcion.getByRole('textbox', { name: 'Habitación' }).fill(HAB)
    await recepcion.getByRole('textbox', { name: 'Desde' }).fill(INICIO)
    await recepcion.getByRole('textbox', { name: 'Hasta' }).fill(FIN)
    await recepcion.getByRole('textbox', { name: 'Huésped' }).fill('Huésped Noches')
    await recepcion.getByRole('button', { name: 'Confirmar reserva' }).click()
    await recepcion.waitForTimeout(1500)
  }

  await caso('TN-01', '/hotel/oferta', 'desde el menú, estadía con noches sin tarifa', 'recepcion', 'la habitación no aparece en la oferta (API y pantalla)', async () => {
    await irDesdeMenu(recepcion, 'Oferta', '/hotel/oferta')
    await consultarOferta()
    const texto = await textoPagina(recepcion)
    await evidencia(recepcion, 'oferta-sin-noches-cubiertas')
    esperar(!texto.includes(HAB), `la pantalla muestra ${HAB}`)
    esperar((await ofertaApi()) === undefined, 'la API la ofrece')
    return `${HAB} ausente en pantalla y en GET /hotel/oferta`
  })

  await caso('TN-02', '/hotel/reserva', 'desde el menú, reservar la misma estadía', 'recepcion', `409: alerta «sin tarifa vigente … la noche ${D(45)}»; la API no registra reserva`, async () => {
    await irDesdeMenu(recepcion, 'Nueva reserva', '/hotel/reserva')
    await confirmarReserva()
    const a = await alerta(recepcion)
    await evidencia(recepcion, 'reserva-rechazada')
    esperar(a && a.includes('sin tarifa vigente') && a.includes(D(45)), `alerta: ${a}`)
    esperar((await confirmacion(recepcion)) === null, 'apareció una confirmación')
    const lista = await reservasDe()
    esperar(lista.length === 0, `la API lista ${lista.length} reserva(s)`)
    return `${a} · 0 reservas releídas`
  })

  const admin = await paginaDe(ADMIN)
  await caso('TN-03', '/hotel/habitaciones/[id] → /hotel/oferta → /hotel/reserva', 'registrar la tarifa siguiente en la ficha, ofrecer y confirmar', 'administrador → recepcion', 'se ofrece; el total y la tarifa confirmados son los ofrecidos y el cargo coincide', async () => {
    await admin.goto(`${FRONT}/hotel/habitaciones/${encodeURIComponent(HAB)}`)
    await admin.waitForTimeout(1800)
    const form = admin.locator('form', { has: admin.getByRole('button', { name: 'Guardar tarifa' }) })
    await form.getByLabel('Desde').fill(D(45))
    await form.getByLabel('Hasta (sin incluir)').fill(D(60))
    await form.getByLabel('Tarifa por noche (CLP)').fill('63000')
    await form.getByRole('button', { name: 'Guardar tarifa' }).click()
    await admin.waitForTimeout(1500)
    const ficha = await api('GET', `/hotel/habitaciones/${HAB}`, { cookie: cAdmin })
    esperar((ficha.datos.tarifas || []).some((t) => t.fecha_desde === D(45) && t.tarifa_noche_clp === 63000), `tarifas releídas: ${JSON.stringify(ficha.datos.tarifas)}`)

    await irDesdeMenu(recepcion, 'Oferta', '/hotel/oferta')
    await consultarOferta()
    const ofrecida = await ofertaApi()
    esperar(ofrecida, 'la API no la ofrece')
    esperar((await textoPagina(recepcion)).includes(HAB), 'la pantalla no la muestra')
    await evidencia(recepcion, 'oferta-cubierta')

    await irDesdeMenu(recepcion, 'Nueva reserva', '/hotel/reserva')
    await confirmarReserva()
    const c = await confirmacion(recepcion)
    await evidencia(recepcion, 'reserva-confirmada')
    esperar(c && c.includes('confirmada'), `confirmación: ${c} · alerta: ${await alerta(recepcion)}`)
    const lista = await reservasDe()
    esperar(lista.length === 1 && lista[0].estado === 'confirmada', `releído: ${JSON.stringify(lista).slice(0, 200)}`)
    esperar(lista[0].tarifa_noche_aceptada_clp === ofrecida.tarifa_noche_clp, `tarifa aceptada ${lista[0].tarifa_noche_aceptada_clp} ≠ ofrecida ${ofrecida.tarifa_noche_clp}`)
    const detalle = await api('GET', `/hotel/reservas/${lista[0].reserva_id}`, { cookie: cRecepcion })
    const cargos = (detalle.datos.cargos || []).reduce((s, x) => s + x.monto_clp, 0)
    esperar(cargos === ofrecida.total_clp, `cargos ${cargos} ≠ total ofrecido ${ofrecida.total_clp} · ${JSON.stringify(detalle.datos).slice(0, 200)}`)
    return `${lista[0].reserva_id}: $${ofrecida.tarifa_noche_clp}/noche, total $${ofrecida.total_clp} = cargos`
  })
} finally {
  await navegador.close()
  const archivo = join(AQUI, 'e2e-tarifa-noches-resultados.json')
  writeFileSync(archivo, JSON.stringify(resultados, null, 2) + '\n')
  const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
  console.log(`\n${aprobados}/${resultados.length} aprobados → ${archivo}`)
  if (aprobados !== resultados.length) process.exitCode = 1
}
