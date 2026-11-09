/**
 * Formulario de contacto de la sección #contacto. D-PUB-01 resuelta
 * (2026-11-04, orden del propietario): formulario propio que postea a la
 * plataforma (`{API_URL}/publico/leads`, spec-api-v1 «Contacto y leads de la
 * landing»); Formspree se retira. Sin `API_URL` configurado, no se simula un
 * envío y se orienta al visitante hacia teléfono y WhatsApp.
 */
import { API_URL } from './config.js'
import { mapearCuerpo, mensajePara } from './leads.js'

export function inicializarFormulario(documento) {
  const formulario = documento.querySelector('[data-formulario-contacto]')
  if (!formulario) return
  const estado = formulario.querySelector('[role="status"]')

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault()
    if (!API_URL) {
      estado.textContent =
        'El formulario web está en preparación: llámanos o escríbenos por WhatsApp y respondemos a la brevedad.'
      return
    }
    const boton = formulario.querySelector('button[type="submit"]')
    boton.disabled = true
    estado.textContent = 'Enviando…'
    const datos = Object.fromEntries(new FormData(formulario).entries())
    const cuerpo = mapearCuerpo(datos)
    try {
      const respuesta = await fetch(`${API_URL.replace(/\/+$/, '')}/publico/leads`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'Idempotency-Key': crypto.randomUUID(),
        },
        body: JSON.stringify(cuerpo),
      })
      estado.textContent = mensajePara(respuesta.status)
    } catch {
      estado.textContent = 'No se pudo enviar. Inténtalo por teléfono o WhatsApp.'
    } finally {
      boton.disabled = false
    }
  })
}
