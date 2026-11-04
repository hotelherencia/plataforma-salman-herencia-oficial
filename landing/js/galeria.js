/**
 * Carrusel accesible de las secciones Habitaciones y Galería.
 * Mejora progresiva: sin JS queda visible la primera imagen de cada grupo.
 * Cada carrusel se declara en el HTML como `[data-carrusel]` con viñetas
 * `[data-carrusel-viñeta]` y un `aria-live` para el cambio.
 */
export function inicializarCarruseles(documento) {
  documento.querySelectorAll('[data-carrusel]').forEach((carrusel) => {
    const laminas = [...carrusel.querySelectorAll('[data-carrusel-lamina]')]
    const vinetas = [...carrusel.querySelectorAll('[data-carrusel-vineta]')]
    if (laminas.length === 0 || vinetas.length === 0) return

    const mostrar = (indice) => {
      laminas.forEach((lamina, i) => {
        lamina.hidden = i !== indice
      })
      vinetas.forEach((vineta, i) => {
        vineta.setAttribute('aria-pressed', i === indice ? 'true' : 'false')
      })
    }
    const actual = () => vinetas.findIndex((v) => v.getAttribute('aria-pressed') === 'true')

    carrusel.querySelector('[data-carrusel-anterior]')?.addEventListener('click', () => {
      mostrar((actual() - 1 + laminas.length) % laminas.length)
    })
    carrusel.querySelector('[data-carrusel-siguiente]')?.addEventListener('click', () => {
      mostrar((actual() + 1) % laminas.length)
    })
    vinetas.forEach((vineta, i) => vineta.addEventListener('click', () => mostrar(i)))
    mostrar(Math.max(actual(), 0))
  })
}
