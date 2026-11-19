// Carga de productos, búsqueda de estadías y mensajes sin datos técnicos
// (2026-11-19). Reglas puras + revisión de las pantallas por su fuente.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  bloqueoSalida, fechaCorta, insigniasEstadia, pesos, resumenPago, resumenSalida, textoBuscable, rotuloLista, horaChile,
} from '../lib/estadias.js'
import {
  adivinarMapeo, decodificarXml, filaRevision, lineaParaConfirmar, lineasDesdePlanilla, numeroFlexible, parsearPlanilla,
  pareceEncabezado, resumenImportacion, resumenRevision, validarRevision,
} from '../lib/importacion.js'
import { traducirDetalle, traducirValidacion } from '../lib/mensajes.js'

const raiz = join(dirname(fileURLToPath(import.meta.url)), '..')
const leer = (p) => readFileSync(join(raiz, p), 'utf8')
function archivos(dir) {
  return readdirSync(join(raiz, dir)).flatMap((n) => {
    const rel = join(dir, n)
    if (statSync(join(raiz, rel)).isDirectory()) return archivos(rel)
    return /\.(js|jsx)$/.test(n) ? [rel] : []
  })
}

// ---------------------------------------------------------- estadías
test('fechas cortas y montos a la chilena', () => {
  assert.equal(fechaCorta('2026-11-19'), '19/11')
  assert.equal(fechaCorta('2026-11-19T13:00:00+00:00'), '19/11')
  assert.equal(fechaCorta(null), '—')
  assert.equal(pesos(1234567), '$1.234.567')
  assert.equal(pesos(-40000), '-$40.000')
  assert.equal(pesos(0), '$0')
  assert.match(horaChile('2026-11-19T17:05:00+00:00'), /^14:05$/)
})

test('texto buscable: 2 letras o un número de habitación', () => {
  assert.ok(textoBuscable(''))
  assert.ok(textoBuscable('7'))
  assert.ok(textoBuscable('pe'))
  assert.ok(!textoBuscable('p'))
  assert.equal(rotuloLista('salida', true, 3), 'Salidas de hoy y atrasadas')
  assert.equal(rotuloLista('pago', false, 1), '1 resultado')
})

test('insignias: sale hoy, atrasada, saldo y cuenta al día', () => {
  const t = (r) => insigniasEstadia(r).map((i) => i.texto)
  assert.deepEqual(t({ estado: 'en_estadia', sale_hoy: true, cuenta: { saldo_clp: 0 } }), ['Sale hoy', 'Cuenta al día'])
  assert.deepEqual(t({ estado: 'en_estadia', salida_atrasada: true, cuenta: { saldo_clp: 40000 } }), ['Salida atrasada', 'Saldo $40.000'])
  assert.deepEqual(t({ estado: 'confirmada', llega_hoy: true, cuenta: { saldo_clp: -500 } }), ['Llega hoy', 'A favor $500'])
})

test('la Salida explica por qué no se puede registrar', () => {
  assert.equal(bloqueoSalida({ estado: 'en_estadia', cuenta: { saldo_clp: 0 } }), null)
  assert.match(bloqueoSalida({ estado: 'en_estadia', cuenta: { saldo_clp: 40000 } }), /saldo pendiente de \$40\.000/)
  assert.match(bloqueoSalida({ estado: 'en_estadia', cuenta: { saldo_clp: -1000 } }), /a favor/)
  assert.match(bloqueoSalida({ estado: 'confirmada', cuenta: { saldo_clp: 0 } }), /huésped en casa/)
  assert.match(bloqueoSalida({ estado: 'finalizada', cuenta: { saldo_clp: 0 } }), /ya registró su Salida/)
})

test('resúmenes de Salida y pago en castellano, sin identificadores técnicos', () => {
  const s = resumenSalida({ total_clp: 120000, pagado_clp: 120000, reserva_id: 'RSV-1', liquidacion_id: 'LQ-x' },
    { huesped_nombre: 'José Pérez', habitacion_id: '104' })
  assert.match(s, /^Salida registrada de José Pérez: cuenta liquidada por \$120\.000/)
  assert.doesNotMatch(s, /LQ-/)
  const p = resumenPago({ pago_id: 'PAG-1', monto_clp: 50000, huesped_nombre: 'Ana', habitacion_id: '102', tipo: 'parcial', saldo_despues_clp: 10000 })
  assert.equal(p, 'Pago de $50.000 registrado para Ana (habitación 102). Saldo pendiente: $10.000.')
  assert.doesNotMatch(p, /PAG-/)
})

// ---------------------------------------------------------- importación
test('números de planilla en formato chileno o inglés', () => {
  assert.equal(numeroFlexible('1.234'), 1234)
  assert.equal(numeroFlexible('1.234,5'), 1234.5)
  assert.equal(numeroFlexible('1,234.5'), 1234.5)
  assert.equal(numeroFlexible('$ 990'), 990)
  assert.equal(numeroFlexible('2,5'), 2.5)
  assert.equal(numeroFlexible('abc'), null)
  assert.equal(numeroFlexible(''), null)
})

test('planilla pegada desde Excel: separador, encabezado y mapeo', () => {
  const { separador, filas } = parsearPlanilla('Producto\tCantidad\tCosto\tCódigo\nAgua 500 ml\t24\t650\t780123\nBebida "cola"\t12\t833\t\n')
  assert.equal(separador, '\t')
  assert.equal(filas.length, 3)
  assert.ok(pareceEncabezado(filas[0]))
  const mapeo = adivinarMapeo(filas)
  assert.deepEqual(mapeo, ['nombre', 'cantidad', 'costo', 'codigo'])
  const { lineas, errores } = lineasDesdePlanilla(filas, mapeo, true)
  assert.deepEqual(errores, [])
  assert.deepEqual(lineas[0], { nombre: 'Agua 500 ml', cantidad: 24, costo_unitario_clp: 650, codigo: '780123', unidad: null })
  assert.equal(lineas[1].codigo, null)
})

test('planilla CSV con punto y coma y comillas, sin encabezado', () => {
  const { separador, filas } = parsearPlanilla('"Maní; salado";3;1.200\nPapas;5;710')
  assert.equal(separador, ';')
  assert.equal(filas[0][0], 'Maní; salado')
  assert.ok(!pareceEncabezado(filas[0]))
  const mapeo = adivinarMapeo(filas)
  assert.deepEqual(mapeo, ['nombre', 'cantidad', 'costo'])
  const { lineas } = lineasDesdePlanilla(filas, mapeo, false)
  assert.equal(lineas[0].costo_unitario_clp, 1200)
  const malo = lineasDesdePlanilla([['Agua', 'muchas']], ['nombre', 'cantidad'], false)
  assert.match(malo.errores[0], /Fila 1: la cantidad «muchas» no es un número/)
  assert.match(lineasDesdePlanilla([['x']], ['cantidad'], false).errores[0], /nombre del producto/)
})

test('el XML se decodifica con la codificación declarada (ISO-8859-1 del SII)', () => {
  const latin = Uint8Array.from([...Buffer.from('<?xml version="1.0" encoding="ISO-8859-1"?><a>'), 0xe9, ...Buffer.from('</a>')])
  assert.equal(decodificarXml(latin).slice(-6), '<a>é</a>'.slice(-6))
  assert.equal(decodificarXml(new TextEncoder().encode('<a>ñ</a>')), '<a>ñ</a>')
})

test('revisión: propone sumar o crear, valida y arma las líneas', () => {
  const sumar = filaRevision({ linea: 1, nombre: 'Agua', cantidad: 24, costo_unitario_clp: 650, codigo: '780',
    coincidencia: { producto_id: 'PRD-1', categoria: 'minibar' }, confianza: 'codigo' })
  const crear = filaRevision({ linea: 2, nombre: 'Queso', cantidad: 1.5, unidad: 'KG', costo_unitario_clp: 9000, codigo: null, coincidencia: null })
  assert.equal(sumar.accion, 'sumar')
  assert.equal(crear.accion, 'crear')
  assert.equal(crear.cantidad, '2')
  assert.ok(crear.redondeada)
  assert.match(validarRevision([sumar, crear]), /precio de venta \(con IVA\) en 1 producto nuevo/)
  crear.precio = '2500'
  assert.equal(validarRevision([sumar, crear]), null)
  assert.deepEqual(resumenRevision([sumar, crear]), { sumar: 1, crear: 1, omitir: 0, unidades: 26 })
  assert.deepEqual(lineaParaConfirmar(sumar), { accion: 'sumar', nombre: 'Agua', cantidad: 24, codigo: '780', costo_unitario_clp: 650, producto_id: 'PRD-1', precio_clp: null })
  assert.deepEqual(lineaParaConfirmar(crear), { accion: 'crear', nombre: 'Queso', cantidad: 2, codigo: null, costo_unitario_clp: 9000, categoria: 'minibar', precio_clp: 2500, controla_stock: true })
  assert.match(validarRevision([{ ...sumar, accion: 'omitir' }]), /No cargar/)
  assert.match(validarRevision([{ ...sumar, producto_id: '' }]), /Elige el producto/)
})

test('resumen de la carga en castellano', () => {
  assert.equal(
    resumenImportacion({ creados: 2, actualizados: 1, unidades: 56, documento: { folio: '1001', emisor_razon_social: 'DISTRIBUIDORA SPA' } }),
    'Factura N° 1001 de DISTRIBUIDORA SPA cargada: 2 productos nuevos, 1 producto actualizado · 56 unidades sumadas al stock.',
  )
  assert.match(resumenImportacion({ creados: 0, actualizados: 1, unidades: 1, documento: null }), /^Carga lista: 1 producto actualizado · 1 unidad/)
})

// ---------------------------------------------------------- mensajes
test('las validaciones 422 se leen en castellano, sin rutas ni inglés', () => {
  const m = traducirValidacion([
    { type: 'greater_than', loc: ['body', 'monto_clp'], msg: 'Input should be greater than 0' },
    { type: 'missing', loc: ['body', 'nombre'], msg: 'Field required' },
  ])
  assert.equal(m, 'Revisa los datos: El monto debe ser mayor que 0; El nombre es obligatorio.')
  assert.doesNotMatch(m, /Input|Field|body/)
  const via = traducirValidacion([{ type: 'string_pattern_mismatch', loc: ['body', 'lineas', 0, 'codigo'], msg: 'String should match pattern' }])
  assert.equal(via, 'Revisa los datos: El código tiene un formato no válido.')
  assert.equal(traducirValidacion([{ type: 'raro', loc: ['body', 'otro_campo'] }]), 'Revisa los datos: El campo «otro campo» no es válido.')
})

test('detalles técnicos del servicio se reescriben para recepción', () => {
  assert.match(traducirDetalle('la cuenta tiene saldo pendiente de 40000 CLP'), /saldo pendiente de \$40\.000\. Registra el pago/)
  assert.match(traducirDetalle('check-out requiere una estadía en curso'), /La Salida solo se registra/)
  assert.match(traducirDetalle('falta la cabecera Idempotency-Key'), /Recarga la página/)
  assert.equal(traducirDetalle('rol no autorizado'), 'Tu usuario no tiene permiso para esta operación.')
  assert.equal(traducirDetalle('mensaje de negocio ya en castellano'), 'mensaje de negocio ya en castellano')
})

// ---------------------------------------------------------- pantallas
test('ninguna pantalla vuelca JSON ni claves técnicas a la vista', () => {
  for (const archivo of archivos('app')) {
    const src = leer(archivo)
    const render = src.replace(/body:\s*JSON\.stringify/g, '').replace(/JSON\.parse\(JSON\.stringify/g, '').replace(/setItem\([^)]*JSON\.stringify/g, '')
    assert.doesNotMatch(render, /JSON\.stringify/, `${archivo}: JSON.stringify en pantalla`)
    assert.doesNotMatch(src, /<pre[^>]*>\s*\{[^}]*(datos|respuesta|salida|resultado)\b/, `${archivo}: <pre> con respuesta de la API`)
    assert.doesNotMatch(src, /Claves de operación/, `${archivo}: claves técnicas visibles`)
  }
  const api = leer('lib/api.js')
  assert.doesNotMatch(api, /JSON\.stringify\(d\)/)
  assert.match(api, /if \(Array\.isArray\(detalle\)\) return traducirValidacion\(detalle\)/)
})

test('Salida y pago buscan por huésped, habitación o documento (no por código escrito)', () => {
  for (const archivo of ['app/hotel/salida/page.js', 'app/hotel/pago/page.js']) {
    const src = leer(archivo)
    assert.match(src, /<BuscadorEstadias alcance="(salida|pago)"/, archivo)
    assert.doesNotMatch(src, /etiqueta="Reserva"/, `${archivo}: campo de código a mano`)
    assert.doesNotMatch(src, /Clave del cobro/, `${archivo}: clave técnica visible`)
    assert.doesNotMatch(src, /nota-idempotencia/, `${archivo}: clave técnica en el DOM`)
  }
  const buscador = leer('app/hotel/_componentes/buscador-estadias.js')
  assert.match(buscador, /\/hotel\/estadias\/busqueda/)
  assert.match(buscador, /Nombre, habitación, documento o código/)
  assert.match(leer('app/hotel/estadia/page.js'), /<BuscadorEstadias alcance="llegada"/)
})

test('Productos carga desde factura, planilla o lector en pestañas, sin entradas nuevas al menú', () => {
  const src = leer('app/hotel/productos/page.js')
  for (const t of ['Cargar desde factura', 'Pegar planilla', 'Lector de códigos']) assert.match(src, new RegExp(t))
  assert.match(src, /role="tablist"/)
  const menu = leer('lib/menu-hotel.js')
  assert.doesNotMatch(menu, /importa|factura|lector/i)
  const imp = leer('app/hotel/_componentes/importar-productos.js')
  assert.match(imp, /\/hotel\/productos\/importacion\/vista-previa/)
  assert.match(imp, /<FacturasProveedor /)
  assert.match(leer('app/hotel/_componentes/facturas-proveedor.js'), /\/hotel\/productos\/documentos\/archivo/)
})
