/**
 * Formulario de contacto de la sección #contacto. D-PUB-01 (convivencia con
 * Formspree) sigue DECISIÓN PENDIENTE del propietario: con FORMSPREE_URL
 * configurado envía por fetch ( Accept: application/json ); sin él, no
 * simula un envío y orienta al visitante hacia teléfono y WhatsApp.
 */
import { FORMSPREE_URL } from './config.js'

export function inicializarFormulario(documento) {
  const formulario = documento.querySelector('[data-formulario-contacto]')
  if (!formulario) return
  const estado = formulario.querySelector('[role="status"]')

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault()
    if (!FORMSPREE_URL) {
      estado.textContent =
        'El formulario web está en preparación: llámanos o escríbenos por WhatsApp y respondemos a la brevedad.'
      return
    }
    const boton = formulario.querySelector('button[type="submit"]')
    boton.disabled = true
    estado.textContent = 'Enviando…'
    try {
      const respuesta = await fetch(FORMSPREE_URL, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        body: new FormData(formulario),
      })
      estado.textContent = respuesta.ok
        ? 'Consulta enviada. Responderemos a la brevedad.'
        : 'No se pudo enviar. Inténtalo por teléfono o WhatsApp.'
    } catch {
      estado.textContent = 'No se pudo enviar. Inténtalo por teléfono o WhatsApp.'
    } finally {
      boton.disabled = false
    }
  })
}
