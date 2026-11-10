/**
 * reCAPTCHA v3 del formulario de contacto. La clave de sitio es pública; la
 * secreta solo la usa el servicio. Sin clave (el E2E la deja vacía) no se
 * carga el script y el envío sigue, porque el servicio solo exige el token
 * cuando RECAPTCHA_SECRET_KEY está configurada. La acción es `consulta`,
 * distinta de `reserva` en /reservar.
 */
const CLAVE_POR_DEFECTO = '6LcKehguAAAAAG07HWp0QQOHJyMxQeWfQl3epp7n'

export function claveSitio() {
  if (typeof window === 'undefined') return ''
  if (window.LANDING_RECAPTCHA_SITE_KEY !== undefined) return window.LANDING_RECAPTCHA_SITE_KEY
  return CLAVE_POR_DEFECTO
}

export function prepararCaptcha(documento) {
  const clave = claveSitio()
  if (!clave || documento.querySelector('script[data-recaptcha]')) return
  const script = documento.createElement('script')
  script.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(clave)}`
  script.async = true
  script.referrerPolicy = 'origin'
  script.dataset.recaptcha = 'v3'
  documento.head.append(script)
}

/** Token de la acción, o cadena vacía si el script no alcanzó a cargar. */
export function tokenCaptcha(accion, esperaMs = 1500) {
  const clave = claveSitio()
  if (!clave || typeof window === 'undefined') return Promise.resolve('')
  return new Promise((resolve) => {
    const inicio = Date.now()
    const intentar = () => {
      if (!window.grecaptcha) {
        if (Date.now() - inicio > esperaMs) {
          resolve('')
          return
        }
        window.setTimeout(intentar, 50)
        return
      }
      try {
        window.grecaptcha.ready(() => {
          window.grecaptcha
            .execute(clave, { action: accion })
            .then((valor) => resolve(valor || ''))
            .catch(() => resolve(''))
        })
      } catch {
        resolve('')
      }
    }
    intentar()
  })
}
