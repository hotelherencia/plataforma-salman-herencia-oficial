/**
 * Formulario de contacto de la sección #contacto. D-PUB-01 resuelta
 * (2026-11-04, orden del propietario): formulario propio que postea a la
 * plataforma (`{API_URL}/publico/leads`, spec-api-v1 «Contacto y leads de la
 * landing»); Formspree se retira. Sin `API_URL` configurado, no se simula un
 * envío y se orienta al visitante hacia teléfono y WhatsApp.
 *
 * La Idempotency-Key vive mientras el resultado no esté decidido. Un fallo
 * de red reintenta la misma clave y no crea otro lead. Al confirmar, si la
 * respuesta trae `referencia`, el enlace a /reservar lleva solo fechas y
 * esa referencia: el nombre y el correo no van en la URL.
 */
import { API_URL, PLATAFORMA_URL } from './config.js'
import { prepararCaptcha, tokenCaptcha } from './captcha.js'
import { decidirClave, mapearCuerpo, mensajePara, problemaConsulta } from './leads.js'
import { construirEnlaceReserva } from './reserva.js'

function pintarEstado(estado, texto, enlace) {
  estado.replaceChildren(document.createTextNode(texto))
  if (!enlace) return
  estado.append(document.createTextNode(' '))
  const continuar = document.createElement('a')
  continuar.href = enlace
  continuar.textContent = 'Continuar con la reserva'
  estado.append(continuar)
}

function enlaceDeReferencia(cuerpo, referencia) {
  if (!cuerpo.check_in || !cuerpo.check_out) return null
  try {
    return construirEnlaceReserva(
      PLATAFORMA_URL,
      cuerpo.check_in,
      cuerpo.check_out,
      cuerpo.huespedes || 1,
      referencia,
    )
  } catch {
    return null
  }
}

export function inicializarFormulario(documento) {
  const formulario = documento.querySelector('[data-formulario-contacto]')
  if (!formulario) return
  const estado = formulario.querySelector('[role="status"]')
  prepararCaptcha(documento)
  let clave = crypto.randomUUID()

  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault()
    if (!API_URL) {
      estado.textContent =
        'El formulario web está en preparación: llámanos o escríbenos por WhatsApp y respondemos a la brevedad.'
      return
    }
    const datos = Object.fromEntries(new FormData(formulario).entries())
    const cuerpo = mapearCuerpo(datos)
    const problema = problemaConsulta(cuerpo)
    if (problema) {
      pintarEstado(estado, `${mensajePara(422)} ${problema}`)
      return
    }
    const boton = formulario.querySelector('button[type="submit"]')
    boton.disabled = true
    estado.textContent = 'Enviando…'
    try {
      const cabeceras = {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'Idempotency-Key': clave,
      }
      const token = await tokenCaptcha('consulta')
      if (token) cabeceras['X-Recaptcha-Token'] = token
      const respuesta = await fetch(`${API_URL.replace(/\/+$/, '')}/publico/leads`, {
        method: 'POST',
        headers: cabeceras,
        body: JSON.stringify(cuerpo),
      })
      if (decidirClave(respuesta.status) === 'renovar') clave = crypto.randomUUID()
      if (respuesta.status === 201 || respuesta.status === 200) {
        let referencia = ''
        try {
          referencia = (await respuesta.json()).referencia || ''
        } catch {
          referencia = ''
        }
        formulario.reset()
        pintarEstado(estado, mensajePara(respuesta.status), enlaceDeReferencia(cuerpo, referencia))
      } else {
        pintarEstado(estado, mensajePara(respuesta.status))
      }
    } catch {
      pintarEstado(estado, 'No se pudo enviar. Inténtalo por teléfono o WhatsApp.')
    } finally {
      boton.disabled = false
    }
  })
}
