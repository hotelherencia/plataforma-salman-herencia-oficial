/**
 * Cableado del CTA «Consultar reserva» (CA-PUB-12, V1-ISSUE-25): valida el
 * rango con la misma regla del front y navega al deep link
 * `/reservar?inicio=…&fin=…&personas=…`. Sin datos personales en la URL.
 */
import { PLATAFORMA_URL } from './config.js'
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
