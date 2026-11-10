'use client'

import { Suspense, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { api, clp, mensajeDeError, Campo, useClaveOperacion, alRechazar } from '../../lib/api'

/** Fecha local de hoy (AAAA-MM-DD): toISOString es UTC y adelanta un día tras
 *  las 21:00 en Chile, vetando llegadas válidas. */
function hoyLocal() {
  const d = new Date()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const dia = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${m}-${dia}`
}

const CLAVE_SITIO_RECAPTCHA = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || '6LcKehguAAAAAG07HWp0QQOHJyMxQeWfQl3epp7n'

function prepararRecaptcha() {
  if (document.querySelector('script[data-recaptcha]')) return
  const script = document.createElement('script')
  script.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(CLAVE_SITIO_RECAPTCHA)}`
  script.async = true
  script.referrerPolicy = 'origin'
  script.dataset.recaptcha = 'v3'
  document.head.append(script)
}

function tokenRecaptcha(accion) {
  return new Promise((resolve) => {
    const inicio = Date.now()
    const ejecutar = () => {
      window.grecaptcha.ready(() => {
        window.grecaptcha.execute(CLAVE_SITIO_RECAPTCHA, { action: accion }).then(resolve).catch(() => resolve(''))
      })
    }
    if (window.grecaptcha) {
      ejecutar()
      return
    }
    const reloj = window.setInterval(() => {
      if (window.grecaptcha) {
        window.clearInterval(reloj)
        ejecutar()
      } else if (Date.now() - inicio > 8000) {
        window.clearInterval(reloj)
        resolve('')
      }
    }, 50)
  })
}

function fechaIso(valor) {
  return /^\d{4}-\d{2}-\d{2}$/.test(valor)
}

function personasValidas(valor) {
  return /^\d{1,2}$/.test(String(valor)) && Number(valor) >= 1 && Number(valor) <= 30
}

function referenciaValida(valor) {
  return /^[A-Za-z0-9_-]{20,128}$/.test(valor)
}

function validar(inicio, fin, personas) {
  if (!inicio || !fin) return 'Indica las fechas de tu estadía.'
  if (fin <= inicio) return 'La salida debe ser posterior a la llegada.'
  if (inicio < hoyLocal()) return 'La llegada no puede ser una fecha pasada.'
  if ((new Date(`${fin}T00:00:00`) - new Date(`${inicio}T00:00:00`)) / 86400000 > 30)
    return 'El rango supera las 30 noches.'
  const n = Number(personas)
  if (!Number.isInteger(n) || n < 1 || n > 30) return 'Personas debe estar entre 1 y 30.'
  return null
}

/** Página pública del visitante (spec-front-v1 «Rutas públicas», V1-ISSUE-23):
 *  fuera del menú interno, lee y valida los parámetros de la landing, muestra
 *  lo que responde /publico/disponibilidad sin calcular nada, y envía la
 *  solicitud con Idempotency-Key estable. */
function Reservar() {
  const params = useSearchParams()
  const inicioParam = params.get('inicio') || ''
  const finParam = params.get('fin') || ''
  const personasParam = params.get('personas') || ''
  const [inicio, setInicio] = useState(fechaIso(inicioParam) ? inicioParam : '')
  const [fin, setFin] = useState(fechaIso(finParam) ? finParam : '')
  const [personas, setPersonas] = useState(personasValidas(personasParam) ? String(Number(personasParam)) : '2')
  const [datosDeLaLanding, setDatosDeLaLanding] = useState(false)
  const [avisoSinRef, setAvisoSinRef] = useState(false)
  const [oferta, setOferta] = useState(null)
  const [elegida, setElegida] = useState('')
  const [nombre, setNombre] = useState('')
  const [contacto, setContacto] = useState('')
  const [buscando, setBuscando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [confirmada, setConfirmada] = useState(null)
  const [clave, renovarClave] = useClaveOperacion()

  async function buscar(proximoInicio, proximoFin, proximasPersonas) {
    const problema = validar(proximoInicio, proximoFin, proximasPersonas)
    setError(problema || '')
    setOferta(null)
    setConfirmada(null)
    if (problema) return
    setBuscando(true)
    try {
      const r = await api(
        `/publico/disponibilidad?inicio=${proximoInicio}&fin=${proximoFin}&personas=${Number(proximasPersonas)}`
      )
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
      } else {
        setOferta(r.datos)
        setElegida(r.datos.oferta[0] ? r.datos.oferta[0].habitacion_id : '')
      }
    } catch {
      setError('La API no está disponible: nada se puede confirmar. Intenta de nuevo en unos minutos.')
    } finally {
      setBuscando(false)
    }
  }

  // Deep link desde la landing (CA-PUB-07): precarga y consulta al entrar.
  useEffect(() => {
    prepararRecaptcha()
  }, [])

  useEffect(() => {
    const i = fechaIso(inicioParam) ? inicioParam : ''
    const f = fechaIso(finParam) ? finParam : ''
    const p = personasValidas(personasParam) ? String(Number(personasParam)) : ''
    if (!fechaIso(inicioParam) && inicioParam) setError('La llegada indicada en el enlace no es válida.')
    else if (!fechaIso(finParam) && finParam) setError('La salida indicada en el enlace no es válida.')
    else if (personasParam && !personasValidas(personasParam)) setError('La cantidad de personas del enlace no es válida.')
    if (i) setInicio(i)
    if (f) setFin(f)
    if (p) setPersonas(p)
    if (i && f) buscar(i, f, p || '2')

    const ref = params.get('ref') || ''
    if (!referenciaValida(ref)) {
      // V1-ISSUE-42: fechas sin `ref` no son un fallo silencioso — el visitante
      // debe saber que tendrá que escribir el contacto otra vez.
      if (i && f) setAvisoSinRef(true)
      return
    }
    let vigente = true
    api(`/publico/referencia?token=${encodeURIComponent(ref)}`)
      .then((r) => {
        if (!vigente) return
        if (r.estado !== 200) {
          setAvisoSinRef(true)
          return
        }
        if (r.datos.nombre) setNombre(r.datos.nombre)
        if (r.datos.correo) setContacto(r.datos.correo)
        else if (r.datos.telefono) setContacto(r.datos.telefono)
        setDatosDeLaLanding(true)
        setAvisoSinRef(false)
      })
      .catch(() => {
        if (vigente) setAvisoSinRef(true)
      })
    return () => {
      vigente = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params])

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setConfirmada(null)
    const problema = validar(inicio, fin, personas)
    if (problema) {
      setError(problema)
      return
    }
    if (!elegida) {
      setError('Elige una de las opciones disponibles.')
      return
    }
    if (!nombre.trim() || !contacto.trim()) {
      setError('Indica tu nombre y un medio de contacto.')
      return
    }
    setEnviando(true)
    try {
      const cabeceras = {}
      const token = await tokenRecaptcha('reserva')
      if (token) cabeceras['X-Recaptcha-Token'] = token
      const r = await api('/publico/solicitudes', {
        metodo: 'POST',
        cuerpo: {
          habitacion_id: elegida, inicio, fin, personas: Number(personas),
          huesped_nombre: nombre.trim(), huesped_contacto: contacto.trim(),
        },
        claveIdempotencia: clave,
        cabeceras,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
      } else {
        setConfirmada(r.datos)
        renovarClave() // 2xx: la clave se repone para una operación nueva
      }
    } catch {
      setError('La API no está disponible: tu solicitud no se envió. Intenta de nuevo.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="pagina">
      <header className="pagina-cabecera">
        <h1>Reserva · Hotel Herencia</h1>
        <p className="operador">Consulta disponibilidad y deja tu solicitud: recepción la confirma contigo.</p>
      </header>

      <section className="tarjeta">
        <form
          className="formulario"
          onSubmit={(e) => {
            e.preventDefault()
            buscar(inicio, fin, personas)
          }}
        >
          <Campo etiqueta="Llegada" type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} />
          <Campo etiqueta="Salida" type="date" value={fin} onChange={(e) => setFin(e.target.value)} />
          <Campo
            etiqueta="Personas"
            type="number"
            min="1"
            max="30"
            value={personas}
            onChange={(e) => setPersonas(e.target.value)}
          />
          <button type="submit" className="boton-primario" disabled={buscando}>
            {buscando ? 'Consultando…' : 'Ver disponibilidad'}
          </button>
        </form>
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}

      {oferta && (
        <section className="tarjeta">
          <h2>Disponibilidad</h2>
          {oferta.oferta.length === 0 ? (
            <p className="estado">
              No hay opciones para esas fechas. Prueba con otro rango o escríbenos y te ayudamos.
            </p>
          ) : (
            <>
              <p className="estado">
                Valores por noche según tarifa vigente; la oferta vence en {oferta.vigencia_minutos} minutos.
              </p>
              <div className="lista-opciones">
                {oferta.oferta.map((item) => (
                  <label key={item.habitacion_id} className="opcion">
                    <input
                      type="radio"
                      name="habitacion"
                      checked={elegida === item.habitacion_id}
                      onChange={() => setElegida(item.habitacion_id)}
                    />
                    <span>
                      {item.habitacion_id} · {item.tipo} — {clp(item.tarifa_noche_clp)} por noche ·{' '}
                      <strong>{clp(item.total_clp)}</strong> total · cancelación: {item.politica_cancelacion}
                    </span>
                  </label>
                ))}
              </div>
              <form className="formulario" onSubmit={enviar}>
                {datosDeLaLanding && (
                  <p className="estado">Tomamos tu nombre y tu correo de la consulta que ya enviaste. No hace falta repetirlos.</p>
                )}
                {avisoSinRef && !datosDeLaLanding && (
                  <p className="estado" role="status" data-aviso-sin-ref>
                    Esta página no trajo tu consulta previa. Completa nombre y correo o teléfono aquí, o vuelve al formulario de contacto de la landing y usa «Continuar con la reserva» para no escribirlos otra vez.
                  </p>
                )}
                <Campo etiqueta="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} />
                <Campo
                  etiqueta="Correo o teléfono"
                  value={contacto}
                  onChange={(e) => setContacto(e.target.value)}
                />
                <p className="aviso-tratamiento" data-aviso-version="2026-11-10-aviso-02">
                  Hotel Herencia usará tu nombre, correo, teléfono, fechas y mensaje para responder esta consulta y, si sigues, para dejar la solicitud de alojamiento. Recepción la revisa: enviar no confirma la estadía. No pedimos RUT, datos de salud ni tarjeta; no los escribas en el mensaje. Google reCAPTCHA puntúa el envío. Lee quién trata tus datos, por cuánto tiempo y cómo pedir acceso o supresión en la <Link href="/privacidad">política de tratamiento</Link> (versión 2026-11-10-aviso-02).
                </p>
                <button type="submit" className="boton-primario" disabled={enviando || oferta.oferta.length === 0}>
                  {enviando ? 'Enviando…' : 'Enviar solicitud'}
                </button>
              </form>
            </>
          )}
        </section>
      )}

      {confirmada && (
        <section className="tarjeta" role="status">
          <h2>Solicitud recibida</h2>
          <p className="resumen">
            Tu solicitud <strong>{confirmada.solicitud_id}</strong> quedó registrada. Recepción la revisará y
            te contactará por el medio que indicaste para confirmar.
          </p>
        </section>
      )}
    </main>
  )
}

export default function ReservarEnvuelta() {
  return (
    <Suspense fallback={<main className="pagina"><p className="estado">Cargando…</p></main>}>
      <Reservar />
    </Suspense>
  )
}
