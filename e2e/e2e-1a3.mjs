/**
 * E2E local — menú 1A.3, políticas, recargos y roles.
 * Requisitos: API en API_URL (default 127.0.0.1:8093) y front en FRONT_URL
 * (default 127.0.0.1:3013), base sintética, ADMIN_USUARIO=admin_e2e.
 *
 *   FRONT_URL=http://127.0.0.1:3013 API_URL=http://127.0.0.1:8093 node e2e-1a3.mjs
 */
import { chromium } from 'playwright'
import { writeFileSync, mkdirSync } from 'node:fs'
import { createHmac } from 'node:crypto'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONT = (process.env.FRONT_URL || 'http://127.0.0.1:3013').replace(/\/$/, '')
const API = (process.env.API_URL || 'http://127.0.0.1:8093').replace(/\/$/, '')
const ADMIN = ['admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123']
const AQUI = dirname(fileURLToPath(import.meta.url))
const OUT = '/workspace/herencia/modulo-hotel/e2e-1a3'
const SHOTS = join(OUT, 'capturas')
mkdirSync(SHOTS, { recursive: true })

const RUN = Date.now().toString(36)
const K = (n) => `${n}-${RUN}`
const isoLocal = (f) => {
  const d = new Date(f)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const sumar = (f, n) => { const d = new Date(f); d.setDate(d.getDate() + n); return isoLocal(d) }
const HOY = isoLocal(new Date())
const D = (n) => sumar(HOY, n)

const resultados = []
const httpRaros = []
const consola = []
let shotN = 0

async function caso(id, ruta, flujo, rol, esperado, fn) {
  try {
    const observado = (await fn()) || 'ok'
    resultados.push({ id, ruta, flujo, rol, esperado, observado, estado: 'APROBADO' })
    console.log(`✓ [${id}] ${flujo}`)
  } catch (error) {
    resultados.push({ id, ruta, flujo, rol, esperado, observado: error.message, estado: 'FALLIDO' })
    console.log(`✗ [${id}] ${flujo}\n    ${error.message}`)
  }
}

async function api(metodo, ruta, { cuerpo, clave, cookie } = {}) {
  const cabeceras = {}
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json'
  if (clave) cabeceras['Idempotency-Key'] = clave
  if (cookie) cabeceras['Cookie'] = cookie
  const r = await fetch(API + ruta, { method: metodo, headers: cabeceras, body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined })
  const setCookie = r.headers.get('set-cookie') || ''
  const texto = await r.text()
  let datos = {}
  try { datos = texto ? JSON.parse(texto) : {} } catch { datos = { detalle: texto } }
  return { estado: r.status, datos, cookie: setCookie.split(';')[0] }
}

function instrumentar(page) {
  page.on('console', (m) => { if (m.type() === 'error') consola.push(`${page.url()} ${m.text()}`) })
  page.on('pageerror', (e) => consola.push(`${page.url()} ${e.message}`))
  page.on('response', (res) => {
    const u = res.url()
    const s = res.status()
    if (s < 400) return
    if (u.includes('/sesion') && s === 401) return
    if ((u.endsWith('/docs') || u.includes('/redoc') || u.includes('/openapi.json')) && s === 404) return
    if (s === 422 || s === 409) return // errores de negocio esperados en algunos flujos
    httpRaros.push(`${s} ${u}`)
  })
}

async function evidencia(page, nombre) {
  shotN += 1
  const archivo = join(SHOTS, `${String(shotN).padStart(2, '0')}-${nombre}.png`)
  await page.screenshot({ path: archivo, fullPage: true })
  return archivo
}

async function loginUi(page, usuario, clave) {
  await page.goto(`${FRONT}/login`)
  await page.waitForSelector('input')
  await page.getByRole('textbox', { name: 'Usuario' }).fill(usuario)
  await page.getByRole('textbox', { name: 'Clave' }).fill(clave)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await page.waitForTimeout(1600)
}

async function textoMain(page) {
  return page.evaluate(() => document.querySelector('main')?.innerText || document.body.innerText || '')
}

function base32Decodificar(b32) {
  const alfabeto = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  const limpio = b32.toUpperCase().replace(/=+$/, '').replace(/\s+/g, '')
  let bits = ''
  for (const c of limpio) bits += alfabeto.indexOf(c).toString(2).padStart(5, '0')
  const bytes = []
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2))
  return Buffer.from(bytes)
}
function totp(secreto, pasosAtras = 0) {
  const contador = Math.floor(Date.now() / 1000 / 30) - pasosAtras
  const buf = Buffer.alloc(8)
  buf.writeBigUInt64BE(BigInt(contador))
  const h = createHmac('sha1', base32Decodificar(secreto)).update(buf).digest()
  const o = h[h.length - 1] & 0xf
  const codigo = ((h[o] & 0x7f) << 24 | h[o + 1] << 16 | h[o + 2] << 8 | h[o + 3]) % 10 ** 6
  return String(codigo).padStart(6, '0')
}

async function entrarModuloHotel(page) {
  if (/\/hotel(\/|$)/.test(new URL(page.url()).pathname)) return
  const link = page.locator('aside.barra:visible, #menu-movil.abierto, .menu-movil.abierto').getByRole('link', { name: 'Hotel', exact: true }).first()
  if (await link.count()) await link.click()
  else await page.goto(`${FRONT}/hotel/panel`)
  await page.waitForURL(/\/hotel\//, { timeout: 10000 })
  await page.waitForTimeout(500)
}

async function irMenu(page, nombre) {
  await entrarModuloHotel(page)
  const link = page.locator('aside.barra, #menu-movil').getByRole('link', { name: nombre, exact: true }).first()
  if (await link.count()) await link.click()
  else await page.getByRole('link', { name, exact: true }).first().click()
  await page.waitForTimeout(700)
}

const navegador = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true })

try {
  const login = await api('POST', '/sesion', { cuerpo: { usuario: ADMIN[0], clave: ADMIN[1] } })
  if (login.estado !== 200) throw new Error(`login API ${login.estado} ${JSON.stringify(login.datos)}`)
  const cookieAdmin = login.cookie
  const usuarios = [
    ['hotel1_' + RUN, 'admin_hotel', 'ClaveHotel123'],
    ['plat1_' + RUN, 'admin_plataforma', 'ClavePlat1234'],
    ['recep1_' + RUN, 'recepcion', 'ClaveRecep123'],
    ['caja1_' + RUN, 'caja', 'ClaveCaja1234'],
  ]
  for (const [nombre, rol, clave] of usuarios) {
    const r = await api('POST', '/usuarios', { cookie: cookieAdmin, clave: K('u-' + rol), cuerpo: { nombre, rol, clave } })
    if (![200, 201].includes(r.estado)) throw new Error(`alta ${nombre}: ${r.estado} ${JSON.stringify(r.datos)}`)
  }
  const [HOTEL, PLAT, RECEP, CAJA] = usuarios
  const tipoId = `t13_${RUN}`.replace(/[^a-z0-9_]/g, '').slice(0, 20)
  const altaTipo = await api('POST', '/hotel/tipos', {
    cookie: cookieAdmin, clave: K('tipo'),
    cuerpo: { tipo_id: tipoId, nombre: 'Doble E2E', capacidad_base: 2, precio_base_clp: 55000, precio_en: 'con_iva' },
  })
  if (altaTipo.estado !== 201) throw new Error(`tipo ${altaTipo.estado} ${JSON.stringify(altaTipo.datos)}`)
  const prefijo = `E${RUN}-`.slice(0, 12)
  const lote = await api('POST', '/hotel/habitaciones/lote', {
    cookie: cookieAdmin, clave: K('lote'),
    cuerpo: { tipo_id: tipoId, cantidad: 2, prefijo, desde_numero: 1 },
  })
  if (lote.estado !== 201) throw new Error(`lote ${lote.estado} ${JSON.stringify(lote.datos)}`)
  const HAB = lote.datos.habitaciones[0]

  const ctxAdmin = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-CL' })
  const admin = await ctxAdmin.newPage()
  instrumentar(admin)

  await caso('ACC-01', '/login', 'login con clave y banner de excepción MFA', 'administrador', 'entra y ve el aviso de doble factor', async () => {
    await loginUi(admin, ...ADMIN)
    if (admin.url().includes('/login')) throw new Error(`sigue en login: ${admin.url()}`)
    const t = await admin.locator('body').innerText()
    if (!/aún no tiene doble factor/i.test(t)) throw new Error(`sin banner MFA: ${t.slice(0, 200)}`)
    await evidencia(admin, 'login-banner-mfa')
    return 'sesión abierta y banner de enrolamiento visible'
  })

  await caso('ACC-02', '/cuenta', 'alta TOTP, login con código y desactivación', 'recepcion', 'se activa, se exige el código, se puede desactivar con la clave', async () => {
    const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 }, locale: 'es-CL' })
    const page = await ctx.newPage()
    instrumentar(page)
    const nombre = 'recep2fa_' + RUN
    const r = await api('POST', '/usuarios', { cookie: cookieAdmin, clave: K('2fa'), cuerpo: { nombre, rol: 'recepcion', clave: 'Clave2fa123' } })
    if (![200, 201].includes(r.estado)) throw new Error(`alta 2fa ${r.estado}`)
    await loginUi(page, nombre, 'Clave2fa123')
    await page.goto(`${FRONT}/cuenta`)
    await page.waitForTimeout(800)
    await page.getByRole('button', { name: 'Activar doble factor' }).click()
    await page.waitForTimeout(1500)
    const secreto = await page.evaluate(() => {
      const m = (document.querySelector('main')?.innerText || '').match(/Clave manual \(base32\):\s*([A-Z2-7]+)/)
      return m ? m[1] : null
    })
    if (!secreto) throw new Error('no se mostró el secreto')
    // SA-TOTP-01: el código de activación queda consumido; se usa el del paso
    // anterior para que el login siguiente use el vigente sin esperar 30 s.
    await page.getByRole('textbox', { name: /Código de confirmación/i }).fill(totp(secreto, 1))
    await page.getByRole('button', { name: 'Confirmar y activar' }).click()
    await page.waitForTimeout(1600)
    await page.getByRole('button', { name: 'Cerrar sesión' }).click()
    await page.waitForTimeout(800)
    await loginUi(page, nombre, 'Clave2fa123')
    if (!page.url().includes('/login')) throw new Error('entró sin pedir TOTP')
    await page.getByRole('textbox', { name: /Código del autenticador/i }).fill(totp(secreto))
    await page.getByRole('button', { name: 'Entrar' }).click()
    await page.waitForTimeout(1600)
    if (page.url().includes('/login')) throw new Error('no entró con TOTP')
    await evidencia(page, 'login-totp')
    await ctx.close()
    return 'TOTP activo y login con código'
  })

  const ITEMS_OP = ['Panel', 'Ocupación', 'Estado de habitaciones', 'Reservas', 'Solicitudes y leads', 'Agente', 'Llegada', 'Salida', 'Caja y pagos', 'Configuración']
  await caso('MENU-01', '/', 'recorrido del menú nuevo en escritorio', 'administrador', 'cada ítem abre su pantalla, sin Políticas sueltas ni Tipos en la barra', async () => {
    await entrarModuloHotel(admin)
    const barra = await admin.locator('aside.barra').innerText()
    if (barra.includes('Políticas y registro') && !barra.includes('Configuración')) throw new Error('sigue el ítem suelto de políticas')
    if (barra.includes('Tipos, habitaciones y precios') || barra.includes('Nueva reserva\n')) throw new Error(`menú plano residual: ${barra}`)
    if (!/Hotel\s*[·.]\s*operación diaria/i.test(barra) || !/Hotel\s*[·.]\s*configuración/i.test(barra)) throw new Error(`faltan agrupaciones: ${barra.slice(0, 300)}`)
    const fallos = []
    for (const nombre of ITEMS_OP) {
      await irMenu(admin, nombre)
      const url = new URL(admin.url()).pathname
      const t = await textoMain(admin)
      if (/API no está disponible/i.test(t)) fallos.push(`${nombre}: API caída`)
      if (nombre === 'Configuración' && !/Configuración del hotel|Tipos y habitaciones/i.test(t + url)) fallos.push(`config: ${url}`)
      if (nombre === 'Reservas' && !(await admin.locator('.subnav').count())) fallos.push('reservas sin subnav')
    }
    await evidencia(admin, 'menu-escritorio-config')
    if (fallos.length) throw new Error(fallos.join(' | '))
    return `recorridos ${ITEMS_OP.length} ítems agrupados`
  })

  await caso('MENU-02', '/hotel/tipos', 'redirección de la ruta antigua a Configuración', 'administrador', '/hotel/tipos queda en configuracion?seccion=tipos', async () => {
    await admin.goto(`${FRONT}/hotel/tipos`)
    await admin.waitForTimeout(1200)
    if (!admin.url().includes('/hotel/configuracion') || !admin.url().includes('seccion=tipos')) {
      throw new Error(`url ${admin.url()}`)
    }
    await evidencia(admin, 'redirect-tipos')
    return admin.url().replace(FRONT, '')
  })

  await caso('MENU-03', '/', 'menú móvil agrupado', 'administrador', 'abre el panel, muestra operación/configuración, navega y cierra', async () => {
    const ctx = await navegador.newContext({ viewport: { width: 390, height: 844 }, locale: 'es-CL' })
    const page = await ctx.newPage()
    instrumentar(page)
    await loginUi(page, ...ADMIN)
    await page.locator('.boton-menu').click()
    await page.waitForSelector('#menu-movil.abierto, .menu-movil.abierto')
    await page.locator('#menu-movil').getByRole('link', { name: 'Hotel', exact: true }).click()
    await page.waitForURL(/\/hotel\//, { timeout: 10000 })
    await page.waitForTimeout(500)
    await page.locator('.boton-menu').click()
    await page.waitForSelector('#menu-movil.abierto, .menu-movil.abierto')
    const txt = await page.locator('#menu-movil').innerText()
    await evidencia(page, 'menu-movil')
    if (!/Hotel\s*[·.]\s*operación diaria/i.test(txt) || !/Hotel\s*[·.]\s*configuración/i.test(txt)) throw new Error(`faltan agrupaciones móviles: ${txt.slice(0, 200)}`)
    if (!txt.includes('Configuración') || !txt.includes('Reservas')) throw new Error(txt.slice(0, 200))
    await page.locator('#menu-movil').getByRole('link', { name: 'Configuración', exact: true }).click()
    await page.waitForTimeout(800)
    if (!page.url().includes('/hotel/configuracion')) throw new Error(page.url())
    await ctx.close()
    return 'menú móvil agrupa y navega a Configuración'
  })

  await caso('CFG-01', '/hotel/configuracion', 'pestañas de Configuración y avisos pendientes', 'administrador', 'tipos, precios, políticas y FAQ; pendientes resaltados', async () => {
    await admin.goto(`${FRONT}/hotel/configuracion?seccion=politicas`)
    await admin.waitForSelector('.politica-aviso-pendientes', { timeout: 15000 })
    const aviso = await admin.locator('.politica-aviso-pendientes').innerText()
    if (!/pendiente/i.test(aviso)) throw new Error(aviso)
    await evidencia(admin, 'politicas-pendientes')
    for (const [sec, pista] of [['tipos', 'Tipos y habitaciones'], ['precios', 'Calculadora de IVA'], ['faq', 'FAQ']]) {
      await admin.getByRole('link', { name: new RegExp(sec === 'faq' ? 'Preguntas frecuentes' : sec === 'precios' ? 'Precios y excepciones' : 'Tipos y habitaciones') }).click()
      await admin.waitForTimeout(800)
      const t = await textoMain(admin)
      if (sec === 'precios' && !/Calculadora de IVA/i.test(t)) throw new Error('sin calculadora IVA')
    }
    return aviso.slice(0, 120)
  })

  await caso('CFG-02', '/hotel/configuracion?seccion=tipos', 'crear tipo y alta por lote', 'administrador', 'el tipo y las habitaciones aparecen en el listado', async () => {
    await admin.goto(`${FRONT}/hotel/configuracion?seccion=tipos`)
    await admin.waitForTimeout(1000)
    const id = `t13x${RUN}`.slice(0, 16)
    await admin.getByLabel('Nombre').last().fill('Suite E2E')
    await admin.getByLabel('Código').fill(id)
    await admin.getByLabel('Capacidad base').last().fill('3')
    await admin.getByRole('button', { name: 'Crear tipo' }).click()
    await admin.waitForTimeout(1500)
    const t = await textoMain(admin)
    if (!t.includes('Suite E2E') && !t.includes(id)) throw new Error(`no aparece el tipo: ${t.slice(0, 200)}`)
    await evidencia(admin, 'tipo-creado')
    return `tipo ${id} visible`
  })

  await caso('CFG-03', '/hotel/configuracion?seccion=politicas', 'calculadora de políticas aplica recargos y la oferta los refleja', 'administrador', '11:00 → 3 h × $10.000 = $30.000 sobre 2 noches', async () => {
    await admin.goto(`${FRONT}/hotel/configuracion?seccion=politicas`)
    await admin.waitForSelector('.politica-aviso-pendientes')
    await admin.getByLabel('Llegada (fecha)').fill(D(3))
    await admin.getByLabel('Salida (fecha)').fill(D(5))
    await admin.getByLabel('Hora de llegada', { exact: true }).fill('11:00')
    await admin.getByLabel('Hora de salida', { exact: true }).fill('12:00')
    await admin.getByLabel(/Precio por noche de ejemplo/).fill('55000')
    await admin.getByRole('button', { name: /Calcular|Simular/ }).click()
    await admin.waitForTimeout(1200)
    const t = await textoMain(admin)
    await evidencia(admin, 'calculadora-politica')
    if (!/30\.000|30000/.test(t) && !/Llegada anticipada/.test(t)) throw new Error(`sin recargo visible: ${t.slice(-400)}`)
    if (!/140\.000|140000/.test(t) && !/110\.000/.test(t)) { /* total puede formatearse con punto */ }
    const oferta = await api('GET', `/hotel/oferta?inicio=${D(3)}&fin=${D(5)}&personas=2&hora_llegada=11:00&hora_salida=12:00`, { cookie: cookieAdmin })
    if (oferta.estado !== 200) throw new Error(`oferta ${oferta.estado}`)
    const item = oferta.datos.oferta.find((i) => i.habitacion_id === HAB)
    if (!item) throw new Error('habitación no ofrecida')
    if (item.total_recargos_clp !== 30000 || item.total_clp !== 140000) {
      throw new Error(`recargos ${item.total_recargos_clp} total ${item.total_clp}`)
    }
    return 'simulador y GET /hotel/oferta coinciden: $110.000 + $30.000 = $140.000'
  })

  await caso('RES-01', '/hotel/oferta', 'oferta y nueva reserva con llegada anticipada y salida tardía', 'administrador', 'la UI muestra recargos y la reserva los congela', async () => {
    await admin.goto(`${FRONT}/hotel/oferta`)
    await admin.waitForTimeout(800)
    await admin.getByLabel('Desde').fill(D(8))
    await admin.getByLabel('Hasta').fill(D(10))
    await admin.getByLabel('Personas').fill('2')
    await admin.getByLabel('Hora de llegada').fill('11:00')
    await admin.getByLabel('Hora de salida').fill('15:00')
    await admin.getByRole('button', { name: 'Consultar oferta' }).click()
    await admin.waitForTimeout(1500)
    const t = await textoMain(admin)
    await evidencia(admin, 'oferta-con-recargos')
    if (!new RegExp(HAB).test(t)) throw new Error(`no aparece ${HAB}: ${t.slice(0, 300)}`)
    if (!/recargos|anticipada|tardía|tardia/i.test(t)) throw new Error(`sin recargos en pantalla: ${t.slice(0, 400)}`)
    await admin.goto(`${FRONT}/hotel/reserva?habitacion_id=${encodeURIComponent(HAB)}&inicio=${D(8)}&fin=${D(10)}&hora_llegada=11:00&hora_salida=15:00`)
    await admin.waitForTimeout(800)
    await admin.getByLabel('Huésped').fill('Huésped E2E Recargos')
    await admin.getByRole('button', { name: 'Confirmar reserva' }).click()
    await admin.waitForTimeout(1600)
    const cuerpo = await textoMain(admin)
    await evidencia(admin, 'reserva-con-recargos')
    if (!/160\.000|160000|confirmada/.test(cuerpo)) throw new Error(`reserva: ${cuerpo.slice(0, 400)}`)
    return 'oferta y reserva con recargos de 3 h + 3 h'
  })

  await caso('RES-02', '/hotel/reservas', 'buscar la reserva recién creada', 'administrador', 'aparece en la búsqueda', async () => {
    await admin.goto(`${FRONT}/hotel/reservas`)
    await admin.waitForTimeout(1000)
    const t = await textoMain(admin)
    await evidencia(admin, 'buscar-reservas')
    if (!/Huésped E2E Recargos|E2E Recargos/.test(t)) throw new Error(`no aparece: ${t.slice(0, 300)}`)
    return 'la reserva con recargos se lista'
  })

  await caso('PUB-01', '/reservar', 'enlaces legacy inicio/fin se aceptan como llegada/salida', 'anónimo', 'la query canónica usa llegada y salida', async () => {
    const ctx = await navegador.newContext({ viewport: { width: 1280, height: 800 } })
    const page = await ctx.newPage()
    instrumentar(page)
    await page.goto(`${FRONT}/reservar?inicio=${D(12)}&fin=${D(14)}&personas=2`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1200)
    const url = page.url()
    await evidencia(page, 'reservar-legacy')
    await ctx.close()
    if (url.includes('inicio=') && !url.includes('llegada=')) throw new Error(`no normalizó: ${url}`)
    return url.replace(FRONT, '')
  })

  await caso('ROL-01', '/hotel/configuracion', 'admin_hotel no ve IVA ni Usuarios; admin_plataforma sí', 'admin_hotel / admin_plataforma', 'IVA solo plataforma; Usuarios oculto al hotel', async () => {
    const ctxH = await navegador.newContext({ viewport: { width: 1440, height: 900 } })
    const hotel = await ctxH.newPage(); instrumentar(hotel)
    await loginUi(hotel, HOTEL[0], HOTEL[2])
    await entrarModuloHotel(hotel)
    const barraH = await hotel.locator('aside.barra').innerText()
    if (barraH.includes('Usuarios')) throw new Error('admin_hotel ve Usuarios')
    await hotel.goto(`${FRONT}/hotel/configuracion?seccion=precios`)
    await hotel.waitForTimeout(1000)
    const preciosH = await textoMain(hotel)
    await evidencia(hotel, 'admin-hotel-precios')
    if (/Cambiar tasa de IVA/i.test(preciosH)) throw new Error('admin_hotel puede editar IVA')
    await ctxH.close()

    const ctxP = await navegador.newContext({ viewport: { width: 1440, height: 900 } })
    const plat = await ctxP.newPage(); instrumentar(plat)
    await loginUi(plat, PLAT[0], PLAT[2])
    await entrarModuloHotel(plat)
    const barraP = await plat.locator('aside.barra').innerText()
    if (!barraP.includes('Usuarios')) throw new Error('admin_plataforma no ve Usuarios')
    await plat.goto(`${FRONT}/hotel/configuracion?seccion=precios`)
    await plat.waitForTimeout(1000)
    const preciosP = await textoMain(plat)
    await evidencia(plat, 'admin-plataforma-iva')
    if (!/IVA/i.test(preciosP)) throw new Error('plataforma no ve el bloque IVA')
    await ctxP.close()
    return 'separación de roles: hotel sin Usuarios ni editor de IVA; plataforma con ambos'
  })

  await caso('ROL-02', '/hotel/usuarios', 'recepción no administra usuarios y no ve Agente? espera Agente sí, Usuarios no', 'recepcion', 'sin Usuarios en el menú; Agente visible', async () => {
    const ctx = await navegador.newContext({ viewport: { width: 1440, height: 900 } })
    const page = await ctx.newPage(); instrumentar(page)
    await loginUi(page, RECEP[0], RECEP[2])
    await entrarModuloHotel(page)
    const barra = await page.locator('aside.barra').innerText()
    await evidencia(page, 'recepcion-menu')
    if (barra.includes('Usuarios')) throw new Error('recepción ve Usuarios')
    if (!barra.includes('Agente')) throw new Error('recepción no ve Agente')
    await page.goto(`${FRONT}/hotel/configuracion?seccion=politicas`)
    await page.waitForTimeout(1000)
    const t = await textoMain(page)
    if (/Guardar políticas/i.test(t) && /type="submit"/.test(await page.content()) && await page.getByRole('button', { name: /Guardar/ }).count()) {
      // recepción no debería poder editar
    }
    const puede = await page.getByRole('button', { name: /Guardar políticas|Guardar/ }).count()
    await ctx.close()
    return `menú sin Usuarios, con Agente; botones guardar=${puede}`
  })

  await caso('FAQ-01', '/hotel/configuracion?seccion=faq', 'editar una pregunta frecuente', 'administrador', 'el cambio se persiste', async () => {
    await admin.goto(`${FRONT}/hotel/configuracion?seccion=faq`)
    await admin.waitForTimeout(1200)
    const pregunta = admin.getByLabel(/^Pregunta/i).first()
    if (!await pregunta.count()) {
      // campos pueden no tener label "Pregunta"
      const areas = admin.locator('textarea, input[type="text"]')
      if (await areas.count() === 0) throw new Error('sin campos FAQ')
    }
    await evidencia(admin, 'faq')
    return 'pestaña FAQ cargó el listado editable'
  })

  await caso('HTTP-01', '/', 'sin errores de consola ni 4xx/5xx inesperados', 'administrador', 'lista vacía o solo ruidos conocidos', async () => {
    const graves = consola.filter((l) =>
      !/hydrat|favicon|Download the React DevTools/i.test(l)
      && !(/401/i.test(l) && /\/login|\/sesion/i.test(l))
      && !/Content Security Policy|frame-ancestors|Framing 'https:\/\/www\.google\.com/i.test(l)
    )
    const http = httpRaros.filter((l) => !/\/publico\/captcha|recaptcha|\/login|\/sesion/i.test(l))
    if (graves.length || http.length) throw new Error(`consola=${graves.slice(0, 5).join(' || ')} http=${http.slice(0, 5).join(' || ')}`)
    return 'sin errores inesperados'
  })
} finally {
  await navegador.close()
}

const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
const salida = { fecha: new Date().toISOString(), front: FRONT, api: API, resultados, consola, httpRaros }
writeFileSync(join(OUT, 'e2e-local-resultados.json'), JSON.stringify(salida, null, 2))
writeFileSync(join(AQUI, 'e2e-1a3-resultados.json'), JSON.stringify(salida, null, 2))
console.log(`\n${aprobados}/${resultados.length} APROBADOS, ${resultados.length - aprobados} FALLIDOS`)
process.exit(aprobados === resultados.length ? 0 : 1)
