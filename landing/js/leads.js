/**
 * Utilidades puras del formulario de contacto (spec-api-v1 «Contacto y leads
 * de la landing», V1-ISSUE-20 punto 8: formulario propio, Formspree
 * retirado). Sin dependencias de DOM: las mismas funciones corren en el
 * navegador (formulario) y en Node (tests, `node --test landing/test/`).
 *
 * El formulario postea a `{API_URL}/publico/leads` (spec del contrato): los
 * campos usan snake_case y las fechas viajan como YYYY-MM-DD o null; el
 * HTML del sitio real usa name, email, phone, guests, checkin, checkout y
 * message. El marcador anterior usaba nombre, correo, telefono, huespedes,
 * check-in y check-out. El mapeo vive aquí y queda probado; el cuerpo que
 * sale hacia la API sigue en snake_case.
 */
function textoPresente(datos, ...claves) {
  for (const clave of claves) {
    if (datos[clave] == null) continue
    const limpio = String(datos[clave]).trim()
    if (limpio !== '') return limpio
  }
  return ''
}

export function mapearCuerpo(datos) {
  const huespedes = textoPresente(datos, 'huespedes', 'guests')
  const checkIn = textoPresente(datos, 'check_in', 'checkin', 'check-in')
  const checkOut = textoPresente(datos, 'check_out', 'checkout', 'check-out')
  return {
    nombre: textoPresente(datos, 'nombre', 'name'),
    correo: textoPresente(datos, 'correo', 'email'),
    telefono: textoPresente(datos, 'telefono', 'phone'),
    huespedes: huespedes === '' ? null : Number(huespedes),
    check_in: checkIn || null,
    check_out: checkOut || null,
    mensaje: textoPresente(datos, 'mensaje', 'message') || null,
  }
}

/** Mensaje de estado legible según el código HTTP de /publico/leads. */
export function mensajePara(estadoHttp) {
  if (estadoHttp === 201 || estadoHttp === 200) {
    return 'Consulta enviada. Responderemos a la brevedad.'
  }
  if (estadoHttp === 429) {
    return 'Recibimos demasiados intentos; espera un minuto e inténtalo de nuevo.'
  }
  if (estadoHttp === 422) {
    return 'Revisa los datos del formulario e inténtalo de nuevo.'
  }
  return 'No se pudo enviar. Inténtalo por teléfono o WhatsApp.'
}
