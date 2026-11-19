/**
 * Smoke E2E de la fase 1 contable (2026-11-19): turno de caja, pago con medio
 * y boleta, retiro para depósito, cierre de turno con arqueo y cierre diario.
 * Navegador real contra front y API locales; datos sintéticos únicos por corrida.
 * Uso: FRONT_URL=… API_URL=… CAPTURAS_DIR=… node e2e-caja.mjs
 */
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const FRONT = process.env.FRONT_URL || 'http://127.0.0.1:3000'
const API = process.env.API_URL || 'http://127.0.0.1:8080'
const CAPTURAS = process.env.CAPTURAS_DIR || 'capturas-caja'
const ADMIN = ['admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123']
const RUN = Date.now().toString(36)
const K = (n) => `${n}-${RUN}`
const CAJA = [`caja${RUN}`, 'Clave-caja-e2e-1']
mkdirSync(CAPTURAS, { recursive: true })

async function api(metodo, ruta, { cuerpo, clave, cookie, cabeceras = {} } = {}) {
  const h = { ...cabeceras }
  if (cuerpo !== undefined) h['Content-Type'] = 'application/json'
  if (clave) h['Idempotency-Key'] = clave
  if (cookie) h.Cookie = cookie
  const r = await fetch(API + ruta, { method: metodo, headers: h, body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined })
  const texto = await r.text()
  let datos = {}
  try { datos = JSON.parse(texto) } catch { datos = { texto } }
  return { estado: r.status, datos, cookie: (r.headers.get('set-cookie') || '').split(';')[0] }
}
const login = async ([usuario, clave]) => (await api('POST', '/sesion', { cuerpo: { usuario, clave } })).cookie

const resultados = []
function caso(id, descripcion, ok, detalle = '') {
  resultados.push({ id, descripcion, ok, detalle })
  console.log(`${ok ? '✓' : '✗'} ${id} ${descripcion}${detalle ? ` — ${detalle}` : ''}`)
}
const sinTecnicos = (t) => !['{"', '":', 'Idempotency', 'undefined', 'Input should', 'Field required'].some((m) => t.includes(m))

const cAdmin = await login(ADMIN)
await api('POST', '/usuarios', { cookie: cAdmin, clave: K('u'), cuerpo: { nombre: CAJA[0], rol: 'caja', clave: CAJA[1] } })
const cCaja = await login(CAJA)
const HOY = (await api('GET', '/hotel/caja/estado', { cookie: cCaja })).datos.fecha_contable
const hab = `HAB-${RUN}`
await api('PUT', `/hotel/habitaciones/${hab}`, { cookie: cAdmin, clave: K('h'), cuerpo: { tipo: 'doble', capacidad: 2 }, cabeceras: { 'If-None-Match': '*' } })
await api('POST', '/hotel/precios/excepciones', { cookie: cAdmin, clave: K('t'), cuerpo: { habitacion_id: hab, fecha_desde: HOY, fecha_hasta: '2027-12-31', precio_clp: 45000 } })
const fin = new Date(`${HOY}T00:00:00Z`); fin.setUTCDate(fin.getUTCDate() + 2)
const rsv = await api('POST', '/hotel/reservas', { cookie: cAdmin, clave: K('r'), cuerpo: { habitacion_id: hab, inicio: HOY, fin: fin.toISOString().slice(0, 10), huesped: { nombre: `Huésped Caja ${RUN}`, documento: '11.111.111-1' } } })
const RID = rsv.datos.reserva_id
await api('POST', `/hotel/reservas/${RID}/entrada`, { cookie: cAdmin, clave: K('e'), cuerpo: {} })

const navegador = await chromium.launch({ executablePath: process.env.CHROME_PATH })
const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1366, height: 900 } })
const page = await ctx.newPage()
await page.goto(`${FRONT}/login`)
await page.getByRole('textbox', { name: 'Usuario' }).fill(CAJA[0])
await page.getByRole('textbox', { name: 'Clave' }).fill(CAJA[1])
await page.getByRole('button', { name: 'Entrar' }).click()
await page.waitForTimeout(1800)

try {
  // 1. Abrir turno desde la pestaña Turno.
  await page.goto(`${FRONT}/hotel/caja?pestana=turno`)
  await page.waitForTimeout(1500)
  await page.getByRole('spinbutton', { name: 'Fondo inicial contado (CLP)' }).fill('20000')
  await page.getByRole('button', { name: 'Abrir turno' }).click()
  await page.waitForTimeout(1500)
  let estado = (await api('GET', '/hotel/caja/estado', { cookie: cCaja })).datos
  caso('CJ-01', 'abrir turno con fondo inicial', estado.turno?.fondo_inicial_clp === 20000)

  // 2. Pago en efectivo con boleta desde Registrar pago.
  await page.goto(`${FRONT}/hotel/pago?reserva_id=${RID}`)
  await page.waitForTimeout(2000)
  await page.getByRole('spinbutton', { name: 'Monto pagado (CLP)' }).fill('50000')
  await page.getByRole('combobox', { name: 'Medio de pago' }).selectOption('efectivo')
  await page.getByRole('combobox', { name: '¿Boleta o factura?' }).selectOption('boleta')
  await page.screenshot({ path: join(CAPTURAS, 'cj-01-pago-efectivo-boleta.png'), fullPage: true })
  await page.getByRole('button', { name: 'Registrar pago' }).click()
  await page.waitForTimeout(1800)
  const det = (await api('GET', `/hotel/reservas/${RID}`, { cookie: cAdmin })).datos
  const pago = det.pagos.find((p) => p.monto_clp === 50000)
  caso('CJ-02', 'pago en efectivo con boleta queda en el turno', pago?.medio === 'efectivo' && pago?.documento_tipo === 'boleta', JSON.stringify(pago ? { medio: pago.medio, doc: pago.documento_tipo } : null))

  // 3. Retiro para depósito.
  await page.goto(`${FRONT}/hotel/caja?pestana=turno`)
  await page.waitForTimeout(1500)
  await page.getByRole('button', { name: 'Retirar efectivo para depósito' }).click()
  await page.getByRole('spinbutton', { name: 'Monto (CLP)' }).fill('30000')
  await page.getByRole('textbox', { name: 'N° de comprobante del depósito' }).fill(`DEP-${RUN}`)
  await page.getByRole('button', { name: 'Registrar retiro' }).click()
  await page.waitForTimeout(1500)
  estado = (await api('GET', '/hotel/caja/estado', { cookie: cCaja })).datos
  caso('CJ-03', 'retiro para depósito descuenta el efectivo esperado', estado.turno?.totales.efectivo_esperado_clp === 40000)
  await page.screenshot({ path: join(CAPTURAS, 'cj-02-turno-abierto.png'), fullPage: true })

  // 4. Cierre de turno con arqueo (2 × $20.000).
  await page.getByRole('button', { name: 'Cerrar turno (arqueo)' }).click()
  await page.getByRole('spinbutton', { name: 'Cantidad de $20.000' }).fill('2')
  await page.waitForTimeout(300)
  const textoArqueo = await page.evaluate(() => document.querySelector('[data-arqueo]')?.textContent || '')
  caso('CJ-04', 'arqueo en pantalla cuadra', textoArqueo.includes('Cuadra'), textoArqueo)
  await page.screenshot({ path: join(CAPTURAS, 'cj-03-arqueo.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cerrar turno', exact: true }).click()
  await page.waitForTimeout(1500)
  estado = (await api('GET', '/hotel/caja/estado', { cookie: cCaja })).datos
  caso('CJ-05', 'turno cerrado y efectivo para el turno siguiente', !estado.turno && estado.entrega_pendiente?.monto_clp === 40000)

  // 5. Cierre diario con la conciliación.
  await page.goto(`${FRONT}/hotel/caja?pestana=cierre`)
  await page.waitForTimeout(2000)
  const texto = await page.evaluate(() => document.querySelector('main')?.innerText || '')
  caso('CJ-06', 'conciliación sin datos técnicos y con la habitación', sinTecnicos(texto) && texto.includes(hab))
  await page.screenshot({ path: join(CAPTURAS, 'cj-04-conciliacion.png'), fullPage: true })
  const confirmar = page.getByRole('checkbox', { name: /cierro igual/ })
  if (await confirmar.count()) await confirmar.check()
  await page.getByRole('button', { name: /^Cerrar el día/ }).click()
  await page.waitForTimeout(1800)
  const cierres = (await api('GET', '/hotel/caja/cierres', { cookie: cCaja })).datos
  caso('CJ-07', 'día cerrado y fecha contable avanza', cierres.cierres[0]?.fecha === HOY && cierres.fecha_contable > HOY)
  await page.screenshot({ path: join(CAPTURAS, 'cj-05-dia-cerrado.png'), fullPage: false })
  // Deja la base como estaba para correr de nuevo: reabre el día.
  await api('POST', `/hotel/caja/cierres/${HOY}/reapertura`, { cookie: cAdmin, clave: K('reab'), cuerpo: { motivo: 'Reapertura del smoke E2E' } })
} catch (error) {
  caso('CJ-ERR', 'el flujo se interrumpió', false, String(error).slice(0, 300))
  await page.screenshot({ path: join(CAPTURAS, 'cj-error.png'), fullPage: true })
}
await navegador.close()
writeFileSync('e2e-caja-resultados.json', JSON.stringify({ corrida: RUN, resultados }, null, 2))
const fallas = resultados.filter((r) => !r.ok).length
console.log(`${resultados.length - fallas}/${resultados.length} aprobados`)
process.exit(fallas ? 1 : 0)
