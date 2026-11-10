/**
 * E2E de la landing → plataforma — V1-ISSUE-25 (CA-PUB-12).
 *
 * Sirve `landing/` (sitio estático del repo) en un puerto efímero y, con
 * navegador real (Chromium), verifica que «Ver disponibilidad» abre
 * `/reservar` del front con inicio, fin y personas en la query, y que los
 * rangos inválidos se rechazan en la landing sin navegar (misma regla que
 * `front/app/reservar/page.js`). El consumo del deep link por `/reservar`
 * ya se acepta en `e2e-reserva-publica.mjs` (PUB-01).
 *
 * Requisito: front en FRONT_URL (default http://127.0.0.1:3000, build de
 * producción). La base del front se inyecta en la landing vía
 * `window.LANDING_PLATAFORMA_URL` (addInitScript), sin tocar los estáticos.
 *
 * Uso: cd e2e && FRONT_URL=http://127.0.0.1:3000 node e2e-landing.mjs
 */

import { chromium } from 'playwright'
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname, extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONT = process.env.FRONT_URL || 'http://127.0.0.1:3000'
const AQUI = dirname(fileURLToPath(import.meta.url))
const RAIZ_LANDING = join(AQUI, '..', 'landing')

const TIPOS = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
}

function servirLanding() {
  const servidor = createServer(async (peticion, respuesta) => {
    try {
      const ruta = new URL(peticion.url, 'http://local').pathname
      const relativa = ruta === '/' ? 'index.html' : ruta.slice(1)
      const archivo = normalize(join(RAIZ_LANDING, relativa))
      if (!archivo.startsWith(normalize(RAIZ_LANDING))) {
        respuesta.writeHead(403).end('prohibido')
        return
      }
      const cuerpo = await readFile(archivo)
      respuesta.writeHead(200, { 'Content-Type': TIPOS[extname(archivo)] || 'application/octet-stream' })
      respuesta.end(cuerpo)
    } catch {
      respuesta.writeHead(404).end('no encontrado')
    }
  })
  return new Promise((resuelve) => servidor.listen(0, '127.0.0.1', () => resuelve(servidor)))
}

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
const EN_4 = sumarDias(HOY, 4)

const servidor = await servirLanding()
const LANDING = `http://127.0.0.1:${servidor.address().port}`
console.log(`landing en ${LANDING} → front ${FRONT}`)

const navegador = await chromium.launch()
try {
  const ctx = await navegador.newContext({ viewport: { width: 1280, height: 720 } })
  await ctx.addInitScript((base) => {
    window.LANDING_PLATAFORMA_URL = base
    window.LANDING_RECAPTCHA_SITE_KEY = ''
  }, FRONT)
  const page = await ctx.newPage()

  // ---------- PUB-07: el CTA abre /reservar con las fechas elegidas (CA-PUB-12) ----------
  await caso('PUB-07', '/', 'desde la landing, elegir fechas y huéspedes y pulsar «Ver disponibilidad» abre /reservar con inicio, fin y personas', 'visitante', `navega a /reservar?inicio=${MANANA}&fin=${EN_4}&personas=3 y el formulario llega precargado`, async () => {
    await page.goto(LANDING)
    const formulario = page.locator('[data-formulario-contacto]')
    await formulario.locator('#checkin').fill(MANANA)
    await formulario.locator('#checkout').fill(EN_4)
    await formulario.locator('#guests').fill('3')
    await formulario.getByRole('button', { name: 'Ver disponibilidad' }).click()
    await page.waitForURL(`**/reservar?inicio=${MANANA}&fin=${EN_4}&personas=3`, { timeout: 15000 })
    esperar(page.url().startsWith(`${FRONT}/reservar`), `destino inesperado: ${page.url()}`)
    const llegada = await page.getByLabel('Llegada').inputValue()
    const salida = await page.getByLabel('Salida').inputValue()
    const personas = await page.getByLabel('Personas').inputValue()
    esperar(llegada === MANANA, `Llegada=${llegada}`)
    esperar(salida === EN_4, `Salida=${salida}`)
    esperar(personas === '3', `Personas=${personas}`)
    await evidencia(page, 'pub-07-reservar-precargado')
    return page.url()
  })

  // ---------- PUB-08: rango inválido se rechaza en la landing ----------
  await caso('PUB-08', '/', 'salida anterior a la llegada: mensaje local y sin navegación', 'visitante', 'alerta «salida posterior» y la URL sigue en la landing', async () => {
    await page.goto(LANDING)
    const formulario = page.locator('[data-formulario-contacto]')
    await formulario.locator('#checkin').fill(EN_4)
    await formulario.locator('#checkout').fill(MANANA)
    await formulario.getByRole('button', { name: 'Ver disponibilidad' }).click()
    const alerta = page.getByRole('alert')
    await alerta.waitFor({ state: 'visible', timeout: 5000 })
    const texto = await alerta.textContent()
    esperar(/posterior/i.test(texto || ''), `alerta inesperada: ${texto}`)
    esperar(page.url() === `${LANDING}/`, `navegó pese a rango inválido: ${page.url()}`)
    await evidencia(page, 'pub-08-rango-invalido')
    return texto
  })

  // ---------- PUB-09: fechas vacías se rechazan en la landing ----------
  await caso('PUB-09', '/', 'fechas sin completar: mensaje local y sin navegación', 'visitante', 'alerta «indica las fechas» y la URL sigue en la landing', async () => {
    await page.goto(LANDING)
    const formulario = page.locator('[data-formulario-contacto]')
    await formulario.getByRole('button', { name: 'Ver disponibilidad' }).click()
    const alerta = page.getByRole('alert')
    await alerta.waitFor({ state: 'visible', timeout: 5000 })
    const texto = await alerta.textContent()
    esperar(/fechas/i.test(texto || ''), `alerta inesperada: ${texto}`)
    esperar(page.url() === `${LANDING}/`, `navegó pese a fechas vacías: ${page.url()}`)
    return texto
  })

  await ctx.close()
} finally {
  await navegador.close()
  servidor.close()
}

const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
const fallidos = resultados.filter((r) => r.estado === 'FALLIDO')
console.log(`\n${aprobados}/${resultados.length} aprobados → ${join(AQUI, 'e2e-landing-resultados.json')}`)
writeFileSync(join(AQUI, 'e2e-landing-resultados.json'), JSON.stringify({ fecha: HOY, landing: LANDING, front: FRONT, resultados }, null, 2))
if (fallidos.length > 0) process.exitCode = 1
