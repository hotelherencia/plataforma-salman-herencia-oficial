/**
 * E2E de las funciones pedidas por el propietario el 2026-11-19:
 *  1. Productos: carga desde la factura XML del SII, planilla pegada y lector
 *     de códigos (pestañas dentro de «Productos y stock»).
 *  2. Salida: buscar al huésped por nombre, habitación o documento; Salidas de
 *     hoy primero; con saldo, atajo al pago y vuelta a la Salida.
 *  3. Caja: registrar pago buscando por nombre, documento, habitación o
 *     código; sin JSON ni claves técnicas en pantalla.
 *
 * Navegador real (Chromium) contra front y API locales, datos 100 %
 * sintéticos y únicos por corrida. Cada mutación se verifica releyendo la API.
 * Uso: FRONT_URL=… API_URL=… [E2E_DB_URL=…] node e2e-funciones.mjs
 * Salida: consola + e2e-funciones-resultados.json; capturas en
 * ../capturas/e2e-AAAA-MM-DD/fn-NN-*.png (o en CAPTURAS_DIR si se indica).
 */

import { chromium } from 'playwright'
import { execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONT = process.env.FRONT_URL || 'http://127.0.0.1:3000'
const API = process.env.API_URL || 'http://127.0.0.1:8080'
const DB_URL = process.env.E2E_DB_URL || ''
const ADMIN = ['admin_e2e', process.env.ADMIN_CLAVE_E2E || 'E2eClave123']
const RUN = Date.now().toString(36)
const K = (nombre) => `${nombre}-${RUN}`
const AQUI = dirname(fileURLToPath(import.meta.url))

function sumarDias(isoFecha, dias) {
  const d = new Date(`${isoFecha}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + dias)
  return d.toISOString().slice(0, 10)
}

function dv(cuerpo) {
  let suma = 0
  let factor = 2
  for (const c of String(cuerpo).split('').reverse()) {
    suma += Number(c) * factor
    factor = factor === 7 ? 2 : factor + 1
  }
  const r = 11 - (suma % 11)
  return r === 11 ? '0' : r === 10 ? 'K' : String(r)
}
function rutUnico(semilla) {
  const cuerpo = 10_000_000 + (parseInt(RUN.slice(-5), 36) * 7 + semilla * 104729) % 89_000_000
  return `${cuerpo.toLocaleString('de-DE')}-${dv(cuerpo)}`
}

async function api(metodo, ruta, { cuerpo, clave, cookie, cabeceras = {} } = {}) {
  const h = { ...cabeceras }
  if (cuerpo !== undefined) h['Content-Type'] = 'application/json'
  if (clave) h['Idempotency-Key'] = clave
  if (cookie) h.Cookie = cookie
  const r = await fetch(API + ruta, { method: metodo, headers: h, body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined })
  const texto = await r.text()
  let datos = {}
  try { datos = texto ? JSON.parse(texto) : {} } catch { datos = { detalle: texto } }
  return { estado: r.status, datos, cookie: (r.headers.get('set-cookie') || '').split(';')[0] }
}

async function loginApi(usuario, clave) {
  const r = await api('POST', '/sesion', { cuerpo: { usuario, clave } })
  if (r.estado !== 200) throw new Error(`login API falló para ${usuario}: ${r.estado}`)
  return r.cookie
}

const esperar = (cond, msg) => { if (!cond) throw new Error(msg) }

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
async function evidencia(page, nombre, completa = true) {
  evidenciaN += 1
  const archivo = join(carpeta, `fn-${String(evidenciaN).padStart(2, '0')}-${nombre}.png`)
  await page.screenshot({ path: archivo, fullPage: completa })
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

const textoMain = (page) => page.evaluate(() => document.querySelector('main')?.innerText || '')
const alerta = (page) => page.evaluate(() => [...document.querySelectorAll('[role=alert]')].map((e) => e.textContent).join(' | ') || null)
const confirmacion = (page) => page.evaluate(() => document.querySelector('.operacion-confirmada')?.textContent || null)
async function ir(page, ruta) {
  await page.goto(`${FRONT}${ruta}`)
  await page.waitForTimeout(1700)
}
function sinDatosTecnicos(texto, donde) {
  for (const marca of ['{"', '":', 'Idempotency', 'cobro-', 'Input should', 'Field required', 'undefined', 'null']) {
    esperar(!texto.includes(marca), `${donde}: aparece «${marca}» en pantalla`)
  }
}

const navegador = await chromium.launch({ executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome' })
async function paginaDe(credenciales, viewport = { width: 1366, height: 900 }) {
  const ctx = await navegador.newContext({ baseURL: FRONT, viewport })
  const page = await ctx.newPage()
  await loginUi(page, credenciales)
  return page
}

function facturaXml({ folio, rut, items }) {
  const detalle = items.map((it, i) => `
    <Detalle>
      <NroLinDet>${i + 1}</NroLinDet>
      ${it.codigo ? `<CdgItem><TpoCodigo>EAN13</TpoCodigo><VlrCodigo>${it.codigo}</VlrCodigo></CdgItem>` : ''}
      <NmbItem>${it.nombre}</NmbItem>
      <QtyItem>${it.cantidad}</QtyItem>
      <UnmdItem>UN</UnmdItem>
      <PrcItem>${it.costo}</PrcItem>
      <MontoItem>${it.cantidad * it.costo}</MontoItem>
    </Detalle>`).join('')
  const neto = items.reduce((s, it) => s + it.cantidad * it.costo, 0)
  const iva = Math.round(neto * 0.19)
  return `<?xml version="1.0" encoding="ISO-8859-1"?>
<DTE xmlns="http://www.sii.cl/SiiDte" version="1.0">
  <Documento ID="F33T${folio}">
    <Encabezado>
      <IdDoc><TipoDTE>33</TipoDTE><Folio>${folio}</Folio><FchEmis>2026-11-18</FchEmis></IdDoc>
      <Emisor><RUTEmisor>${rut}</RUTEmisor><RznSoc>DISTRIBUIDORA PRUEBA G SPA</RznSoc></Emisor>
      <Receptor><RUTRecep>77.777.777-7</RUTRecep><RznSocRecep>HOTEL PRUEBA G</RznSocRecep></Receptor>
      <Totales><MntNeto>${neto}</MntNeto><TasaIVA>19</TasaIVA><IVA>${iva}</IVA><MntTotal>${neto + iva}</MntTotal></Totales>
    </Encabezado>${detalle}
  </Documento>
</DTE>`
}

try {
  // ===== Semilla sintética =====
  const cAdmin = await loginApi(...ADMIN)
  const RECEPCION = [`recepcion_fn_${RUN}`, 'RecepFn12345']
  const CAJA = [`caja_fn_${RUN}`, 'CajaFn123456']
  await api('POST', '/usuarios', { cookie: cAdmin, clave: K('u-rec'), cuerpo: { nombre: RECEPCION[0], rol: 'recepcion', clave: RECEPCION[1] } })
  await api('POST', '/usuarios', { cookie: cAdmin, clave: K('u-caj'), cuerpo: { nombre: CAJA[0], rol: 'caja', clave: CAJA[1] } })
  const cRecepcion = await loginApi(...RECEPCION)
  const cCaja = await loginApi(...CAJA)
  const HOY = (await api('GET', '/hotel/indicadores', { cookie: cAdmin })).datos.fecha_corte
  carpeta = process.env.CAPTURAS_DIR || join(AQUI, '..', 'capturas', `e2e-${HOY}`)
  mkdirSync(carpeta, { recursive: true })
  const D = (n) => sumarDias(HOY, n)

  const HAB = [1, 2, 3].map((n) => `HAB-${RUN}-${n}`)
  for (const id of HAB) {
    await api('PUT', `/hotel/habitaciones/${id}`, { cookie: cAdmin, clave: K(`alta-${id}`), cuerpo: { tipo: 'doble', capacidad: 2 }, cabeceras: { 'If-None-Match': '*' } })
    await api('POST', '/hotel/precios/excepciones', { cookie: cAdmin, clave: K(`tar-${id}`), cuerpo: { habitacion_id: id, fecha_desde: D(-30), fecha_hasta: D(365), precio_clp: 45000 } })
  }
  const APELLIDO = `Fn${RUN}`
  const DOCS = [rutUnico(1), rutUnico(2), rutUnico(3)]
  const reservar = async (hid, inicio, fin, nombre, doc) => {
    const r = await api('POST', '/hotel/reservas', { cookie: cRecepcion, clave: K(`rsv-${hid}`), cuerpo: { habitacion_id: hid, inicio, fin, huesped: { nombre, documento: doc } } })
    if (r.estado !== 201) throw new Error(`reserva ${hid}: ${r.estado} ${JSON.stringify(r.datos)}`)
    return r.datos.reserva_id
  }
  const entrar = async (rid) => {
    const r = await api('POST', `/hotel/reservas/${rid}/entrada`, { cookie: cRecepcion, clave: K(`ent-${rid}`), cuerpo: {} })
    if (r.estado !== 200) throw new Error(`entrada ${rid}: ${r.estado} ${JSON.stringify(r.datos)}`)
  }
  const saldo = async (rid) => (await api('GET', `/hotel/reservas/${rid}`, { cookie: cAdmin })).datos.cuenta.saldo_clp
  // R1: sale hoy, cuenta al día. R2: en casa con saldo. R3: llega hoy.
  const R1 = await reservar(HAB[0], HOY, D(2), `Josefina ${APELLIDO}`, DOCS[0])
  const R2 = await reservar(HAB[1], HOY, D(1), `Tomás ${APELLIDO}`, DOCS[1])
  const R3 = await reservar(HAB[2], HOY, D(2), `Lucía ${APELLIDO}`, DOCS[2])
  await entrar(R1)
  await entrar(R2)
  await api('POST', `/hotel/reservas/${R1}/pagos`, { cookie: cAdmin, clave: K('pago-r1'), cuerpo: { monto_clp: await saldo(R1), clave: K('cobro-r1'), modo: 'manual' } })
  let saleHoy = false
  if (DB_URL) {
    // La estadía R1 «empezó» hace dos días y sale hoy (no se puede reservar en pasado por API).
    execFileSync('psql', [DB_URL, '-c', `UPDATE reservas SET inicio = '${D(-2)}', fin = '${HOY}' WHERE id = '${R1}'`], { stdio: 'ignore' })
    saleHoy = true
  }

  // ===== Salida =====
  const pRec = await paginaDe(RECEPCION)
  await caso('FN-SAL-01', '/hotel/salida', 'al entrar se ven las Salidas de hoy como tarjetas', 'recepcion', 'tarjeta de R1 con «Sale hoy» sin escribir nada', async () => {
    await ir(pRec, '/hotel/salida')
    await pRec.waitForTimeout(800)
    const rotulo = await pRec.evaluate(() => document.querySelector('[data-buscador-estadias] [role=status]')?.textContent || '')
    esperar(rotulo.includes('Salidas de hoy'), `rótulo: ${rotulo}`)
    if (saleHoy) {
      const tarjeta = pRec.locator(`[data-reserva="${R1}"]`)
      esperar((await tarjeta.count()) === 1, 'R1 no aparece en las Salidas de hoy')
      esperar((await tarjeta.innerText()).includes('Sale hoy'), 'sin insignia «Sale hoy»')
    }
    await evidencia(pRec, 'salida-lista-del-dia')
    return saleHoy ? `R1 en la lista con «Sale hoy» · ${rotulo}` : `sin E2E_DB_URL: solo el rótulo (${rotulo})`
  })
  await caso('FN-SAL-02', '/hotel/salida', 'buscar por nombre, habitación y documento', 'recepcion', 'cada búsqueda deja la tarjeta correcta', async () => {
    const buscar = async (q) => {
      await pRec.getByRole('searchbox', { name: 'Buscar huésped' }).fill(q)
      await pRec.waitForTimeout(1100)
      return pRec.evaluate(() => [...document.querySelectorAll('[data-reserva]')].map((e) => e.dataset.reserva))
    }
    const porNombre = await buscar(`tomas ${APELLIDO.toLowerCase()}`)
    esperar(porNombre.length === 1 && porNombre[0] === R2, `nombre (sin tilde): ${porNombre}`)
    const porHab = await buscar(HAB[0].toLowerCase())
    esperar(porHab.length === 1 && porHab[0] === R1, `habitación: ${porHab}`)
    const porDoc = await buscar(DOCS[1].replace(/[.-]/g, '').slice(0, 6))
    esperar(porDoc.includes(R2), `documento: ${porDoc}`)
    const corta = await buscar('t')
    const aviso = await pRec.evaluate(() => document.querySelector('[data-buscador-estadias] [role=status]')?.textContent || '')
    esperar(aviso.includes('al menos 2'), `texto corto: ${aviso}`)
    await buscar(APELLIDO)
    await evidencia(pRec, 'salida-busqueda-nombre')
    return `nombre→${porNombre[0]} · habitación→${porHab[0]} · documento→${porDoc.length} · corto→aviso (${corta.length})`
  })
  await caso('FN-SAL-03', '/hotel/salida', 'con saldo: Salida bloqueada, pago y vuelta a la Salida', 'recepcion', 'aviso de saldo, pago total, «Continuar con la Salida» y Salida registrada', async () => {
    await pRec.locator(`[data-reserva="${R2}"]`).click()
    await pRec.waitForTimeout(1300)
    const a = await alerta(pRec)
    esperar(a && a.includes('saldo pendiente'), `alerta: ${a}`)
    esperar(await pRec.getByRole('button', { name: 'Registrar Salida y liquidar cuenta' }).isDisabled(), 'Salida habilitada con saldo')
    sinDatosTecnicos(await textoMain(pRec), 'Salida')
    await evidencia(pRec, 'salida-saldo-pendiente')
    await pRec.getByRole('link', { name: 'Registrar pago del saldo' }).click()
    await pRec.waitForTimeout(2200)
    esperar(pRec.url().includes('/hotel/pago') && pRec.url().includes('volver=salida'), `url: ${pRec.url()}`)
    const monto = await pRec.getByRole('spinbutton', { name: 'Monto pagado (CLP)' }).inputValue()
    esperar(Number(monto) === (await saldo(R2)), `monto propuesto ${monto}`)
    await pRec.getByRole('button', { name: 'Registrar pago' }).click()
    await pRec.waitForTimeout(2000)
    const conf = await confirmacion(pRec)
    esperar(conf && conf.includes('Cuenta saldada'), `pago: ${conf}`)
    await pRec.getByRole('link', { name: 'Continuar con la Salida' }).click()
    await pRec.waitForTimeout(2200)
    await pRec.getByRole('button', { name: 'Registrar Salida y liquidar cuenta' }).click()
    await pRec.waitForTimeout(2000)
    const fin = await confirmacion(pRec)
    esperar(fin && fin.startsWith('Salida registrada') && fin.includes('liquidada'), `salida: ${fin}`)
    const det = await api('GET', `/hotel/reservas/${R2}`, { cookie: cAdmin })
    esperar(det.datos.estado === 'finalizada', `estado ${det.datos.estado}`)
    await evidencia(pRec, 'salida-registrada')
    return fin
  })

  // ===== Caja: registrar pago =====
  const pCaja = await paginaDe(CAJA)
  // Cargo extra en R1 para que tenga saldo y aparezca en la lista de caja.
  const prodCaja = await api('POST', '/hotel/productos', { cookie: cAdmin, clave: K('prod-caja'), cuerpo: { nombre: `Lavandería ${RUN}`, categoria: 'servicio', precio_clp: 7000 } })
  await api('POST', `/hotel/reservas/${R1}/cargos`, { cookie: cRecepcion, clave: K('cargo-r1'), cuerpo: { producto_id: prodCaja.datos.producto_id, cantidad: 1 } })
  await caso('FN-PAG-01', '/hotel/pago', 'caja encuentra al huésped sin ver ni enumerar documentos', 'caja', 'por nombre y documento completo sí; por prefijo no; sin documento en la tarjeta', async () => {
    await ir(pCaja, '/hotel/pago')
    const rotulo = await pCaja.evaluate(() => document.querySelector('[data-buscador-estadias] [role=status]')?.textContent || '')
    esperar(rotulo.includes('saldo pendiente'), `rótulo: ${rotulo}`)
    const buscar = async (q) => {
      await pCaja.getByRole('searchbox', { name: 'Buscar huésped' }).fill(q)
      await pCaja.waitForTimeout(1100)
      return pCaja.evaluate(() => [...document.querySelectorAll('[data-reserva]')].map((e) => ({ id: e.dataset.reserva, t: e.innerText })))
    }
    const prefijo = await buscar(DOCS[0].replace(/[.-]/g, '').slice(0, 6))
    esperar(!prefijo.some((x) => x.id === R1), 'caja enumeró por prefijo del documento')
    const completo = await buscar(DOCS[0])
    esperar(completo.length === 1 && completo[0].id === R1, `documento completo: ${JSON.stringify(completo.map((x) => x.id))}`)
    esperar(!completo[0].t.includes('Documento'), 'la tarjeta muestra el documento a caja')
    const nombre = await buscar(`josefina ${APELLIDO}`)
    esperar(nombre.length === 1 && nombre[0].t.includes('Saldo $7.000'), `nombre: ${nombre.map((x) => x.t).join(' / ')}`)
    await evidencia(pCaja, 'pago-busqueda-caja')
    return 'prefijo→0 · documento completo→R1 · nombre→R1 con «Saldo $7.000»'
  })
  await caso('FN-PAG-02', '/hotel/pago', 'registrar un pago parcial desde la tarjeta', 'caja', 'ficha con saldo, resumen en castellano, sin datos técnicos; la caja lo lista con hora', async () => {
    await pCaja.locator(`[data-reserva="${R1}"]`).click()
    await pCaja.waitForTimeout(1300)
    const saldoFicha = await pCaja.locator('[data-saldo]').getAttribute('data-saldo')
    esperar(Number(saldoFicha) === 7000, `saldo en la ficha ${saldoFicha}`)
    await pCaja.getByRole('spinbutton', { name: 'Monto pagado (CLP)' }).fill('5000')
    esperar((await pCaja.locator('[data-pago="parcial"]').count()) === 1, 'sin aviso de pago parcial')
    await evidencia(pCaja, 'pago-ficha-parcial')
    await pCaja.getByRole('button', { name: 'Registrar pago' }).click()
    await pCaja.waitForTimeout(2000)
    const conf = await confirmacion(pCaja)
    esperar(conf && conf.includes('Pago de $5.000') && conf.includes('Saldo pendiente: $2.000'), `confirmación: ${conf}`)
    sinDatosTecnicos(await textoMain(pCaja), 'Pago')
    esperar((await saldo(R1)) === 2000, 'saldo en la API')
    await evidencia(pCaja, 'pago-registrado')
    await ir(pCaja, '/hotel/caja')
    const caja = await textoMain(pCaja)
    esperar(caja.includes(`Josefina ${APELLIDO}`) && caja.includes('$5.000') && /\d{2}:\d{2}/.test(caja), 'la caja no lista el pago con hora')
    esperar(!caja.includes('PAG-'), 'la caja muestra ids técnicos de pago')
    await evidencia(pCaja, 'caja-del-dia')
    return conf
  })
  await caso('FN-PAG-03', '/hotel/estadias/busqueda', 'permisos de la búsqueda por pantalla', 'caja', 'caja: Salida 403, pago 200', async () => {
    const s = await api('GET', '/hotel/estadias/busqueda?alcance=salida', { cookie: cCaja })
    const p = await api('GET', '/hotel/estadias/busqueda?alcance=pago&q=ab', { cookie: cCaja })
    esperar(s.estado === 403 && p.estado === 200, `${s.estado}/${p.estado}`)
    return `${s.estado}/${p.estado}`
  })

  // ===== Llegada =====
  await caso('FN-LLE-01', '/hotel/estadia', 'Llegada: elegir de las Llegadas de hoy y registrar', 'recepcion', 'tarjeta de R3, Llegada registrada', async () => {
    await ir(pRec, '/hotel/estadia')
    const tarjeta = pRec.locator(`[data-reserva="${R3}"]`)
    if ((await tarjeta.count()) === 0) {
      await pRec.getByRole('searchbox', { name: 'Buscar huésped' }).fill(`lucia ${APELLIDO}`)
      await pRec.waitForTimeout(1100)
    }
    await pRec.locator(`[data-reserva="${R3}"]`).click()
    await pRec.waitForTimeout(1500)
    await evidencia(pRec, 'llegada-elegida')
    await pRec.getByRole('button', { name: 'Registrar Llegada' }).click()
    await pRec.waitForTimeout(2000)
    const conf = await confirmacion(pRec)
    esperar(conf && conf.includes('Llegada registrada'), `confirmación: ${conf}`)
    return conf
  })

  // ===== Productos =====
  const pAdm = await paginaDe(ADMIN)
  const COD = `E2E${RUN}A`.toUpperCase()
  // Con dígitos propios: el emparejamiento «parecido» exige las mismas cifras, así una corrida no se cruza con otra.
  const PRD = `${RUN}${Date.now() % 100000}`
  const ITEMS = [
    { codigo: COD, nombre: `Agua mineral ${PRD} 500 ml`, cantidad: 24, costo: 650 },
    { codigo: null, nombre: `Papas fritas ${PRD} 45 g`, cantidad: 10, costo: 710 },
  ]
  const FOLIO = String(parseInt(RUN.slice(-6), 36) % 900000 + 100000)
  const archivoXml = join(tmpdir(), `factura-${RUN}.xml`)
  writeFileSync(archivoXml, Buffer.from(facturaXml({ folio: FOLIO, rut: '76.123.456-0', items: ITEMS }), 'latin1'))
  const catalogo = async () => Object.fromEntries((await api('GET', '/hotel/productos?inactivos=true', { cookie: cAdmin })).datos.productos.map((p) => [p.nombre, p]))

  await caso('FN-PRD-01', '/hotel/productos', 'cargar la factura XML: revisión y carga al inventario', 'administrador', '2 productos nuevos con stock y costo; factura en «Últimas cargas»', async () => {
    await ir(pAdm, '/hotel/productos')
    await pAdm.getByRole('tab', { name: 'Cargar desde factura' }).click()
    await pAdm.waitForTimeout(500)
    await evidencia(pAdm, 'productos-pestana-factura')
    await pAdm.getByLabel('Archivo XML de la factura').setInputFiles(archivoXml)
    await pAdm.waitForTimeout(2000)
    const doc = await pAdm.evaluate(() => document.querySelector('[data-documento-factura]')?.innerText || '')
    esperar(doc.includes(`N° ${FOLIO}`) && doc.includes('DISTRIBUIDORA PRUEBA G SPA'), `cabecera: ${doc}`)
    esperar((await pAdm.locator('tr[data-linea]').count()) === 2, 'no se listaron las 2 líneas')
    await pAdm.getByRole('button', { name: 'Cargar al inventario' }).click()
    await pAdm.waitForTimeout(800)
    const falta = await alerta(pAdm)
    esperar(falta && falta.includes('precio de venta'), `sin aviso de precio: ${falta}`)
    await pAdm.getByLabel(`Precio de venta de ${ITEMS[0].nombre}`).fill('1500')
    await pAdm.getByLabel(`Precio de venta de ${ITEMS[1].nombre}`).fill('1800')
    await evidencia(pAdm, 'productos-revision-factura')
    await pAdm.getByRole('button', { name: 'Cargar al inventario' }).click()
    await pAdm.waitForTimeout(2200)
    const conf = await confirmacion(pAdm)
    esperar(conf && conf.includes(`Factura N° ${FOLIO}`) && conf.includes('2 productos nuevos') && conf.includes('34 unidades'), `confirmación: ${conf}`)
    const cat = await catalogo()
    esperar(cat[ITEMS[0].nombre]?.stock === 24 && cat[ITEMS[0].nombre]?.costo_clp === 650 && cat[ITEMS[0].nombre]?.codigo === COD, 'agua mal cargada')
    esperar(cat[ITEMS[1].nombre]?.stock === 10 && cat[ITEMS[1].nombre]?.precio_clp === 1800, 'papas mal cargadas')
    sinDatosTecnicos(await textoMain(pAdm), 'Productos')
    await evidencia(pAdm, 'productos-factura-cargada')
    return conf
  })
  await caso('FN-PRD-02', '/hotel/productos', 'la misma factura no se carga dos veces', 'administrador', 'aviso «ya se cargó» y botón deshabilitado; stock intacto', async () => {
    await pAdm.getByRole('button', { name: 'Cargar otra' }).click()
    await pAdm.waitForTimeout(500)
    await pAdm.getByLabel('Archivo XML de la factura').setInputFiles(archivoXml)
    await pAdm.waitForTimeout(2000)
    const a = await pAdm.evaluate(() => document.querySelector('[data-ya-importada]')?.textContent || '')
    esperar(a.includes('ya se cargó'), `aviso: ${a}`)
    esperar(await pAdm.getByRole('button', { name: 'Cargar al inventario' }).isDisabled(), 'botón habilitado')
    const lineas = await pAdm.evaluate(() => [...document.querySelectorAll('tr[data-linea]')].map((t) => t.innerText))
    // Tras la primera carga, el proveedor queda recordado (bandeja de facturas).
    esperar(lineas.every((t) => t.includes('Mismo') || t.includes('Recordado')), `emparejamiento: ${lineas.join(' / ')}`)
    await evidencia(pAdm, 'productos-factura-repetida')
    const r = await api('POST', '/hotel/productos/importacion', { cookie: cAdmin, clave: K('imp-dup'), cuerpo: {
      origen: 'factura_xml', xml: facturaXml({ folio: FOLIO, rut: '76.123.456-0', items: ITEMS }),
      lineas: [{ accion: 'sumar', producto_id: (await catalogo())[ITEMS[0].nombre].producto_id, nombre: ITEMS[0].nombre, cantidad: 24 }] } })
    esperar(r.estado === 409, `API: ${r.estado}`)
    esperar((await catalogo())[ITEMS[0].nombre].stock === 24, 'el stock cambió')
    return a.trim()
  })
  await caso('FN-PRD-03', '/hotel/productos', 'pegar planilla de Excel con mapeo de columnas', 'administrador', 'columnas adivinadas, coincidencia por nombre y stock sumado', async () => {
    await pAdm.getByRole('tab', { name: 'Pegar planilla' }).click()
    await pAdm.waitForTimeout(500)
    await pAdm.getByRole('textbox', { name: 'Filas copiadas' }).fill(`Producto\tCantidad\tCosto\n${ITEMS[1].nombre}\t6\t700\nManí salado ${PRD}\t4\t500`)
    await pAdm.waitForTimeout(400)
    await evidencia(pAdm, 'productos-planilla-mapeo')
    await pAdm.getByRole('button', { name: 'Revisar coincidencias' }).click()
    await pAdm.waitForTimeout(1800)
    const filas = await pAdm.evaluate(() => [...document.querySelectorAll('tr[data-linea]')].map((t) => t.innerText))
    esperar(filas.length === 2 && filas[0].includes('Mismo nombre') && filas[1].includes('Producto nuevo'), `filas: ${filas.join(' / ')}`)
    await pAdm.getByLabel(`Precio de venta de Maní salado ${PRD}`).fill('1200')
    await pAdm.getByRole('button', { name: 'Cargar al inventario' }).click()
    await pAdm.waitForTimeout(2000)
    const conf = await confirmacion(pAdm)
    esperar(conf && conf.includes('1 producto nuevo') && conf.includes('10 unidades'), `confirmación: ${conf}`)
    const cat = await catalogo()
    esperar(cat[ITEMS[1].nombre].stock === 16 && cat[`Maní salado ${PRD}`].stock === 4, 'stock de planilla')
    return conf
  })
  await caso('FN-PRD-04', '/hotel/productos', 'lector de códigos: cada lectura suma una unidad', 'administrador', 'dos lecturas del mismo código → +2 al stock', async () => {
    await pAdm.getByRole('tab', { name: 'Lector de códigos' }).click()
    await pAdm.waitForTimeout(500)
    const campo = pAdm.getByRole('textbox', { name: 'Código de barras o del proveedor' })
    for (let i = 0; i < 2; i += 1) {
      await campo.click()
      await pAdm.keyboard.type(COD.toLowerCase())
      await pAdm.keyboard.press('Enter')
      await pAdm.waitForTimeout(900)
    }
    const item = await pAdm.evaluate((c) => document.querySelector(`[data-codigo="${c.toLowerCase()}"]`)?.innerText || '', COD)
    esperar(item.includes(ITEMS[0].nombre), `lote: ${item}`)
    esperar((await pAdm.getByRole('spinbutton', { name: `Cantidad de ${ITEMS[0].nombre}` }).inputValue()) === '2', 'cantidad ≠ 2')
    await evidencia(pAdm, 'productos-lector')
    await pAdm.getByRole('button', { name: /Revisar y cargar/ }).click()
    await pAdm.waitForTimeout(1800)
    await pAdm.getByRole('button', { name: 'Cargar al inventario' }).click()
    await pAdm.waitForTimeout(2000)
    const conf = await confirmacion(pAdm)
    esperar(conf && conf.includes('2 unidades'), `confirmación: ${conf}`)
    esperar((await catalogo())[ITEMS[0].nombre].stock === 26, 'stock tras lector')
    return conf
  })
  await caso('FN-PRD-05', '/hotel/productos', 'recepción y caja no ven la carga de productos', 'recepcion/caja', 'API 403 en vista previa', async () => {
    const a = await api('POST', '/hotel/productos/importacion/vista-previa', { cookie: cRecepcion, cuerpo: { origen: 'planilla', lineas: [{ nombre: 'x', cantidad: 1 }] } })
    const b = await api('POST', '/hotel/productos/importacion/vista-previa', { cookie: cCaja, cuerpo: { origen: 'planilla', lineas: [{ nombre: 'x', cantidad: 1 }] } })
    esperar(a.estado === 403 && b.estado === 403, `${a.estado}/${b.estado}`)
    return `${a.estado}/${b.estado}`
  })

  // ===== Facturas de proveedores: foto con timbre, envases, pedidos =====
  const PY = process.env.E2E_PYTHON || join(AQUI, '..', '.venv', 'bin', 'python')
  const RUT_F = rutUnico(41).replace(/\./g, '')
  const FOLIO_F = String(parseInt(RUN.slice(-6), 36) % 800000 + 150000)
  const fotoFactura = join(tmpdir(), `foto-factura-${RUN}.jpg`)
  const fotoPedido = join(tmpdir(), `foto-pedido-${RUN}.jpg`)
  // Fotos sintéticas (sin datos reales): página con timbre PDF417 y otra sin timbre.
  execFileSync(PY, ['-c', [
    'import sys; from servicio.tests import facturas_sinteticas as s',
    `open(sys.argv[1], "wb").write(s.jpeg(s.pagina(folio="${FOLIO_F}", rut="${RUT_F}"), escala=2))`,
    `open(sys.argv[2], "wb").write(s.jpeg(s.pagina(folio="1", rut="${RUT_F}", con_timbre=False), escala=1))`,
  ].join('\n'), fotoFactura, fotoPedido], { cwd: join(AQUI, '..'), stdio: 'inherit' })
  const AGUA = `Agua sin gas caja x 24 ${PRD}`
  const BEBIDA = `Bebida cola ${PRD} lata x 6`
  let pedidoId = null

  await caso('FN-FAC-01', '/hotel/productos', 'fotografiar la factura: timbre SII, líneas a mano y unidades por envase', 'administrador',
    'proveedor y folio desde el timbre; 2 cajas x 24 + 3 packs x 6 = 66 unidades; costo por unidad', async () => {
      await ir(pAdm, '/hotel/productos')
      await pAdm.getByRole('tab', { name: 'Cargar desde factura' }).click()
      await pAdm.waitForTimeout(600)
      await evidencia(pAdm, 'facturas-bandeja')
      await pAdm.locator('input[capture="environment"]').setInputFiles(fotoFactura)
      await pAdm.locator('[data-documento-abierto]').waitFor({ timeout: 30000 })
      const cab = await textoMain(pAdm)
      esperar(cab.includes(`Factura N° ${FOLIO_F}`), `sin folio del timbre: ${cab.slice(0, 300)}`)
      esperar((await pAdm.locator('[data-timbre]').count()) === 1, 'no se leyó el timbre')
      await pAdm.getByLabel('Descripción línea 1').fill(AGUA)
      await pAdm.getByLabel('Cantidad línea 1').fill('2')
      await pAdm.getByLabel('Costo línea 1').fill('12000')
      await pAdm.getByLabel('Descripción línea 2').fill(BEBIDA)
      await pAdm.getByLabel('Cantidad línea 2').fill('3')
      await pAdm.getByLabel('Costo línea 2').fill('3990')
      await evidencia(pAdm, 'facturas-foto-lineas-a-mano')
      await pAdm.getByRole('button', { name: 'Guardar líneas' }).click()
      await pAdm.locator('tr[data-linea]').first().waitFor({ timeout: 10000 })
      const envAgua = await pAdm.getByLabel(`Unidades por envase de ${AGUA}`).inputValue()
      const envBebida = await pAdm.getByLabel(`Unidades por envase de ${BEBIDA}`).inputValue()
      esperar(envAgua === '24' && envBebida === '6', `envases sugeridos ${envAgua}/${envBebida}`)
      await pAdm.getByLabel(`Precio de venta de ${AGUA}`).fill('1500')
      await pAdm.getByLabel(`Precio de venta de ${BEBIDA}`).fill('1200')
      await evidencia(pAdm, 'facturas-revision-envases')
      await pAdm.getByRole('button', { name: 'Cargar al inventario' }).click()
      await pAdm.waitForTimeout(2500)
      const conf = await confirmacion(pAdm)
      esperar(conf && conf.includes('66 unidades'), `confirmación: ${conf}`)
      const cat = await catalogo()
      esperar(cat[AGUA]?.stock === 48 && cat[AGUA]?.costo_clp === 500, `agua: ${JSON.stringify(cat[AGUA])}`)
      esperar(cat[BEBIDA]?.stock === 18 && cat[BEBIDA]?.costo_clp === 665, `bebida: ${JSON.stringify(cat[BEBIDA])}`)
      sinDatosTecnicos(await textoMain(pAdm), 'Productos')
      await evidencia(pAdm, 'facturas-foto-cargada')
      return conf
    })
  await caso('FN-FAC-02', '/hotel/productos', 'la misma foto no se carga dos veces', 'administrador', 'abre la misma factura con aviso «ya se cargó»', async () => {
    await pAdm.getByRole('button', { name: 'Cargar otra' }).click()
    await pAdm.waitForTimeout(500)
    await pAdm.getByLabel('PDF o foto de la factura').setInputFiles(fotoFactura)
    await pAdm.locator('[data-ya-importada]').waitFor({ timeout: 30000 })
    esperar(await pAdm.getByRole('button', { name: 'Cargar al inventario' }).isDisabled(), 'botón habilitado')
    esperar((await catalogo())[AGUA].stock === 48, 'el stock cambió')
    await evidencia(pAdm, 'facturas-foto-repetida')
    return (await pAdm.locator('[data-ya-importada]').textContent()).trim()
  })
  await caso('FN-FAC-03', '/hotel/productos/documentos', 'pedido en borrador: no suma stock', 'administrador', 'foto sin timbre marcada como pedido → borrador', async () => {
    const buf = readFileSync(fotoPedido)
    const r = await fetch(`${API}/hotel/productos/documentos/archivo`, { method: 'POST', body: buf,
      headers: { cookie: cAdmin, 'Content-Type': 'image/jpeg', 'X-Nombre-Archivo': 'pedido.jpg' } })
    const d = await r.json()
    esperar(r.status === 201 && d.clase === 'desconocido', `subida ${r.status} ${d.clase}`)
    const p = await api('PUT', `/hotel/productos/documentos/${d.documento_id}`, { cookie: cAdmin, cuerpo: { clase: 'pedido', emisor_rut: RUT_F, folio: '21027' } })
    esperar(p.estado === 200 && p.datos.estado === 'borrador', `pedido ${p.estado} ${p.datos.estado}`)
    pedidoId = d.documento_id
    return 'borrador'
  })
  await caso('FN-FAC-04', '/hotel/productos', 'segunda factura del proveedor: producto y envase recordados; cierra el pedido', 'administrador',
    '«Recordado del proveedor», 24 por caja sin escribirlo; pedido facturado', async () => {
      const xml = facturaXml({ folio: String(Number(FOLIO_F) + 1), rut: RUT_F, items: [{ codigo: null, nombre: AGUA, cantidad: 1, costo: 12600 }] })
      const archivo = join(tmpdir(), `factura2-${RUN}.xml`)
      writeFileSync(archivo, Buffer.from(xml, 'latin1'))
      await pAdm.getByRole('button', { name: 'Volver a la bandeja' }).first().click()
      await pAdm.waitForTimeout(800)
      await evidencia(pAdm, 'facturas-bandeja-con-pedido')
      await pAdm.getByLabel('Archivo XML de la factura').setInputFiles(archivo)
      await pAdm.locator('tr[data-linea]').first().waitFor({ timeout: 15000 })
      const fila = await pAdm.locator('tr[data-linea]').first().innerText()
      esperar(fila.includes('Recordado del proveedor'), `sin recordar: ${fila}`)
      esperar(await pAdm.getByLabel(`Unidades por envase de ${AGUA}`).inputValue() === '24', 'envase no recordado')
      esperar(await pAdm.getByRole('checkbox', { name: /cierra el pedido N° 21027/ }).isChecked(), 'no sugiere cerrar el pedido')
      await evidencia(pAdm, 'facturas-recordado-y-pedido')
      await pAdm.getByRole('button', { name: 'Cargar al inventario' }).click()
      await pAdm.waitForTimeout(2500)
      const conf = await confirmacion(pAdm)
      esperar(conf && conf.includes('24 unidades'), `confirmación: ${conf}`)
      esperar((await catalogo())[AGUA].stock === 72 && (await catalogo())[AGUA].costo_clp === 525, 'stock/costo tras 2ª factura')
      const ped = await api('GET', `/hotel/productos/documentos/${pedidoId}`, { cookie: cAdmin })
      esperar(ped.datos.estado === 'facturado', `pedido ${ped.datos.estado}`)
      return conf
    })
  await caso('FN-FAC-05', '/hotel/productos', 'productos recordados por proveedor: editar unidades por envase', 'administrador', 'cambio a 12 guardado', async () => {
    await pAdm.getByRole('button', { name: 'Cargar otra' }).click()
    await pAdm.waitForTimeout(800)
    await pAdm.locator('summary', { hasText: 'Productos recordados por proveedor' }).click()
    const campo = pAdm.getByLabel(`Unidades por envase de ${AGUA}`)
    await campo.fill('12')
    await campo.locator('xpath=ancestor::tr').getByRole('button', { name: 'Guardar' }).click()
    await pAdm.waitForTimeout(1000)
    const eq = (await api('GET', '/hotel/productos/equivalencias', { cookie: cAdmin })).datos.equivalencias.find((e) => e.descripcion === AGUA)
    esperar(eq?.unidades_por_paquete === 12, `equivalencia ${JSON.stringify(eq)}`)
    await evidencia(pAdm, 'facturas-recordados')
    return 'unidades_por_paquete=12'
  })
  await caso('FN-FAC-06', '/hotel/productos/documentos', 'recepción y caja no ven la bandeja de facturas', 'recepcion/caja', 'API 403', async () => {
    const a = await api('GET', '/hotel/productos/documentos', { cookie: cRecepcion })
    const b = await api('GET', '/hotel/productos/documentos', { cookie: cCaja })
    esperar(a.estado === 403 && b.estado === 403, `${a.estado}/${b.estado}`)
    return `${a.estado}/${b.estado}`
  })
  await caso('FN-FAC-07', '/hotel/productos', 'cargar desde factura en celular (390 px)', 'administrador', 'botón «Fotografiar factura» con cámara; sin desborde', async () => {
    const p = await paginaDe(ADMIN, { width: 390, height: 844 })
    await ir(p, '/hotel/productos')
    await p.getByRole('tab', { name: 'Cargar desde factura' }).click()
    await p.waitForTimeout(800)
    const m = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth,
      cam: document.querySelector('input[capture="environment"]')?.accept }))
    await evidencia(p, 'facturas-celular')
    await p.context().close()
    esperar(m.cam === 'image/*', 'sin entrada de cámara')
    esperar(m.sw <= m.iw, `desborde ${m.sw} > ${m.iw}`)
    return `scrollWidth ${m.sw} ≤ ${m.iw}`
  })

  // ===== Celular =====
  await caso('FN-MOV-01', '/hotel/salida', 'Salida en celular (390 px): tarjetas sin desborde', 'recepcion', 'scrollWidth ≤ ancho', async () => {
    const p = await paginaDe(RECEPCION, { width: 390, height: 844 })
    await ir(p, '/hotel/salida')
    await p.getByRole('searchbox', { name: 'Buscar huésped' }).fill(APELLIDO)
    await p.waitForTimeout(1200)
    const m = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }))
    await evidencia(p, 'salida-celular')
    await p.locator(`[data-reserva="${R1}"]`).click()
    await p.waitForTimeout(1200)
    const m2 = await p.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: window.innerWidth }))
    await evidencia(p, 'salida-celular-ficha')
    await p.context().close()
    esperar(m.sw <= m.iw && m2.sw <= m2.iw, `desborde ${m.sw}/${m2.sw} > ${m.iw}`)
    return `scrollWidth ${m.sw}/${m2.sw} ≤ ${m.iw}`
  })
} catch (error) {
  console.error('ERROR FATAL', error)
  resultados.push({ id: 'FATAL', estado: 'FALLIDO', observado: error.message })
} finally {
  await navegador.close()
  writeFileSync(join(AQUI, 'e2e-funciones-resultados.json'), JSON.stringify(resultados, null, 2))
  const aprobados = resultados.filter((r) => r.estado === 'APROBADO').length
  console.log(`\n${aprobados}/${resultados.length} APROBADOS`)
  process.exit(aprobados === resultados.length ? 0 : 1)
}
