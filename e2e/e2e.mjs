/**
 * Revisión E2E ejecutable — plataforma V1, módulo hotel.
 *
 * Corre el navegador (Chromium) contra el front y la API en local, con datos
 * 100% sintéticos y desechables. Verifica para cada ruta/flujo/rol el
 * resultado permitido y el rechazo esperado del contrato, y comprueba el
 * efecto de cada mutación releyendo el estado desde la API.
 *
 * Requisitos:
 *   - Backend en 127.0.0.1:8080 con DATABASE_URL apuntando a una base
 *     sintética desechable y ORIGIN_FRONT=http://127.0.0.1:3000
 *   - Front servido en 127.0.0.1:3000 (npm run build && npm run start con
 *     API_BASE_URL=http://127.0.0.1:8080)
 *
 * Uso:
 *   cd e2e && npm install && npm run e2e
 *
 * Salida: resultados en consola + e2e-resultados.json en este directorio.
 * La evidencia visual queda en ../capturas/e2e-AAAA-MM-DD/.
 */

import { chromium } from 'playwright'
import { writeFileSync, mkdirSync } from 'node:fs'
import { createHmac } from 'node:crypto'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONT = process.env.FRONT_URL || 'http://127.0.0.1:3000'
const API = process.env.API_URL || 'http://127.0.0.1:8080'
const HOY = new Date()
// Fecha local del servidor de pruebas: toISOString() es UTC y tras las 21:00
// en Chile (UTC-3) adelanta un día, rompiendo la comparación con la fecha del
// backend (entrada, caja del día). Todo se formatea en hora local.
function isoLocal(fecha) {
  const d = new Date(fecha)
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dia = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${dia}`
}
const HOY_FECHA = isoLocal(HOY)
const EN_1_DIA = sumarDias(HOY, 1)
const EN_3_DIAS = sumarDias(HOY, 3)
const EN_30_DIAS = sumarDias(HOY, 30)
const EN_33_DIAS = sumarDias(HOY, 33)
const EN_40_DIAS = sumarDias(HOY, 40)

function sumarDias(fecha, dias) {
  const d = new Date(fecha)
  d.setDate(d.getDate() + dias)
  return isoLocal(d)
}

const RUN = Date.now().toString(36)
const K = (nombre) => `${nombre}-${RUN}`

function iso(fecha) {
  return isoLocal(fecha)
}

// ---------- cliente API con cookie ----------
async function api(metodo, ruta, { cuerpo, clave, cookie } = {}) {
  const cabeceras = {}
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json'
  if (clave) cabeceras['Idempotency-Key'] = clave
  if (cookie) cabeceras['Cookie'] = cookie
  const respuesta = await fetch(API + ruta, {
    method: metodo,
    headers: cabeceras,
    body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
  })
  const setCookie = respuesta.headers.get('set-cookie') || ''
  const texto = await respuesta.text()
  let datos = {}
  try {
    datos = texto ? JSON.parse(texto) : {}
  } catch {
    datos = { detalle: texto }
  }
  return { estado: respuesta.status, datos, cookie: setCookie.split(';')[0] }
}

async function loginApi(usuario, clave) {
  const r = await api('POST', '/sesion', { cuerpo: { usuario, clave } })
  if (r.estado !== 200) throw new Error(`login API falló para ${usuario}: ${r.estado}`)
  return r.cookie
}

// ---------- runner ----------
const resultados = []
let evidenciaN = 0

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
  const marca = estado === 'APROBADO' ? '✓' : estado === 'FALLIDO' ? '✗' : '•'
  console.log(`${marca} [${id}] ${ruta} · ${flujo} · ${rol} → ${estado}`)
  if (estado === 'FALLIDO') console.log(`    esperado: ${esperado}\n    observado: ${observado}`)
}

const CARPETA_EVIDENCIA = join(dirname(fileURLToPath(import.meta.url)), '..', 'capturas', `e2e-${iso(HOY)}`)
mkdirSync(CARPETA_EVIDENCIA, { recursive: true })

async function evidencia(page, nombre) {
  evidenciaN += 1
  const archivo = join(CARPETA_EVIDENCIA, `${String(evidenciaN).padStart(2, '0')}-${nombre}.png`)
  await page.screenshot({ path: archivo })
  return `capturas/e2e-${iso(HOY)}/${String(evidenciaN).padStart(2, '0')}-${nombre}.png`
}

// ---------- helpers de UI ----------
async function loginUi(page, usuario, clave) {
  await page.goto(`${FRONT}/login`)
  await page.waitForSelector('input')
  await page.getByRole('textbox', { name: 'Usuario' }).fill(usuario)
  await page.getByRole('textbox', { name: 'Clave' }).fill(clave)
  await page.getByRole('button', { name: 'Entrar' }).click()
  await page.waitForTimeout(1800)
}

async function textoPrincipal(page) {
  return page.evaluate(() => document.querySelector('main')?.innerText || '')
}

async function alerta(page) {
  return page.evaluate(() => document.querySelector('[role=alert]')?.textContent || null)
}

async function confirmacion(page) {
  return page.evaluate(() => document.querySelector('.operacion-confirmada')?.textContent || null)
}

// ---------- TOTP (RFC 6238, SHA-1, 30 s, 6 dígitos) para el alta 2FA en UI ----------
function base32Decodificar(b32) {
  const alfabeto = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
  const limpio = b32.toUpperCase().replace(/=+$/, '').replace(/\s+/g, '')
  let bits = ''
  for (const c of limpio) bits += alfabeto.indexOf(c).toString(2).padStart(5, '0')
  const bytes = []
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2))
  return Buffer.from(bytes)
}

function totp(secreto, pasoSegundos = 30, digitos = 6) {
  const contador = Math.floor(Date.now() / 1000 / pasoSegundos)
  const buf = Buffer.alloc(8)
  buf.writeBigUInt64BE(BigInt(contador))
  const h = createHmac('sha1', base32Decodificar(secreto)).update(buf).digest()
  const o = h[h.length - 1] & 0xf
  const codigo = ((h[o] & 0x7f) << 24 | h[o + 1] << 16 | h[o + 2] << 8 | h[o + 3]) % 10 ** digitos
  return String(codigo).padStart(digitos, '0')
}

// ---------- suite ----------
const navegador = await chromium.launch()
const contextos = {}
async function contextoRol(nombre) {
  if (!contextos[nombre]) {
    contextos[nombre] = await navegador.newContext({ baseURL: FRONT })
  }
  return contextos[nombre]
}

let cookieAdmin, cookieRecepcion, cookieCaja

try {
  // ===== Semilla sintética (vía API, con admin del arranque) =====
  cookieAdmin = await loginApi('admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
  await api('POST', '/usuarios', { cookie: cookieAdmin, clave: K('e2e-semilla-recepcion'), cuerpo: { nombre: 'recepcion_e2e', rol: 'recepcion', clave: 'RecepE2e123' } })
  await api('POST', '/usuarios', { cookie: cookieAdmin, clave: K('e2e-semilla-caja'), cuerpo: { nombre: 'caja_e2e', rol: 'caja', clave: 'CajaE2e1234' } })
  const HAB_A = `HAB-${RUN}-A`, HAB_B = `HAB-${RUN}-B`, HAB_C = `HAB-${RUN}-C`
  // Alta por UI: id por corrida (el alta es «solo crear», If-None-Match: *;
  // spec-hotel-operacion-v1 §2.2). Nace sin tarifa: la usa RES-02.
  const HAB_NUEVA = `HAB-${RUN}-201`
  for (const [id, tipo, cap, tarifa] of [[HAB_A, 'doble', 2, 50000], [HAB_B, 'simple', 1, 35000], [HAB_C, 'doble', 2, 60000]]) {
    await api('PUT', `/hotel/habitaciones/${id}`, { cookie: cookieAdmin, clave: K(`semilla-${id}`), cuerpo: { tipo, capacidad: cap } })
    await api('PUT', '/hotel/tarifas', { cookie: cookieAdmin, clave: K(`tarifa-${id}`), cuerpo: { habitacion_id: id, fecha_desde: '2026-01-01', fecha_hasta: '2027-12-31', tarifa_noche_clp: tarifa } })
  }
  cookieRecepcion = await loginApi('recepcion_e2e', 'RecepE2e123')
  cookieCaja = await loginApi('caja_e2e', 'CajaE2e1234')

  // ===== A. Acceso y cuenta =====
  {
    const ctx = await contextoRol('admin')
    const page = await ctx.newPage()
    await caso('ACC-01', '/login', 'login admin redirige a la plataforma', 'administrador', '200 y home con empresa y módulos', async () => {
      await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
      if (!page.url().endsWith(`${FRONT}/`.replace('http://127.0.0.1:3000', '')) && page.url() !== `${FRONT}/`) throw new Error(`url final: ${page.url()}`)
      const texto = await textoPrincipal(page)
      if (!texto.includes('EMP-SINTETICA-001') || !texto.includes('admin_e2e')) throw new Error('no muestra empresa/usuario de la sesión')
      await evidencia(page, 'acc-01-home-admin')
      return 'home con sesión admin'
    })
    await caso('ACC-02', '/login', 'clave inválida no abre sesión y avisa', 'anónimo', '401 y mensaje de credenciales inválidas', async () => {
      await page.goto(`${FRONT}/login`)
      await page.getByRole('textbox', { name: 'Usuario' }).fill('admin_e2e')
      await page.getByRole('textbox', { name: 'Clave' }).fill('clave-mala')
      await page.getByRole('button', { name: 'Entrar' }).click()
      await page.waitForTimeout(1500)
      const a = await alerta(page)
      if (!a) throw new Error('no se mostró alerta')
      if (page.url() !== `${FRONT}/login`) throw new Error(`navegó a ${page.url()}`)
      return a
    })
    await caso('ACC-03', '/hotel/oferta', 'ruta hotel sin sesión pide login', 'anónimo', 'solo la pantalla de acceso, sin menú interno ni datos', async () => {
      const ctx2 = await navegador.newContext({ baseURL: FRONT })
      const anonima = await ctx2.newPage()
      await anonima.goto(`${FRONT}/hotel/oferta`)
      await anonima.waitForTimeout(1500)
      const texto = await textoPrincipal(anonima)
      const menuInterno = await anonima.getByRole('link', { name: 'Panel' }).count()
      await ctx2.close()
      if (menuInterno !== 0) throw new Error('menú interno visible sin sesión')
      if (!texto.includes('Plataforma Herencia')) throw new Error(`texto: ${texto.slice(0, 120)}`)
      return 'pide inicio de sesión, sin menú interno'
    })
    await caso('ACC-04', '/cuenta', 'estado 2FA visible', 'administrador', 'muestra «Estado: desactivado» y alta disponible', async () => {
      await page.goto(`${FRONT}/cuenta`)
      await page.waitForTimeout(1500)
      const texto = await textoPrincipal(page)
      if (!texto.includes('desactivado')) throw new Error(`texto: ${texto.slice(0, 160)}`)
      return 'estado 2FA desactivado visible'
    })
    await caso('ACC-05', '/login', 'botón Google oculto sin adaptador', 'anónimo', 'sin botón «Entrar con Google» (configurado:false)', async () => {
      const botones = await page.evaluate(() => [...document.querySelectorAll('a,button')].map((b) => b.textContent))
      if (botones.some((b) => b.includes('Google'))) throw new Error('botón Google visible sin configuración')
      return 'sin botón Google'
    })
    await page.close()
  }

  // ===== B. Módulos cerrados =====
  for (const ruta of ['/cafeteria', '/inmobiliaria', '/constructora']) {
    const ctx = await contextoRol('admin')
    const page = await ctx.newPage()
    await caso(`CER-${ruta.slice(1).toUpperCase().slice(0, 3)}`, ruta, 'módulo cerrado no operable', 'administrador', 'aviso de fuera de la versión, sin formularios ni fetch', async () => {
      await page.goto(`${FRONT}${ruta}`)
      await page.waitForTimeout(1200)
      const texto = await textoPrincipal(page)
      if (!/cerrad|fuera de la versión/i.test(texto)) throw new Error(`no anuncia cierre: ${texto.slice(0, 140)}`)
      if (texto.includes('Guardar') || texto.includes('Confirmar')) throw new Error('muestra acciones')
      return 'presentado como fuera de la versión, sin operación'
    })
    await page.close()
  }

  // ===== C/D/E. Habitaciones por rol =====
  await caso('HAB-01', '/hotel/habitaciones', 'inventario refleja la semilla', 'administrador', 'las 3 habitaciones sembradas listadas con tarifa ref.', async () => {
    const r = await api('GET', '/hotel/habitaciones', { cookie: cookieAdmin })
    if (r.estado !== 200) throw new Error(`${r.estado}`)
    const porId = Object.fromEntries(r.datos.habitaciones.map((h) => [h.habitacion_id, h]))
    for (const id of [HAB_A, HAB_B, HAB_C]) {
      if (!porId[id]) throw new Error(`falta ${id}`)
      if (porId[id].tarifa_noche_clp <= 0) throw new Error(`${id} sin tarifa ref.`)
    }
    return `${r.datos.habitaciones.length} unidades (3 sembradas + sintéticas del dominio)`
  })
  {
    const ctx = await contextoRol('admin')
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await caso('HAB-02', '/hotel/habitaciones', 'alta desde la UI aparece en el inventario', 'administrador', 'HAB-201 creada y listada', async () => {
      await page.goto(`${FRONT}/hotel/habitaciones`)
      await page.waitForTimeout(1500)
      await page.getByRole('textbox', { name: 'Habitación' }).first().fill(HAB_NUEVA)
      await page.getByRole('button', { name: 'Dar de alta' }).click()
      await page.waitForTimeout(1800)
      const filas = await page.evaluate(() => [...document.querySelectorAll('.inventario-fila')].map((f) => f.innerText))
      if (!filas.some((f) => f.includes(HAB_NUEVA))) throw new Error(`${HAB_NUEVA} no aparece en el inventario`)
      await evidencia(page, 'hab-02-alta')
      return `${HAB_NUEVA} listada tras el alta`
    })
    await caso('HAB-03', '/hotel/habitaciones', 'abrir mantenimiento excluye de la oferta', 'administrador', 'oferta sin HAB-103; al cerrar vuelve', async () => {
      const fila = page.locator('.inventario-fila', { hasText: HAB_C })
      await fila.getByRole('button', { name: 'Abrir mantenimiento' }).click()
      await page.waitForTimeout(1800)
      let oferta = await api('GET', `/hotel/oferta?inicio=${EN_30_DIAS}&fin=${EN_33_DIAS}&personas=2`, { cookie: cookieAdmin })
      const ids = oferta.datos.oferta.map((u) => u.habitacion_id)
      if (ids.includes(HAB_C)) throw new Error('HAB-103 sigue en oferta con mantenimiento abierto')
      await fila.getByRole('button', { name: 'Cerrar mantenimiento' }).click()
      await page.waitForTimeout(1800)
      oferta = await api('GET', `/hotel/oferta?inicio=${EN_30_DIAS}&fin=${EN_33_DIAS}&personas=2`, { cookie: cookieAdmin })
      if (!oferta.datos.oferta.map((u) => u.habitacion_id).includes(HAB_C)) throw new Error('HAB-103 no volvió a la oferta')
      return 'oferta excluye/incluye según mantenimiento'
    })
    await page.close()
  }
  await caso('HAB-04', '/hotel/habitaciones', 'recepción no puede abrir mantenimiento', 'recepcion', '403 «acceso denegado»', async () => {
    const r = await api('POST', `/hotel/habitaciones/${HAB_A}/mantenimiento`, { cookie: cookieRecepcion, clave: K('e2e-mant-403'), cuerpo: { abierto: true } })
    if (r.estado !== 403) throw new Error(`${r.estado}`)
    return '403'
  })
  await caso('HAB-05', '/hotel/habitaciones', 'caja no puede completar limpieza', 'caja', '403 «acceso denegado»', async () => {
    const r = await api('POST', `/hotel/habitaciones/${HAB_A}/limpieza`, { cookie: cookieCaja, clave: K('e2e-limp-403'), cuerpo: {} })
    if (r.estado !== 403) throw new Error(`${r.estado}`)
    return '403'
  })
  await caso('HAB-06', '/hotel/habitaciones', 'caja lee el inventario', 'caja', '200 con las unidades', async () => {
    const r = await api('GET', '/hotel/habitaciones', { cookie: cookieCaja })
    if (r.estado !== 200) throw new Error(`${r.estado}`)
    return `${r.datos.habitaciones.length} unidades visibles`
  })

  // ===== F. Oferta =====
  for (const [rol, cookie] of [['administrador', cookieAdmin], ['recepcion', cookieRecepcion], ['caja', cookieCaja]]) {
    await caso(`OFE-${rol.slice(0, 3).toUpperCase()}`, '/hotel/oferta', 'consulta de oferta', rol, '200 solo disponibles, con tarifa y vencimiento', async () => {
      const r = await api('GET', `/hotel/oferta?inicio=${EN_30_DIAS}&fin=${EN_33_DIAS}&personas=2`, { cookie })
      if (r.estado !== 200) throw new Error(`${r.estado}`)
      if (!r.datos.oferta.length) throw new Error('oferta vacía')
      const u = r.datos.oferta[0]
      if (!u.tarifa_noche_clp || !u.vigente_hasta) throw new Error('falta tarifa o vigencia')
      return `${r.datos.oferta.length} unidades con tarifa y vigencia`
    })
  }

  // ===== G. Reserva =====
  let reservaId, reservaCortaId
  {
    const ctx = await contextoRol('recepcion')
    const page = await ctx.newPage()
    await loginUi(page, 'recepcion_e2e', 'RecepE2e123')
    await caso('RES-01', '/hotel/reserva', 'crear reserva desde la UI', 'recepcion', '201 confirmada; aparece en la búsqueda', async () => {
      await page.goto(`${FRONT}/hotel/reserva`)
      await page.waitForTimeout(1500)
      await page.getByRole('textbox', { name: 'Habitación' }).fill(HAB_A)
      await page.getByRole('textbox', { name: 'Desde' }).fill(HOY_FECHA)
      await page.getByRole('textbox', { name: 'Hasta' }).fill(EN_3_DIAS)
      await page.getByRole('textbox', { name: 'Huésped' }).fill('Huésped Sintético')
      await page.getByRole('textbox', { name: /Documento/ }).fill('E2E-DOC-123')
      await page.getByRole('button', { name: 'Confirmar reserva' }).click()
      await page.waitForTimeout(2000)
      const conf = await confirmacion(page)
      if (!conf || !conf.includes('confirmada')) throw new Error(`sin confirmación: ${conf}`)
      reservaId = JSON.parse(await page.evaluate(() => document.querySelector('.json-panel')?.textContent || '{}')).reserva_id
      const busqueda = await api('GET', `/hotel/reservas?texto=${reservaId}`, { cookie: cookieRecepcion })
      if (busqueda.datos.total !== 1) throw new Error('la reserva no aparece en la búsqueda')
      await evidencia(page, 'res-01-confirmada')
      return conf
    })
    await caso('RES-02', '/hotel/reserva', 'reserva sin tarifa vigente es rechazada', 'recepcion', '409 con mensaje «sin tarifa vigente»', async () => {
      await page.getByRole('button', { name: 'Nueva operación' }).click()
      await page.waitForTimeout(500)
      await page.getByRole('textbox', { name: 'Habitación' }).fill(HAB_NUEVA)
      await page.getByRole('textbox', { name: 'Desde' }).fill(EN_30_DIAS)
      await page.getByRole('textbox', { name: 'Hasta' }).fill(EN_33_DIAS)
      await page.getByRole('textbox', { name: 'Huésped' }).fill('Sin Tarifa')
      await page.getByRole('button', { name: 'Confirmar reserva' }).click()
      await page.waitForTimeout(1800)
      const a = await alerta(page)
      if (!a || !a.includes('tarifa')) throw new Error(`alerta: ${a}`)
      return a
    })
    await caso('RES-03', '/hotel/reserva', 'solape en misma unidad y fechas', 'recepcion', '409 sin cupo (la carrera la gana una)', async () => {
      const r = await api('POST', '/hotel/reservas', {
        cookie: cookieRecepcion,
        clave: K('e2e-solape'),
        cuerpo: { habitacion_id: HAB_A, inicio: HOY_FECHA, fin: EN_3_DIAS, huesped: { nombre: 'Segunda Carrera' } },
      })
      if (r.estado !== 409) throw new Error(`${r.estado} ${JSON.stringify(r.datos)}`)
      return r.datos.detail
    })
    await page.close()
  }

  // ===== H. Búsqueda de reservas =====
  await caso('BUS-01', '/hotel/reservas', 'filtro de estado inválido', 'administrador', '422 «estado inválido»', async () => {
    const r = await api('GET', '/hotel/reservas?estado=loquesea', { cookie: cookieAdmin })
    if (r.estado !== 422) throw new Error(`${r.estado}`)
    return r.datos.detail
  })
  await caso('BUS-02', '/hotel/reservas', 'documento del huésped por rol', 'recepcion vs caja', 'recepcion lo ve; caja no', async () => {
    const conRecepcion = await api('GET', `/hotel/reservas?texto=${reservaId}`, { cookie: cookieRecepcion })
    const conCaja = await api('GET', `/hotel/reservas?texto=${reservaId}`, { cookie: cookieCaja })
    const docRecep = conRecepcion.datos.reservas[0].huesped_documento
    const docCaja = conCaja.datos.reservas[0].huesped_documento
    if (docRecep !== 'E2E-DOC-123') throw new Error(`recepcion no recibió el documento enviado: ${docRecep}`)
    if (docCaja !== undefined && docCaja !== null) throw new Error('caja recibió documento')
    return `recepcion:${String(docRecep)} caja:${String(docCaja)}`
  })
  {
    const ctx = await contextoRol('caja')
    const page = await ctx.newPage()
    await loginUi(page, 'caja_e2e', 'CajaE2e1234')
    await caso('BUS-03', '/hotel/reservas', 'la página nace con reservas listadas', 'caja', 'tabla visible al entrar, sin buscar', async () => {
      await page.goto(`${FRONT}/hotel/reservas`)
      await page.waitForTimeout(2200)
      const total = await page.evaluate(() => document.querySelector('.reservas-total')?.textContent || null)
      if (!total || total.startsWith('0 ')) throw new Error(`total: ${total}`)
      await evidencia(page, 'bus-03-reservas-auto')
      return total
    })
    await page.close()
  }

  // ===== I. Pago =====
  {
    const ctx = await contextoRol('caja')
    const page = await ctx.newPage()
    await loginUi(page, 'caja_e2e', 'CajaE2e1234')
    await caso('PAG-01', '/hotel/pago', 'pago manual de caja registra efecto', 'caja', '201 confirmado; la caja del día lo lista', async () => {
      await page.goto(`${FRONT}/hotel/pago`)
      await page.waitForTimeout(1500)
      await page.getByRole('textbox', { name: 'Reserva' }).fill(reservaId)
      await page.getByRole('spinbutton', { name: 'Monto (CLP)' }).fill('100000')
      await page.getByRole('textbox', { name: 'Clave del cobro' }).fill('e2e-cobro-1')
      await page.getByRole('button', { name: 'Registrar pago' }).click()
      await page.waitForTimeout(2000)
      const conf = await confirmacion(page)
      if (!conf || !conf.includes('Pago')) throw new Error(`sin confirmación: ${conf}`)
      const caja = await api('GET', `/hotel/caja?fecha=${iso(HOY)}`, { cookie: cookieCaja })
      if (!caja.datos.pagos.some((p) => p.reserva_id === reservaId)) throw new Error('el pago no aparece en caja')
      await evidencia(page, 'pag-01-manual')
      return conf
    })
    await caso('PAG-02', '/hotel/pago', 'pasarela sin adaptador', 'caja', '503 «no configurado», nada cobrado', async () => {
      await page.getByRole('button', { name: 'Nueva operación' }).click()
      await page.waitForTimeout(500)
      await page.getByRole('textbox', { name: 'Reserva' }).fill(reservaId)
      await page.getByRole('spinbutton', { name: 'Monto (CLP)' }).fill('1000')
      await page.getByRole('combobox', { name: 'Modo' }).selectOption('pasarela')
      await page.getByRole('button', { name: 'Registrar pago' }).click()
      await page.waitForTimeout(1800)
      const a = await alerta(page)
      if (!a || !a.includes('no está configurada')) throw new Error(`alerta: ${a}`)
      return a
    })
    await caso('PAG-03', '/hotel/pago', 'pago duplicado con misma clave y cuerpo', 'caja', 'mismo resultado, un solo efecto', async () => {
      const cuerpo = { monto_clp: 5000, clave: K('e2e-cobro-dup'), modo: 'manual' }
      const r1 = await api('POST', `/hotel/reservas/${reservaId}/pagos`, { cookie: cookieCaja, clave: K('e2e-idem-pago'), cuerpo })
      const r2 = await api('POST', `/hotel/reservas/${reservaId}/pagos`, { cookie: cookieCaja, clave: K('e2e-idem-pago'), cuerpo })
      if (r1.estado !== 201 || r2.estado !== 201) throw new Error(`${r1.estado}/${r2.estado}`)
      if (r1.datos.pago_id !== r2.datos.pago_id) throw new Error('dos pagos distintos con la misma clave')
      return `mismo pago ${r1.datos.pago_id}`
    })
    await page.close()
  }

  // ===== J. Estadía: entrada, cargo, cancelación =====
  await caso('EST-01', '/hotel/estadia', 'check-in deja la unidad ocupada', 'recepcion', 'reserva en_estadia; inventario «ocupada»', async () => {
    const r = await api('POST', `/hotel/reservas/${reservaId}/entrada`, { cookie: cookieRecepcion, clave: K('e2e-ent-1'), cuerpo: { documento: '11.111.111-1' } })
    if (r.estado !== 200) throw new Error(`${r.estado} ${JSON.stringify(r.datos)}`)
    const inv = await api('GET', '/hotel/habitaciones', { cookie: cookieRecepcion })
    const hab101 = inv.datos.habitaciones.find((h) => h.habitacion_id === HAB_A)
    if (hab101.estado_operativo !== 'ocupada') throw new Error(`estado: ${hab101.estado_operativo}`)
    return 'HAB-101 ocupada'
  })
  await caso('EST-01b', '/hotel/estadia', 'check-in de una reserva que aún no comienza', 'recepcion', '409 «aún no llega su día de entrada» (v1-issue-07)', async () => {
    const futura = await api('POST', '/hotel/reservas', {
      cookie: cookieRecepcion,
      clave: K('e2e-ent-futura'),
      cuerpo: { habitacion_id: HAB_A, inicio: EN_40_DIAS, fin: sumarDias(HOY, 42), huesped: { nombre: 'Llegada Futura' } },
    })
    if (futura.estado !== 201) throw new Error(`no se creó: ${futura.estado}`)
    const r = await api('POST', `/hotel/reservas/${futura.datos.reserva_id}/entrada`, { cookie: cookieRecepcion, clave: K('e2e-ent-futura-2'), cuerpo: {} })
    if (r.estado !== 409) throw new Error(`esperado 409, llegó ${r.estado}: ${JSON.stringify(r.datos)}`)
    if (!r.datos.detail || !r.datos.detail.includes('día de entrada')) throw new Error(`detalle: ${JSON.stringify(r.datos)}`)
    return r.datos.detail
  })
  await caso('EST-02', '/hotel/estadia', 'cargo de minibar en estadía', 'caja', '201 cargo; entra en la liquidación', async () => {
    const r = await api('POST', `/hotel/reservas/${reservaId}/cargos`, { cookie: cookieCaja, clave: K('e2e-cargo-1'), cuerpo: { concepto: 'minibar', monto_clp: 5000 } })
    if (r.estado !== 201) throw new Error(`${r.estado}`)
    return r.datos.cargo_id
  })
  await caso('EST-03', '/hotel/estadia', 'cargo con monto inválido', 'recepcion', '422', async () => {
    const r = await api('POST', `/hotel/reservas/${reservaId}/cargos`, { cookie: cookieRecepcion, clave: K('e2e-cargo-422'), cuerpo: { concepto: 'x', monto_clp: -5 } })
    if (r.estado !== 422) throw new Error(`${r.estado}`)
    return '422'
  })
  await caso('EST-04', '/hotel/estadia', 'caja no puede cancelar', 'caja', '403 (cancelación: recepción o admin)', async () => {
    const r = await api('POST', `/hotel/reservas/${reservaId}/cancelacion`, { cookie: cookieCaja, clave: K('e2e-cancel-403'), cuerpo: {} })
    if (r.estado !== 403) throw new Error(`${r.estado}`)
    return '403'
  })
  await caso('EST-05', '/hotel/estadia', 'cancelación fuera de plazo carga la primera noche', 'recepcion', '409 (solo desde confirmada) + penalidad en otra', async () => {
    // La reserva en estadía no se puede cancelar (409)…
    const r = await api('POST', `/hotel/reservas/${reservaId}/cancelacion`, { cookie: cookieRecepcion, clave: K('e2e-cancel-est'), cuerpo: {} })
    if (r.estado !== 409) throw new Error(`en_estadia cancelable: ${r.estado}`)
    // …y una con llegada < 48 h desde «ahora» sí, con penalidad.
    const futura = await api('POST', '/hotel/reservas', {
      cookie: cookieRecepcion,
      clave: K('e2e-res-corta'),
      cuerpo: { habitacion_id: HAB_B, inicio: EN_1_DIA, fin: EN_30_DIAS, huesped: { nombre: 'Cancelación Corta' } },
    })
    reservaCortaId = futura.datos.reserva_id
    const cancelada = await api('POST', `/hotel/reservas/${reservaCortaId}/cancelacion`, { cookie: cookieRecepcion, clave: K('e2e-cancel-corta'), cuerpo: {} })
    if (cancelada.estado !== 200) throw new Error(`cancelación: ${cancelada.estado} ${JSON.stringify(cancelada.datos)}`)
    if (!cancelada.datos.penalidad_clp || cancelada.datos.penalidad_clp <= 0) throw new Error(`sin penalidad: ${JSON.stringify(cancelada.datos)}`)
    return `en_estadia→409; corta→cancelada con penalidad ${cancelada.datos.penalidad_clp}`
  })

  // ===== K. Salida =====
  {
    const ctx = await contextoRol('admin')
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await caso('SAL-01', '/hotel/salida', 'salida con saldo pendiente es bloqueada', 'administrador', '409 «saldo pendiente»', async () => {
      await page.goto(`${FRONT}/hotel/salida`)
      await page.waitForTimeout(1500)
      await page.getByRole('textbox', { name: 'Reserva' }).fill(reservaId)
      await page.getByRole('button', { name: 'Liquidar cuenta' }).click()
      await page.waitForTimeout(1800)
      const a = await alerta(page)
      if (!a || !a.includes('saldo pendiente')) throw new Error(`alerta: ${a}`)
      await evidencia(page, 'sal-01-saldo-pendiente')
      return a
    })
    await caso('SAL-02', '/hotel/salida', 'pago del resto y liquidación', 'administrador', 'liquidación con saldo 0; unidad sucia + tarea', async () => {
      const detalle = await api('GET', `/hotel/reservas?texto=${reservaId}`, { cookie: cookieAdmin })
      const tarifa = detalle.datos.reservas[0].tarifa_noche_aceptada_clp
      const noches = (new Date(EN_3_DIAS) - new Date(HOY_FECHA)) / 86400000
      const total = tarifa * noches + 5000
      const pagado = 100000 + 5000
      const restante = total - pagado
      if (restante > 0) {
        const rp = await api('POST', `/hotel/reservas/${reservaId}/pagos`, { cookie: cookieAdmin, clave: K('e2e-pago-final'), cuerpo: { monto_clp: restante, clave: K('e2e-cobro-final'), modo: 'manual' } })
        if (rp.estado !== 201) throw new Error(`pago final: ${rp.estado}`)
      } else if (restante < 0) {
        throw new Error(`escenario mal plantado: sobrepagado en ${-restante}`)
      }
      await page.getByRole('button', { name: 'Nueva operación' }).click()
      await page.waitForTimeout(500)
      await page.getByRole('textbox', { name: 'Reserva' }).fill(reservaId)
      await page.getByRole('button', { name: 'Liquidar cuenta' }).click()
      await page.waitForTimeout(2000)
      const conf = await confirmacion(page)
      if (!conf || !conf.includes('liquidada')) throw new Error(`sin liquidación: ${conf}`)
      const inv = await api('GET', '/hotel/habitaciones', { cookie: cookieAdmin })
      const hab101 = inv.datos.habitaciones.find((h) => h.habitacion_id === HAB_A)
      if (hab101.estado_preparacion !== 'sucia' || hab101.limpieza_pendiente !== true) throw new Error(`tras salida: ${JSON.stringify(hab101)}`)
      await evidencia(page, 'sal-02-liquidada')
      return `${conf}; HAB-101 sucia con tarea`
    })
    await page.close()
  }

  // ===== L. Caja del día =====
  await caso('CAJ-01', '/hotel/caja', 'recepción no lee la caja', 'recepcion', '403 en la API', async () => {
    const r = await api('GET', `/hotel/caja?fecha=${iso(HOY)}`, { cookie: cookieRecepcion })
    if (r.estado !== 403) throw new Error(`${r.estado}`)
    return '403'
  })
  await caso('CAJ-02', '/hotel/caja', 'caja ve los pagos del día', 'caja', '200 con total y pagos', async () => {
    const r = await api('GET', `/hotel/caja?fecha=${iso(HOY)}`, { cookie: cookieCaja })
    if (r.estado !== 200 || r.datos.total_clp <= 0) throw new Error(`${r.estado} total=${r.datos.total_clp}`)
    return `total $${r.datos.total_clp} en ${r.datos.pagos.length} pago(s)`
  })

  // ===== M. Usuarios =====
  let idRecepcion
  {
    const ctx = await contextoRol('admin')
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await caso('USR-01', '/hotel/usuarios', 'alta y listado con «Usar id»', 'administrador', 'usuario creado y listado', async () => {
      await page.goto(`${FRONT}/hotel/usuarios`)
      await page.waitForTimeout(1800)
      await page.getByRole('textbox', { name: 'Nombre' }).fill(`recepcion_tmp_${RUN}`)
      await page.getByRole('textbox', { name: 'Clave', exact: true }).fill('TmpRecep99')
      await page.getByRole('button', { name: 'Crear usuario' }).click()
      await page.waitForTimeout(2000)
      const filas = await page.evaluate(() => [...document.querySelectorAll('.usuario-fila')].map((f) => f.innerText))
      if (!filas.some((f) => f.includes(`recepcion_tmp_${RUN}`))) throw new Error('no listado tras el alta')
      await evidencia(page, 'usr-01-listado')
      return 'creado y listado'
    })
    await caso('USR-02', '/hotel/usuarios', 'revocación cierra la sesión del otro', 'administrador', 'la sesión revocada pasa a 401', async () => {
      const r = await api('GET', '/usuarios', { cookie: cookieAdmin })
      idRecepcion = r.datos.usuarios.find((u) => u.nombre === `recepcion_tmp_${RUN}`).id
      const sesionTmp = await loginApi(`recepcion_tmp_${RUN}`, 'TmpRecep99')
      const viva = await api('GET', '/sesion', { cookie: sesionTmp })
      if (viva.estado !== 200) throw new Error('la sesión nueva no está viva')
      await api('POST', `/usuarios/${idRecepcion}/revocacion`, { cookie: cookieAdmin, clave: K('e2e-revoc'), cuerpo: {} })
      const muerta = await api('GET', '/sesion', { cookie: sesionTmp })
      if (muerta.estado !== 401) throw new Error(`tras revocar: ${muerta.estado}`)
      return 'sesión revocada → 401'
    })
    await caso('USR-03', '/hotel/usuarios', 'baja impide el login', 'administrador', 'activo=false; login 401', async () => {
      await api('POST', `/usuarios/${idRecepcion}/baja`, { cookie: cookieAdmin, clave: K('e2e-baja'), cuerpo: {} })
      const r = await api('POST', '/sesion', { cuerpo: { usuario: `recepcion_tmp_${RUN}`, clave: 'TmpRecep99' } })
      if (r.estado !== 401) throw new Error(`login tras baja: ${r.estado}`)
      return 'login rechazado tras la baja'
    })
    await page.close()
  }
  await caso('USR-04', '/hotel/usuarios', 'recepción no gestiona usuarios', 'recepcion', '403 en la API; la UI avisa «solo administrador»', async () => {
    const r = await api('GET', '/usuarios', { cookie: cookieRecepcion })
    if (r.estado !== 403) throw new Error(`${r.estado}`)
    const ctx = await contextoRol('recepcion')
    const page = await ctx.newPage()
    await loginUi(page, 'recepcion_e2e', 'RecepE2e123')
    await page.goto(`${FRONT}/hotel/usuarios`)
    await page.waitForTimeout(1500)
    const texto = await textoPrincipal(page)
    await page.close()
    if (!texto.includes('solo para administrador')) throw new Error(`texto: ${texto.slice(0, 140)}`)
    return 'UI y API rechazan'
  })

  // ===== N. Idempotencia (navegador) =====
  await caso('IDE-01', '/hotel/reserva', 'la clave se muestra antes del envío y rota tras el 2xx', 'recepcion', 'clave visible; tras confirmar, otra distinta', async () => {
    const ctx = await contextoRol('recepcion')
    const page = await ctx.newPage()
    await loginUi(page, 'recepcion_e2e', 'RecepE2e123')
    await page.goto(`${FRONT}/hotel/reserva`)
    await page.waitForTimeout(1500)
    const claveAntes = await page.evaluate(() => document.querySelector('.nota-clave code')?.textContent)
    if (!claveAntes) throw new Error('clave no visible antes del envío')
    await page.getByRole('textbox', { name: 'Habitación' }).fill(HAB_C)
    await page.getByRole('textbox', { name: 'Desde' }).fill(EN_40_DIAS)
    const hasta = sumarDias(new Date(HOY), 42)
    await page.getByRole('textbox', { name: 'Hasta' }).fill(hasta)
    await page.getByRole('textbox', { name: 'Huésped' }).fill('Idempotencia E2E')
    await page.getByRole('button', { name: 'Confirmar reserva' }).click()
    await page.waitForTimeout(2000)
    const conf = await confirmacion(page)
    if (!conf) throw new Error('no confirmó')
    const claveDespues = await page.evaluate(() => document.querySelector('.nota-clave code')?.textContent)
    await page.close()
    if (claveDespues === claveAntes) throw new Error('la clave no rotó tras el 2xx')
    return 'visible y rotada'
  })

  // ===== N-bis. Doble factor (TOTP) completo en navegador =====
  {
    const nombre2fa = `recepcion_2fa_${RUN}`
    await api('POST', '/usuarios', { cookie: cookieAdmin, clave: K('2fa-alta'), cuerpo: { nombre: nombre2fa, rol: 'recepcion', clave: 'Clave2fa123' } })
    const ctx = await contextoRol('2fa')
    const page = await ctx.newPage()
    await caso('TFA-01', '/cuenta', 'alta del segundo factor, login con TOTP y baja con reautenticación', 'recepcion', 'secreto mostrado, activación con código, login exigiendo totp; desactivar exige la clave actual (SEC-A02)', async () => {
      await loginUi(page, nombre2fa, 'Clave2fa123')
      await page.goto(`${FRONT}/cuenta`)
      await page.waitForTimeout(1500)
      await page.getByRole('button', { name: 'Activar doble factor' }).click()
      await page.waitForTimeout(1800)
      const secreto = await page.evaluate(() => {
        const texto = document.querySelector('main')?.innerText || ''
        const m = texto.match(/Clave manual \(base32\):\s*([A-Z2-7]+)/)
        return m ? m[1] : null
      })
      if (!secreto) throw new Error('no se mostró el secreto base32')
      await page.getByRole('textbox', { name: /Código de confirmación/i }).fill(totp(secreto))
      await page.getByRole('button', { name: 'Confirmar y activar' }).click()
      await page.waitForTimeout(2000)
      const texto = await textoPrincipal(page)
      if (!texto.includes('activado')) throw new Error(`no quedó activado: ${texto.slice(0, 160)}`)
      await evidencia(page, 'tfa-01-activado')
      // cerrar sesión y entrar de nuevo: ahora exige el código del autenticador
      await page.getByRole('button', { name: 'Cerrar sesión' }).click()
      await page.waitForTimeout(1200)
      await page.goto(`${FRONT}/login`)
      await page.waitForTimeout(1200)
      await page.getByRole('textbox', { name: 'Usuario' }).fill(nombre2fa)
      await page.getByRole('textbox', { name: 'Clave' }).fill('Clave2fa123')
      await page.getByRole('button', { name: 'Entrar' }).click()
      await page.waitForTimeout(1800)
      if (!page.url().includes('/login')) throw new Error(`entró sin 2FA: ${page.url()}`)
      await page.getByRole('textbox', { name: /Código del autenticador/i }).fill(totp(secreto))
      await page.getByRole('button', { name: 'Entrar' }).click()
      await page.waitForTimeout(2000)
      if (page.url().includes('/login')) throw new Error('no entró con el código TOTP')
      // SEC-A02 (#327): desactivar el factor exige la clave actual
      // (reautenticación). Sin clave el front lo exige; con clave baja.
      await page.goto(`${FRONT}/cuenta`)
      await page.waitForTimeout(1500)
      page.on('dialog', (d) => d.accept())
      await page.getByRole('button', { name: 'Desactivar doble factor' }).click()
      await page.waitForTimeout(800)
      let textoCuenta = await textoPrincipal(page)
      if (!textoCuenta.includes('Escribe tu clave actual')) throw new Error('desactivó sin pedir la clave')
      await page.getByLabel(/Tu clave actual/).fill('Clave2fa123')
      await page.getByRole('button', { name: 'Desactivar doble factor' }).click()
      await page.waitForTimeout(1500)
      textoCuenta = await textoPrincipal(page)
      if (!textoCuenta.includes('desactivado')) throw new Error(`no se desactivó: ${textoCuenta.slice(0, 160)}`)
      return '2FA activado, login con código y baja exigiendo la clave'
    })
    await page.close()
  }

  // ===== P. Acciones ocultas según rol (spec-api-v1) =====
  await caso('ROL-01', '/hotel/caja', 'recepción no ve la caja del día', 'recepcion', 'aviso de rol, sin formulario', async () => {
    const ctx = await contextoRol('recepcion')
    const page = await ctx.newPage()
    await loginUi(page, 'recepcion_e2e', 'RecepE2e123')
    await page.goto(`${FRONT}/hotel/caja`)
    await page.waitForTimeout(1800)
    const texto = await textoPrincipal(page)
    await page.close()
    if (!texto.includes('solo para caja o administrador')) throw new Error(`texto: ${texto.slice(0, 140)}`)
    if (texto.includes('Ver caja')) throw new Error('muestra el formulario a recepción')
    return 'formulario oculto y aviso de rol'
  })
  await caso('ROL-02', '/hotel/estadia', 'caja no ve la cancelación de reserva', 'caja', 'sin sección «Cancelar reserva»', async () => {
    const ctx = await contextoRol('caja')
    const page = await ctx.newPage()
    await loginUi(page, 'caja_e2e', 'CajaE2e1234')
    await page.goto(`${FRONT}/hotel/estadia`)
    await page.waitForTimeout(1800)
    const texto = await textoPrincipal(page)
    await page.close()
    if (texto.includes('Cancelar reserva')) throw new Error('caja ve la cancelación')
    if (!texto.includes('Check-in')) throw new Error('caja debería ver el check-in')
    return 'cancelación oculta para caja; check-in visible'
  })

  // ===== Q-bis. Renovación de clave tras 4xx (V1-ISSUE-13) =====
  await caso('IDE-01', '/hotel/habitaciones', 'tras un 4xx la clave se renueva: corregir y reintentar ejecuta', 'administrador', '409 «ya existe» → cambiar id → reintento 201 sin recargar', async () => {
    const ctx = await contextoRol('admin')
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await page.goto(`${FRONT}/hotel/habitaciones`)
    await page.waitForTimeout(1800)
    await page.getByRole('textbox', { name: 'Habitación' }).first().fill(HAB_A) // ya existe → 409
    await page.getByRole('button', { name: 'Dar de alta' }).click()
    await page.waitForTimeout(1600)
    const alerta1 = await alerta(page)
    if (!alerta1 || !alerta1.includes('ya existe')) throw new Error(`primer intento: ${alerta1}`)
    await page.getByRole('textbox', { name: 'Habitación' }).first().fill(`HAB-${RUN}-NUEVA`)
    await page.getByRole('button', { name: 'Dar de alta' }).click()
    await page.waitForTimeout(1800)
    const conf = await confirmacion(page)
    await ctx.close()
    if (!conf) throw new Error('el reintento corregido no se confirmó (clave quemada)')
    return '409 → corregir → 201 sin recargar'
  })

  await caso('SES-02', '/hotel/panel', 'una sola petición GET /sesion por carga de página', 'administrador', 'exactamente 1 por carga (V1-ISSUE-37: antes 2–3)', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT })
    const page = await ctx.newPage()
    let sesiones = 0
    page.on('request', (r) => { if (r.url().endsWith('/sesion') && r.method() === 'GET') sesiones += 1 })
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    sesiones = 0 // contar solo la carga completa del panel
    await page.goto(`${FRONT}/hotel/panel`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(1200)
    await ctx.close()
    if (sesiones !== 1) throw new Error(`GET /sesion = ${sesiones}, esperado 1 por carga`)
    return `GET /sesion = ${sesiones} en la carga del panel`
  })

  // ===== R. Precarga entre pantallas y reflujo de fichas (V1-ISSUE-35/34) =====
  await caso('PRE-01', '/hotel/oferta', 'oferta → reserva → detalle → pago con campos precargados', 'recepcion', 'sin copiar/pegar IDs: la query precarga y el «Siguiente paso» también', async () => {
    const ctx = await contextoRol('recepcion')
    const page = await ctx.newPage()
    await loginUi(page, 'recepcion_e2e', 'RecepE2e123')
    await page.goto(`${FRONT}/hotel/oferta`)
    await page.waitForTimeout(1800)
    await page.getByRole('button', { name: 'Consultar oferta' }).click()
    await page.waitForTimeout(2000)
    const reservar = page.getByRole('link', { name: 'Reservar estas noches' }).first()
    if ((await reservar.count()) === 0) throw new Error('la oferta no ofrece «Reservar estas noches»')
    await reservar.click()
    await page.waitForTimeout(1800)
    const pre = await page.evaluate(() => ({
      url: location.pathname + location.search,
      habitacion: document.querySelectorAll('input')[0]?.value,
      desde: document.querySelectorAll('input')[1]?.value,
    }))
    if (!pre.url.includes('/hotel/reserva') || !pre.habitacion || !pre.desde) throw new Error(`no precargó: ${JSON.stringify(pre)}`)
    await page.getByRole('textbox', { name: 'Huésped' }).fill('Flujo Precargado')
    await page.getByRole('button', { name: 'Confirmar reserva' }).click()
    await page.waitForTimeout(2000)
    const rid = JSON.parse(await page.evaluate(() => document.querySelector('.json-panel')?.textContent || '{}')).reserva_id
    if (!rid) throw new Error('no se confirmó la reserva precargada')
    await page.goto(`${FRONT}/hotel/reservas/${rid}`)
    await page.waitForTimeout(1800)
    const enlacePago = page.getByRole('link', { name: 'Registrar pago' }).first()
    if ((await enlacePago.count()) === 0) throw new Error('sin «Siguiente paso» al pago')
    const href = await enlacePago.getAttribute('href')
    if (!href.includes(`reserva_id=${rid}`)) throw new Error(`el enlace no lleva la reserva: ${href}`)
    await enlacePago.click()
    await page.waitForTimeout(1800)
    const reservaPre = await page.evaluate(() => [...document.querySelectorAll('input')].map((i) => i.value).find((v) => v.startsWith('RSV-')))
    await ctx.close()
    if (reservaPre !== rid) throw new Error(`el pago no nació con la reserva precargada: ${reservaPre}`)
    return `flujo completo precargado (${rid})`
  })
  await caso('MOV-02', '/hotel/habitaciones/[id]', 'fichas y oferta sin desborde de documento a 320px', 'administrador', 'scrollWidth ≤ innerWidth en ficha, detalle y oferta', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 320, height: 568 } })
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    const rutas = [`/hotel/habitaciones/${HAB_A}`, '/hotel/oferta']
    const rid = (await api('GET', '/hotel/reservas', { cookie: cookieAdmin })).datos.reservas[0]?.reserva_id
    if (rid) rutas.push(`/hotel/reservas/${rid}`)
    const malas = []
    for (const ruta of rutas) {
      await page.goto(`${FRONT}${ruta}`)
      await page.waitForTimeout(1800)
      const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }))
      if (m.sw > m.iw) malas.push(`${ruta}: ${m.sw}>${m.iw}`)
    }
    await ctx.close()
    if (malas.length) throw new Error(malas.join(' | '))
    return `${rutas.length} rutas sin desborde a 320px`
  })

  // ===== Q. Navegación móvil y accesibilidad responsive (issues #276–#280) =====
  await caso('MUX-01', '/hotel/panel', 'menú móvil: panel con todas las opciones, activo único y visible', 'administrador', 'menú abre, «Ocupación» navega y cierra, un solo activo', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 375, height: 667 } })
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await page.goto(`${FRONT}/hotel/panel`)
    await page.waitForTimeout(2000)
    const salirOculto = await page.evaluate(() => {
      const pie = document.querySelector('.barra-pie button')
      return pie ? pie.offsetParent === null : true
    })
    await page.getByRole('button', { name: 'Menú' }).click()
    await page.waitForTimeout(700)
    const enPanel = await page.evaluate(() => ({
      enlaces: [...document.querySelectorAll('#menu-movil .nav-enlace')].map((e) => e.textContent.trim()),
      salirEnMenu: !!document.querySelector('#menu-movil .boton-salir'),
    }))
    await evidencia(page, 'mux-01-menu-abierto')
    await page.getByRole('link', { name: 'Ocupación' }).click()
    await page.waitForTimeout(1800)
    const despues = await page.evaluate(() => ({
      url: location.pathname,
      menuCerrado: !document.querySelector('#menu-movil')?.classList.contains('abierto'),
    }))
    await page.getByRole('button', { name: 'Menú' }).click()
    await page.waitForTimeout(500)
    const activosVisibles = await page.evaluate(() => document.querySelectorAll('#menu-movil .activo').length)
    await ctx.close()
    if (!enPanel.salirEnMenu) throw new Error('sin «Cerrar sesión» en el menú móvil')
    if (!enPanel.enlaces.includes('Usuarios') || !enPanel.enlaces.includes('Ocupación')) throw new Error(`faltan opciones: ${enPanel.enlaces.join(',')}`)
    if (despues.url !== '/hotel/ocupacion' || !despues.menuCerrado) throw new Error(`navegación/cierre falló: ${JSON.stringify(despues)}`)
    if (activosVisibles !== 1) throw new Error(`activos = ${activosVisibles}, esperado 1`)
    if (!salirOculto) throw new Error('el pie del aside sigue visible (modo móvil no aplicado)')
    return `${enPanel.enlaces.length} opciones; activo único; cierra al navegar`
  })
  await caso('MUX-02', '/hotel/panel', 'cerrar sesión operativo en móvil (375px)', 'administrador', 'botón visible en el menú; DELETE /sesion y vuelve a /login', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 375, height: 667 } })
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await page.getByRole('button', { name: 'Menú' }).click()
    await page.waitForTimeout(600)
    const objetivo = await page.evaluate(() => {
      const b = document.querySelector('#menu-movil .boton-salir')
      const r = b?.getBoundingClientRect()
      return { existe: !!b, alto: Math.round(r?.height || 0) }
    })
    if (!objetivo.existe || objetivo.alto < 44) throw new Error(`objetivo: ${JSON.stringify(objetivo)}`)
    await page.getByRole('button', { name: 'Cerrar sesión' }).click()
    await page.waitForTimeout(1800)
    const url = page.url()
    await ctx.close()
    if (!url.includes('/login')) throw new Error(`no volvió a login: ${url}`)
    return 'sesión cerrada desde móvil, redirección a /login'
  })
  await caso('MUX-03', '/hotel/panel', 'reflujo a 320px sin scroll horizontal de documento', 'administrador', 'scrollWidth <= innerWidth', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 320, height: 568 } })
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await page.goto(`${FRONT}/hotel/panel`)
    await page.waitForTimeout(2200)
    const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }))
    await evidencia(page, 'mux-03-panel-320')
    await ctx.close()
    if (m.sw > m.iw) throw new Error(`desborde: scrollWidth ${m.sw} > ${m.iw}`)
    return `scrollWidth ${m.sw} ≤ ${m.iw}`
  })
  await caso('MUX-04', '/hotel/habitaciones', 'contraste de la nota técnica ≥ 4.5:1', 'administrador', 'ratio AA para texto normal', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await page.goto(`${FRONT}/hotel/habitaciones`)
    await page.waitForTimeout(1800)
    const ratio = await page.evaluate(() => {
      const el = document.querySelector('.nota-tecnica')
      if (!el) return null
      const cs = getComputedStyle(el)
      const f = (c) => {
        const m = c.match(/[\d.]+/g).map(Number)
        return m.length >= 3 ? m.slice(0, 3) : [0, 0, 0]
      }
      const fg = f(cs.color)
      const bg = f(cs.backgroundColor.includes('rgba') && cs.backgroundColor.match(/[\d.]+/g)[3] === '0' ? 'rgb(251,247,240)' : cs.backgroundColor)
      const lum = (rgb) => {
        const ch = rgb.map((v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4 })
        return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]
      }
      const [a, b] = [lum(fg), lum(bg)].sort((x, y) => y - x)
      return (a + 0.05) / (b + 0.05)
    })
    await ctx.close()
    if (!ratio || ratio < 4.5) throw new Error(`ratio ${ratio}`)
    return `ratio ${ratio.toFixed(2)}:1`
  })
  await caso('MUX-05', '/hotel/reserva', 'zoom 200% sin scroll horizontal (formulario)', 'administrador', 'documento sin desborde con texto ampliado', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 390, height: 844 } })
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await page.goto(`${FRONT}/hotel/reserva`)
    await page.waitForTimeout(1800)
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
    await page.waitForTimeout(400)
    const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }))
    await ctx.close()
    if (m.sw > m.iw) throw new Error(`desborde con zoom: ${m.sw} > ${m.iw}`)
    return `zoom 200%: scrollWidth ${m.sw} ≤ ${m.iw}`
  })

  // ===== AUT. Guardia de sesión en el Lienzo (V1-ISSUE-27) =====
  await caso('AUT-01', '/hotel/reserva', 'visitante sin sesión: solo la pantalla de acceso, jamás el menú interno', 'anonimo', 'login visible y menú ausente; al entrar aparece la página en la misma ruta', async () => {
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    await page.goto(`${FRONT}/hotel/reserva`)
    await page.waitForTimeout(1800)
    const menuInterno = await page.getByRole('link', { name: 'Panel' }).count()
    const tarjetaLogin = await page.locator('.login-tarjeta').count()
    const texto = await textoPrincipal(page)
    if (menuInterno !== 0) throw new Error('menú interno visible sin sesión')
    if (tarjetaLogin === 0) throw new Error('no apareció la pantalla de acceso')
    if (texto.includes('Sesión cerrada') || texto.includes('Operando como'))
      throw new Error('texto interno filtrado en la pantalla de acceso')
    const captura = await evidencia(page, 'aut-01-sin-sesion')
    await page.getByRole('textbox', { name: 'Usuario' }).fill('admin_e2e')
    await page.getByRole('textbox', { name: 'Clave' }).fill(process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await page.getByRole('button', { name: 'Entrar' }).click()
    await page.waitForTimeout(2200)
    const ruta = new URL(page.url()).pathname
    const formularioReserva = await page.getByRole('textbox', { name: 'Huésped' }).count()
    await ctx.close()
    if (ruta !== '/hotel/reserva') throw new Error(`ruta tras entrar: ${ruta}`)
    if (formularioReserva === 0) throw new Error('no apareció el formulario de reserva')
    return `solo login + vuelta en misma ruta (${captura})`
  })

  // ===== O. Cierre de sesión =====
  // Liberar los contextos acumulados: Chromium agota memoria con ~10
  // contextos abiertos y el último caso muere («browser has been closed»).
  for (const nombre of Object.keys(contextos)) {
    await contextos[nombre].close()
    delete contextos[nombre]
  }
  await caso('SES-01', '/salida-de-sesion', 'cerrar sesión deja el panel fuera', 'administrador', 'la ruta protegida muestra solo el login, sin menú interno', async () => {
    const ctx = await contextoRol('admin')
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await page.getByRole('button', { name: 'Cerrar sesión' }).click()
    await page.waitForTimeout(1500)
    await page.goto(`${FRONT}/hotel/oferta`)
    await page.waitForTimeout(1800)
    const menuInterno = await page.getByRole('link', { name: 'Panel' }).count()
    const tarjetaLogin = await page.locator('.login-tarjeta').count()
    const texto = await textoPrincipal(page)
    await page.close()
    if (menuInterno !== 0) throw new Error('el menú interno quedó visible tras cerrar sesión')
    if (tarjetaLogin === 0) throw new Error('no se mostró la pantalla de login')
    if (texto.includes('Sesión cerrada')) throw new Error('texto «Sesión cerrada» aún visible')
    return 'solo login tras cerrar sesión, sin menú interno'
  })

  // ===== CLV. Cambio de clave propia del administrador (spec-api-v1 «Gestión de usuarios») =====
  await caso('CLV-01', '/cuenta', 'el administrador cambia su propia clave desde «Mi cuenta»', 'administrador', 'formulario visible y 200; la otra sesión queda 401, la actual sigue, la vieja clave deja de servir y la nueva abre sesión', async () => {
    const sesionAdmin = await api('POST', '/sesion', { cuerpo: { usuario: 'admin_e2e', clave: process.env.ADMIN_CLAVE_E2E || 'E2eClave123' } })
    if (sesionAdmin.estado !== 200) throw new Error(`login admin: ${sesionAdmin.estado}`)
    const nombre = `admin_clv_${RUN}`
    const claveVieja = 'ClaveVieja123'
    const claveNueva = 'ClaveNueva456'
    const alta = await api('POST', '/usuarios', {
      cuerpo: { nombre, rol: 'administrador', clave: claveVieja }, clave: K('clv-alta'), cookie: sesionAdmin.cookie,
    })
    if (alta.estado !== 201) throw new Error(`alta admin dedicado: ${alta.estado} ${JSON.stringify(alta.datos)}`)
    const otra = await api('POST', '/sesion', { cuerpo: { usuario: nombre, clave: claveVieja } })
    if (otra.estado !== 200) throw new Error(`segunda sesión: ${otra.estado}`)
    const ctx = await navegador.newContext({ baseURL: FRONT, viewport: { width: 1280, height: 720 } })
    const page = await ctx.newPage()
    await loginUi(page, nombre, claveVieja)
    await page.goto(`${FRONT}/cuenta`)
    await page.waitForTimeout(1800)
    if ((await page.getByRole('textbox', { name: 'Clave nueva' }).count()) === 0)
      throw new Error('sin formulario de cambio de clave en /cuenta')
    await page.getByRole('textbox', { name: 'Clave nueva' }).fill(claveNueva)
    await page.getByRole('button', { name: 'Cambiar clave' }).click()
    await page.waitForSelector('[role=status]', { timeout: 8000 })
    const otraAhora = await api('GET', '/sesion', { cookie: otra.cookie })
    await page.goto(`${FRONT}/hotel/usuarios`)
    await page.waitForTimeout(1500)
    const sigue = await page.getByText(nombre).count()
    await page.getByRole('button', { name: 'Cerrar sesión' }).click()
    await page.waitForTimeout(1500)
    await loginUi(page, nombre, claveVieja)
    const alertaVieja = await page.locator('.login-tarjeta [role=alert]').count()
    await loginUi(page, nombre, claveNueva)
    const ruta = new URL(page.url()).pathname
    await ctx.close()
    if (otraAhora.estado !== 401) throw new Error(`la otra sesión siguió viva: ${otraAhora.estado}`)
    if (sigue === 0) throw new Error('la sesión vigente no siguió activa tras el cambio')
    if (alertaVieja === 0) throw new Error('la vieja clave siguió sirviendo')
    if (ruta !== '/') throw new Error(`con la clave nueva no abrió sesión: ${ruta}`)
    return 'formulario → 200 → otra sesión 401 → sesión actual viva → vieja rechazada → nueva abre sesión'
  })
} finally {
  await navegador.close()
}

// ===== Resumen =====
const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
const fallidos = resultados.filter((r) => r.estado === 'FALLIDO')
console.log(`\n${aprobados}/${resultados.length} APROBADOS, ${fallidos.length} FALLIDOS`)
writeFileSync(join(dirname(fileURLToPath(import.meta.url)), 'e2e-resultados.json'), JSON.stringify(resultados, null, 2))
if (fallidos.length > 0) process.exit(1)
