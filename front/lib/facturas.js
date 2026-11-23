// Facturas de proveedores (2026-11-19): reglas puras de la bandeja, sin JSX
// para probarlas con node --test.

export const MAX_ARCHIVO = 10 * 1024 * 1024
/** Lado mayor de la foto que se sube: suficiente para leer el timbre del SII
 *  (~3 px por módulo del PDF417) y liviana para el celular. */
export const LADO_MAXIMO_FOTO = 3200
export const CALIDAD_FOTO = 0.9
const IMAGENES = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']

/** Dimensiones reducidas manteniendo proporción (nunca agranda). */
export function dimensionesReducidas(ancho, alto, maximo = LADO_MAXIMO_FOTO) {
  const mayor = Math.max(ancho, alto)
  if (!mayor || mayor <= maximo) return { ancho, alto, reducida: false }
  const f = maximo / mayor
  return { ancho: Math.round(ancho * f), alto: Math.round(alto * f), reducida: true }
}

/** Qué hacer con un archivo elegido: 'foto' | 'pdf' | 'xml' | mensaje de error. */
export function clasificarArchivo(nombre, tipo, tamano) {
  const n = String(nombre || '').toLowerCase()
  const t = String(tipo || '').toLowerCase()
  if (n.endsWith('.xml') || t === 'text/xml' || t === 'application/xml') {
    return tamano > 1_500_000 ? { error: 'El XML es demasiado grande para una factura (máximo 1,5 MB).' } : { tipo: 'xml' }
  }
  if (t === 'application/pdf' || n.endsWith('.pdf')) {
    return tamano > MAX_ARCHIVO ? { error: 'El PDF es demasiado grande (máximo 10 MB).' } : { tipo: 'pdf' }
  }
  if (IMAGENES.includes(t) || /\.(jpe?g|png|webp|heic|heif)$/.test(n)) return { tipo: 'foto' }
  return { error: 'Sube una foto, un PDF o el XML de la factura.' }
}

const CLASES = {
  factura: 'Factura', nota_credito: 'Nota de crédito', pedido: 'Pedido', desconocido: 'Por identificar',
}
const ESTADOS = {
  pendiente: { texto: 'Por revisar', tono: 'aviso' },
  borrador: { texto: 'Borrador (sin stock)', tono: 'neutro' },
  cargada: { texto: 'Cargada', tono: 'exito' },
  facturado: { texto: 'Facturado', tono: 'exito' },
  archivada: { texto: 'Archivada', tono: 'neutro' },
  descartada: { texto: 'Descartada', tono: 'neutro' },
  aplicada: { texto: 'Aplicada', tono: 'exito' },
}
const ORIGENES = { correo: 'Correo SII', foto: 'Foto', pdf: 'PDF', xml: 'XML' }
const LECTURAS = {
  xml: 'Leída del XML del SII',
  ia: 'Leída automáticamente: revisa',
  timbre: 'Identificada por el timbre del SII; faltan las líneas',
  manual: 'Escrita a mano',
}

export const etiquetaClase = (c) => CLASES[c] || 'Documento'
export const etiquetaEstado = (e) => ESTADOS[e] || { texto: e, tono: 'neutro' }
export const etiquetaOrigen = (o) => ORIGENES[o] || o
export const etiquetaLectura = (l) => LECTURAS[l] || ''

/** «Factura N° 3797574» / «Pedido N° 21027» / «Foto sin identificar». */
export function tituloDocumento(d) {
  const clase = etiquetaClase(d.clase)
  if (d.folio) return `${clase} N° ${d.folio}`
  return d.clase === 'desconocido' ? `${etiquetaOrigen(d.origen)} sin identificar` : clase
}

export function proveedorDocumento(d) {
  return d.emisor_razon_social || d.emisor_rut || 'Proveedor por confirmar'
}

/** Qué se puede hacer con un documento de la bandeja. */
export function accionesDocumento(d) {
  if (d.estado === 'borrador') return { cargar: false, descartar: true, texto: 'Pedido: no suma stock. Se cierra cuando llegue la factura.' }
  if (d.estado !== 'pendiente') return { cargar: false, descartar: false, texto: '' }
  if (d.clase === 'nota_credito') return { cargar: false, aplicar: true, descartar: true, texto: 'Nota de crédito: elige qué unidades se devuelven al proveedor. Al aplicarla baja el stock y se rebaja lo que se le debe. Si no corresponde, archívala.' }
  if (d.clase === 'desconocido') return { cargar: false, descartar: true, texto: 'Indica si es una factura, una nota de crédito o un pedido.' }
  return { cargar: true, descartar: true, texto: '' }
}

const ORIGEN_UNIDADES = {
  recordado: 'Recordado de este proveedor',
  texto: 'Sugerido por la descripción',
  nota: 'Según la anotación a mano',
}
export const textoOrigenUnidades = (o) => ORIGEN_UNIDADES[o] || ''

/** Unidades que entran al stock: cantidad de envases × unidades por envase. */
export function unidadesTotales(fila) {
  const cantidad = Math.max(0, Number(fila.cantidad) || 0)
  const factor = Math.max(1, Math.round(Number(fila.unidades_por_paquete) || 1))
  return Math.round(cantidad * factor)
}

/** Costo por unidad a partir del costo del envase (para mostrar). */
export function costoPorUnidad(fila) {
  const costo = Number(fila.costo)
  if (fila.costo === '' || fila.costo === null || Number.isNaN(costo)) return null
  return Math.round(costo / Math.max(1, Math.round(Number(fila.unidades_por_paquete) || 1)))
}

/** Línea del documento (con lo recordado del proveedor) → campos extra de la fila. */
export function extrasDocumento(linea) {
  return {
    unidades_por_paquete: String(linea.unidades_por_paquete || 1),
    origen_unidades: linea.origen_unidades || null,
    unidades_nota: linea.unidades_nota || null,
    nota: linea.nota || '',
    nombre_proveedor: linea.nombre,
    codigo_proveedor: linea.codigo || '',
    recordar: true,
  }
}

/** Fila revisada → línea para POST /hotel/productos/documentos/{id}/confirmacion. */
export function lineaConfirmacionDocumento(f, base) {
  const linea = {
    ...base,
    cantidad: Math.max(0, Number(f.cantidad) || 0),
    unidades_por_paquete: Math.max(1, Math.min(10000, Math.round(Number(f.unidades_por_paquete) || 1))),
    nombre_proveedor: (f.nombre_proveedor || '').slice(0, 120) || null,
    codigo_proveedor: (f.codigo_proveedor || '').slice(0, 60) || null,
    recordar: f.recordar !== false,
  }
  return linea
}

/** Validación extra del modo documento (envases). */
export function validarEnvases(filas) {
  const malas = filas.filter((f) => f.accion !== 'omitir'
    && (!Number.isInteger(Number(f.unidades_por_paquete)) || Number(f.unidades_por_paquete) < 1))
  return malas.length ? 'Las unidades por envase deben ser un número entero (1 o más).' : null
}

/** Fila vacía del editor de líneas a mano (sin lectura automática). */
export function lineaManualVacia() {
  return { nombre: '', codigo: '', cantidad: '', unidad: '', costo: '' }
}

/** Filas del editor a mano → líneas para PUT del documento; o {error}. */
export function lineasManuales(filas) {
  const usadas = filas.filter((f) => String(f.nombre || '').trim())
  if (!usadas.length) return { error: 'Escribe al menos una línea con su descripción.' }
  for (const f of usadas) {
    if (!(Number(f.cantidad) > 0)) return { error: `Falta la cantidad de «${f.nombre.trim()}».` }
  }
  return {
    lineas: usadas.map((f) => {
      const cantidad = Number(f.cantidad)
      const costo = f.costo === '' ? null : Math.max(0, Math.round(Number(f.costo) || 0))
      return {
        nombre: f.nombre.trim().slice(0, 120),
        codigo: String(f.codigo || '').trim().slice(0, 60) || null,
        cantidad,
        unidad: String(f.unidad || '').trim().slice(0, 20) || null,
        costo_unitario_clp: costo,
        monto_neto_clp: costo === null ? null : Math.round(costo * cantidad),
      }
    }),
  }
}

/** Resumen de la revisión del correo. */
export function resumenCorreo(r) {
  if (r.buzones === 0) return 'No hay un buzón de intercambio configurado (Configuración → Correo).'
  if (r.errores) return 'No se pudo revisar el correo. Revisa la configuración del buzón.'
  if (!r.documentos) return 'Correo revisado: no llegaron facturas nuevas.'
  return r.documentos === 1 ? 'Llegó 1 documento nuevo por revisar.' : `Llegaron ${r.documentos} documentos nuevos por revisar.`
}

/** Filas de la nota de crédito (líneas del documento con su coincidencia) → campos editables. */
export function filasNotaCredito(lineas) {
  return (lineas || []).map((l) => ({
    nombre: l.nombre || '',
    producto_id: l.coincidencia?.producto_id || '',
    cantidad: String(l.cantidad ?? 0),
    unidades_por_paquete: String(l.unidades_por_paquete || 1),
    descontar: Boolean(l.coincidencia?.producto_id),
  }))
}

/** Filas revisadas → líneas para POST /hotel/productos/documentos/{id}/aplicacion. */
export function lineasAplicacion(filas) {
  return filas.map((f) => (f.descontar
    ? {
        accion: 'descontar',
        producto_id: f.producto_id || null,
        nombre: (f.nombre || '').slice(0, 120) || null,
        cantidad: Math.max(0, Number(f.cantidad) || 0),
        unidades_por_paquete: Math.max(1, Math.min(10000, Math.round(Number(f.unidades_por_paquete) || 1))),
      }
    : { accion: 'omitir', nombre: (f.nombre || '').slice(0, 120) || null }))
}

/** Problema que impide aplicar la nota (o null): producto elegido y cantidad positiva en cada línea a descontar. */
export function problemaAplicacion(filas) {
  for (const f of filas) {
    if (!f.descontar) continue
    if (!f.producto_id) return `Elige el producto de «${f.nombre || 'la línea'}» o desmarca «Devolver».`
    if (!(Number(f.cantidad) > 0)) return `La cantidad de «${f.nombre || 'la línea'}» debe ser mayor que cero.`
    if (!Number.isInteger(Number(f.unidades_por_paquete)) || Number(f.unidades_por_paquete) < 1)
      return 'Las unidades por envase deben ser un número entero (1 o más).'
  }
  return null
}
