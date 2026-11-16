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

export function traducirDetalle(detalle) {
  return Object.prototype.hasOwnProperty.call(TRADUCCIONES, detalle) ? TRADUCCIONES[detalle] : detalle
}
