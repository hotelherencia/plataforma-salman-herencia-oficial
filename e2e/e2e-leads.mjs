/**
 * E2E de leads — V1-ISSUE-20 punto 8 (spec-api-v1 «Contacto y leads de la
 * landing»): el formulario propio de la landing postea a la plataforma
 * (`POST /publico/leads`, Formspree retirado) y recepción gestiona la
 * prospección desde la bandeja `/hotel/leads` (contactado/cerrado con nota).
 *
 * Navegador real (Chromium): sirve `landing/` en puerto efímero con
 * `window.LANDING_API_URL` inyectado (addInitScript) apuntando a la API; el
 * front de FRONT_URL debe tener build con API_BASE_URL de esa misma API. Cada
 * mutación se verifica releyendo el estado por la API con sesión de
 * administrador. Datos 100 % sintéticos, únicos por corrida.
 *
 * Uso:
 *   # API con ORIGEN_LANDING del puerto fijo de abajo, front y landing:
 *   cd e2e && LANDING_PORT=4173 FRONT_URL=http://127.0.0.1:3000 \
 *     API_URL=http://127.0.0.1:8080 ADMIN_CLAVE_E2E='E2eClave123' node e2e-leads.mjs
 */

import { chromium } from 'playwright'
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname, extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONT = process.env.FRONT_URL || 'http://127.0.0.1:3000'
const API = process.env.API_URL || 'http://127.0.0.1:8080'
// Puerto fijo: la API valida el CORS del formulario contra
// ORIGEN_LANDING=http://127.0.0.1:LANDING_PORT (prefijo /publico/*), así que
// el origen de la landing tiene que ser conocido antes de arrancarla.
const LANDING_PORT = Number(process.env.LANDING_PORT || 4173)
const ADMIN = ['admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123']
const RUN = Date.now().toString(36)
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
  return new Promise((resuelve, rechaza) => {
    servidor.once('error', rechaza)
    servidor.listen(LANDING_PORT, '127.0.0.1', () => resuelve(servidor))
  })
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

async function api(metodo, ruta, { cuerpo, cookie } = {}) {
  const r = await fetch(`${API}${ruta}`, {
    method: metodo,
    headers: {
      Accept: 'application/json',
      ...(cuerpo ? { 'Content-Type': 'application/json' } : {}),
      ...(cookie ? { Cookie: cookie } : {}),
    },
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  })
  let datos
  const texto = await r.text()
  try {
    datos = texto ? JSON.parse(texto) : {}
  } catch {
    datos = { detalle: texto }
  }
  return { estado: r.status, datos }
}

async function loginApi(usuario, clave) {
  const r = await fetch(`${API}/sesion`, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ usuario, clave }),
  })
  if (r.status !== 200) throw new Error(`login API falló para ${usuario}: ${r.status}`)
  return (r.headers.get('set-cookie') || '').split(';')[0]
}

async function loginNavegador(page, usuario, clave) {
  await page.goto(`${FRONT}/login`)
  await page.getByRole('textbox', { name: 'Usuario' }).fill(usuario)
  await page.getByRole('textbox', { name: 'Clave' }).fill(clave)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await page.waitForTimeout(1800)
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

const LEAD = {
  nombre: `Lead E2E ${RUN}`,
  correo: `lead-${RUN}@example.test`,
  telefono: '+56 9 4000 0000',
  huespedes: '3',
  check_in: MANANA,
  check_out: EN_4,
  mensaje: `Consulta E2E ${RUN}: viajamos en familia`,
}

const servidor = await servirLanding()
const LANDING = `http://127.0.0.1:${LANDING_PORT}`
console.log(`landing en ${LANDING} → api ${API}, front ${FRONT}`)

const cookieAdmin = await loginApi(ADMIN[0], ADMIN[1])
const leadsPorApi = async () => (await api('GET', '/hotel/leads', { cookie: cookieAdmin })).datos.leads

const navegador = await chromium.launch()
try {
  const ctx = await navegador.newContext({ viewport: { width: 1280, height: 720 } })
  await ctx.addInitScript(({ front, api: apiBase }) => {
    window.LANDING_PLATAFORMA_URL = front
    window.LANDING_API_URL = apiBase
    window.LANDING_RECAPTCHA_SITE_KEY = ''
  }, { front: FRONT, api: API })
  const page = await ctx.newPage()

  // ---------- LEAD-E2E-01: el formulario propio deja el lead en la plataforma ----------
  await caso('LEAD-E2E-01', '/#contacto', 'enviar el formulario de contacto: el lead queda nuevo en la plataforma', 'visitante',
    'mensaje «Consulta enviada» y lead nuevo persistido con los datos enviados (origen landing)', async () => {
      await page.goto(`${LANDING}/#contacto`)
      const formulario = page.locator('[data-formulario-contacto]')
      await formulario.getByRole('textbox', { name: 'Nombre completo' }).fill(LEAD.nombre)
      await formulario.getByRole('textbox', { name: 'Correo electrónico' }).fill(LEAD.correo)
      await formulario.getByRole('textbox', { name: 'Teléfono' }).fill(LEAD.telefono)
      await formulario.getByRole('spinbutton', { name: 'Huéspedes' }).fill(LEAD.huespedes)
      await formulario.getByLabel('Check-in').fill(LEAD.check_in)
      await formulario.getByLabel('Check-out').fill(LEAD.check_out)
      await formulario.getByRole('textbox', { name: 'Mensaje o requerimientos' }).fill(LEAD.mensaje)
      await formulario.getByRole('button', { name: 'Enviar consulta' }).click()
      const estado = formulario.locator('[role="status"]')
      await estado.waitFor({ state: 'visible', timeout: 10000 })
      await estado.filter({ hasText: /Consulta enviada/ }).waitFor({ timeout: 10000 })
      const leads = await leadsPorApi()
      const mio = leads.find((l) => l.nombre === LEAD.nombre)
      esperar(mio, `lead no aparece en la bandeja API: ${JSON.stringify(leads)}`)
      esperar(mio.estado === 'nuevo', `estado inesperado: ${mio.estado}`)
      esperar(mio.correo === LEAD.correo && mio.telefono === LEAD.telefono, 'datos de contacto distintos')
      esperar(mio.origen === 'landing', `origen inesperado: ${mio.origen}`)
      esperar(mio.check_in === LEAD.check_in && mio.check_out === LEAD.check_out, 'fechas distintas')
      return await evidencia(page, 'lead-e2e-01-formulario-enviado')
    })

  // ---------- LEAD-E2E-02: rechazo visible y nada persiste ----------
  await caso('LEAD-E2E-02', '/#contacto', 'fechas invertidas: mensaje local y nada se persiste', 'visitante',
    'mensaje «Revisa los datos» y el conteo de leads no cambia', async () => {
      const antes = (await leadsPorApi()).length
      await page.goto(`${LANDING}/#contacto`)
      const formulario = page.locator('[data-formulario-contacto]')
      await formulario.getByRole('textbox', { name: 'Nombre completo' }).fill(`Lead rechazado ${RUN}`)
      await formulario.getByRole('textbox', { name: 'Correo electrónico' }).fill(`rechazo-${RUN}@example.test`)
      await formulario.getByRole('textbox', { name: 'Teléfono' }).fill('+56 9 4000 0001')
      await formulario.getByLabel('Check-in').fill(EN_4)
      await formulario.getByLabel('Check-out').fill(MANANA) // invertido
      await formulario.getByRole('button', { name: 'Enviar consulta' }).click()
      const estado = formulario.locator('[role="status"]')
      await estado.filter({ hasText: /Revisa los datos/ }).waitFor({ timeout: 10000 })
      const despues = (await leadsPorApi()).length
      esperar(despues === antes, `se persistió el lead rechazado: ${antes} → ${despues}`)
      return `${await estado.textContent()} · leads ${antes} → ${despues}`
    })

  // ---------- LEAD-E2E-03: la bandeja del front muestra el lead ----------
  await caso('LEAD-E2E-03', '/hotel/leads', 'la bandeja muestra el lead con sus datos de contacto', 'administrador',
    'fila con nombre, correo, teléfono, fechas y mensaje únicos de la corrida', async () => {
      await loginNavegador(page, ADMIN[0], ADMIN[1])
      await page.goto(`${FRONT}/hotel/leads`)
      const fila = page.getByRole('row', { name: new RegExp(LEAD.nombre) })
      await fila.waitFor({ state: 'visible', timeout: 10000 })
      const texto = await fila.textContent()
      esperar(texto.includes(LEAD.correo) && texto.includes(LEAD.telefono), `fila sin datos de contacto: ${texto}`)
      esperar(texto.includes('nuevo'), `fila sin estado nuevo: ${texto}`)
      return await evidencia(page, 'lead-e2e-03-bandeja')
    })

  // ---------- LEAD-E2E-04: contactado con nota ----------
  await caso('LEAD-E2E-04', '/hotel/leads', 'marcar contactado con nota de gestión', 'administrador',
    'la fila queda contactada con la nota y gestion_por del administrador', async () => {
      const fila = page.getByRole('row', { name: new RegExp(LEAD.nombre) })
      await fila.getByRole('textbox', { name: 'Nota de gestión' }).fill(`Llamado ${RUN}`)
      await fila.getByRole('button', { name: 'Contactado' }).click()
      // hasText con string es case-insensitive y matchearía el botón
      // «Contactado»; el regex sin flags exige la celda de estado en minúscula
      await fila.filter({ hasText: /contactado/ }).waitFor({ timeout: 10000 })
      const texto = await fila.textContent()
      esperar(texto.includes(`Llamado ${RUN}`), `nota no visible: ${texto}`)
      const mio = (await leadsPorApi()).find((l) => l.nombre === LEAD.nombre)
      esperar(mio.estado === 'contactado' && mio.gestion_por === ADMIN[0], `gestión no reflejada: ${JSON.stringify(mio)}`)
      return await evidencia(page, 'lead-e2e-04-contactado')
    })

  // ---------- LEAD-E2E-05: cierre y sin reapertura ----------
  await caso('LEAD-E2E-05', '/hotel/leads', 'cerrar el lead: queda cerrado y sin acciones de reapertura', 'administrador',
    'estado cerrado con nota y la fila ya no ofrece Contactado/Cerrar', async () => {
      const fila = page.getByRole('row', { name: new RegExp(LEAD.nombre) })
      await fila.getByRole('textbox', { name: 'Nota de gestión' }).fill(`Cerrado ${RUN}: reservó por teléfono`)
      await fila.getByRole('button', { name: 'Cerrar' }).click()
      await fila.filter({ hasText: /cerrado/ }).waitFor({ timeout: 10000 })
      esperar((await fila.getByRole('button', { name: 'Contactado' }).count()) === 0, 'sigue ofreciendo Contactado')
      const mio = (await leadsPorApi()).find((l) => l.nombre === LEAD.nombre)
      esperar(mio.estado === 'cerrado' && mio.nota.includes('reservó por teléfono'), `cierre no reflejado: ${JSON.stringify(mio)}`)
      return await evidencia(page, 'lead-e2e-05-cerrado')
    })

  await ctx.close()
} finally {
  await navegador.close()
  servidor.close()
}

const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
const fallidos = resultados.filter((r) => r.estado === 'FALLIDO')
console.log(`\n${aprobados}/${resultados.length} aprobados → ${join(AQUI, 'e2e-leads-resultados.json')}`)
writeFileSync(join(AQUI, 'e2e-leads-resultados.json'), JSON.stringify({ fecha: HOY, landing: LANDING, front: FRONT, api: API, resultados }, null, 2))
if (fallidos.length > 0) process.exitCode = 1
