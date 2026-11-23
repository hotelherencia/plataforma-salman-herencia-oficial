/**
 * Reglas puras de /reservar (sin React), para poder probarlas con `node --test`:
 * lista blanca de parámetros de la URL, referencia opaca de la landing y
 * presentación de la oferta agrupada por tipo.
 */

export const MAX_PERSONAS = 30
export const MAX_NOCHES = 30
export const CLAVE_REFERENCIA = 'herencia:consulta-ref'
export const HORAS_REFERENCIA = 72
export const WHATSAPP = '56956491501'
const PATRON_FECHA = /^\d{4}-\d{2}-\d{2}$/
const PATRON_REFERENCIA = /^[A-Za-z0-9_-]{20,128}$/
const PATRON_CORREO = /^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$/
const PATRON_TELEFONO = /^[+\d\s().-]+$/

/** Nombres visibles de los tipos; los códigos de la base no cambian. */
export const NOMBRE_TIPO = {
  single: 'Single',
  doble: 'Doble',
  matrimonial: 'Matrimonial',
  matrimonial_mas_1: 'Matrimonial + 1',
  triple: 'Triple',
}

export function nombreTipo(codigo) {
  if (Object.prototype.hasOwnProperty.call(NOMBRE_TIPO, codigo)) return NOMBRE_TIPO[codigo]
  const texto = String(codigo || '').replace(/_mas_/g, ' + ').replace(/_/g, ' ').trim()
  return texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : 'Habitación'
}

function dosDigitos(n) {
  return String(n).padStart(2, '0')
}

export function isoLocal(d) {
  return `${d.getFullYear()}-${dosDigitos(d.getMonth() + 1)}-${dosDigitos(d.getDate())}`
}

/** Fecha ISO que existe en el calendario (2026-02-31 no pasa). */
export function fechaIso(valor) {
  if (typeof valor !== 'string' || !PATRON_FECHA.test(valor)) return false
  const d = new Date(`${valor}T00:00:00`)
  return !Number.isNaN(d.getTime()) && isoLocal(d) === valor
}

export function personasValidas(valor) {
  return /^\d{1,2}$/.test(String(valor)) && Number(valor) >= 1 && Number(valor) <= MAX_PERSONAS
}

export function referenciaValida(valor) {
  return typeof valor === 'string' && PATRON_REFERENCIA.test(valor)
}

export function validarRango(inicio, fin, personas, hoy) {
  if (!inicio || !fin) return 'Indica las fechas de tu estadía.'
  if (!fechaIso(inicio) || !fechaIso(fin)) return 'Indica fechas válidas.'
  if (fin <= inicio) return 'La salida debe ser posterior a la llegada.'
  if (inicio < hoy) return 'La llegada no puede ser una fecha pasada.'
  if ((new Date(`${fin}T00:00:00`) - new Date(`${inicio}T00:00:00`)) / 86400000 > MAX_NOCHES)
    return 'El rango supera las 30 noches.'
  const n = Number(personas)
  if (!Number.isInteger(n) || n < 1 || n > MAX_PERSONAS) return 'Personas debe estar entre 1 y 30.'
  return null
}

/**
 * Lista blanca de la query: llegada (alias inicio), salida (alias fin), personas y ref.
 * Lo inválido se descarta (nunca se refleja el valor crudo); `avisos` dice qué
 * se descartó con textos fijos.
 */
export function leerParametros(params) {
  const tomar = (...nombres) => {
    for (const n of nombres) {
      const v = params.get(n)
      if (v != null && v !== '') return v
    }
    return ''
  }
  // Canónicos: llegada/salida. inicio/fin solo como alias de enlaces antiguos.
  const crudoInicio = tomar('llegada', 'inicio')
  const crudoFin = tomar('salida', 'fin')
  const crudoPersonas = tomar('personas')
  const crudoRef = tomar('ref')
  // landinpage#1: la tarjeta de la landing pide un tipo (código, sin PII).
  const crudoTipo = tomar('tipo')
  const tipo = /^[a-z0-9_]{2,40}$/.test(crudoTipo) ? crudoTipo : ''
  const avisos = []
  const inicio = fechaIso(crudoInicio) ? crudoInicio : ''
  const fin = fechaIso(crudoFin) ? crudoFin : ''
  const personas = personasValidas(crudoPersonas) ? String(Number(crudoPersonas)) : ''
  if (crudoInicio && !inicio) avisos.push('La llegada indicada en el enlace no es válida.')
  if (crudoFin && !fin) avisos.push('La salida indicada en el enlace no es válida.')
  if (crudoPersonas && !personas) avisos.push('La cantidad de personas del enlace no es válida.')
  const ref = referenciaValida(crudoRef) ? crudoRef : ''
  const limpiar = params.get('limpiar') === '1'
  return { inicio, fin, personas, ref, tipo, limpiar, avisos }
}

/**
 * landinpage#1: preselecciona el tipo pedido si tiene cupo; si no, elige el
 * primero disponible y explica por qué (sin prometer números de habitación).
 */
export function elegirTipo(grupos, preferido) {
  if (!grupos.length) return { tipo: '', aviso: '' }
  if (preferido && grupos.some((g) => g.tipo === preferido)) return { tipo: preferido, aviso: '' }
  const aviso = preferido
    ? `No queda cupo en ${nombreTipo(preferido)} para esas fechas; te mostramos los otros tipos disponibles.`
    : ''
  return { tipo: grupos[0].tipo, aviso }
}

/**
 * URL canónica de /reservar: solo llegada, salida y personas válidas (sin `ref`,
 * sin alias inicio/fin, sin parámetros ajenos). null si ya es canónica.
 */
export function urlCanonica(href, { inicio, fin, personas, tipo }) {
  const url = new URL(href)
  const q = new URLSearchParams()
  if (inicio) q.set('llegada', inicio)
  if (fin) q.set('salida', fin)
  if (personas) q.set('personas', personas)
  if (tipo) q.set('tipo', tipo)
  const destino = `${url.pathname}${q.toString() ? `?${q}` : ''}`
  return destino === `${url.pathname}${url.search}` ? null : destino
}

export function guardarReferencia(almacen, ref, ahora = Date.now()) {
  if (!almacen || !referenciaValida(ref)) return false
  try {
    almacen.setItem(CLAVE_REFERENCIA, JSON.stringify({ ref, expira: ahora + HORAS_REFERENCIA * 3600000 }))
    return true
  } catch {
    return false
  }
}

export function leerReferencia(almacen, ahora = Date.now()) {
  if (!almacen) return ''
  try {
    const datos = JSON.parse(almacen.getItem(CLAVE_REFERENCIA) || 'null')
    if (datos && referenciaValida(datos.ref) && Number.isFinite(datos.expira) && datos.expira > ahora) return datos.ref
  } catch {
    // valor corrupto: se descarta
  }
  olvidarReferencia(almacen)
  return ''
}

export function olvidarReferencia(almacen) {
  try {
    almacen?.removeItem(CLAVE_REFERENCIA)
  } catch {
    // sin almacenamiento
  }
}

/** Valida que el teléfono sea obligatorio y tenga entre 8 y 15 dígitos. */
export function errorTelefono(telefono) {
  const t = String(telefono || '').trim()
  if (!t) return 'Escribe tu número de teléfono.'
  if (t.length > 30) return 'El teléfono admite hasta 30 caracteres.'
  const digitos = t.replace(/\D/g, '')
  if (!PATRON_TELEFONO.test(t) || digitos.length < 8 || digitos.length > 15) {
    return 'Escribe un teléfono válido de 8 a 15 dígitos.'
  }
  return undefined
}

/** Valida que el correo sea obligatorio y tenga formato válido. */
export function errorCorreo(correo) {
  const c = String(correo || '').trim()
  if (!c) return 'Escribe tu correo electrónico.'
  if (c.length > 120) return 'El correo admite hasta 120 caracteres.'
  if (!PATRON_CORREO.test(c)) return 'Revisa el correo: parece incompleto.'
  return undefined
}

/** Valida el RUT o pasaporte si se entrega (es opcional en la solicitud pública, #414). */
export function errorDocumento(documento) {
  const d = String(documento || '').trim()
  if (!d) return undefined
  if (d.length < 5 || d.length > 30) return 'Escribe un RUT o pasaporte válido.'
  return undefined
}

/** Errores por campo del formulario de solicitud (textos fijos). */
export function erroresContacto(nombre, contacto, telefono, documento) {
  const errores = {}
  const n = String(nombre || '').trim()
  const c = String(contacto || '').trim()
  if (!n) errores.nombre = 'Escribe tu nombre.'
  else if (n.length > 120) errores.nombre = 'El nombre admite hasta 120 caracteres.'
  if (telefono !== undefined || documento !== undefined) {
    const errCorreo = errorCorreo(c)
    if (errCorreo) errores.contacto = errCorreo
    const errTel = errorTelefono(telefono)
    if (errTel) errores.telefono = errTel
    if (documento !== undefined) {
      const errDoc = errorDocumento(documento)
      if (errDoc) errores.documento = errDoc
    }
  } else {
    if (!c) errores.contacto = 'Escribe un correo o un teléfono.'
    else if (c.length > 120) errores.contacto = 'El contacto admite hasta 120 caracteres.'
    else if (c.includes('@')) {
      if (!PATRON_CORREO.test(c)) errores.contacto = 'Revisa el correo: parece incompleto.'
    } else {
      const digitos = c.replace(/\D/g, '')
      if (!PATRON_TELEFONO.test(c) || digitos.length < 8 || digitos.length > 15)
        errores.contacto = 'Escribe un correo o un teléfono de 8 a 15 dígitos.'
    }
  }
  return errores
}

/**
 * Agrupa la oferta por tipo: una opción por tipo con su capacidad, cuántas
 * quedan y el precio (desde el menor). La solicitud se envía por TIPO (#346):
 * el visitante nunca elige ni ve un número; el hotel asigna la unidad.
 */
export function agruparOferta(items) {
  const grupos = new Map()
  for (const item of items || []) {
    const g = grupos.get(item.tipo) || {
      tipo: item.tipo,
      nombre: nombreTipo(item.tipo),
      capacidad: item.capacidad ?? null,
      disponibles: 0,
      tarifa_noche_clp: item.tarifa_noche_clp,
      total_clp: item.total_clp,
      precios_distintos: false,
    }
    g.disponibles += 1
    if (item.total_clp !== g.total_clp) g.precios_distintos = true
    if (item.total_clp < g.total_clp) {
      g.total_clp = item.total_clp
      g.tarifa_noche_clp = item.tarifa_noche_clp
    }
    if (item.capacidad != null && (g.capacidad == null || item.capacidad > g.capacidad)) g.capacidad = item.capacidad
    grupos.set(item.tipo, g)
  }
  return [...grupos.values()].sort((a, b) => a.total_clp - b.total_clp || a.nombre.localeCompare(b.nombre))
}

/** Política de cancelación una sola vez (si todas coinciden) o null. */
export function politicaUnica(items) {
  const politicas = new Set((items || []).map((i) => i.politica_cancelacion).filter(Boolean))
  return politicas.size === 1 ? [...politicas][0] : null
}

/** WhatsApp con fechas y personas validadas; nunca datos personales. */
export function enlaceWhatsapp(inicio, fin, personas) {
  const partes = ['Hola, quiero consultar disponibilidad en Hotel Herencia']
  if (personasValidas(personas)) partes.push(`para ${Number(personas)} personas`)
  if (fechaIso(inicio) && fechaIso(fin) && fin > inicio) partes.push(`del ${inicio} al ${fin}`)
  return `https://wa.me/${WHATSAPP}?text=${encodeURIComponent(`${partes.join(' ')}.`)}`
}
