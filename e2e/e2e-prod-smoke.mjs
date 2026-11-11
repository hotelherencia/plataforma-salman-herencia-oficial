/**
 * Smoke E2E de contención en producción (favicon + sesión + OAuth cookie).
 *
 * Uso:
 *   cd e2e && node e2e-prod-smoke.mjs
 *   FRONT_URL=https://plataforma-salman-herencia-oficial.vercel.app node e2e-prod-smoke.mjs
 *
 * No usa secretos. Espera: iconos 200 imagen; GET /api/sesion → 401;
 * /auth/google fija oauth_tx con Path=/ (no /auth).
 */
import { chromium } from 'playwright'
import { writeFileSync } from 'node:fs'

const FRONT = (process.env.FRONT_URL || 'https://plataforma-salman-herencia-oficial.vercel.app').replace(/\/$/, '')

const resultados = []

async function caso(id, fn) {
  try {
    const observado = await fn()
    resultados.push({ id, estado: 'APROBADO', observado })
    console.log(`APROBADO ${id}: ${observado}`)
  } catch (error) {
    resultados.push({ id, estado: 'FALLIDO', observado: error.message })
    console.error(`FALLIDO ${id}: ${error.message}`)
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg)
}

await caso('ICON-SVG', async () => {
  const r = await fetch(`${FRONT}/icon.svg`)
  const tipo = r.headers.get('content-type') || ''
  assert(r.status === 200, `status ${r.status}`)
  assert(tipo.includes('svg') || tipo.includes('xml'), `content-type ${tipo}`)
  return `${r.status} ${tipo}`
})

await caso('ICON-PNG', async () => {
  const r = await fetch(`${FRONT}/icon.png`)
  const tipo = r.headers.get('content-type') || ''
  assert(r.status === 200, `status ${r.status}`)
  assert(tipo.includes('png') || tipo.includes('image'), `content-type ${tipo}`)
  const buf = Buffer.from(await r.arrayBuffer())
  assert(buf.length > 50, 'icon.png vacío')
  assert(!(buf.slice(0, 15).toString('utf8').includes('<!DOCTYPE')), 'HTML en vez de imagen')
  return `${r.status} ${tipo} bytes=${buf.length}`
})

await caso('FAVICON-ICO', async () => {
  const r = await fetch(`${FRONT}/favicon.ico`)
  const tipo = r.headers.get('content-type') || ''
  assert(r.status === 200, `status ${r.status}`)
  assert(!tipo.includes('text/html'), `HTML inaceptable: ${tipo}`)
  const buf = Buffer.from(await r.arrayBuffer())
  assert(buf.length > 50, 'favicon vacío')
  assert(!(buf.slice(0, 15).toString('utf8').includes('<!DOCTYPE')), 'HTML en vez de ico')
  return `${r.status} ${tipo} bytes=${buf.length}`
})

await caso('SESION-SIN-COOKIE', async () => {
  const r = await fetch(`${FRONT}/api/sesion`, {
    headers: { Accept: 'application/json', Origin: FRONT },
  })
  const cuerpo = await r.json()
  assert(r.status === 401, `esperado 401, got ${r.status}`)
  assert(cuerpo.detail, `sin detail: ${JSON.stringify(cuerpo)}`)
  return `${r.status} ${cuerpo.detail}`
})

await caso('OAUTH-COOKIE-PATH', async () => {
  const r = await fetch(`${FRONT}/api/auth/google`, { redirect: 'manual' })
  assert(r.status === 302 || r.status === 307, `esperado redirect, got ${r.status}`)
  const setCookie = r.headers.getSetCookie?.() || []
  const raw = setCookie.length ? setCookie.join('\n') : (r.headers.get('set-cookie') || '')
  assert(/oauth_tx=/i.test(raw), `sin oauth_tx: ${raw}`)
  assert(/path=\/(;|$|\s)/i.test(raw), `Path incorrecto: ${raw}`)
  assert(!/path=\/auth/i.test(raw), `Path=/auth residual: ${raw}`)
  const loc = r.headers.get('location') || ''
  assert(loc.includes('accounts.google.com'), `location ${loc}`)
  return `cookie Path=/; location google`
})

await caso('BROWSER-HOME-LOGIN', async () => {
  const browser = await chromium.launch({ headless: true })
  try {
    const page = await browser.newPage()
    const fallos = []
    page.on('response', (res) => {
      const u = res.url()
      if (u.includes('/favicon.ico') || u.includes('/icon.')) {
        if (res.status() === 404) fallos.push(`${res.status()} ${u}`)
        const ct = res.headers()['content-type'] || ''
        if (ct.includes('text/html')) fallos.push(`html ${u}`)
      }
    })
    await page.goto(FRONT + '/', { waitUntil: 'networkidle', timeout: 45000 })
    await page.waitForTimeout(1500)
    const texto = await page.locator('body').innerText()
    assert(!/API no está disponible/i.test(texto), 'UI marca API caída')
    assert(/entrar|iniciar|usuario|clave|google|sesión/i.test(texto), `no hay UI de acceso: ${texto.slice(0, 200)}`)
    assert(fallos.length === 0, fallos.join(' | '))
    return 'login visible; iconos sin 404/HTML'
  } finally {
    await browser.close()
  }
})

const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
writeFileSync(
  new URL('./e2e-prod-smoke-resultados.json', import.meta.url),
  JSON.stringify({ front: FRONT, fecha: new Date().toISOString(), resultados }, null, 2),
)
console.log(`\n${aprobados}/${resultados.length} aprobados`)
process.exit(aprobados === resultados.length ? 0 : 1)
