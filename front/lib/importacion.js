// Carga amigable de productos (2026-11-19): lectura de planillas pegadas,
// del XML de la factura y armado de la revisión. Puro, sin JSX.

export const CAMPOS_PLANILLA = [
  ['ignorar', 'No usar'],
  ['nombre', 'Nombre del producto'],
  ['cantidad', 'Cantidad'],
  ['costo', 'Costo unitario (neto)'],
  ['codigo', 'Código'],
  ['unidad', 'Unidad'],
]

/** Número escrito a la chilena o a la inglesa: «1.234,5», «1,234.5», «$ 990». */
export function numeroFlexible(texto) {
  if (texto === null || texto === undefined) return null
  let t = String(texto).replace(/[$\s]/g, '').replace(/CLP/i, '')
  if (!t) return null
  const coma = t.lastIndexOf(',')
  const punto = t.lastIndexOf('.')
  if (coma > -1 && punto > -1) {
    t = coma > punto ? t.replace(/\./g, '').replace(',', '.') : t.replace(/,/g, '')
  } else if (coma > -1) {
    t = /,\d{3}$/.test(t) && t.split(',').length > 2 ? t.replace(/,/g, '') : t.replace(',', '.')
  } else if (punto > -1 && /^\d{1,3}(\.\d{3})+$/.test(t)) {
    t = t.replace(/\./g, '')
  }
  const n = Number(t)
  return Number.isFinite(n) ? n : null
}

/** Divide el texto pegado en filas y columnas (tabulador, punto y coma o coma). */
export function parsearPlanilla(texto) {
  const lineas = String(texto || '').replace(/\r/g, '').split('\n').filter((l) => l.trim() !== '')
  if (!lineas.length) return { separador: null, filas: [] }
  const muestra = lineas.slice(0, 5).join('\n')
  const separador = muestra.includes('\t') ? '\t' : (muestra.split(';').length >= muestra.split(',').length ? ';' : ',')
  const filas = lineas.map((l) => partirLinea(l, separador).map((c) => c.trim()))
  return { separador, filas }
}

function partirLinea(linea, sep) {
  const out = []
  let actual = ''
  let comillas = false
  for (let i = 0; i < linea.length; i += 1) {
    const c = linea[i]
    if (c === '"') {
      if (comillas && linea[i + 1] === '"') { actual += '"'; i += 1 } else comillas = !comillas
    } else if (c === sep && !comillas) {
      out.push(actual)
      actual = ''
    } else actual += c
  }
  out.push(actual)
  return out
}

const PISTAS = [
  ['nombre', /(nombre|producto|descrip|detalle|art[ií]culo|item)/i],
  ['cantidad', /(cant|qty|unidades|uds)/i],
  ['costo', /(costo|precio|valor|neto|unit)/i],
  ['codigo', /(c[oó]d|sku|ean|barra)/i],
  ['unidad', /(unidad|um|medida)/i],
]

/** ¿La primera fila parece encabezado? (sin números en las columnas). */
export function pareceEncabezado(fila) {
  return Boolean(fila && fila.length && fila.every((c) => numeroFlexible(c) === null) && fila.some((c) => PISTAS.some(([, re]) => re.test(c))))
}

/** Mapeo inicial de columnas a partir del encabezado o del contenido. */
export function adivinarMapeo(filas) {
  if (!filas.length) return []
  const primera = filas[0]
  const usados = new Set()
  if (pareceEncabezado(primera)) {
    return primera.map((c) => {
      const hit = PISTAS.find(([campo, re]) => !usados.has(campo) && re.test(c))
      if (!hit) return 'ignorar'
      usados.add(hit[0])
      return hit[0]
    })
  }
  // Sin encabezado: la primera columna con texto es el nombre; luego números.
  return primera.map((c) => {
    const n = numeroFlexible(c)
    if (n === null && !usados.has('nombre')) { usados.add('nombre'); return 'nombre' }
    if (n !== null && !usados.has('cantidad')) { usados.add('cantidad'); return 'cantidad' }
    if (n !== null && !usados.has('costo')) { usados.add('costo'); return 'costo' }
    return 'ignorar'
  })
}

/** Filas + mapeo → líneas para la API (máximo 300). Devuelve {lineas, errores}. */
export function lineasDesdePlanilla(filas, mapeo, conEncabezado) {
  const errores = []
  if (!mapeo.includes('nombre')) return { lineas: [], errores: ['Indica qué columna trae el nombre del producto.'] }
  const datos = conEncabezado ? filas.slice(1) : filas
  const lineas = []
  datos.forEach((fila, i) => {
    const valor = (campo) => {
      const idx = mapeo.indexOf(campo)
      return idx >= 0 ? fila[idx] : undefined
    }
    const nombre = (valor('nombre') || '').trim()
    if (!nombre) return
    const cantidad = mapeo.includes('cantidad') ? numeroFlexible(valor('cantidad')) : 1
    if (cantidad === null || cantidad < 0) {
      errores.push(`Fila ${i + 1 + (conEncabezado ? 1 : 0)}: la cantidad «${valor('cantidad') || ''}» no es un número.`)
      return
    }
    const costo = mapeo.includes('costo') ? numeroFlexible(valor('costo')) : null
    const codigo = (valor('codigo') || '').trim().replace(/\s+/g, '')
    lineas.push({
      nombre: nombre.slice(0, 120),
      cantidad,
      costo_unitario_clp: costo !== null && costo >= 0 ? Math.round(costo) : null,
      codigo: /^[A-Za-z0-9._/-]{1,60}$/.test(codigo) ? codigo : null,
      unidad: (valor('unidad') || '').slice(0, 20) || null,
    })
  })
  if (lineas.length > 300) errores.push('Son más de 300 filas: divide la planilla en partes.')
  return { lineas: lineas.slice(0, 300), errores }
}

/** Decodifica el XML respetando la codificación declarada (el SII usa ISO-8859-1). */
export function decodificarXml(bytes) {
  const cabecera = new TextDecoder('latin1').decode(bytes.slice(0, 200))
  const m = /encoding=["']([A-Za-z0-9_-]+)["']/i.exec(cabecera)
  const cod = m ? m[1].toLowerCase() : 'utf-8'
  try {
    return new TextDecoder(cod === 'iso-8859-1' || cod === 'latin1' ? 'latin1' : cod).decode(bytes)
  } catch {
    return new TextDecoder('utf-8').decode(bytes)
  }
}

const CONFIANZA = {
  codigo: { texto: 'Mismo código', tono: 'exito' },
  nombre: { texto: 'Mismo nombre', tono: 'exito' },
  parecido: { texto: 'Parecido: revisa', tono: 'aviso' },
  recordado: { texto: 'Recordado del proveedor', tono: 'exito' },
}

export function etiquetaConfianza(linea) {
  if (linea.accion === 'crear') return { texto: 'Producto nuevo', tono: 'info' }
  if (linea.accion === 'omitir') return { texto: 'No se carga', tono: 'neutro' }
  return CONFIANZA[linea.confianza] || { texto: 'Elegido a mano', tono: 'neutro' }
}

/** Línea de la vista previa → fila editable de la revisión. */
export function filaRevision(linea) {
  const cantidadOriginal = Number(linea.cantidad) || 0
  const cantidad = Math.max(0, Math.round(cantidadOriginal))
  const coincidencia = linea.coincidencia
  return {
    linea: linea.linea,
    accion: coincidencia ? 'sumar' : 'crear',
    producto_id: coincidencia ? coincidencia.producto_id : '',
    confianza: linea.confianza,
    puntaje: linea.puntaje,
    nombre_factura: linea.nombre,
    nombre: linea.nombre,
    codigo: linea.codigo || '',
    unidad: linea.unidad || '',
    cantidad: String(cantidad),
    redondeada: cantidad !== cantidadOriginal,
    cantidad_original: cantidadOriginal,
    costo: linea.costo_unitario_clp ?? '',
    precio: coincidencia ? '' : '',
    categoria: coincidencia ? coincidencia.categoria : 'minibar',
    controla_stock: true,
  }
}

export function resumenRevision(filas) {
  const activas = filas.filter((f) => f.accion !== 'omitir')
  return {
    sumar: filas.filter((f) => f.accion === 'sumar').length,
    crear: filas.filter((f) => f.accion === 'crear').length,
    omitir: filas.length - activas.length,
    unidades: activas.reduce((s, f) => s + (Number(f.cantidad) || 0), 0),
  }
}

/** Mensaje de lo que falta antes de confirmar, o null. */
export function validarRevision(filas) {
  const activas = filas.filter((f) => f.accion !== 'omitir')
  if (!activas.length) return 'Todas las líneas están en «No cargar». Elige al menos una.'
  const sinProducto = activas.filter((f) => f.accion === 'sumar' && !f.producto_id)
  if (sinProducto.length) return `Elige el producto al que se suman ${sinProducto.length === 1 ? '1 línea' : `${sinProducto.length} líneas`}.`
  const sinPrecio = activas.filter((f) => f.accion === 'crear' && !(Number(f.precio) > 0))
  if (sinPrecio.length) {
    return `Falta el precio de venta (con IVA) en ${sinPrecio.length === 1 ? '1 producto nuevo' : `${sinPrecio.length} productos nuevos`}.`
  }
  const sinNombre = activas.filter((f) => f.accion === 'crear' && f.nombre.trim().length < 2)
  if (sinNombre.length) return 'Escribe el nombre de cada producto nuevo.'
  const malCantidad = activas.filter((f) => !Number.isInteger(Number(f.cantidad)) || Number(f.cantidad) < 0)
  if (malCantidad.length) return 'Las cantidades deben ser números enteros (0 o más).'
  return null
}

/** Fila de la revisión → línea que acepta POST /hotel/productos/importacion. */
export function lineaParaConfirmar(f) {
  const base = {
    accion: f.accion,
    nombre: (f.nombre || f.nombre_factura || '').trim().slice(0, 120) || 'Producto',
    cantidad: Math.max(0, Math.round(Number(f.cantidad) || 0)),
    codigo: /^[A-Za-z0-9._/-]{1,60}$/.test(f.codigo || '') ? f.codigo : null,
    costo_unitario_clp: f.costo === '' || f.costo === null ? null : Math.max(0, Math.round(Number(f.costo) || 0)),
  }
  if (base.nombre.length < 2) base.nombre = `Producto ${base.nombre}`
  if (f.accion === 'sumar') return { ...base, producto_id: f.producto_id, precio_clp: Number(f.precio) > 0 ? Math.round(Number(f.precio)) : null }
  if (f.accion === 'crear') {
    return { ...base, categoria: f.categoria, precio_clp: Math.round(Number(f.precio)), controla_stock: Boolean(f.controla_stock) }
  }
  return base
}

export function resumenImportacion(r) {
  const partes = []
  if (r.creados) partes.push(r.creados === 1 ? '1 producto nuevo' : `${r.creados} productos nuevos`)
  if (r.actualizados) partes.push(r.actualizados === 1 ? '1 producto actualizado' : `${r.actualizados} productos actualizados`)
  const unidades = r.unidades === 1 ? '1 unidad sumada al stock' : `${r.unidades} unidades sumadas al stock`
  const origen = r.documento
    ? `Factura N° ${r.documento.folio} de ${r.documento.emisor_razon_social || r.documento.emisor_rut} cargada`
    : 'Carga lista'
  return `${origen}: ${partes.join(', ') || 'sin cambios de productos'} · ${unidades}.`
}
