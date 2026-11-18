/**
 * Servidores de correo (#355): proveedores conocidos para prellenar el
 * formulario y armado del cuerpo que va a la API. Los secretos vacíos no se
 * envían (el servicio conserva los guardados).
 */
export const PROPOSITOS = [
  ['lectura_enviados', 'Leer enviados (marca leads contactados)'],
  ['envio_avisos', 'Enviar avisos de solicitudes'],
]

export const PROVEEDORES = {
  lectura_enviados: [['imap', 'IMAP (cualquier servidor)'], ['gmail_api', 'API de Gmail / Google Workspace'], ['microsoft_graph', 'Microsoft 365 (Graph)']],
  envio_avisos: [['smtp', 'SMTP (cualquier servidor)'], ['gmail_api', 'API de Gmail / Google Workspace'], ['microsoft_graph', 'Microsoft 365 (Graph)']],
}

export const AUTENTICACIONES = {
  imap: [['clave', 'Usuario y clave (o clave de aplicación)'], ['oauth2', 'OAuth2 (XOAUTH2)']],
  smtp: [['clave', 'Usuario y clave (o clave de aplicación)'], ['oauth2', 'OAuth2 (XOAUTH2)'], ['ninguna', 'Sin autenticación (relay)']],
  gmail_api: [['cuenta_servicio', 'Cuenta de servicio (Workspace, delegación de dominio)'], ['oauth2', 'OAuth2 con refresh token']],
  microsoft_graph: [['aplicacion', 'Aplicación de Entra ID (client credentials)']],
}

export const SEGURIDADES = [['ssl', 'SSL/TLS'], ['starttls', 'STARTTLS'], ['ninguna', 'Ninguna (no recomendado)']]

const TOKEN_GOOGLE = 'https://oauth2.googleapis.com/token'
const TOKEN_MICROSOFT = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'

// [id, nombre, imap, smtp, token_url]
export const PRESETS = [
  ['gmail', 'Gmail / Google Workspace', { host: 'imap.gmail.com', puerto: 993, seguridad: 'ssl' }, { host: 'smtp.gmail.com', puerto: 587, seguridad: 'starttls' }, TOKEN_GOOGLE],
  ['outlook', 'Outlook / Microsoft 365', { host: 'outlook.office365.com', puerto: 993, seguridad: 'ssl' }, { host: 'smtp.office365.com', puerto: 587, seguridad: 'starttls' }, TOKEN_MICROSOFT],
  ['yahoo', 'Yahoo', { host: 'imap.mail.yahoo.com', puerto: 993, seguridad: 'ssl' }, { host: 'smtp.mail.yahoo.com', puerto: 465, seguridad: 'ssl' }, ''],
  ['zoho', 'Zoho Mail', { host: 'imap.zoho.com', puerto: 993, seguridad: 'ssl' }, { host: 'smtp.zoho.com', puerto: 465, seguridad: 'ssl' }, ''],
  ['icloud', 'iCloud', { host: 'imap.mail.me.com', puerto: 993, seguridad: 'ssl' }, { host: 'smtp.mail.me.com', puerto: 587, seguridad: 'starttls' }, ''],
  ['hosting', 'Hosting (cPanel / Plesk)', { host: '', puerto: 993, seguridad: 'ssl' }, { host: '', puerto: 465, seguridad: 'ssl' }, ''],
]

export const PARAMETROS = {
  imap: ['host', 'puerto', 'seguridad', 'usuario', 'autenticacion', 'carpeta_enviados', 'token_url', 'client_id'],
  smtp: ['host', 'puerto', 'seguridad', 'usuario', 'autenticacion', 'remitente', 'destino', 'token_url', 'client_id'],
  gmail_api: ['usuario', 'autenticacion', 'client_id', 'remitente', 'destino'],
  microsoft_graph: ['tenant_id', 'client_id', 'usuario', 'remitente', 'destino'],
}

export const SECRETOS = {
  imap: ['clave', 'client_secret', 'refresh_token'],
  smtp: ['clave', 'client_secret', 'refresh_token'],
  gmail_api: ['cuenta_servicio_json', 'client_secret', 'refresh_token'],
  microsoft_graph: ['client_secret'],
}

/** Qué campos se muestran según proveedor, autenticación y propósito. */
export function camposVisibles(proposito, proveedor, autenticacion) {
  const oauth = autenticacion === 'oauth2'
  const parametros = PARAMETROS[proveedor].filter((c) => {
    if (c === 'autenticacion') return false
    if (c === 'token_url') return oauth
    if (c === 'client_id') return oauth || proveedor === 'microsoft_graph'
    if (c === 'remitente' || c === 'destino') return proposito === 'envio_avisos'
    if (c === 'usuario') return autenticacion !== 'ninguna'
    return true
  })
  const porAuth = {
    clave: ['clave'], oauth2: ['client_secret', 'refresh_token'], cuenta_servicio: ['cuenta_servicio_json'],
    aplicacion: ['client_secret'], ninguna: [],
  }
  return { parametros, secretos: porAuth[autenticacion] || [] }
}

export function formularioVacio(proposito = 'lectura_enviados', proveedor = proposito === 'envio_avisos' ? 'smtp' : 'imap') {
  return {
    buzon_id: null, etiqueta: '', proposito, proveedor, activo: true,
    autenticacion: AUTENTICACIONES[proveedor][0][0], parametros: {}, secretos: {},
  }
}

export function aplicarPreset(form, presetId) {
  const preset = PRESETS.find(([id]) => id === presetId)
  if (!preset || !['imap', 'smtp'].includes(form.proveedor)) return form
  const servidor = form.proveedor === 'imap' ? preset[2] : preset[3]
  const parametros = { ...form.parametros, ...servidor }
  if (preset[4]) parametros.token_url = preset[4]
  return { ...form, parametros }
}

/** Cuerpo para POST/PUT /hotel/correo/buzones. */
export function cuerpoBuzon(form) {
  const { parametros: visibles, secretos: secretosVisibles } = camposVisibles(form.proposito, form.proveedor, form.autenticacion)
  const parametros = {}
  for (const c of visibles) {
    const v = form.parametros[c]
    if (v === undefined || v === null || String(v).trim() === '') continue
    parametros[c] = c === 'puerto' ? Number(v) : String(v).trim()
  }
  if (form.proveedor !== 'microsoft_graph') parametros.autenticacion = form.autenticacion
  const secretos = {}
  for (const s of secretosVisibles) {
    const v = form.secretos[s]
    if (typeof v === 'string' && v.trim() !== '') secretos[s] = v
  }
  const cuerpo = { etiqueta: form.etiqueta.trim(), proveedor: form.proveedor, activo: form.activo, parametros, secretos }
  if (!form.buzon_id) cuerpo.proposito = form.proposito
  return cuerpo
}

export const ETIQUETAS_CAMPO = {
  host: 'Servidor', puerto: 'Puerto', seguridad: 'Seguridad', usuario: 'Usuario (correo del buzón)',
  carpeta_enviados: 'Carpeta de enviados (vacío = detectar)', remitente: 'Remitente (vacío = usuario)',
  destino: 'Quién recibe los avisos', token_url: 'URL de token OAuth2', client_id: 'Client ID',
  tenant_id: 'Tenant ID (directorio)', clave: 'Clave o clave de aplicación', client_secret: 'Client secret',
  refresh_token: 'Refresh token', cuenta_servicio_json: 'JSON de la cuenta de servicio',
}
