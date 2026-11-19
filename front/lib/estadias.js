// Reglas puras de la búsqueda de estadías (Salida, Caja y Llegada), sin JSX
// para probarlas con node --test (2026-11-19).

/** «2026-11-19» → «19/11» (formato chileno corto). */
export function fechaCorta(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || '')
  return m ? `${m[3]}/${m[2]}` : '—'
}

export function pesos(monto) {
  if (monto === null || monto === undefined || Number.isNaN(Number(monto))) return '—'
  const n = Math.round(Number(monto))
  return `${n < 0 ? '-' : ''}$${Math.abs(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`
}

export function noches(n) {
  return n === 1 ? '1 noche' : `${n} noches`
}

/** Texto mínimo aceptado por la API: 2 letras o un número de habitación. */
export function textoBuscable(texto) {
  const t = (texto || '').trim()
  return t === '' || t.length >= 2 || /^\d+$/.test(t)
}

const ROTULOS_LISTA = {
  salida: 'Salidas de hoy y atrasadas',
  llegada: 'Llegadas de hoy',
  pago: 'Huéspedes en casa con saldo pendiente',
}

const VACIOS_LISTA = {
  salida: 'No hay Salidas pendientes para hoy. Busca al huésped por nombre, habitación o documento.',
  llegada: 'No hay Llegadas pendientes para hoy. Busca la reserva por nombre, habitación o documento.',
  pago: 'No hay huéspedes en casa con saldo pendiente. Busca por nombre, habitación, documento o código.',
}

export function rotuloLista(alcance, listaDelDia, total) {
  if (listaDelDia) return ROTULOS_LISTA[alcance]
  return total === 1 ? '1 resultado' : `${total} resultados`
}

export function mensajeVacio(alcance, listaDelDia) {
  if (listaDelDia) return VACIOS_LISTA[alcance]
  return 'Sin coincidencias. Revisa el nombre, prueba con el número de habitación o el documento.'
}

/** Insignias de una estadía: [{texto, tono}] con tono exito|aviso|error|info|neutro. */
export function insigniasEstadia(r) {
  const out = []
  if (r.salida_atrasada) out.push({ texto: 'Salida atrasada', tono: 'error' })
  else if (r.sale_hoy && r.estado === 'en_estadia') out.push({ texto: 'Sale hoy', tono: 'info' })
  if (r.estado === 'confirmada') out.push({ texto: r.llega_hoy ? 'Llega hoy' : 'Por llegar', tono: r.llega_hoy ? 'info' : 'neutro' })
  if (r.estado === 'en_estadia' && !r.sale_hoy && !r.salida_atrasada) out.push({ texto: 'En casa', tono: 'neutro' })
  const saldo = r.cuenta ? r.cuenta.saldo_clp : null
  if (saldo > 0) out.push({ texto: `Saldo ${pesos(saldo)}`, tono: 'aviso' })
  else if (saldo < 0) out.push({ texto: `A favor ${pesos(-saldo)}`, tono: 'info' })
  else if (saldo === 0) out.push({ texto: 'Cuenta al día', tono: 'exito' })
  return out
}

/** Qué impide registrar la Salida (o null si se puede). */
export function bloqueoSalida(detalle) {
  if (!detalle) return null
  if (detalle.estado !== 'en_estadia') {
    return detalle.estado === 'finalizada'
      ? 'Este huésped ya registró su Salida.'
      : 'La Salida solo se registra para un huésped en casa (con Llegada registrada).'
  }
  const saldo = detalle.cuenta.saldo_clp
  if (saldo > 0) return `La cuenta tiene saldo pendiente de ${pesos(saldo)}. Registra el pago antes de la Salida.`
  if (saldo < 0) return `La cuenta tiene ${pesos(-saldo)} a favor del huésped. Ajusta la cuenta antes de la Salida.`
  return null
}

export function resumenSalida(liquidacion, detalle) {
  const hab = detalle ? ` La habitación ${detalle.habitacion_id} queda para aseo.` : ''
  const quien = detalle ? ` de ${detalle.huesped_nombre}` : ''
  return `Salida registrada${quien}: cuenta liquidada por ${pesos(liquidacion.total_clp)} (pagado ${pesos(liquidacion.pagado_clp)}).${hab}`
}

export function resumenPago(pago) {
  const base = `Pago de ${pesos(pago.monto_clp)} registrado para ${pago.huesped_nombre || 'el huésped'}${pago.habitacion_id ? ` (habitación ${pago.habitacion_id})` : ''}.`
  if (pago.tipo === 'parcial') return `${base} Saldo pendiente: ${pesos(pago.saldo_despues_clp)}.`
  if (pago.tipo === 'exceso') return `${base} Saldo a favor del huésped: ${pesos(-pago.saldo_despues_clp)}.`
  if (pago.tipo === 'total') return `${base} Cuenta saldada.`
  return base
}

/** Hora local de Chile («14:05») de un instante ISO de la API. */
export function horaChile(iso) {
  const d = new Date(iso || '')
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'America/Santiago' })
}

const MEDIOS = { manual: 'Caja (efectivo, tarjeta o transferencia)', pasarela: 'Pago en línea' }

export function medioDePago(modo) {
  return MEDIOS[modo] || 'Otro'
}
