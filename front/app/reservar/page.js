'use client'

import { Suspense, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { api, clp, mensajeDeError, Campo, useClaveOperacion, alRechazar } from '../../lib/api'
import { LOGO, NOMBRE_COMERCIAL } from '../../lib/marca'
import {
  agruparOferta, elegirTipo, enlaceWhatsapp, erroresContacto, guardarReferencia, isoLocal, leerParametros,
  leerReferencia, olvidarReferencia, politicaUnica, urlCanonica, validarRango,
} from './continuidad'
import { enviarSolicitud, mensajeSolicitud, obtenerToken } from './envio'

/** Fecha local de hoy (AAAA-MM-DD): toISOString es UTC y adelanta un día tras
 *  las 21:00 en Chile, vetando llegadas válidas. */
function hoyLocal() {
  return isoLocal(new Date())
}

const CLAVE_SITIO_RECAPTCHA = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || '6LcKehguAAAAAG07HWp0QQOHJyMxQeWfQl3epp7n'
const SITIO = 'https://www.hotelherencia.cl'

// Si el script de Google no carga (bloqueador, Firefox estricto, red) se sabe al
// instante por su evento error y se avisa eso, no un error genérico.
let recaptchaBloqueado = false

function prepararRecaptcha() {
  if (document.querySelector('script[data-recaptcha]')) return
  recaptchaBloqueado = false
  const script = document.createElement('script')
  script.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(CLAVE_SITIO_RECAPTCHA)}&hl=es-419`
  script.async = true
  script.referrerPolicy = 'origin'
  script.dataset.recaptcha = 'v3'
  script.onerror = () => {
    recaptchaBloqueado = true
    script.remove() // un intento posterior lo vuelve a pedir (p. ej. tras desactivar el bloqueador)
  }
  document.head.append(script)
}

/** Token nuevo al momento de enviar; nunca se reutiliza (cada uno sirve una vez). */
function tokenRecaptcha(accion) {
  prepararRecaptcha()
  return obtenerToken(window, CLAVE_SITIO_RECAPTCHA, accion, { bloqueado: () => recaptchaBloqueado })
}

function almacenSesion() {
  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

function limpiarAlmacenLegacy() {
  try {
    window.localStorage.removeItem('herencia:consulta-ref')
  } catch {
    // sin almacenamiento
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
  // landinpage#1: tipo pedido por el enlace (o el último que eligió el visitante).
  const preferidoRef = useRef(inicial.tipo)
  const [avisoTipo, setAvisoTipo] = useState('')
  const [nombre, setNombre] = useState('')
  const [contacto, setContacto] = useState('')
  const [erroresCampo, setErroresCampo] = useState({})
  const [buscando, setBuscando] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(inicial.avisos[0] || '')
  const [errorSolicitud, setErrorSolicitud] = useState('')
  const [confirmada, setConfirmada] = useState(null)
  const [clave, renovarClave] = useClaveOperacion()
  const refActiva = useRef('')
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
        const { tipo: elegidoAhora, aviso } = elegirTipo(agruparOferta(r.datos.oferta), preferidoRef.current)
        setElegida(elegidoAhora)
        setAvisoTipo(aviso)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Nada se puede confirmar por el momento. Intenta de nuevo en unos minutos.')
    } finally {
      setBuscando(false)
    }
  }

  useEffect(() => {
    prepararRecaptcha()
  }, [])

  // Una sola vez al entrar: limpia cualquier referencia heredada en localStorage,
  // respeta ?limpiar=1 o llegada sin ref (sin arrastrar datos de otra consulta),
  // y si viene ?ref= opaco resuelve fechas/personas/contacto desde el servidor
  // dejando la URL completamente limpia (sin ref ni datos personales).
  useEffect(() => {
    const { inicio: i, fin: f, personas: p, ref: refUrl, limpiar } = inicial
    const almacen = almacenSesion()
    limpiarAlmacenLegacy()
    if (i && f) buscar(i, f, p || '2')

    if (limpiar || (!refUrl && (i || f))) {
      olvidarReferencia(almacen)
      refActiva.current = ''
      const canonica = urlCanonica(window.location.href, { inicio: i, fin: f, personas: p, tipo: inicial.tipo })
      if (canonica) window.history.replaceState(window.history.state, '', canonica)
      return
    }

    if (refUrl) guardarReferencia(almacen, refUrl)
    const canonica = urlCanonica(window.location.href, { inicio: i, fin: f, personas: p, tipo: inicial.tipo })
    if (canonica) window.history.replaceState(window.history.state, '', canonica)

    const ref = refUrl || leerReferencia(almacen)
    if (!ref) return
    refActiva.current = ref
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
          // Si las fechas viajaron de forma opaca dentro de `ref` (sin texto plano en la URL),
          // se precargan y consultan disponibilidad automáticamente.
          const llegadaSrv = r.datos.llegada || ''
          const salidaSrv = r.datos.salida || ''
          const personasSrv = r.datos.personas ? String(r.datos.personas) : (p || '2')
          if (!i && !f && llegadaSrv && salidaSrv) {
            setInicio(llegadaSrv)
            setFin(salidaSrv)
            setPersonas(personasSrv)
            buscar(llegadaSrv, salidaSrv, personasSrv)
          }
        } else if (r.estado === 404 || r.estado === 422) {
          olvidarReferencia(almacen) // vencida, revocada o ajena: no se reintenta
          refActiva.current = ''
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

  function limpiarContactoPrevio() {
    olvidarReferencia(almacenSesion())
    limpiarAlmacenLegacy()
    refActiva.current = ''
    setPrevio(null)
    setEditando(false)
    setNombre('')
    setContacto('')
    setErroresCampo({})
  }

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
      const resultado = await enviarSolicitud({
        token: () => tokenRecaptcha('reserva'),
        pedir: (cabeceras) => api('/publico/solicitudes', {
          metodo: 'POST',
          cuerpo: {
            tipo: elegida, inicio, fin, personas: Number(personas),
            huesped_nombre: nombre.trim(), huesped_contacto: contacto.trim(),
            ...(refActiva.current ? { referencia: refActiva.current } : {}),
          },
          claveIdempotencia: clave,
          cabeceras,
          timeoutMs: 30000,
        }),
      })
      if (resultado.tipo === 'respuesta' && resultado.estado < 400) {
        setConfirmada(resultado.datos)
        limpiarContactoPrevio()
        renovarClave() // 2xx: la clave se repone para una operación nueva
        requestAnimationFrame(() => enfocar(refConfirmada))
      } else {
        setErrorSolicitud(mensajeSolicitud(resultado, mensajeDeError))
        // 4xx definitivo: clave nueva. Red caída o 5xx: se conserva para que
        // reintentar no duplique la solicitud.
        if (resultado.tipo === 'respuesta') alRechazar(resultado.estado, renovarClave)
        requestAnimationFrame(() => enfocar(refErrorSolicitud))
      }
    } catch {
      setErrorSolicitud('No pudimos enviar tu solicitud. Inténtalo de nuevo o escríbenos por WhatsApp al +56 9 5649 1501. (código JS)')
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
        <img className="cabecera-logo" src={LOGO.hojaSvg} alt="" width="68" height="60" />
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
          <Campo etiqueta="Llegada" type="date" min={hoyLocal()} value={inicio} onChange={(e) => { setInicio(e.target.value); setOferta(null); setElegida('') }} />
          <Campo etiqueta="Salida" type="date" min={inicio || hoyLocal()} value={fin} onChange={(e) => { setFin(e.target.value); setOferta(null); setElegida('') }} />
          <Campo
            etiqueta="Personas"
            type="number"
            min="1"
            max="30"
            value={personas}
            onChange={(e) => { setPersonas(e.target.value); setOferta(null); setElegida('') }}
          />
          <button type="submit" className="boton-primario" disabled={buscando}>
            {buscando ? 'Consultando…' : 'Ver disponibilidad'}
          </button>
        </form>
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}

      {oferta && !confirmada && (
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
              {avisoTipo && <p className="estado" role="status" data-aviso-tipo>{avisoTipo}</p>}
              <fieldset className="lista-opciones">
                <legend className="sr-only">Tipo de habitación</legend>
                {grupos.map((g) => (
                  <label key={g.tipo} className="opcion opcion-tipo">
                    <input
                      type="radio"
                      name="habitacion"
                      checked={elegida === g.tipo}
                      onChange={() => { setElegida(g.tipo); preferidoRef.current = g.tipo; setAvisoTipo('') }}
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
                    <div className="acciones-fila">
                      <button type="button" className="boton-secundario" onClick={() => setEditando(true)}>
                        Editar mis datos
                      </button>
                      <button type="button" className="boton-fantasma" onClick={limpiarContactoPrevio}>
                        Usar otros datos
                      </button>
                    </div>
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
                        autoComplete="on"
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
                  Hotel Herencia usará tu nombre, correo o teléfono y fechas para responder esta consulta y registrar tu solicitud de alojamiento. Recepción la revisa: enviar no confirma la estadía. No pedimos RUT, datos de salud ni tarjeta; no los escribas en la solicitud. Google reCAPTCHA puntúa el envío. Lee quién trata tus datos, por cuánto tiempo y cómo pedir acceso o supresión en la <Link href="/privacidad">política de tratamiento</Link> (versión 2026-11-10-aviso-02).
                </p>
                {errorSolicitud && (
                  <p role="alert" className="alerta" tabIndex={-1} ref={refErrorSolicitud}>{errorSolicitud}</p>
                )}
                <button type="submit" className="boton-primario boton-enviar" disabled={enviando || grupos.length === 0}>
                  {enviando ? 'Enviando…' : 'Enviar solicitud'}
                </button>
                {/* El sello flotante de reCAPTCHA se oculta (tapaba la página); Google lo permite con este aviso visible junto al envío. */}
                <p className="recaptcha-aviso">
                  Este sitio está protegido por reCAPTCHA y se aplican la{' '}
                  <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Política de privacidad</a> y las{' '}
                  <a href="https://policies.google.com/terms" target="_blank" rel="noopener noreferrer">Condiciones del servicio</a> de Google.
                </p>
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
          <p className="acciones">
            <button
              type="button"
              className="boton-secundario"
              onClick={() => {
                setConfirmada(null)
                setOferta(null)
                setElegida('')
                limpiarContactoPrevio()
              }}
            >
              Hacer otra consulta
            </button>
          </p>
        </section>
      )}
    </main>
  )
}

export default function ReservarEnvuelta() {
  return (
    <Suspense fallback={<main className="pagina pagina-publica"><p className="estado" role="status" aria-busy="true">Cargando…</p></main>}>
      <Reservar />
    </Suspense>
  )
}
