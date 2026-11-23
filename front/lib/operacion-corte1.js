/**
 * Utilidades puras del Corte 1 operativo (#415 Incidencias, #416 Tareas/Checklists,
 * #417 Bloque «Lo que necesita atención»). Sin React, probables con `node --test`.
 */

export const ETIQUETA_PREPARACION = {
  sucia: 'Sucia',
  en_limpieza: 'En limpieza',
  limpia: 'Limpia',
  inspeccionada: 'Inspeccionada',
}

export const ETIQUETA_GRAVEDAD = {
  baja: 'Baja',
  media: 'Media',
  alta: 'Alta',
  critica: 'Crítica',
}

export const ETIQUETA_TIPO_TAREA = {
  limpieza: 'Limpieza',
  banos: 'Baños',
  lavanderia: 'Lavandería',
  desayunos: 'Desayunos',
  mantenimiento: 'Mantención',
  general: 'General',
}

export const ETIQUETA_PRIORIDAD = {
  baja: 'Baja',
  media: 'Media',
  alta: 'Alta',
  urgente: 'Urgente',
}

export const ETIQUETA_AREA = {
  habitacion: 'Habitación',
  pasillo: 'Pasillo',
  comedor: 'Comedor',
  recepcion: 'Recepción',
  banos_comunes: 'Baños comunes',
  lavanderia: 'Lavandería',
  estacionamiento: 'Estacionamiento',
  cocina: 'Cocina',
  otro: 'Otra área',
}

export function etiquetaPreparacion(estado) {
  return ETIQUETA_PREPARACION[estado] || estado || '—'
}

export function progresoSubtareas(subtareas = []) {
  const lista = Array.isArray(subtareas) ? subtareas : []
  const total = lista.length
  const completadas = lista.filter((s) => Boolean(s.completada)).length
  const obligatoriasPendientes = lista.filter((s) => Boolean(s.obligatoria) && !s.completada).length
  return {
    total,
    completadas,
    obligatoriasPendientes,
    puedeCerrar: obligatoriasPendientes === 0,
  }
}

/**
 * Organiza los bloques de «Lo que necesita atención» (#417) en orden operativo
 * (vocabulario «Llegada» y «Salida»).
 */
export function resumirAtencion(atencion) {
  if (!atencion || typeof atencion !== 'object') {
    return { total: 0, grupos: [] }
  }
  const grupos = [
    {
      id: 'llegadas_atrasadas',
      titulo: 'Llegadas atrasadas',
      urgente: true,
      items: (atencion.llegadas_atrasadas || []).map((r) => ({
        clave: r.reserva_id,
        texto: `${r.huesped_nombre} · ${r.habitacion_id} (prevista ${r.fecha})`,
        href: r.enlace || `/hotel/reservas/${r.reserva_id}`,
      })),
    },
    {
      id: 'salidas_atrasadas',
      titulo: 'Salidas atrasadas',
      urgente: true,
      items: (atencion.salidas_atrasadas || []).map((r) => ({
        clave: r.reserva_id,
        texto: `${r.huesped_nombre} · ${r.habitacion_id} (prevista ${r.fecha})`,
        href: r.enlace || `/hotel/reservas/${r.reserva_id}`,
      })),
    },
    {
      id: 'incidencias_abiertas',
      titulo: 'Incidencias abiertas',
      urgente: (atencion.incidencias_abiertas || []).some((i) => i.bloquea_disponibilidad || i.gravedad === 'critica'),
      items: (atencion.incidencias_abiertas || []).map((i) => ({
        clave: i.incidencia_id,
        texto: `${i.habitacion_id || ETIQUETA_AREA[i.area] || i.area}: ${i.titulo}`,
        etiqueta: i.bloquea_disponibilidad ? 'Bloquea habitación' : (ETIQUETA_GRAVEDAD[i.gravedad] || i.gravedad),
        bloquea: Boolean(i.bloquea_disponibilidad),
        href: i.enlace || (i.habitacion_id ? `/hotel/habitaciones/${i.habitacion_id}` : '/hotel/aseo'),
      })),
    },
    {
      id: 'limpiezas_por_verificar',
      titulo: 'Limpiezas por verificar',
      urgente: false,
      items: (atencion.limpiezas_por_verificar || []).map((l) => ({
        clave: l.tarea_id,
        texto: `${l.habitacion_id}${l.completada_por ? ` · lista por ${l.completada_por}` : ''}`,
        href: l.enlace || '/hotel/aseo',
      })),
    },
    {
      id: 'productos_bajo_stock',
      titulo: 'Productos bajo stock mínimo',
      urgente: (atencion.productos_bajo_stock || []).some((p) => p.nivel === 'sin_stock'),
      items: (atencion.productos_bajo_stock || []).map((p) => ({
        clave: p.producto_id,
        texto: `${p.nombre} (${p.stock_actual} / mín. ${p.stock_minimo})`,
        etiqueta: p.nivel === 'sin_stock' ? 'Sin stock' : 'Bajo mínimo',
        bloquea: p.nivel === 'sin_stock',
        href: p.enlace || '/hotel/productos',
      })),
    },
  ].filter((g) => g.items.length > 0)

  const total = typeof atencion.total === 'number'
    ? atencion.total
    : grupos.reduce((acc, g) => acc + g.items.length, 0)
  return { total, grupos }
}
