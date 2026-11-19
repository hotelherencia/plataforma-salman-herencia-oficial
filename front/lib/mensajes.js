// Traducción de detalles del servicio a mensajes para personas (módulo puro,
// sin JSX, para poder probarlo con node --test).
const TRADUCCIONES = {
  codigo_totp_requerido: 'Ingresa el código del autenticador.',
  sesion_empresa_ajena:
    'La sesión no pertenece a la empresa activa del servidor. Revisa EMPRESA_TITULAR / redeploy.',
  'sesión inválida o vencida': 'Sesión expirada o revocada. Inicia sesión de nuevo.',
  'sin sesión': 'No hay sesión activa.',
  // Servicio anterior a fix-e2e: textos técnicos del canal público.
  'canal público temporalmente no disponible':
    'No pudimos recibir tu solicitud en este momento. Escríbenos por WhatsApp al +56 9 5649 1501 o inténtalo de nuevo más tarde.',
  'no se pudo verificar el envío':
    'No pudimos verificar el envío. Recarga la página e inténtalo de nuevo; si persiste, escríbenos por WhatsApp al +56 9 5649 1501.',
}

// Detalles técnicos del servicio que antes llegaban tal cual a la pantalla
// (2026-11-19): se reescriben en castellano de recepción.
const PATRONES = [
  [/^check-out requiere una estadía en curso$/i, () => 'La Salida solo se registra para un huésped en casa (con Llegada registrada).'],
  [/^la cuenta tiene saldo pendiente de (-?\d+) CLP$/i, (m) => {
    const n = Number(m[1])
    const monto = `$${Math.abs(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`
    return n > 0
      ? `No se puede registrar la Salida: la cuenta tiene saldo pendiente de ${monto}. Registra el pago primero.`
      : `No se puede registrar la Salida: la cuenta tiene ${monto} a favor del huésped. Ajusta la cuenta primero.`
  }],
  [/^falta la cabecera Idempotency-Key$/i, () => 'No se pudo enviar la operación. Recarga la página e inténtalo de nuevo.'],
  [/^la clave ya fue usada con otro cuerpo$/i, () => 'Esta operación ya se envió con otros datos. Empieza una nueva e inténtalo otra vez.'],
  [/^rol no autorizado$/i, () => 'Tu usuario no tiene permiso para esta operación.'],
  [/^solo administración del hotel$/i, () => 'Solo la administración del hotel puede hacer esta operación.'],
  [/^solo administración de plataforma$/i, () => 'Solo la administración de la plataforma puede hacer esta operación.'],
  [/^pasarela no configurada$/i, () => 'El pago en línea aún no está habilitado: no quedó nada cobrado.'],
  [/^estado inválido$/i, () => 'El estado elegido no es válido.'],
  [/^hasta debe ser mayor que desde$/i, () => 'La fecha «hasta» debe ser posterior a la fecha «desde».'],
]

export function traducirDetalle(detalle) {
  if (Object.prototype.hasOwnProperty.call(TRADUCCIONES, detalle)) return TRADUCCIONES[detalle]
  for (const [re, f] of PATRONES) {
    const m = re.exec(String(detalle || ''))
    if (m) return f(m)
  }
  return detalle
}

// Validaciones 422 (FastAPI/pydantic): nunca se muestran tipos, rutas ni
// mensajes en inglés; se nombra el campo y lo que hay que corregir.
const NOMBRES_CAMPO = {
  monto_clp: 'el monto', precio_clp: 'el precio', precio_base_clp: 'el precio base', nombre: 'el nombre',
  cantidad: 'la cantidad', concepto: 'el concepto', motivo: 'el motivo', documento: 'el documento',
  documento_tipo: 'el tipo de documento', inicio: 'la fecha de Llegada', fin: 'la fecha de Salida',
  habitacion_id: 'la habitación', personas: 'las personas', clave: 'la clave', email: 'el correo',
  telefono: 'el teléfono', rol: 'el rol', usuario: 'el usuario', fecha: 'la fecha', delta: 'el ajuste',
  categoria: 'la categoría', codigo: 'el código', capacidad: 'la capacidad', stock: 'el stock',
  costo_unitario_clp: 'el costo', xml: 'el archivo', lineas: 'las líneas', q: 'la búsqueda',
}

function campoLegible(loc) {
  const partes = Array.isArray(loc) ? loc.filter((x) => typeof x === 'string' && !['body', 'query', 'path', 'header'].includes(x)) : []
  const ultimo = partes[partes.length - 1]
  if (!ultimo) return 'un dato'
  return NOMBRES_CAMPO[ultimo] || `el campo «${ultimo.replace(/_/g, ' ')}»`
}

function problema(d) {
  const tipo = String(d.type || '')
  const msg = String(d.msg || '')
  const numero = (/(-?[\d.]+)\s*$/.exec(msg) || [])[1]
  if (tipo === 'missing') return 'es obligatorio'
  if (tipo.startsWith('greater_than_equal')) return `debe ser ${numero ?? 'mayor'} o más`
  if (tipo.startsWith('greater_than')) return `debe ser mayor que ${numero ?? '0'}`
  if (tipo.startsWith('less_than')) return 'es demasiado grande'
  if (tipo === 'string_too_short') return 'es demasiado corto'
  if (tipo === 'string_too_long' || tipo === 'too_long') return 'es demasiado largo'
  if (tipo === 'string_pattern_mismatch') return 'tiene un formato no válido'
  if (tipo.startsWith('int_') || tipo.startsWith('float_') || tipo === 'decimal_parsing') return 'debe ser un número'
  if (tipo.startsWith('date')) return 'debe ser una fecha válida'
  if (tipo === 'literal_error' || tipo === 'enum') return 'no es una opción válida'
  if (tipo === 'extra_forbidden') return 'no corresponde a esta operación'
  if (tipo === 'value_error') return msg.replace(/^Value error,\s*/i, '')
  return 'no es válido'
}

/** Lista de errores 422 → una frase legible. */
export function traducirValidacion(detalle) {
  if (!Array.isArray(detalle) || !detalle.length) return 'Revisa los datos ingresados.'
  const frases = [...new Set(detalle.map((d) => {
    if (!d || typeof d !== 'object') return 'Revisa los datos ingresados.'
    const texto = `${campoLegible(d.loc)} ${problema(d)}`
    return texto.charAt(0).toUpperCase() + texto.slice(1)
  }))]
  return `Revisa los datos: ${frases.slice(0, 3).join('; ')}.`
}

// Errores que el callback de Google devuelve en /login?error=… .
const ERRORES_LOGIN = {
  mfa_requerido:
    'Para entrar con Google, tu cuenta de administrador debe tener activo el doble factor (Google Authenticator). Entra con tu usuario y clave y actívalo en «Mi cuenta».',
  cuenta_sin_vinculo: 'Tu cuenta de Google no está vinculada a un usuario de la plataforma.',
  acceso_denegado: 'Acceso con Google cancelado o denegado.',
  google_vencido: 'El intento de acceso con Google venció o se abrió en otra pestaña. Vuelve a intentarlo.',
  google_fallo: 'No pudimos validar tu identidad con Google. Intenta de nuevo o con otra cuenta.',
}

/** Mensaje para el parámetro `error` de /login, o null si no es conocido. */
export function mensajeErrorLogin(codigo) {
  return Object.prototype.hasOwnProperty.call(ERRORES_LOGIN, codigo) ? ERRORES_LOGIN[codigo] : null
}

const FORMULAS_HUMANAS = {
  'noches_ocupadas / unidades-noche':
    'Porcentaje de habitaciones con estadías activas respecto a la capacidad total de habitaciones vendibles durante las noches seleccionadas.',
  'noches_reservadas / unidades-noche':
    'Porcentaje de habitaciones con reserva confirmada respecto a la capacidad total del hotel para el período.',
  'habitaciones_vendibles * noches':
    'Capacidad hotelera total: habitaciones en servicio multiplicadas por las noches del período.',
  'sum(cargos) - sum(reversos)':
    'Monto neto facturado por cargos de habitación y consumos, descontando cancelaciones y reversos contables.',
  'noches_ocupadas':
    'Total acumulado de noches en que una habitación estuvo efectivamente ocupada por huéspedes.',
  'noches_reservadas':
    'Total de noches comprometidas bajo reservas confirmadas en el período.',
  'reservas_canceladas':
    'Cantidad de reservas anuladas en el período y total de noches liberadas.',
  'reservas_registradas':
    'Cantidad de reservas gestionadas en el sistema para este período.',
}

/** Explicación en lenguaje de negocio para fórmulas e indicadores del panel (#381). */
export function traducirFormula(formula) {
  if (!formula || typeof formula !== 'string') return ''
  const f = formula.trim()
  if (Object.prototype.hasOwnProperty.call(FORMULAS_HUMANAS, f)) {
    return FORMULAS_HUMANAS[f]
  }
  return f
    .replace(/noches_ocupadas/g, 'noches ocupadas')
    .replace(/unidades-noche/g, 'capacidad total de noches')
    .replace(/habitaciones_vendibles/g, 'habitaciones vendibles')
    .replace(/reservas_canceladas/g, 'reservas canceladas')
    .replace(/reservas_registradas/g, 'reservas registradas')
    .replace(/sum\(cargos\)/g, 'suma de cargos')
    .replace(/sum\(reversos\)/g, 'suma de reversos')
}
