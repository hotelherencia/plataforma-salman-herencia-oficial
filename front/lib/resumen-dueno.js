// Resumen del dueño: lecturas del panel y de contabilidad, comparadas con el mes anterior.
// No recalcula montos oficiales: solo ordena, compara y avisa lo que pide atención.

/** Variación porcentual entera de `actual` respecto de `previo`; null si no hay base comparable. */
export function variacion(actual, previo) {
  if (actual === null || actual === undefined || previo === null || previo === undefined || previo === 0) return null
  return Math.round(((actual - previo) / Math.abs(previo)) * 100)
}

export function flechaVariacion(v) {
  if (v === null || v === undefined) return 'sin base para comparar'
  if (v === 0) return 'igual que el mes anterior'
  return `${v > 0 ? '▲' : '▼'} ${Math.abs(v)} % vs. mes anterior`
}

/** Mes anterior (desde, hasta sin incluir) a partir del inicio del mes actual. */
export function mesAnterior(inicioMes) {
  const [a, m] = inicioMes.split('-').map(Number)
  const ant = m === 1 ? `${a - 1}-12-01` : `${a}-${String(m - 1).padStart(2, '0')}-01`
  return { desde: ant, hasta: inicioMes }
}

/** Alertas del dueño en orden de importancia, solo las que existen. */
export function alertasDueno({ atencionTotal = 0, cxcVencidoClp = 0, mantencionesVencidas = 0, sugerenciasNuevas = 0, cambiosTurno = 0 }) {
  const a = []
  if (cxcVencidoClp > 0) a.push({ clave: 'cxc', texto: 'Cuentas por cobrar vencidas', valor: cxcVencidoClp, tipo: 'clp' })
  if (atencionTotal > 0) a.push({ clave: 'atencion', texto: 'Cosas que necesitan atención hoy', valor: atencionTotal, tipo: 'n' })
  if (mantencionesVencidas > 0) a.push({ clave: 'mant', texto: 'Mantenciones preventivas vencidas', valor: mantencionesVencidas, tipo: 'n' })
  if (cambiosTurno > 0) a.push({ clave: 'turnos', texto: 'Cambios de turno por aprobar', valor: cambiosTurno, tipo: 'n' })
  if (sugerenciasNuevas > 0) a.push({ clave: 'sug', texto: 'Sugerencias nuevas del personal', valor: sugerenciasNuevas, tipo: 'n' })
  return a
}
