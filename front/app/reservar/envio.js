/** Envío de la solicitud de /reservar (fix-forms): sin React ni red propia para
 *  poder probarlo con node --test. page.js inyecta api(), grecaptcha y los
 *  mensajes del servicio.
 *
 *  - El token de reCAPTCHA se pide al momento de enviar (cada token sirve una
 *    sola vez y vence a los 2 minutos): nunca se reutiliza ni envejece.
 *  - Ante red caída o 502/503/504 (Railway despertando o desplegando) se
 *    reintenta UNA vez con token nuevo y la MISMA Idempotency-Key: si el primer
 *    intento alcanzó a guardarse, el servicio devuelve la original (200).
 *  - Si el script de Google no carga (bloqueador, Firefox estricto, VPN), se
 *    avisa eso mismo en vez de mandar un envío que terminaría en 403.
 *  - Cada mensaje de error lleva un código corto que viaja como X-Request-Id. */

export const ESTADOS_REINTENTABLES = new Set([502, 503, 504])
export const WHATSAPP_TEXTO = 'WhatsApp al +56 9 5649 1501'

const LETRAS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

export function nuevoCodigoEnvio(cripto = globalThis.crypto) {
  try {
    return Array.from(cripto.getRandomValues(new Uint8Array(8)), (n) => LETRAS[n % LETRAS.length]).join('')
  } catch {
    return Date.now().toString(36).toUpperCase().slice(-8)
  }
}

export function conCodigo(mensaje, codigo) {
  return codigo ? `${mensaje} (código ${codigo})` : mensaje
}

function errorRecaptcha(causa) {
  return Object.assign(new Error(causa), { causa })
}

/** Token nuevo de reCAPTCHA v3. Rechaza con causa 'recaptcha_bloqueado' si
 *  grecaptcha no llega (o el script dio error) y 'recaptcha' si llegó pero no
 *  entregó token. */
export function obtenerToken(ventana, claveSitio, accion, { bloqueado = () => false, esperaMs = 10000, pasoMs = 50 } = {}) {
  return new Promise((resolve, reject) => {
    const inicio = Date.now()
    const ejecutar = () => {
      try {
        ventana.grecaptcha.ready(() => {
          Promise.resolve(ventana.grecaptcha.execute(claveSitio, { action: accion }))
            .then((token) => (typeof token === 'string' && token.length > 20 ? resolve(token) : reject(errorRecaptcha('recaptcha'))))
            .catch(() => reject(errorRecaptcha('recaptcha')))
        })
      } catch {
        reject(errorRecaptcha('recaptcha'))
      }
    }
    const listo = () => ventana.grecaptcha && typeof ventana.grecaptcha.ready === 'function'
    if (listo()) {
      ejecutar()
      return
    }
    const reloj = ventana.setInterval(() => {
      if (listo()) {
        ventana.clearInterval(reloj)
        ejecutar()
      } else if (bloqueado() || Date.now() - inicio > esperaMs) {
        ventana.clearInterval(reloj)
        reject(errorRecaptcha('recaptcha_bloqueado'))
      }
    }, pasoMs)
  })
}

/** pedir(cabeceras) → { estado, datos } o lanza (red caída/timeout).
 *  token() → Promise<string> o rechaza con { causa }.
 *  Devuelve { tipo: 'respuesta'|'red'|'captcha'|'captcha_bloqueado', estado?, datos?, codigo }. */
export async function enviarSolicitud({ pedir, token, codigo = nuevoCodigoEnvio(), esperar = (ms) => new Promise((r) => setTimeout(r, ms)), esperaMs = 1500 }) {
  for (let intento = 1; intento <= 2; intento += 1) {
    let t
    try {
      t = await token()
    } catch (error) {
      return { tipo: error && error.causa === 'recaptcha_bloqueado' ? 'captcha_bloqueado' : 'captcha', codigo }
    }
    const cabeceras = { 'X-Request-Id': `${codigo}-${intento}` }
    if (t) cabeceras['X-Recaptcha-Token'] = t
    let r
    try {
      r = await pedir(cabeceras)
    } catch {
      if (intento === 1) {
        await esperar(esperaMs)
        continue
      }
      return { tipo: 'red', codigo }
    }
    if (ESTADOS_REINTENTABLES.has(r.estado) && intento === 1) {
      await esperar(esperaMs)
      continue
    }
    return { tipo: 'respuesta', estado: r.estado, datos: r.datos, codigo }
  }
  return { tipo: 'red', codigo }
}

/** Mensaje para el huésped (español de Chile, con qué hacer y el código).
 *  traducir = mensajeDeError de lib/api.js para los 4xx del servicio. */
export function mensajeSolicitud(resultado, traducir) {
  const { tipo, estado, datos, codigo } = resultado
  if (tipo === 'captcha_bloqueado') {
    return conCodigo(
      'No pudimos cargar la verificación de seguridad de Google (reCAPTCHA), así que tu solicitud no se envió. Si usas un bloqueador de '
        + `anuncios, VPN o la protección estricta de Firefox, desactívalos para este sitio y vuelve a intentarlo, o escríbenos por ${WHATSAPP_TEXTO}.`,
      codigo,
    )
  }
  if (tipo === 'captcha' || estado === 403) {
    return conCodigo(`No pudimos verificar el envío. Recarga la página e inténtalo de nuevo; si persiste, escríbenos por ${WHATSAPP_TEXTO}.`, codigo)
  }
  if (tipo === 'red') {
    return conCodigo(
      `No pudimos conectar con el servidor y tu solicitud no se envió. Revisa tu conexión (si usas VPN, prueba sin ella) e inténtalo de nuevo, o escríbenos por ${WHATSAPP_TEXTO}.`,
      codigo,
    )
  }
  if (estado === 503 && typeof datos?.detail === 'string') return conCodigo(traducir(datos, estado), codigo)
  if (estado >= 500) {
    return conCodigo(
      `No pudimos recibir tu solicitud por un problema de nuestro lado. Inténtalo de nuevo en unos minutos o escríbenos por ${WHATSAPP_TEXTO}.`,
      codigo,
    )
  }
  if (estado === 429) return conCodigo('Recibimos demasiados intentos; espera un minuto e inténtalo de nuevo.', codigo)
  return conCodigo(traducir(datos, estado), codigo)
}
