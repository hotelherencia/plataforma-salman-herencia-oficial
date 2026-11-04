/**
 * Utilidades puras del formulario de contacto (spec-api-v1 «Contacto y leads
 * de la landing», V1-ISSUE-20 punto 8: formulario propio, Formspree
 * retirado). Sin dependencias de DOM: las mismas funciones corren en el
 * navegador (formulario) y en Node (tests, `node --test landing/test/`).
 *
 * El formulario postea a `{API_URL}/publico/leads` (spec del contrato): los
 * campos usan snake_case y las fechas viajan como YYYY-MM-DD o null; el
 * HTML conserva los names históricos con guion (check-in/check-out), así que
 * el mapeo vive aquí y queda probado.
 */
export function mapearCuerpo(datos) {
  return {
    nombre: (datos.nombre || '').trim(),
    correo: (datos.correo || '').trim(),
    telefono: (datos.telefono || '').trim(),
    huespedes: datos.huespedes === '' || datos.huespedes == null ? null : Number(datos.huespedes),
    check_in: datos.check_in || null,
    check_out: datos.check_out || null,
    mensaje: (datos.mensaje || '').trim() || null,
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
