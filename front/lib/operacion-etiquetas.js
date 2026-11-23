// Etiquetas legibles del Corte 1 operativo (#426). Los valores técnicos vienen de la API.
export const ETIQUETA_GRAVEDAD = { baja: 'Baja', media: 'Media', alta: 'Alta', critica: 'Crítica' }
export const ETIQUETA_PRIORIDAD = { baja: 'Baja', normal: 'Normal', alta: 'Alta', urgente: 'Urgente' }
export const ETIQUETA_AREA = {
  general: 'General', limpieza: 'Limpieza', banos: 'Baños',
  lavanderia: 'Lavandería', desayunos: 'Desayunos', mantencion: 'Mantención',
}
export const ETIQUETA_ESTADO_INCIDENCIA = { abierta: 'Abierta', en_curso: 'En curso', resuelta: 'Resuelta', cerrada: 'Cerrada' }

export function etiqueta(mapa, valor) {
  return mapa[valor] || String(valor ?? '')
}

/** Resumen corto del bloque de atención para lectores de pantalla y títulos. */
export function resumirAtencion(atencion) {
  if (!atencion || !atencion.total) return 'Todo al día'
  const partes = []
  const n = (clave, singular, plural) => {
    const c = (atencion[clave] || []).length
    if (c) partes.push(`${c} ${c === 1 ? singular : plural}`)
  }
  n('llegadas_atrasadas', 'llegada atrasada', 'llegadas atrasadas')
  n('salidas_atrasadas', 'salida atrasada', 'salidas atrasadas')
  n('limpiezas_por_verificar', 'limpieza por verificar', 'limpiezas por verificar')
  n('incidencias_abiertas', 'incidencia abierta', 'incidencias abiertas')
  n('productos_bajo_minimo', 'producto bajo el mínimo', 'productos bajo el mínimo')
  return partes.join(', ')
}

/** Progreso de subtareas: hechas, total y si faltan obligatorias. */
export function progresoSubtareas(subtareas = []) {
  const total = subtareas.length
  const hechas = subtareas.filter((s) => s.hecha).length
  const faltanObligatorias = subtareas.filter((s) => s.obligatoria && !s.hecha).length
  return { hechas, total, faltanObligatorias, porcentaje: total ? Math.round((hechas / total) * 100) : 0 }
}
