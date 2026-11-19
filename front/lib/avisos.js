/**
 * Configuración → Avisos (2026-11-19): qué eventos avisan por correo y a
 * quién, y cómo se muestran los últimos envíos. Funciones puras (se prueban
 * en tests/avisos.test.mjs); la pantalla vive en _componentes/ajustes-avisos.js.
 */

export const MAX_DESTINATARIOS = 10

// estado de la API → [texto en pantalla, clase de la etiqueta]
export const ESTADOS_ENVIO = {
  enviado: ['Enviado', 'estado-confirmada'],
  reintentando: ['Reintentando', 'estado-en_estadia'],
  fallido: ['Falló', 'estado-cancelada'],
  omitido: ['No enviado', 'estado-finalizada'],
}

export function estadoEnvio(estado) {
  return ESTADOS_ENVIO[estado] || ['Pendiente', 'estado-finalizada']
}

const NOMBRE_CANAL = { correo: 'Correo', whatsapp: 'WhatsApp' }
export const nombreCanal = (canal) => NOMBRE_CANAL[canal] || canal

const RE_CORREO = /^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$/

/** Texto escrito (comas, punto y coma, espacios o saltos de línea) →
 *  { correos: únicos en minúscula, invalidos: lo que no parece correo }. */
export function leerCorreos(texto) {
  const correos = []
  const invalidos = []
  for (const parte of String(texto || '').split(/[\s,;]+/)) {
    const c = parte.trim().toLowerCase()
    if (!c) continue
    if (!RE_CORREO.test(c)) invalidos.push(parte.trim())
    else if (!correos.includes(c)) correos.push(c)
  }
  return { correos, invalidos }
}

/** Lista de la API → filas editables { tipo, nombre, descripcion, activo, texto }. */
export function filasDesdeApi(preferencias) {
  return (preferencias || []).map((p) => ({
    tipo: p.tipo, nombre: p.nombre, descripcion: p.descripcion, activo: Boolean(p.activo),
    texto: (p.destinatarios || []).join(', '),
  }))
}

/** Valida todo antes de guardar. Devuelve { cuerpo } o { error } en castellano. */
export function cuerpoPreferencias(filas, maximo = MAX_DESTINATARIOS) {
  const preferencias = []
  for (const f of filas) {
    const { correos, invalidos } = leerCorreos(f.texto)
    if (invalidos.length) return { error: `${f.nombre}: «${invalidos[0]}» no parece un correo.` }
    if (correos.length > maximo) return { error: `${f.nombre}: máximo ${maximo} destinatarios.` }
    preferencias.push({ tipo: f.tipo, activo: Boolean(f.activo), destinatarios: correos })
  }
  return { cuerpo: { preferencias } }
}

/** A quién llega cada aviso, en una frase. */
export function aQuienLlega(fila, defecto) {
  if (!fila.activo) return 'Apagado: no se envía.'
  const { correos } = leerCorreos(fila.texto)
  if (correos.length) return `Llega a ${correos.join(', ')}.`
  if (defecto?.length) return `Sin lista propia: llega al correo por defecto (${defecto.join(', ')}).`
  return 'Sin destinatarios: agrega al menos un correo o un destino en el buzón de envío.'
}

/** Desde dónde salen los correos, sin datos técnicos. */
export function textoCanal(canal) {
  if (!canal || canal.origen === 'ninguno') {
    return 'Todavía no hay desde dónde enviar. Configura el buzón de envío de avisos en la pestaña Correo.'
  }
  if (canal.origen === 'buzon') return `Los avisos salen desde el buzón «${canal.etiqueta}»${canal.remitente ? ` (${canal.remitente})` : ''}.`
  if (canal.origen === 'entorno') return `Los avisos salen desde el servidor de correo del servicio${canal.remitente ? ` (${canal.remitente})` : ''}.`
  return 'Los avisos tienen un canal de envío configurado.'
}
