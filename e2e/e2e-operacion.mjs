/**
 * E2E de la operación del hotel — mantenedor de habitaciones, consulta de
 * reservas, ocupación e indicadores (spec-hotel-operacion-v1 §6, 2026-11-03).
 *
 * Complementa a e2e.mjs (suite de aceptación V1) sin modificarla: mismos
 * requisitos y misma forma de registrar resultados. Navegador real
 * (Chromium) contra front y API locales, datos 100 % sintéticos, ids y
 * claves de idempotencia únicos por corrida (re-ejecutable sin resetear).
 * Cada mutación se verifica releyendo el estado desde la API.
 *
 * Uso: cd e2e && FRONT_URL=http://127.0.0.1:3000 API_URL=http://127.0.0.1:8080 node e2e-operacion.mjs
 * Salida: consola + e2e-operacion-resultados.json; capturas en
 * ../capturas/e2e-AAAA-MM-DD/op-NN-*.png.
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
  const archivo = join(carpeta, `op-${String(evidenciaN).padStart(2, '0')}-${nombre}.png`)
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

const texto = (page) => page.evaluate(() => document.querySelector('main')?.innerText || '')
const alerta = (page) => page.evaluate(() => document.querySelector('[role=alert]')?.textContent || null)
const confirmacion = (page) => page.evaluate(() => document.querySelector('.operacion-confirmada')?.textContent || null)

async function ir(page, ruta) {
  await page.goto(`${FRONT}${ruta}`)
  await page.waitForTimeout(1600)
}

const navegador = await chromium.launch()
async function paginaDe(credenciales) {
  const ctx = await navegador.newContext({ baseURL: FRONT })
  const page = await ctx.newPage()
  await loginUi(page, credenciales)
  return page
}

try {
  // ===== Semilla sintética =====
  const cAdmin = await loginApi(...ADMIN)
  const RECEPCION = [`recepcion_op_${RUN}`, 'RecepOp1234']
  const CAJA = [`caja_op_${RUN}`, 'CajaOp12345']
  await api('POST', '/usuarios', { cookie: cAdmin, clave: K('u-rec'), cuerpo: { nombre: RECEPCION[0], rol: 'recepcion', clave: RECEPCION[1] } })
  await api('POST', '/usuarios', { cookie: cAdmin, clave: K('u-caj'), cuerpo: { nombre: CAJA[0], rol: 'caja', clave: CAJA[1] } })
  const cRecepcion = await loginApi(...RECEPCION)
  const cCaja = await loginApi(...CAJA)

  const indicadorBase = await api('GET', '/hotel/indicadores', { cookie: cAdmin })
  const HOY = indicadorBase.datos.fecha_corte
  carpeta = join(AQUI, '..', 'capturas', `e2e-${HOY}`)
  mkdirSync(carpeta, { recursive: true })
  const D = (n) => sumarDias(HOY, n)

  const HAB_M = `HAB-${RUN}-M` // mantenedor: edición, tarifa, retiro
  const HAB_O = `HAB-${RUN}-O` // ocupación e indicadores
  for (const [id, tipo, cap, tarifa] of [[HAB_M, 'doble', 2, 50000], [HAB_O, 'doble', 2, 40000]]) {
    await api('PUT', `/hotel/habitaciones/${id}`, { cookie: cAdmin, clave: K(`alta-${id}`), cuerpo: { tipo, capacidad: cap }, cabeceras: { 'If-None-Match': '*' } })
    await api('PUT', '/hotel/tarifas', { cookie: cAdmin, clave: K(`tar-${id}`), cuerpo: { habitacion_id: id, fecha_desde: D(-60), fecha_hasta: D(365), tarifa_noche_clp: tarifa } })
  }
  const reservar = async (hid, inicio, fin, nombre, cookie = cRecepcion) => {
    const r = await api('POST', '/hotel/reservas', { cookie, clave: K(`rsv-${hid}-${inicio}`), cuerpo: { habitacion_id: hid, inicio, fin, huesped: { nombre, documento: '22.222.222-2' } } })
    if (r.estado !== 201) throw new Error(`reserva ${hid} ${inicio}: ${r.estado} ${JSON.stringify(r.datos)}`)
    return r.datos
  }
  const RES_M = await reservar(HAB_M, D(20), D(23), 'Huésped Mantenedor')
  const RES_O1 = await reservar(HAB_O, D(30), D(33), 'Huésped Ocupación')
  const RES_O2 = await reservar(HAB_O, D(36), D(38), 'Huésped Cancelado')
  await api('POST', `/hotel/reservas/${RES_O2.reserva_id}/cancelacion`, { cookie: cRecepcion, clave: K('can-o2'), cuerpo: {} })

  const admin = await paginaDe(ADMIN)

  // ===== NAV: menú =====
  await caso('NAV-01', '/hotel/panel', 'el menú lleva a Panel y Ocupación; Hotel entra al panel', 'administrador', 'enlaces Panel y Ocupación; Hotel → /hotel/panel', async () => {
    await ir(admin, '/')
    await admin.getByRole('link', { name: 'Hotel', exact: true }).first().click()
    await admin.waitForTimeout(1600)
    esperar(admin.url().endsWith('/hotel/panel'), `Hotel llevó a ${admin.url()}`)
    const enlaces = await admin.evaluate(() => [...document.querySelectorAll('.nav a')].map((a) => a.textContent))
    esperar(enlaces.includes('Panel') && enlaces.includes('Ocupación'), `menú: ${enlaces.join(', ')}`)
    await admin.getByRole('link', { name: 'Ocupación', exact: true }).click()
    await admin.waitForTimeout(1600)
    esperar(admin.url().endsWith('/hotel/ocupacion'), admin.url())
    return 'Inicio → Hotel → Panel → Ocupación'
  })

  // ===== MAN: mantenedor de habitaciones =====
  await caso('MAN-01', '/hotel/habitaciones', 'alta duplicada no sobrescribe (If-None-Match)', 'administrador', 'alerta «ya existe»; tipo y capacidad intactos', async () => {
    await ir(admin, '/hotel/habitaciones')
    await admin.getByRole('textbox', { name: 'Habitación' }).first().fill(HAB_M)
    await admin.getByRole('textbox', { name: 'Tipo' }).fill('suite')
    await admin.getByRole('button', { name: 'Dar de alta' }).click()
    await admin.waitForTimeout(1500)
    const a = await alerta(admin)
    esperar(a && a.includes('ya existe'), `alerta: ${a}`)
    const ficha = await api('GET', `/hotel/habitaciones/${HAB_M}`, { cookie: cAdmin })
    esperar(ficha.datos.tipo === 'doble' && ficha.datos.capacidad === 2, JSON.stringify(ficha.datos).slice(0, 120))
    return a
  })

  await caso('MAN-02', '/hotel/habitaciones/[id]', 'abrir la ficha desde el inventario', 'administrador', 'ficha con datos, tarifas, reservas, tareas y auditoría', async () => {
    await ir(admin, '/hotel/habitaciones')
    await admin.locator('.inventario-fila', { hasText: HAB_M }).getByRole('link', { name: 'Ficha' }).click()
    await admin.waitForTimeout(1800)
    esperar(admin.url().endsWith(`/hotel/habitaciones/${HAB_M}`), admin.url())
    const t = await texto(admin)
    for (const seccion of ['Datos y estado actual', 'Editar datos', 'Registrar tarifa nueva', 'Retirar de operación', 'Historial de tarifas', 'Reservas de la habitación', 'Historial de cambios']) {
      esperar(t.includes(seccion), `falta sección «${seccion}»`)
    }
    esperar(t.includes(RES_M.reserva_id), 'la reserva previa no aparece en la ficha')
    await evidencia(admin, 'ficha-habitacion')
    return 'todas las secciones visibles con la reserva previa'
  })

  await caso('MAN-03', '/hotel/habitaciones/[id]', 'editar tipo y capacidad con reserva previa', 'administrador', 'cambio aplicado y auditado; reserva intacta', async () => {
    const antes = (await api('GET', `/hotel/reservas/${RES_M.reserva_id}`, { cookie: cAdmin })).datos
    await admin.getByRole('textbox', { name: 'Tipo' }).fill('suite')
    await admin.getByRole('spinbutton', { name: 'Capacidad' }).fill('3')
    await admin.getByRole('button', { name: 'Guardar cambios' }).click()
    await admin.waitForTimeout(1800)
    const conf = await confirmacion(admin)
    esperar(conf && conf.includes('tipo doble → suite') && conf.includes('capacidad 2 → 3'), `confirmación: ${conf}`)
    const ficha = (await api('GET', `/hotel/habitaciones/${HAB_M}`, { cookie: cAdmin })).datos
    esperar(ficha.tipo === 'suite' && ficha.capacidad === 3, 'no se persistió el cambio')
    esperar(ficha.auditoria.some((x) => x.resultado === 'editada tipo: doble→suite; capacidad: 2→3'), 'sin fila de auditoría')
    const despues = (await api('GET', `/hotel/reservas/${RES_M.reserva_id}`, { cookie: cAdmin })).datos
    for (const campo of ['inicio', 'fin', 'estado', 'tarifa_noche_aceptada_clp']) esperar(antes[campo] === despues[campo], `la reserva cambió ${campo}`)
    esperar(antes.cuenta.saldo_clp === despues.cuenta.saldo_clp, 'la cuenta de la reserva cambió')
    return conf
  })

  await caso('MAN-04', '/hotel/habitaciones/[id]', 'tarifa nueva cambia la venta y no la reserva', 'administrador', 'oferta a 70000; reserva sigue a 50000; historial con vigente', async () => {
    await admin.getByLabel('Desde', { exact: true }).fill(D(-60))
    await admin.getByLabel('Hasta (sin incluir)').fill(D(365))
    await admin.getByRole('spinbutton', { name: 'Tarifa por noche (CLP)' }).fill('70000')
    await admin.getByRole('button', { name: 'Guardar tarifa' }).click()
    await admin.waitForTimeout(1800)
    const conf = await confirmacion(admin)
    esperar(conf && conf.includes('70000'), `confirmación: ${conf}`)
    const oferta = await api('GET', `/hotel/oferta?inicio=${D(40)}&fin=${D(41)}&personas=1`, { cookie: cAdmin })
    const unidad = oferta.datos.oferta.find((u) => u.habitacion_id === HAB_M)
    esperar(unidad && unidad.tarifa_noche_clp === 70000, `oferta: ${JSON.stringify(unidad)}`)
    const reserva = (await api('GET', `/hotel/reservas/${RES_M.reserva_id}`, { cookie: cAdmin })).datos
    esperar(reserva.tarifa_noche_aceptada_clp === 50000 && reserva.cuenta.cargos_netos_clp === 150000, 'la reserva cambió de precio')
    const t = await texto(admin)
    esperar(t.includes('$70.000') && t.includes('vigente'), 'el historial no muestra la tarifa vigente')
    return 'venta nueva a $70.000; reserva previa a $50.000'
  })

  await caso('MAN-05', '/hotel/habitaciones/[id]', 'retiro bloqueado por reserva vigente', 'administrador', '409 con enlace a la reserva; la unidad sigue en servicio', async () => {
    const consola = []
    admin.on('console', (m) => { if (m.type() === 'error') consola.push(m.text().slice(0, 180)) })
    admin.on('requestfailed', (r) => consola.push('FAILED ' + r.url() + ' ' + (r.failure()?.errorText || '')))
    admin.on('response', (r) => { if (r.url().includes('/servicio')) consola.push('RESP ' + r.status() + ' ' + r.url()) })
    await admin.getByRole('textbox', { name: 'Motivo' }).fill('remodelación E2E')
    await admin.getByRole('button', { name: 'Retirar de operación' }).click()
    await admin.waitForTimeout(1600)
    const a = await alerta(admin)
    esperar(a && a.includes('reservas vigentes') && a.includes(RES_M.reserva_id), `alerta: ${a} | red: ${consola.join(' ;; ')}`)
    const ficha = (await api('GET', `/hotel/habitaciones/${HAB_M}`, { cookie: cAdmin })).datos
    esperar(ficha.en_servicio, 'quedó fuera de servicio pese a la reserva')
    await evidencia(admin, 'retiro-bloqueado')
    return a
  })

  await caso('MAN-06', '/hotel/habitaciones/[id]', 'baja lógica y reincorporación', 'administrador', 'fuera de servicio, sin oferta, historial intacto; reincorporada vuelve', async () => {
    const can = await api('POST', `/hotel/reservas/${RES_M.reserva_id}/cancelacion`, { cookie: cRecepcion, clave: K('can-m'), cuerpo: {} })
    esperar(can.estado === 200, `cancelación ${can.estado}`)
    await ir(admin, `/hotel/habitaciones/${HAB_M}`)
    await admin.getByRole('textbox', { name: 'Motivo' }).fill('remodelación E2E')
    await admin.getByRole('button', { name: 'Retirar de operación' }).click()
    await admin.waitForTimeout(1800)
    const conf = await confirmacion(admin)
    esperar(conf && conf.includes('retirada de operación'), `confirmación: ${conf}`)
    let ficha = (await api('GET', `/hotel/habitaciones/${HAB_M}`, { cookie: cAdmin })).datos
    esperar(ficha.estado_operativo === 'fuera_de_servicio' && ficha.motivo_fuera_de_servicio === 'remodelación E2E', 'estado no persistido')
    esperar(ficha.reservas.some((r) => r.reserva_id === RES_M.reserva_id && r.estado === 'cancelada'), 'se perdió la reserva histórica')
    esperar(ficha.tarifas.length === 2, `tarifas: ${ficha.tarifas.length}`)
    let oferta = await api('GET', `/hotel/oferta?inicio=${D(40)}&fin=${D(41)}&personas=1`, { cookie: cAdmin })
    esperar(!oferta.datos.oferta.some((u) => u.habitacion_id === HAB_M), 'sigue en la oferta')
    const ocupacion = await api('GET', `/hotel/ocupacion?desde=${D(0)}&hasta=${D(3)}`, { cookie: cAdmin })
    const fila = ocupacion.datos.habitaciones.find((h) => h.habitacion_id === HAB_M)
    esperar(fila.noches.every((n) => n.estado === 'no_vendible' && n.motivo === 'fuera_de_servicio'), 'la rejilla no la marca no vendible')
    await evidencia(admin, 'baja-logica')
    await admin.getByRole('button', { name: 'Reincorporar a la operación' }).click()
    await admin.waitForTimeout(1800)
    ficha = (await api('GET', `/hotel/habitaciones/${HAB_M}`, { cookie: cAdmin })).datos
    esperar(ficha.en_servicio && ficha.estado_operativo === 'disponible', 'no se reincorporó')
    oferta = await api('GET', `/hotel/oferta?inicio=${D(40)}&fin=${D(41)}&personas=1`, { cookie: cAdmin })
    esperar(oferta.datos.oferta.some((u) => u.habitacion_id === HAB_M), 'no volvió a la oferta')
    const acciones = ficha.auditoria.map((x) => x.resultado)
    esperar(acciones.includes('retirada: remodelación E2E') && acciones.includes('reincorporada'), `auditoría: ${acciones.join(' | ')}`)
    return 'retirada → fuera de oferta → reincorporada, con auditoría'
  })

  await caso('MAN-07', '/hotel/habitaciones/[id]', 'recepción ve la ficha sin acciones de administración', 'recepcion', 'sin formularios de admin ni auditoría; API 403', async () => {
    const page = await paginaDe(RECEPCION)
    await ir(page, `/hotel/habitaciones/${HAB_M}`)
    const t = await texto(page)
    await page.close()
    esperar(t.includes('Historial de tarifas'), 'no carga la ficha')
    for (const ausente of ['Editar datos', 'Registrar tarifa nueva', 'Retirar de operación', 'Historial de cambios']) esperar(!t.includes(ausente), `muestra «${ausente}»`)
    const put = await api('PUT', `/hotel/habitaciones/${HAB_M}`, { cookie: cRecepcion, clave: K('put-rec'), cuerpo: { tipo: 'x', capacidad: 1 } })
    const tar = await api('PUT', '/hotel/tarifas', { cookie: cRecepcion, clave: K('tar-rec'), cuerpo: { habitacion_id: HAB_M, fecha_desde: D(1), fecha_hasta: D(2), tarifa_noche_clp: 1 } })
    const ser = await api('POST', `/hotel/habitaciones/${HAB_M}/servicio`, { cookie: cRecepcion, clave: K('ser-rec'), cuerpo: { en_servicio: false, motivo: 'abc' } })
    esperar([put.estado, tar.estado, ser.estado].every((e) => e === 403), `${put.estado}/${tar.estado}/${ser.estado}`)
    return 'UI de solo lectura; PUT/tarifa/servicio → 403'
  })

  await caso('MAN-08', '/hotel/habitaciones/[id]', 'caja lee la ficha; no administra; no hay borrado', 'caja', 'ficha 200 sin auditoría; servicio 403; DELETE 405', async () => {
    const ficha = await api('GET', `/hotel/habitaciones/${HAB_M}`, { cookie: cCaja })
    esperar(ficha.estado === 200 && !('auditoria' in ficha.datos), `ficha ${ficha.estado}`)
    esperar(ficha.datos.reservas.every((r) => !('huesped_documento' in r)), 'caja ve el documento')
    const ser = await api('POST', `/hotel/habitaciones/${HAB_M}/servicio`, { cookie: cCaja, clave: K('ser-caj'), cuerpo: { en_servicio: false, motivo: 'abc' } })
    const del = await api('DELETE', `/hotel/habitaciones/${HAB_M}`, { cookie: cAdmin })
    esperar(ser.estado === 403 && del.estado === 405, `servicio ${ser.estado}, delete ${del.estado}`)
    return 'lectura sí; servicio 403; DELETE 405 (no publicado)'
  })

  // ===== RSV: consulta de reservas =====
  await caso('RSV-01', '/hotel/reservas', 'buscar por periodo y habitación, abrir detalle', 'recepcion', 'lista solo las del periodo; detalle con cuenta del servidor', async () => {
    const page = await paginaDe(RECEPCION)
    await ir(page, '/hotel/reservas')
    await page.getByLabel('Periodo desde').fill(D(29))
    await page.getByLabel('Periodo hasta (sin incluir)').fill(D(40))
    await page.getByRole('textbox', { name: 'Habitación (exacta)' }).fill(HAB_O)
    await page.getByRole('button', { name: 'Buscar' }).click()
    await page.waitForTimeout(1600)
    const ids = await page.evaluate(() => [...document.querySelectorAll('.reserva-fila .reserva-id')].map((x) => x.textContent))
    const esperadas = (await api('GET', `/hotel/reservas?desde=${D(29)}&hasta=${D(40)}&habitacion_id=${HAB_O}`, { cookie: cRecepcion })).datos.reservas.map((r) => r.reserva_id)
    esperar(JSON.stringify(ids) === JSON.stringify(esperadas) && ids.includes(RES_O1.reserva_id) && ids.includes(RES_O2.reserva_id), `UI ${ids} vs API ${esperadas}`)
    await page.getByRole('link', { name: RES_O1.reserva_id }).click()
    await page.waitForTimeout(1800)
    esperar(page.url().endsWith(`/hotel/reservas/${RES_O1.reserva_id}`), page.url())
    const detalle = (await api('GET', `/hotel/reservas/${RES_O1.reserva_id}`, { cookie: cRecepcion })).datos
    const t = await texto(page)
    const saldo = `$${detalle.cuenta.saldo_clp.toLocaleString('es-CL')}`
    esperar(t.includes('Saldo') && t.includes(saldo) && t.includes('22.222.222-2'), `saldo ${saldo} o documento ausente`)
    await evidencia(page, 'detalle-reserva')
    await page.close()
    return `${ids.length} reservas; detalle con saldo ${saldo}`
  })

  await caso('RSV-02', '/hotel/reservas/[id]', 'caja ve la cuenta pero no el documento', 'caja', 'detalle 200 sin huesped_documento; periodo inválido 422', async () => {
    const r = await api('GET', `/hotel/reservas/${RES_O1.reserva_id}`, { cookie: cCaja })
    esperar(r.estado === 200 && !('huesped_documento' in r.datos) && typeof r.datos.cuenta.saldo_clp === 'number', JSON.stringify(r.datos).slice(0, 100))
    const invalido = await api('GET', `/hotel/reservas?desde=${D(5)}&hasta=${D(5)}`, { cookie: cCaja })
    esperar(invalido.estado === 422, `periodo inválido ${invalido.estado}`)
    return 'cuenta visible, documento oculto; 422 en periodo vacío'
  })

  // ===== OCU: ocupación y disponibilidad =====
  await caso('OCU-01', '/hotel/ocupacion', 'rejilla por noche con confirmada, cancelada y disponible', 'recepcion', 'celdas según §5; cancelada listada sin pintar; enlace al detalle', async () => {
    const page = await paginaDe(RECEPCION)
    await ir(page, '/hotel/ocupacion')
    await page.getByLabel('Desde (noche)').fill(D(29))
    await page.getByLabel('Hasta (sin incluir)').fill(D(40))
    await page.getByRole('button', { name: 'Ver periodo' }).click()
    await page.waitForTimeout(1800)
    const estados = await page.evaluate((hid) => {
      const fila = [...document.querySelectorAll('table.ocupacion tbody tr')].find((tr) => tr.querySelector('th')?.textContent.includes(hid))
      return fila ? [...fila.querySelectorAll('td')].map((td) => td.dataset.estado) : null
    }, HAB_O)
    // noches D29..D39: D29 libre, D30–D32 confirmada, D33–D39 libres (D36–D37 eran de la cancelada)
    const esperado = ['disponible', 'confirmada', 'confirmada', 'confirmada', ...Array(7).fill('disponible')]
    esperar(JSON.stringify(estados) === JSON.stringify(esperado), `fila: ${estados}`)
    const t = await texto(page)
    esperar(t.includes(RES_O2.reserva_id), 'la cancelada no se lista')
    await evidencia(page, 'ocupacion')
    await page.locator(`a[href="/hotel/reservas/${RES_O1.reserva_id}"]`).first().click()
    await page.waitForTimeout(1500)
    esperar(page.url().endsWith(`/hotel/reservas/${RES_O1.reserva_id}`), `la celda no enlaza: ${page.url()}`)
    await page.close()
    return 'D30–D32 confirmada; noches de la cancelada disponibles; celda → detalle'
  })

  await caso('OCU-02', '/hotel/ocupacion', 'cada noche «disponible» coincide con la oferta de esa noche', 'caja', 'consistencia total ocupación ↔ oferta en 10 noches', async () => {
    const r = await api('GET', `/hotel/ocupacion?desde=${D(29)}&hasta=${D(39)}`, { cookie: cCaja })
    esperar(r.estado === 200, `${r.estado}`)
    let comparadas = 0
    for (const noche of r.datos.noches) {
      const oferta = await api('GET', `/hotel/oferta?inicio=${noche}&fin=${sumarDias(noche, 1)}&personas=1`, { cookie: cCaja })
      const ofrecidas = new Set(oferta.datos.oferta.map((u) => u.habitacion_id))
      for (const h of r.datos.habitaciones) {
        const celda = h.noches.find((n) => n.fecha === noche)
        if ((celda.estado === 'disponible') !== ofrecidas.has(h.habitacion_id)) throw new Error(`${h.habitacion_id} ${noche}: ${celda.estado} vs oferta ${ofrecidas.has(h.habitacion_id)}`)
        comparadas += 1
      }
    }
    return `${comparadas} celdas consistentes con la oferta`
  })

  // ===== IND: panel de indicadores =====
  await caso('IND-01', '/hotel/panel', 'panel coincide con un recuento independiente', 'administrador', 'en_casa, llegadas y noches reservadas = recuento desde /hotel/reservas', async () => {
    const desde = D(29), hasta = D(40)
    const ind = (await api('GET', `/hotel/indicadores?desde=${desde}&hasta=${hasta}`, { cookie: cAdmin })).datos
    const todas = (await api('GET', '/hotel/reservas', { cookie: cAdmin })).datos.reservas
    const enCasa = todas.filter((r) => r.estado === 'en_estadia').length
    const llegadas = todas.filter((r) => r.estado === 'confirmada' && r.inicio === HOY).length
    // noches de confirmada/en_estadia/finalizada solapadas, con el fin efectivo
    // de §4.3: una finalizada termina en la fecha de su liquidación si es
    // anterior a `fin` (la base de e2e.mjs liquida estadías futuras: V1-ISSUE-07)
    let noches = 0
    for (const r of todas.filter((x) => ['confirmada', 'en_estadia', 'finalizada'].includes(x.estado))) {
      let fin = r.fin
      if (r.estado === 'finalizada') {
        const liq = (await api('GET', `/hotel/reservas/${r.reserva_id}`, { cookie: cAdmin })).datos.liquidacion
        if (liq && liq.liquidada_en.slice(0, 10) < fin) fin = liq.liquidada_en.slice(0, 10)
      }
      for (let d = desde; d < hasta; d = sumarDias(d, 1)) if (r.inicio <= d && d < fin) noches += 1
    }
    esperar(ind.hoy.en_casa.valor === enCasa, `en_casa ${ind.hoy.en_casa.valor} vs ${enCasa}`)
    esperar(ind.hoy.llegadas_hoy.valor === llegadas, `llegadas ${ind.hoy.llegadas_hoy.valor} vs ${llegadas}`)
    esperar(ind.periodo_indicadores.noches_reservadas.valor === noches, `noches ${ind.periodo_indicadores.noches_reservadas.valor} vs ${noches}`)
    esperar(ind.periodo_indicadores.ocupacion.valor === null, 'ocupación realizada de un periodo futuro debería ser null')
    await ir(admin, '/hotel/panel')
    await admin.getByLabel('Desde (noche)').fill(desde)
    await admin.getByLabel('Hasta (sin incluir)').fill(hasta)
    await admin.getByRole('button', { name: 'Actualizar' }).click()
    await admin.waitForTimeout(1800)
    const t = await texto(admin)
    const pct = `${(ind.periodo_indicadores.ocupacion_reservada.valor * 100).toFixed(1)} %`
    esperar(t.includes(`Fecha de corte del servidor: ${HOY}`) && t.includes(pct) && t.includes('sin muestra'), `panel sin ${pct} / «sin muestra»`)
    await admin.getByText('Cómo se calcula').first().click()
    esperar((await texto(admin)).includes('Fórmula'), 'definición no desplegable')
    await evidencia(admin, 'panel')
    return `en_casa ${enCasa}, llegadas ${llegadas}, noches ${noches}, ocupación reservada ${pct}`
  })

  await caso('IND-02', '/hotel/panel', 'indicadores sin dinero, financieros declarados como no disponibles', 'recepcion y caja', '200 para ambos; sin montos; ADR en no_disponibles', async () => {
    for (const cookie of [cRecepcion, cCaja]) {
      const r = await api('GET', `/hotel/indicadores?desde=${D(-7)}&hasta=${D(1)}`, { cookie })
      esperar(r.estado === 200, `${r.estado}`)
      esperar(!JSON.stringify(r.datos.hoy).includes('_clp') && !JSON.stringify(r.datos.periodo_indicadores).includes('_clp'), 'expone montos')
      esperar(r.datos.no_disponibles.some((x) => x.indicador.includes('ADR')), 'ADR no declarado')
    }
    const page = await paginaDe(CAJA)
    await ir(page, '/hotel/panel')
    const t = await texto(page)
    await page.close()
    esperar(t.includes('No disponibles en esta versión') && t.includes('ADR'), 'la UI no declara lo no disponible')
    const largo = await api('GET', `/hotel/indicadores?desde=${D(0)}&hasta=${D(93)}`, { cookie: cCaja })
    esperar(largo.estado === 422, `periodo > 92: ${largo.estado}`)
    return 'recepción y caja leen; sin montos; ADR/RevPAR declarados pendientes; 422 > 92 noches'
  })

  await caso('IND-03', '/hotel/indicadores', 'sin sesión no hay datos', 'anónimo', '401 en indicadores, ocupación, ficha y detalle', async () => {
    const estados = []
    for (const ruta of ['/hotel/indicadores', '/hotel/ocupacion', `/hotel/habitaciones/${HAB_M}`, `/hotel/reservas/${RES_O1.reserva_id}`]) estados.push((await api('GET', ruta)).estado)
    esperar(estados.every((e) => e === 401), estados.join(','))
    return '401 ×4'
  })

  await caso('IND-04', '/hotel/panel', 'filtro por tipo de habitación recalcula el panel', 'administrador', 'las tarjetas cambian al filtrar por un tipo existente', async () => {
    const page = await paginaDe(ADMIN)
    await page.goto(`${FRONT}/hotel/panel`)
    await page.waitForTimeout(2500)
    const total = await page.evaluate(() => document.querySelector('main')?.innerText?.match(/HABITACIONES REGISTRADAS\s*(\d+)/)?.[1])
    await page.getByRole('combobox', { name: /TIPO DE HABITACIÓN/i }).selectOption('simple')
    await page.getByRole('button', { name: 'Actualizar' }).click()
    await page.waitForTimeout(2500)
    const filtrado = await page.evaluate(() => document.querySelector('main')?.innerText?.match(/HABITACIONES REGISTRADAS\s*(\d+)/)?.[1])
    await page.context().close()
    esperar(total && filtrado && total !== filtrado, `sin filtro ${total} / con filtro ${filtrado}`)
    return `sin filtro ${total} → solo «simple» ${filtrado}`
  })

  // ===== Reconciliación UI ↔ API (2026-11-03) =====
  await caso('OCU-03', '/hotel/ocupacion', 'la rejilla y el resumen pintan exactamente lo que responde la API', 'recepcion', 'cada fila de celdas y el pie coinciden con /hotel/ocupacion del mismo periodo', async () => {
    const desde = D(29), hasta = D(40)
    const r = await api('GET', `/hotel/ocupacion?desde=${desde}&hasta=${hasta}`, { cookie: cRecepcion })
    esperar(r.estado === 200, `${r.estado}`)
    const page = await paginaDe(RECEPCION)
    await ir(page, '/hotel/ocupacion')
    await page.getByLabel('Desde (noche)').fill(desde)
    await page.getByLabel('Hasta (sin incluir)').fill(hasta)
    await page.getByRole('button', { name: 'Ver periodo' }).click()
    await page.waitForTimeout(1800)
    const pintado = await page.evaluate(() => {
      const filas = {}
      for (const tr of document.querySelectorAll('table.ocupacion tbody tr')) {
        const hid = tr.querySelector('th a')?.textContent.trim()
        if (hid) filas[hid] = [...tr.querySelectorAll('td')].map((td) => td.dataset.estado)
      }
      const pie = [...document.querySelectorAll('tfoot .ocupacion-resumen')].map((td) => td.textContent.trim())
      return { filas, pie }
    })
    for (const h of r.datos.habitaciones) {
      const esperadas = h.noches.map((n) => n.estado)
      const apiId = h.habitacion_id
      const coincide = pintado.filas[apiId] && JSON.stringify(pintado.filas[apiId]) === JSON.stringify(esperadas)
      esperar(coincide, `${apiId}: UI ${JSON.stringify(pintado.filas[apiId])} vs API ${JSON.stringify(esperadas)}`)
    }
    const pieEsperado = r.datos.resumen.map((x) => `${x.disponibles}/${x.ocupadas_cupo}`)
    esperar(JSON.stringify(pintado.pie) === JSON.stringify(pieEsperado), `pie ${pintado.pie} vs ${pieEsperado}`)
    await evidencia(page, 'ocu-03-ui-igual-api')
    await page.close()
    return `${Object.keys(pintado.filas).length} filas y ${pintado.pie.length} totales idénticos a la API`
  })

  await caso('OCU-04', '/hotel/ocupacion', 'periodo inválido: la UI muestra el error y no datos viejas', 'recepcion', 'alerta «hasta debe ser mayor…» y la rejilla anterior desaparece', async () => {
    const page = await paginaDe(RECEPCION)
    await ir(page, '/hotel/ocupacion')
    await page.getByLabel('Desde (noche)').fill(D(35))
    await page.getByLabel('Hasta (sin incluir)').fill(D(30))
    await page.getByRole('button', { name: 'Ver periodo' }).click()
    await page.waitForTimeout(1500)
    const mensaje = await alerta(page)
    esperar(mensaje && mensaje.includes('hasta debe ser mayor'), `alerta: ${mensaje}`)
    esperar((await page.locator('table.ocupacion').count()) === 0, 'la rejilla vieja sigue visible pese al error')
    await page.close()
    return `error del servidor visible sin datos obsoletos`
  })

  await caso('IND-05', '/hotel/panel', 'los KPI y la serie muestran los valores del servidor sin recalcular', 'administrador', 'cada tarjeta y cada fila de la serie coinciden con /hotel/indicadores del mismo periodo', async () => {
    const desde = D(29), hasta = D(40)
    const ind = (await api('GET', `/hotel/indicadores?desde=${desde}&hasta=${hasta}`, { cookie: cAdmin })).datos
    const page = await paginaDe(ADMIN)
    await ir(page, '/hotel/panel')
    await page.getByLabel('Desde (noche)').fill(desde)
    await page.getByLabel('Hasta (sin incluir)').fill(hasta)
    await page.getByRole('button', { name: 'Actualizar' }).click()
    await page.waitForTimeout(2000)
    const kpis = await page.evaluate(() => {
      const pares = {}
      for (const kpi of document.querySelectorAll('.kpi')) {
        const titulo = kpi.querySelector('.kpi-titulo')?.textContent.trim()
        const valor = kpi.querySelector('.kpi-valor')?.textContent.trim()
        if (titulo) pares[titulo] = valor
      }
      const serie = [...document.querySelectorAll('table.serie tbody tr')].map((tr) =>
        [...tr.querySelectorAll('td')].map((td) => td.textContent.trim()))
      return { pares, serie }
    })
    esperar(kpis.pares['Huéspedes en casa'] === String(ind.hoy.en_casa.valor),
            `en_casa UI ${kpis.pares['Huéspedes en casa']} vs API ${ind.hoy.en_casa.valor}`)
    esperar(kpis.pares['Llegadas vencidas sin check-in'] === String(ind.hoy.llegadas_vencidas.valor),
            `llegadas_vencidas UI ${kpis.pares['Llegadas vencidas sin check-in']} vs API ${ind.hoy.llegadas_vencidas.valor}`)
    esperar(kpis.pares['Noches reservadas'] === String(ind.periodo_indicadores.noches_reservadas.valor),
            `noches_reservadas UI ${kpis.pares['Noches reservadas']} vs API ${ind.periodo_indicadores.noches_reservadas.valor}`)
    esperar(kpis.pares['Unidades-noche'] === String(ind.periodo_indicadores.unidades_noche.valor),
            `unidades_noche UI ${kpis.pares['Unidades-noche']} vs API ${ind.periodo_indicadores.unidades_noche.valor}`)
    esperar(kpis.serie.length === ind.serie.length, `serie UI ${kpis.serie.length} vs API ${ind.serie.length}`)
    for (let i = 0; i < ind.serie.length; i++) {
      const filaApi = ind.serie[i]
      const filaUi = kpis.serie[i]
      const ocupadasUi = filaApi.ocupadas_estadias === null ? 'futura' : String(filaApi.ocupadas_estadias)
      esperar(filaUi[0] === filaApi.fecha && filaUi[1] === String(filaApi.unidades)
              && filaUi[2] === ocupadasUi && filaUi[3] === String(filaApi.reservadas),
              `serie ${filaApi.fecha}: UI ${filaUi} vs API ${JSON.stringify(filaApi)}`)
    }
    await evidencia(page, 'ind-05-ui-igual-api')
    await page.close()
    return `${Object.keys(kpis.pares).length} KPI y ${kpis.serie.length} noches idénticos a la API`
  })
  await admin.close()
} finally {
  await navegador.close()
}

const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
const fallidos = resultados.filter((r) => r.estado === 'FALLIDO')
console.log(`\n${aprobados}/${resultados.length} APROBADOS, ${fallidos.length} FALLIDOS`)
writeFileSync(join(AQUI, 'e2e-operacion-resultados.json'), JSON.stringify(resultados, null, 2))
if (fallidos.length > 0) process.exit(1)
