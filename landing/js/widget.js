/**
 * Cableado del CTA «Consultar reserva» (CA-PUB-12, V1-ISSUE-25): valida el
 * rango con la misma regla del front y navega al deep link
 * `/reservar?inicio=…&fin=…&personas=…`. Sin datos personales en la URL.
 *
 * «Ver disponibilidad» (V1-ISSUE-42): si el contacto está completo, primero
 * crea el lead y navega con `ref` opaca; si falta contacto, navega solo con
 * fechas y deja el aviso en `/reservar`.
 */
import { API_URL, PLATAFORMA_URL } from './config.js'
import { tokenCaptcha } from './captcha.js'
import { mapearCuerpo, problemaConsulta } from './leads.js'
import { construirEnlaceReserva, validarRango } from './reserva.js'

export function inicializarWidget(documento) {
  const formulario = documento.querySelector('[data-widget-reserva]')
  if (!formulario) return
  const alerta = formulario.querySelector('[role="alert"]')
  const campo = (nombre) => formulario.querySelector(`[name="${nombre}"]`)

  formulario.addEventListener('submit', (evento) => {
    evento.preventDefault()
    const inicio = campo('inicio').value
    const fin = campo('fin').value
    const personas = campo('personas').value
    const problema = validarRango(inicio, fin, personas)
    if (problema) {
      alerta.textContent = problema
      alerta.hidden = false
      return
    }
    alerta.hidden = true
    window.location.assign(construirEnlaceReserva(PLATAFORMA_URL, inicio, fin, personas))
  })
}

/**
 * «Ver disponibilidad» del formulario real (#checkin, #checkout, #guests).
 * Con contacto completo: POST /publico/leads y URL con `ref`. Sin contacto:
 * solo fechas/personas; `/reservar` avisa que hay que completarlos.
 */
export function inicializarDisponibilidad(documento) {
  const boton = documento.querySelector('[data-ver-disponibilidad]')
  if (!boton) return
  const formulario = boton.closest('form') || documento
  const alerta = formulario.querySelector('[data-disponibilidad-estado]')

  boton.addEventListener('click', async () => {
    const datos = Object.fromEntries(new FormData(formulario).entries())
    const cuerpo = mapearCuerpo(datos)
    const problemaFechas = validarRango(
      cuerpo.check_in,
      cuerpo.check_out,
      cuerpo.huespedes || 1,
    )
    if (problemaFechas) {
      if (alerta) {
        alerta.textContent = problemaFechas
        alerta.hidden = false
      }
      return
    }

    const sinContacto = problemaConsulta({
      ...cuerpo,
      // Las fechas ya pasaron validarRango; aquí solo importa el contacto.
      check_in: null,
      check_out: null,
      huespedes: null,
      mensaje: null,
    })

    if (sinContacto || !API_URL) {
      if (alerta) {
        alerta.textContent = sinContacto
          ? 'Vas a la reserva sin consulta previa: allí escribirás nombre y contacto. Para llevarlos, completa el formulario y pulsa Enviar consulta, o rellena nombre, correo y teléfono antes de Ver disponibilidad.'
          : 'Vas a la reserva solo con las fechas; el contacto se pide allá.'
        alerta.hidden = false
      }
      window.location.assign(
        construirEnlaceReserva(PLATAFORMA_URL, cuerpo.check_in, cuerpo.check_out, cuerpo.huespedes || 1),
      )
      return
    }

    boton.disabled = true
    if (alerta) {
      alerta.textContent = 'Enviando consulta…'
      alerta.hidden = false
    }
    try {
      const cabeceras = {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'Idempotency-Key': crypto.randomUUID(),
      }
      const token = await tokenCaptcha('consulta')
      if (token) cabeceras['X-Recaptcha-Token'] = token
      const respuesta = await fetch(`${API_URL.replace(/\/+$/, '')}/publico/leads`, {
        method: 'POST',
        headers: cabeceras,
        body: JSON.stringify(cuerpo),
      })
      if (respuesta.status !== 201 && respuesta.status !== 200) {
        if (alerta) {
          alerta.textContent =
            'No se pudo guardar la consulta. Abriremos la reserva; completa nombre y contacto allí.'
          alerta.hidden = false
        }
        window.location.assign(
          construirEnlaceReserva(PLATAFORMA_URL, cuerpo.check_in, cuerpo.check_out, cuerpo.huespedes || 1),
        )
        return
      }
      let referencia = ''
      try {
        referencia = (await respuesta.json()).referencia || ''
      } catch {
        referencia = ''
      }
      window.location.assign(
        construirEnlaceReserva(
          PLATAFORMA_URL,
          cuerpo.check_in,
          cuerpo.check_out,
          cuerpo.huespedes || 1,
          referencia || undefined,
        ),
      )
    } catch {
      if (alerta) {
        alerta.textContent =
          'No se pudo guardar la consulta. Abriremos la reserva; completa nombre y contacto allí.'
        alerta.hidden = false
      }
      window.location.assign(
        construirEnlaceReserva(PLATAFORMA_URL, cuerpo.check_in, cuerpo.check_out, cuerpo.huespedes || 1),
      )
    } finally {
      boton.disabled = false
    }
  })
}
