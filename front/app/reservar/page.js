'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { api, clp, mensajeDeError, Campo, useClaveOperacion, alRechazar } from '../../lib/api'
import { LOGO, NOMBRE_COMERCIAL } from '../../lib/marca'
import {
  agruparOferta, enlaceWhatsapp, erroresContacto, guardarReferencia, isoLocal, leerParametros,
  leerReferencia, olvidarReferencia, politicaUnica, urlCanonica, validarRango,
} from './continuidad'

/** Fecha local de hoy (AAAA-MM-DD): toISOString es UTC y adelanta un día tras
 *  las 21:00 en Chile, vetando llegadas válidas. */
function hoyLocal() {
  return isoLocal(new Date())
}

const CLAVE_SITIO_RECAPTCHA = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || '6LcKehguAAAAAG07HWp0QQOHJyMxQeWfQl3epp7n'
const SITIO = 'https://www.hotelherencia.cl'

function prepararRecaptcha() {
  if (document.querySelector('script[data-recaptcha]')) return
  const script = document.createElement('script')
  script.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(CLAVE_SITIO_RECAPTCHA)}&hl=es-419`
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

function almacenLocal() {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

/** Página pública del visitante (spec-front-v1 «Rutas públicas», V1-ISSUE-23):
 *  fuera del menú interno, lee la query por lista blanca (llegada/salida/personas
 *  y la referencia opaca de la landing), muestra lo que responde
 *  /publico/disponibilidad sin calcular nada y envía la solicitud con
 *  Idempotency-Key estable. Si el visitante ya dejó su consulta en la landing,
 *  nombre y correo llegan por la referencia y no se vuelven a pedir. */
function Reservar() {
  const params = useSearchParams()
  const inicial = useRef(leerParametros(params)).current
  const [inicio, setInicio] = useState(inicial.inicio)
  const [fin, setFin] = useState(inicial.fin)
  const [personas, setPersonas] = useState(inicial.personas || '2')
  // Contacto que trajo la referencia de la landing (null: no hay o no vigente).
  const [previo, setPrevio] = useState(null)
  const [editando, setEditando] = useState(false)
  const [resolviendoRef, setResolviendoRef] = useState(false)
  const [oferta, setOferta] = useState(null)
  const [personasConsultadas, setPersonasConsultadas] = useState(inicial.personas || '2')
  const [elegida, setElegida] = useState('')
  const [nombre, setNombre] = useState('')
  const [contacto, setContacto] = useState('')
  const [erroresCampo, setErroresCampo] = useState({})
  const [buscando, setBuscando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(inicial.avisos[0] || '')
  const [errorSolicitud, setErrorSolicitud] = useState('')
  const [confirmada, setConfirmada] = useState(null)
  const [clave, renovarClave] = useClaveOperacion()
  const refNombre = useRef(null)
  const refContacto = useRef(null)
  const refErrorSolicitud = useRef(null)
  const refConfirmada = useRef(null)

  async function buscar(proximoInicio, proximoFin, proximasPersonas) {
    const problema = validarRango(proximoInicio, proximoFin, proximasPersonas, hoyLocal())
    setError(problema || '')
    setOferta(null)
    setConfirmada(null)
    setErrorSolicitud('')
    if (problema) return
    setBuscando(true)
    try {
      const q = new URLSearchParams({ inicio: proximoInicio, fin: proximoFin, personas: String(Number(proximasPersonas)) })
      const r = await api(`/publico/disponibilidad?${q}`)
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
      } else {
        setOferta(r.datos)
        setPersonasConsultadas(String(Number(proximasPersonas)))
        const grupos = agruparOferta(r.datos.oferta)
        setElegida(grupos[0] ? grupos[0].habitacion_id : '')
      }
    } catch {
      setError('La API no está disponible: nada se puede confirmar. Intenta de nuevo en unos minutos.')
    } finally {
      setBuscando(false)
    }
  }

  useEffect(() => {
    prepararRecaptcha()
  }, [])

  // Una sola vez al entrar: consulta con las fechas del enlace, guarda la
  // referencia y deja la URL canónica (llegada/salida/personas, sin ref).
  useEffect(() => {
    const { inicio: i, fin: f, personas: p, ref: refUrl } = inicial
    if (i && f) buscar(i, f, p || '2')
    const almacen = almacenLocal()
    if (refUrl) guardarReferencia(almacen, refUrl)
    const canonica = urlCanonica(window.location.href, { inicio: i, fin: f, personas: p })
    if (canonica) window.history.replaceState(window.history.state, '', canonica)

    const ref = refUrl || leerReferencia(almacen)
    if (!ref) return
    let vigente = true
    setResolviendoRef(true)
    api(`/publico/referencia?token=${encodeURIComponent(ref)}`)
      .then((r) => {
        if (!vigente) return
        if (r.estado === 200 && r.datos && (r.datos.nombre || r.datos.correo)) {
          const datos = { nombre: String(r.datos.nombre || ''), correo: String(r.datos.correo || '') }
          setPrevio(datos)
          setNombre(datos.nombre)
          setContacto(datos.correo)
        } else if (r.estado === 404 || r.estado === 422) {
          olvidarReferencia(almacen) // vencida, revocada o ajena: no se reintenta
        }
      })
      .catch(() => {})
      .finally(() => {
        if (vigente) setResolviendoRef(false)
      })
    return () => {
      vigente = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function enfocar(ref) {
    const el = ref.current
    if (!el) return
    el.scrollIntoView({ block: 'center', behavior: 'smooth' })
    el.focus({ preventScroll: true })
  }

  async function enviar(e) {
    e.preventDefault()
    setErrorSolicitud('')
    setConfirmada(null)
    const problema = validarRango(inicio, fin, personas, hoyLocal())
    if (problema) {
      setErrorSolicitud(problema)
      requestAnimationFrame(() => enfocar(refErrorSolicitud))
      return
    }
    if (!elegida) {
      setErrorSolicitud('Elige una de las opciones disponibles.')
      requestAnimationFrame(() => enfocar(refErrorSolicitud))
      return
    }
    const errores = erroresContacto(nombre, contacto)
    setErroresCampo(errores)
    if (errores.nombre || errores.contacto) {
      setEditando(true)
      requestAnimationFrame(() => enfocar(errores.nombre ? refNombre : refContacto))
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
        setErrorSolicitud(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
        requestAnimationFrame(() => enfocar(refErrorSolicitud))
      } else {
        setConfirmada(r.datos)
        renovarClave() // 2xx: la clave se repone para una operación nueva
        requestAnimationFrame(() => enfocar(refConfirmada))
      }
    } catch {
      setErrorSolicitud('La API no está disponible: tu solicitud no se envió. Intenta de nuevo.')
      requestAnimationFrame(() => enfocar(refErrorSolicitud))
    } finally {
      setEnviando(false)
    }
  }

  const grupos = oferta ? agruparOferta(oferta.oferta) : []
  const politica = oferta ? politicaUnica(oferta.oferta) : null
  const tope = oferta ? oferta.capacidad_maxima_habitacion : null
  const excedeHabitacion = oferta && tope && Number(personasConsultadas) > tope
  const mostrarCampos = !previo || editando

  return (
    <main className="pagina pagina-publica reservar">
      <p className="reservar-volver">
        <a href={SITIO}>← Volver a hotelherencia.cl</a>
      </p>
      <header className="pagina-cabecera pagina-cabecera-marca">
        <img className="cabecera-logo" src={LOGO.h64} srcSet={`${LOGO.h64} 1x, ${LOGO.h128} 2x`} alt={NOMBRE_COMERCIAL} width="80" height="64" />
        <div>
          <h1>Reserva · {NOMBRE_COMERCIAL}</h1>
          <p className="operador">Consulta disponibilidad y deja tu solicitud: recepción la confirma contigo.</p>
        </div>
      </header>

      <section className="tarjeta">
        <form
          className="formulario formulario-busqueda"
          onSubmit={(e) => {
            e.preventDefault()
            buscar(inicio, fin, personas)
          }}
        >
          <Campo etiqueta="Llegada" type="date" min={hoyLocal()} value={inicio} onChange={(e) => setInicio(e.target.value)} />
          <Campo etiqueta="Salida" type="date" min={inicio || hoyLocal()} value={fin} onChange={(e) => setFin(e.target.value)} />
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
          {grupos.length === 0 ? (
            excedeHabitacion ? (
              <div className="estado" data-aviso-grupo>
                <p>
                  Cada habitación recibe hasta {tope} personas. Para {Number(personasConsultadas)} personas, recepción arma
                  la reserva con varias habitaciones.
                </p>
                <p className="acciones-fila">
                  <a className="boton-primario" href={enlaceWhatsapp(inicio, fin, personasConsultadas)} target="_blank" rel="noopener noreferrer">
                    Escribir a recepción por WhatsApp
                  </a>
                  <a className="boton-secundario" href={`${SITIO}/#contacto`}>Enviar una consulta</a>
                </p>
              </div>
            ) : (
              <div className="estado">
                <p>No quedan habitaciones para esas fechas. Prueba con otro rango o escríbenos y te ayudamos.</p>
                <p className="acciones-fila">
                  <a className="boton-secundario" href={enlaceWhatsapp(inicio, fin, personasConsultadas)} target="_blank" rel="noopener noreferrer">
                    Escribir por WhatsApp
                  </a>
                </p>
              </div>
            )
          ) : (
            <>
              <p className="estado">
                Valores por noche con IVA incluido; la oferta vence en {oferta.vigencia_minutos} minutos.
              </p>
              <fieldset className="lista-opciones">
                <legend className="sr-only">Tipo de habitación</legend>
                {grupos.map((g) => (
                  <label key={g.tipo} className="opcion opcion-tipo">
                    <input
                      type="radio"
                      name="habitacion"
                      checked={elegida === g.habitacion_id}
                      onChange={() => setElegida(g.habitacion_id)}
                    />
                    <span className="opcion-cuerpo">
                      <span className="opcion-titulo">{g.nombre}</span>
                      <span className="opcion-detalle">
                        {g.capacidad ? `Hasta ${g.capacidad} ${g.capacidad === 1 ? 'persona' : 'personas'} · ` : ''}
                        {g.disponibles === 1 ? 'queda 1' : `quedan ${g.disponibles}`}
                      </span>
                    </span>
                    <span className="opcion-precio">
                      <span>{g.precios_distintos ? 'desde ' : ''}{clp(g.tarifa_noche_clp)} por noche</span>
                      <strong>{clp(g.total_clp)} total</strong>
                    </span>
                  </label>
                ))}
              </fieldset>
              {politica && <p className="estado politica-cancelacion">Cancelación: {politica}.</p>}

              <form className="formulario-solicitud" onSubmit={enviar} noValidate>
                {previo && !editando && (
                  <div className="contacto-previo" data-contacto-previo>
                    <p>
                      Te contactaremos a <strong>{previo.correo || 'tu contacto'}</strong>
                      {previo.nombre ? <> a nombre de <strong>{previo.nombre}</strong></> : null}. Lo tomamos de la consulta
                      que ya enviaste.
                    </p>
                    <button type="button" className="boton-secundario" onClick={() => setEditando(true)}>
                      Editar mis datos
                    </button>
                  </div>
                )}
                {!previo && !resolviendoRef && (
                  <p className="estado nota-contacto" data-aviso-sin-ref>
                    Déjanos tu nombre y un correo o teléfono para que recepción te confirme la reserva.
                  </p>
                )}
                {mostrarCampos && (
                  <div className="campos-contacto">
                    <div>
                      <Campo
                        etiqueta="Nombre"
                        ref={refNombre}
                        autoComplete="name"
                        maxLength={120}
                        value={nombre}
                        aria-invalid={erroresCampo.nombre ? 'true' : undefined}
                        aria-describedby={erroresCampo.nombre ? 'error-nombre' : undefined}
                        onChange={(e) => {
                          setNombre(e.target.value)
                          if (erroresCampo.nombre) setErroresCampo({ ...erroresCampo, nombre: undefined })
                        }}
                      />
                      {erroresCampo.nombre && <p id="error-nombre" className="error-campo">{erroresCampo.nombre}</p>}
                    </div>
                    <div>
                      <Campo
                        etiqueta="Correo o teléfono"
                        ref={refContacto}
                        autoComplete="email"
                        maxLength={120}
                        value={contacto}
                        aria-invalid={erroresCampo.contacto ? 'true' : undefined}
                        aria-describedby={erroresCampo.contacto ? 'error-contacto' : undefined}
                        onChange={(e) => {
                          setContacto(e.target.value)
                          if (erroresCampo.contacto) setErroresCampo({ ...erroresCampo, contacto: undefined })
                        }}
                      />
                      {erroresCampo.contacto && <p id="error-contacto" className="error-campo">{erroresCampo.contacto}</p>}
                    </div>
                  </div>
                )}
                <p className="aviso-tratamiento" data-aviso-version="2026-11-10-aviso-02">
                  Hotel Herencia usará tu nombre, correo, teléfono, fechas y mensaje para responder esta consulta y, si sigues, para dejar la solicitud de alojamiento. Recepción la revisa: enviar no confirma la estadía. No pedimos RUT, datos de salud ni tarjeta; no los escribas en el mensaje. Google reCAPTCHA puntúa el envío. Lee quién trata tus datos, por cuánto tiempo y cómo pedir acceso o supresión en la <Link href="/privacidad">política de tratamiento</Link> (versión 2026-11-10-aviso-02).
                </p>
                {errorSolicitud && (
                  <p role="alert" className="alerta" tabIndex={-1} ref={refErrorSolicitud}>{errorSolicitud}</p>
                )}
                <button type="submit" className="boton-primario boton-enviar" disabled={enviando || grupos.length === 0}>
                  {enviando ? 'Enviando…' : 'Enviar solicitud'}
                </button>
              </form>
            </>
          )}
        </section>
      )}

      {confirmada && (
        <section className="tarjeta" role="status" tabIndex={-1} ref={refConfirmada}>
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
    <Suspense fallback={<main className="pagina pagina-publica"><p className="estado">Cargando…</p></main>}>
      <Reservar />
    </Suspense>
  )
}
