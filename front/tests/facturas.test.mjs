// Facturas de proveedores (2026-11-19): reglas puras de la bandeja.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  accionesDocumento, clasificarArchivo, costoPorUnidad, dimensionesReducidas, extrasDocumento,
  lineaConfirmacionDocumento, lineasManuales, resumenCorreo, tituloDocumento, unidadesTotales, validarEnvases,
} from '../lib/facturas.js'

test('la foto se reduce sin perder el timbre y nunca se agranda', () => {
  assert.deepEqual(dimensionesReducidas(4000, 3000), { ancho: 3200, alto: 2400, reducida: true })
  assert.deepEqual(dimensionesReducidas(1200, 1600), { ancho: 1200, alto: 1600, reducida: false })
  assert.deepEqual(dimensionesReducidas(3000, 6000, 3000), { ancho: 1500, alto: 3000, reducida: true })
})

test('clasifica foto, PDF y XML; rechaza lo demás', () => {
  assert.deepEqual(clasificarArchivo('IMG_1.HEIC', '', 5e6), { tipo: 'foto' })
  assert.deepEqual(clasificarArchivo('f.jpg', 'image/jpeg', 2e7), { tipo: 'foto' }) // se comprime antes de subir
  assert.deepEqual(clasificarArchivo('f.pdf', 'application/pdf', 1e6), { tipo: 'pdf' })
  assert.match(clasificarArchivo('f.pdf', 'application/pdf', 2e7).error, /10 MB/)
  assert.deepEqual(clasificarArchivo('DTE_33.xml', '', 1e5), { tipo: 'xml' })
  assert.match(clasificarArchivo('planilla.xlsx', '', 1e5).error, /foto, un PDF o el XML/)
})

test('envases: unidades al stock y costo por unidad', () => {
  assert.equal(unidadesTotales({ cantidad: '2', unidades_por_paquete: '24' }), 48)
  assert.equal(unidadesTotales({ cantidad: '3', unidades_por_paquete: '' }), 3)
  assert.equal(costoPorUnidad({ costo: '12000', unidades_por_paquete: '24' }), 500)
  assert.equal(costoPorUnidad({ costo: '', unidades_por_paquete: '24' }), null)
  assert.equal(validarEnvases([{ accion: 'crear', unidades_por_paquete: '0' }]), 'Las unidades por envase deben ser un número entero (1 o más).')
  assert.equal(validarEnvases([{ accion: 'omitir', unidades_por_paquete: '0' }, { accion: 'sumar', unidades_por_paquete: '6' }]), null)
})

test('la línea del documento lleva lo recordado del proveedor a la confirmación', () => {
  const extras = extrasDocumento({ nombre: 'AGUA CAJA X 24', codigo: 'CJ24', unidades_por_paquete: 24, origen_unidades: 'texto' })
  assert.equal(extras.unidades_por_paquete, '24')
  const linea = lineaConfirmacionDocumento({ ...extras, cantidad: '2' }, { accion: 'crear', nombre: 'Agua 500 ml', precio_clp: 1500 })
  assert.deepEqual(
    [linea.cantidad, linea.unidades_por_paquete, linea.nombre_proveedor, linea.codigo_proveedor, linea.recordar],
    [2, 24, 'AGUA CAJA X 24', 'CJ24', true])
})

test('qué se puede hacer según clase y estado', () => {
  assert.equal(accionesDocumento({ estado: 'pendiente', clase: 'factura' }).cargar, true)
  assert.equal(accionesDocumento({ estado: 'pendiente', clase: 'nota_credito' }).cargar, false)
  assert.match(accionesDocumento({ estado: 'borrador', clase: 'pedido' }).texto, /no suma stock/)
  assert.equal(accionesDocumento({ estado: 'cargada', clase: 'factura' }).descartar, false)
  assert.equal(tituloDocumento({ clase: 'factura', folio: '3797574' }), 'Factura N° 3797574')
  assert.equal(tituloDocumento({ clase: 'desconocido', origen: 'foto' }), 'Foto sin identificar')
})

test('líneas escritas a mano (sin lectura automática)', () => {
  assert.match(lineasManuales([{ nombre: '', cantidad: '' }]).error, /al menos una línea/)
  assert.match(lineasManuales([{ nombre: 'Torta', cantidad: '' }]).error, /cantidad de «Torta»/)
  const { lineas } = lineasManuales([{ nombre: ' Torta mil hojas ', cantidad: '1', costo: '114540', codigo: '', unidad: 'UN' }])
  assert.deepEqual(lineas[0], { nombre: 'Torta mil hojas', codigo: null, cantidad: 1, unidad: 'UN', costo_unitario_clp: 114540, monto_neto_clp: 114540 })
})

test('resumen de la revisión del correo', () => {
  assert.match(resumenCorreo({ buzones: 0 }), /Configuración/)
  assert.equal(resumenCorreo({ buzones: 1, documentos: 0, errores: 0 }), 'Correo revisado: no llegaron facturas nuevas.')
  assert.equal(resumenCorreo({ buzones: 1, documentos: 2, errores: 0 }), 'Llegaron 2 documentos nuevos por revisar.')
})

test('la pantalla ofrece cámara del celular y no agrega menú', () => {
  const fuente = readFileSync(new URL('../app/hotel/_componentes/facturas-proveedor.js', import.meta.url), 'utf8')
  assert.match(fuente, /capture="environment"/)
  assert.match(fuente, /accept="image\/\*"/)
  assert.match(fuente, /Fotografiar factura/)
  const menu = readFileSync(new URL('../lib/menu-hotel.js', import.meta.url), 'utf8')
  assert.doesNotMatch(menu, /factura|fotograf|equivalencia/i)
})

test('el correo de intercambio SII se configura como un buzón más', async () => {
  const { PROPOSITOS, PROVEEDORES, camposVisibles, formularioVacio } = await import('../lib/correo.js')
  assert.ok(PROPOSITOS.some(([id]) => id === 'recepcion_dte'))
  assert.deepEqual(PROVEEDORES.recepcion_dte.map(([id]) => id), ['imap', 'gmail_api', 'microsoft_graph'])
  const imap = camposVisibles('recepcion_dte', 'imap', 'clave').parametros
  assert.ok(imap.includes('carpeta_entrada') && !imap.includes('carpeta_enviados') && !imap.includes('remitente'))
  assert.ok(!camposVisibles('lectura_enviados', 'imap', 'clave').parametros.includes('carpeta_entrada'))
  assert.equal(formularioVacio('recepcion_dte').proveedor, 'imap')
})
