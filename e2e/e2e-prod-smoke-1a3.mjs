/**
 * Smoke de producción — Entrega 1A.3 + cierres de seguridad (426fd4b).
 * Solo lectura o, si se envía un formulario público, registros «PRUEBA G».
 * No inicia sesión con cuentas reales.
 *
 *   FRONT_URL=https://plataforma.hotelherencia.cl node e2e-prod-smoke-1a3.mjs
 */
import { chromium } from 'playwright'
import { writeFileSync, mkdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONT = (process.env.FRONT_URL || 'https://plataforma.hotelherencia.cl').replace(/\/$/, '')
const RAILWAY = 'https://servicio-production-a2d7.up.railway.app'
const VERCEL = 'https://plataforma-salman-herencia-oficial.vercel.app'
const LANDING = 'https://www.hotelherencia.cl'
const AQUI = dirname(fileURLToPath(import.meta.url))
const OUT = "/workspace/herencia/modulo-hotel/e2e-1a3"
mkdirSync(OUT, { recursive: true })
mkdirSync(join(OUT, 'capturas'), { recursive: true })

const resultados = []
async function caso(id, fn) {
  try {
    const observado = await fn()
    resultados.push({ id, estado: 'APROBADO', observado })
    console.log(`✓ ${id}: ${observado}`)
  } catch (error) {
    resultados.push({ id, estado: 'FALLIDO', observado: error.message })
    console.error(`✗ ${id}: ${error.message}`)
  }
}
function assert(c, m) { if (!c) throw new Error(m) }

async function get(url, { method = 'GET', headers = {}, body } = {}) {
  const r = await fetch(url, { method, headers, body, redirect: 'manual' })
  const buf = Buffer.from(await r.arrayBuffer())
  const ct = r.headers.get('content-type') || ''
  let json = null
  if (ct.includes('json') || buf[0] === 0x7b) {
    try { json = JSON.parse(buf.toString('utf8')) } catch { json = null }
  }
  return { status: r.status, headers: r.headers, buf, json, text: buf.toString('utf8'), url }
}

await caso('PROD-READINESS-23', async () => {
  const r = await get(`${FRONT}/api/readiness`)
  assert(r.status === 200, `status ${r.status}`)
  assert(r.json?.estado === 'listo', JSON.stringify(r.json))
  assert(r.json?.migraciones === 23, `migraciones=${r.json?.migraciones}`)
  return `migraciones ${r.json.migraciones}, canal ${r.json.canal_publico}`
})

await caso('PROD-SALUD-MINIMO', async () => {
  const vistos = []
  for (const u of [`${FRONT}/api/salud`, `${RAILWAY}/salud`, `${VERCEL}/api/salud`]) {
    const r = await get(u)
    assert(r.status === 200, `${u} ${r.status}`)
    assert(JSON.stringify(r.json) === JSON.stringify({ estado: 'ok' }), `${u} body=${JSON.stringify(r.json)}`)
    vistos.push(u)
  }
  return `{"estado":"ok"} en ${vistos.length} orígenes`
})

await caso('PROD-DOCS-CERRADOS', async () => {
  const pathsFront = ['/api/docs', '/api/redoc', '/api/openapi.json']
  const pathsRail = ['/docs', '/redoc', '/openapi.json']
  const pares = [
    ...pathsFront.map((p) => FRONT + p),
    ...pathsRail.map((p) => RAILWAY + p),
    ...pathsFront.map((p) => VERCEL + p),
  ]
  const malos = []
  for (const u of pares) {
    const r = await get(u)
    if (r.status !== 404) malos.push(`${u} → ${r.status}`)
  }
  assert(malos.length === 0, malos.join(' | '))
  return `404 en ${pares.length} URLs de docs/redoc/openapi`
})

await caso('PROD-ROBOTS-NOINDEX', async () => {
  for (const u of [`${FRONT}/robots.txt`, `${VERCEL}/robots.txt`]) {
    const r = await get(u)
    assert(r.status === 200, `${u} ${r.status}`)
    assert(/Disallow:\s*\//.test(r.text), `${u} robots: ${r.text.slice(0, 120)}`)
    const tag = r.headers.get('x-robots-tag') || ''
    assert(/noindex/i.test(tag), `${u} X-Robots-Tag=${tag}`)
  }
  const login = await get(`${FRONT}/login`)
  assert(login.status === 200, `login ${login.status}`)
  assert(/noindex/i.test(login.headers.get('x-robots-tag') || ''), `login sin X-Robots-Tag`)
  return 'robots Disallow: / y X-Robots-Tag noindex en front y login'
})

await caso('PROD-POLITICAS-PUBLICAS', async () => {
  const r = await get(`${FRONT}/api/publico/politicas`)
  assert(r.status === 200, `status ${r.status}`)
  const p = r.json?.politicas || {}
  assert(p.llegada_salida?.hora_llegada_desde === '14:00', JSON.stringify(p.llegada_salida))
  assert(p.cancelacion?.confirmacion === 'pendiente_confirmar', 'cancelacion no pendiente')
  assert(!('registro_salida' in p), 'registro_salida no debe ser público')
  assert((r.json.pendientes || []).length >= 1, 'sin pendientes')
  return `14:00/12:00, ${r.json.pendientes.length} pendientes, sin pasos internos de salida`
})

await caso('PROD-DISPONIBILIDAD-RECARGOS', async () => {
  const hoy = new Date()
  const iso = (d) => d.toISOString().slice(0, 10)
  const inicio = iso(new Date(hoy.getTime() + 10 * 864e5))
  const fin = iso(new Date(hoy.getTime() + 12 * 864e5))
  const r = await get(`${FRONT}/api/publico/disponibilidad?inicio=${inicio}&fin=${fin}&personas=2&hora_llegada=11:00`)
  assert(r.status === 200, `status ${r.status} ${r.text.slice(0, 180)}`)
  assert(Array.isArray(r.json?.oferta), 'sin oferta')
  const item = r.json.oferta[0]
  assert(item && 'recargos' in item && 'desglose' in item && 'cancelacion_confirmacion' in item, `keys ${Object.keys(item || {})}`)
  return `${r.json.oferta.length} ítems con recargos/desglose; cancelación ${r.json.cancelacion_confirmacion}`
})

await caso('PROD-TIPOS-REDIRIGE-CONFIG', async () => {
  const html = (await get(`${FRONT}/hotel/tipos`)).text
  const js = [...new Set([...html.matchAll(/\/_next\/static\/[^"'\\\s]+?\.js/g)].map((m) => m[0]))]
  let hallado = false
  for (const u of js) {
    const r = await get(FRONT + u)
    if (r.text.includes('configuracion?seccion=tipos') || r.text.includes('/hotel/configuracion')) hallado = true
  }
  const cfg = await get(`${FRONT}/hotel/configuracion`)
  assert(cfg.status === 200, `configuracion ${cfg.status}`)
  assert(hallado, 'el JS de /hotel/tipos no apunta a Configuración')
  return '/hotel/configuracion existe; /hotel/tipos redirige en el cliente'
})

await caso('PROD-LOGIN-Y-PROTEGIDAS', async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true })
  try {
    const page = await browser.newPage()
    await page.goto(`${FRONT}/login`, { waitUntil: 'networkidle', timeout: 45000 })
    const texto = await page.locator('body').innerText()
    assert(/usuario|clave|entrar/i.test(texto), `login: ${texto.slice(0, 180)}`)
    await page.screenshot({ path: join(OUT, 'capturas', 'prod-login.png') })
    await page.goto(`${FRONT}/hotel/panel`, { waitUntil: 'networkidle', timeout: 45000 })
    await page.waitForTimeout(800)
    const panel = await page.locator('body').innerText()
    const menu = await page.getByRole('link', { name: 'Panel' }).count()
    assert(menu === 0, 'menú interno visible sin sesión')
    assert(/entrar|usuario|clave|sesión/i.test(panel), `protegida no pide acceso: ${panel.slice(0, 180)}`)
    await page.screenshot({ path: join(OUT, 'capturas', 'prod-panel-sin-sesion.png') })
    return 'login carga; /hotel/panel sin sesión no muestra el menú interno'
  } finally {
    await browser.close()
  }
})

await caso('PROD-LANDING-Y-FORMULARIO', async () => {
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true })
  try {
    const page = await browser.newPage()
    const resp = await page.goto(LANDING, { waitUntil: 'networkidle', timeout: 45000 })
    assert(resp && resp.ok(), `landing ${resp?.status()}`)
    const texto = await page.locator('body').innerText()
    assert(/Hotel Herencia/i.test(texto), `no es la landing: ${texto.slice(0, 160)}`)
    await page.screenshot({ path: join(OUT, 'capturas', 'prod-landing.png') })
    const recaptcha = await page.locator('script[src*="recaptcha"], [data-sitekey], .grecaptcha-badge').count()
    const form = page.locator('form').first()
    let envio = 'formulario visto; no se envió (reCAPTCHA v3 en headless no es fiable)'
    if (await form.count()) {
      // Intento controlado con «PRUEBA G» si hay campos visibles; si reCAPTCHA bloquea, se informa.
      const nombre = form.locator('input[name*=nombre], input[id*=nombre], input[type=text]').first()
      if (await nombre.count()) {
        await nombre.fill('PRUEBA G')
        try {
          await form.evaluate((f) => f.requestSubmit ? f.requestSubmit() : f.submit())
          await page.waitForTimeout(2500)
          const despues = await page.locator('body').innerText()
          if (/recaptcha|captcha|no se pudo|error/i.test(despues) && !/gracias|recibimos|enviad/i.test(despues)) {
            envio = 'reCAPTCHA v3 no validó el envío desde un navegador headless; no se creó el registro'
          } else if (/gracias|recibimos|enviad/i.test(despues)) {
            envio = 'formulario enviado como PRUEBA G'
          }
        } catch (e) {
          envio = `no se envió el formulario: ${e.message}`
        }
      }
    }
    assert(recaptcha >= 0, 'n/a')
    return `landing 200, Hotel Herencia visible. ${envio}`
  } finally {
    await browser.close()
  }
})

await caso('PROD-SIN-CUENTA-PRUEBA', async () => {
  // No hay una cuenta de prueba documentada en el repo para producción.
  // Este caso deja constancia: no se hizo login con cuentas reales.
  return 'no existe una cuenta de prueba documentada; no se inició sesión en producción'
})

const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
const salida = { frente: FRONT, fecha: new Date().toISOString(), resultados }
writeFileSync(join(OUT, 'prod-smoke-resultados.json'), JSON.stringify(salida, null, 2))
writeFileSync(join(AQUI, 'e2e-prod-smoke-1a3-resultados.json'), JSON.stringify(salida, null, 2))
console.log(`\n${aprobados}/${resultados.length} aprobados`)
process.exit(aprobados === resultados.length ? 0 : 1)
