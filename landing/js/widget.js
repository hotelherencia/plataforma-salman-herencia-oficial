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

/**
 * «Ver disponibilidad» del formulario real (#checkin, #checkout, #guests).
 * Los enlaces «Consultar reserva» siguen en #contacto. La URL lleva solo
 * inicio, fin y personas.
 */
export function inicializarDisponibilidad(documento) {
  const boton = documento.querySelector('[data-ver-disponibilidad]')
  if (!boton) return
  const formulario = boton.closest('form') || documento
  const alerta = formulario.querySelector('[data-disponibilidad-estado]')
  const valor = (id) => documento.getElementById(id)?.value ?? ''

  boton.addEventListener('click', () => {
    const inicio = valor('checkin')
    const fin = valor('checkout')
    const personas = valor('guests')
    const problema = validarRango(inicio, fin, personas)
    if (problema) {
      if (alerta) {
        alerta.textContent = problema
        alerta.hidden = false
      }
      return
    }
    if (alerta) alerta.hidden = true
    window.location.assign(construirEnlaceReserva(PLATAFORMA_URL, inicio, fin, personas))
  })
}
