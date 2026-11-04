/**
 * E2E de V1-ISSUE-12 — regla RES-VENDIBLE (spec-hotel-operacion-v1 §2.7,
 * CA-HAB-07): desde el menú, una reserva sobre una habitación fuera del cupo
 * (retirada o con mantenimiento abierto) se rechaza con el mensaje del
 * servidor y no deja reserva; reincorporada, la misma reserva se confirma.
 *
 * Archivo propio: no modifica e2e.mjs ni e2e-operacion.mjs ni sus
 * resultados. Navegador real (Chromium) contra front y API locales, datos
 * 100 % sintéticos, ids y claves únicos por corrida. Cada mutación se
 * verifica releyendo el estado desde la API.
 *
 * Uso: cd e2e && FRONT_URL=http://127.0.0.1:3000 API_URL=http://127.0.0.1:8080 node e2e-reserva-vendible.mjs
 * Salida: consola + e2e-reserva-vendible-resultados.json; capturas en
 * ../capturas/e2e-AAAA-MM-DD/rv-NN-*.png.
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
  const archivo = join(carpeta, `rv-${String(evidenciaN).padStart(2, '0')}-${nombre}.png`)
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

const navegador = await chromium.launch()
async function paginaDe(credenciales) {
  const ctx = await navegador.newContext({ baseURL: FRONT })
  const page = await ctx.newPage()
  await loginUi(page, credenciales)
  return page
}

try {
  // ===== Semilla sintética (por API, como el administrador) =====
  const cAdmin = await loginApi(...ADMIN)
  const RECEPCION = [`recepcion_rv_${RUN}`, 'RecepRv1234']
  await api('POST', '/usuarios', { cookie: cAdmin, clave: K('u-rec'), cuerpo: { nombre: RECEPCION[0], rol: 'recepcion', clave: RECEPCION[1] } })
  const cRecepcion = await loginApi(...RECEPCION)

  const HOY = (await api('GET', '/hotel/indicadores', { cookie: cAdmin })).datos.fecha_corte
  carpeta = join(AQUI, '..', 'capturas', `e2e-${HOY}`)
  mkdirSync(carpeta, { recursive: true })
  const D = (n) => sumarDias(HOY, n)

  const HAB_R = `HAB-${RUN}-R` // se retira de operación
  const HAB_M = `HAB-${RUN}-MT` // mantenimiento abierto
  for (const id of [HAB_R, HAB_M]) {
    await api('PUT', `/hotel/habitaciones/${id}`, { cookie: cAdmin, clave: K(`alta-${id}`), cuerpo: { tipo: 'doble', capacidad: 2 }, cabeceras: { 'If-None-Match': '*' } })
    await api('PUT', '/hotel/tarifas', { cookie: cAdmin, clave: K(`tar-${id}`), cuerpo: { habitacion_id: id, fecha_desde: D(-30), fecha_hasta: D(365), tarifa_noche_clp: 52000 } })
  }
  const retiro = await api('POST', `/hotel/habitaciones/${HAB_R}/servicio`, { cookie: cAdmin, clave: K('ret'), cuerpo: { en_servicio: false, motivo: 'remodelación sintética' } })
  esperar(retiro.estado === 200 && retiro.datos.estado_operativo === 'fuera_de_servicio', `retiro: ${retiro.estado} ${JSON.stringify(retiro.datos)}`)
  const mant = await api('POST', `/hotel/habitaciones/${HAB_M}/mantenimiento`, { cookie: cAdmin, clave: K('mant'), cuerpo: { abierto: true } })
  esperar(mant.estado === 200, `mantenimiento: ${mant.estado} ${JSON.stringify(mant.datos)}`)

  const reservasDe = async (hid) =>
    (await api('GET', `/hotel/reservas?habitacion_id=${encodeURIComponent(hid)}`, { cookie: cRecepcion })).datos.reservas || []

  const recepcion = await paginaDe(RECEPCION)
  const llenarYConfirmar = async (hid, nombre) => {
    await recepcion.getByRole('textbox', { name: 'Habitación' }).fill(hid)
    await recepcion.getByRole('textbox', { name: 'Desde' }).fill(D(40))
    await recepcion.getByRole('textbox', { name: 'Hasta' }).fill(D(42))
    await recepcion.getByRole('textbox', { name: 'Huésped' }).fill(nombre)
    await recepcion.getByRole('button', { name: 'Confirmar reserva' }).click()
    await recepcion.waitForTimeout(1500)
  }

  await caso('RV-01', '/hotel/reserva', 'desde el menú, reservar una habitación retirada', 'recepcion', '409: alerta «fuera del cupo»; la API no registra reserva', async () => {
    await recepcion.goto(`${FRONT}/`)
    await recepcion.waitForTimeout(1200)
    await recepcion.getByRole('link', { name: 'Hotel', exact: true }).first().click()
    await recepcion.waitForTimeout(1400)
    await recepcion.getByRole('link', { name: 'Nueva reserva', exact: true }).click()
    await recepcion.waitForTimeout(1400)
    esperar(recepcion.url().endsWith('/hotel/reserva'), `menú llevó a ${recepcion.url()}`)
    await llenarYConfirmar(HAB_R, 'Huésped Retirada')
    const a = await alerta(recepcion)
    await evidencia(recepcion, 'retirada-rechazada')
    esperar(a && a.includes('fuera del cupo'), `alerta: ${a}`)
    esperar((await confirmacion(recepcion)) === null, 'apareció una confirmación')
    const lista = await reservasDe(HAB_R)
    esperar(lista.length === 0, `la API lista ${lista.length} reserva(s) en ${HAB_R}`)
    return `${a} · 0 reservas releídas`
  })

  await caso('RV-02', '/hotel/reserva', 'reservar una habitación con mantenimiento abierto', 'recepcion', '409: alerta «fuera del cupo»; sin reserva', async () => {
    await recepcion.getByRole('button', { name: 'Nueva operación' }).click()
    await recepcion.waitForTimeout(500)
    await llenarYConfirmar(HAB_M, 'Huésped Mantenimiento')
    const a = await alerta(recepcion)
    esperar(a && a.includes('fuera del cupo'), `alerta: ${a}`)
    const lista = await reservasDe(HAB_M)
    esperar(lista.length === 0, `la API lista ${lista.length} reserva(s) en ${HAB_M}`)
    return `${a} · 0 reservas releídas`
  })

  const admin = await paginaDe(ADMIN)
  await caso('RV-03', '/hotel/habitaciones/[id]', 'reincorporar desde la ficha y volver a reservar', 'administrador → recepcion', 'reincorporada; la misma reserva se confirma con la tarifa vigente', async () => {
    await admin.goto(`${FRONT}/hotel/habitaciones/${encodeURIComponent(HAB_R)}`)
    await admin.waitForTimeout(1800)
    await admin.getByRole('button', { name: 'Reincorporar a la operación' }).click()
    await admin.waitForTimeout(1500)
    const ficha = await api('GET', `/hotel/habitaciones/${HAB_R}`, { cookie: cAdmin })
    esperar(ficha.datos.estado_operativo === 'disponible', `estado tras reincorporar: ${ficha.datos.estado_operativo}`)
    await recepcion.getByRole('button', { name: 'Nueva operación' }).click()
    await recepcion.waitForTimeout(500)
    await llenarYConfirmar(HAB_R, 'Huésped Retirada')
    const c = await confirmacion(recepcion)
    await evidencia(recepcion, 'reincorporada-confirmada')
    esperar(c && c.includes('confirmada'), `confirmación: ${c} · alerta: ${await alerta(recepcion)}`)
    const lista = await reservasDe(HAB_R)
    esperar(lista.length === 1 && lista[0].estado === 'confirmada' && lista[0].tarifa_noche_aceptada_clp === 52000,
      `releído: ${JSON.stringify(lista).slice(0, 160)}`)
    return `${lista[0].reserva_id || lista[0].id} confirmada a $52.000/noche`
  })
} finally {
  await navegador.close()
  const archivo = join(AQUI, 'e2e-reserva-vendible-resultados.json')
  writeFileSync(archivo, JSON.stringify(resultados, null, 2) + '\n')
  const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
  console.log(`\n${aprobados}/${resultados.length} aprobados → ${archivo}`)
  if (aprobados !== resultados.length) process.exitCode = 1
}
