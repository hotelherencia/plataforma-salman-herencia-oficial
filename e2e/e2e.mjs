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
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONT = process.env.FRONT_URL || 'http://127.0.0.1:3000'
const API = process.env.API_URL || 'http://127.0.0.1:8080'
const HOY = new Date()
const EN_1_DIA = sumarDias(HOY, 1)
const EN_30_DIAS = sumarDias(HOY, 30)
const EN_33_DIAS = sumarDias(HOY, 33)
const EN_40_DIAS = sumarDias(HOY, 40)

function sumarDias(fecha, dias) {
  const d = new Date(fecha)
  d.setDate(d.getDate() + dias)
  return d.toISOString().slice(0, 10)
}

const RUN = Date.now().toString(36)
const K = (nombre) => `${nombre}-${RUN}`

function iso(fecha) {
  return fecha.toISOString().slice(0, 10)
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
    await caso('ACC-03', '/hotel/oferta', 'ruta hotel sin sesión pide login', 'anónimo', 'mensaje «Sesión cerrada», sin datos', async () => {
      const ctx2 = await navegador.newContext({ baseURL: FRONT })
      const anonima = await ctx2.newPage()
      await anonima.goto(`${FRONT}/hotel/oferta`)
      await anonima.waitForTimeout(1500)
      const texto = await textoPrincipal(anonima)
      if (!texto.includes('Sesión cerrada')) throw new Error(`texto: ${texto.slice(0, 120)}`)
      await ctx2.close()
      return 'pide inicio de sesión'
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
      await page.getByRole('textbox', { name: 'Habitación' }).first().fill('HAB-201')
      await page.getByRole('button', { name: 'Guardar habitación' }).click()
      await page.waitForTimeout(1800)
      const filas = await page.evaluate(() => [...document.querySelectorAll('.inventario-fila')].map((f) => f.innerText))
      if (!filas.some((f) => f.includes('HAB-201'))) throw new Error('HAB-201 no aparece en el inventario')
      await evidencia(page, 'hab-02-alta')
      return 'HAB-201 listada tras el alta'
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
      await page.getByRole('textbox', { name: 'Desde' }).fill(EN_30_DIAS)
      await page.getByRole('textbox', { name: 'Hasta' }).fill(EN_33_DIAS)
      await page.getByRole('textbox', { name: 'Huésped' }).fill('Huésped Sintético')
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
      await page.getByRole('textbox', { name: 'Habitación' }).fill('HAB-201')
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
        cuerpo: { habitacion_id: HAB_A, inicio: EN_30_DIAS, fin: EN_33_DIAS, huesped: { nombre: 'Segunda Carrera' } },
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
    if (docRecep === undefined) throw new Error('recepcion no recibió documento')
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
    const r = await api('POST', `/hotel/reservas/${reservaId}/entrada`, { cookie: cookieRecepcion, clave: K('e2e-ent-1'), cuerpo: {} })
    if (r.estado !== 200) throw new Error(`${r.estado} ${JSON.stringify(r.datos)}`)
    const inv = await api('GET', '/hotel/habitaciones', { cookie: cookieRecepcion })
    const hab101 = inv.datos.habitaciones.find((h) => h.habitacion_id === HAB_A)
    if (hab101.estado_operativo !== 'ocupada') throw new Error(`estado: ${hab101.estado_operativo}`)
    return 'HAB-101 ocupada'
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
      const noches = (new Date(EN_33_DIAS) - new Date(EN_30_DIAS)) / 86400000
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

  // ===== O. Cierre de sesión =====
  await caso('SES-01', '/salida-de-sesion', 'cerrar sesión deja el panel fuera', 'administrador', 'la siguiente lectura pide login', async () => {
    const ctx = await contextoRol('admin')
    const page = await ctx.newPage()
    await loginUi(page, 'admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123')
    await page.getByRole('button', { name: 'Cerrar sesión' }).click()
    await page.waitForTimeout(1500)
    await page.goto(`${FRONT}/hotel/oferta`)
    await page.waitForTimeout(1500)
    const texto = await textoPrincipal(page)
    await page.close()
    if (!texto.includes('Sesión cerrada')) throw new Error(`texto: ${texto.slice(0, 120)}`)
    return 'sesión cerrada, ruta pide login'
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
