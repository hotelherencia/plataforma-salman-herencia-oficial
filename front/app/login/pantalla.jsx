'use client'

import { useEffect, useState } from 'react'
import { api, urlApi, refrescarSesion, useSesion, mensajeMotivoSesion, mensajeDeError, CampoClave } from '../../lib/api'
import { LOGO, NOMBRE_COMERCIAL } from '../../lib/marca'
import { mensajeErrorLogin } from '../../lib/mensajes.js'

/** Formulario de acceso compartido (V1-ISSUE-27): lo usa la ruta /login y el
 *  Lienzo, que lo muestra en cualquier ruta interna cuando no hay sesión, en
 *  vez de revelar el menú de operación (spec-front-v1 «Sin sesión: pantalla de
 *  login»). Tras un 200 refresca la sesión compartida: el Lienzo vuelve a
 *  renderizar y la página protegida aparece en la misma ruta; el callback
 *  `despues` (opcional) permite navegar, p. ej. a «/» desde /login. */
export default function PantallaAcceso({ despues } = {}) {
  const [credenciales, setCredenciales] = useState({ usuario: '', clave: '', totp: '' })
  const [fase, setFase] = useState('clave') // 'clave' | 'totp' | 'totp_google'
  const [error, setError] = useState('')
  const [ofrecerOtraCuenta, setOfrecerOtraCuenta] = useState(false)
  const [googleDisponible, setGoogleDisponible] = useState(false)
  const sesion = useSesion()

  useEffect(() => {
    api('/auth/google/estado')
      .then((r) => setGoogleDisponible(r.estado === 200 && r.datos?.configurado === true))
      .catch(() => setGoogleDisponible(false))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    // CE-HH C-03: administrador que entró con Google y tiene TOTP activo.
    if (params.get('paso') === 'totp_google') setFase('totp_google')
    const errorGoogle = mensajeErrorLogin(params.get('error'))
    if (errorGoogle) {
      setError(errorGoogle)
      // #351: tras un fallo con Google, ofrecer otra cuenta (el selector se
      // fuerza con prompt=select_account en el servicio).
      setOfrecerOtraCuenta(params.get('error') !== 'mfa_requerido')
    } else if (params.get('error') === 'sesion_empresa_ajena') {
      setError(mensajeMotivoSesion('sesion_empresa_ajena'))
    }
  }, [])

  // Cookie presente pero rechazada (p. ej. tras Google o redeploy titular):
  // no dejar al usuario adivinando por un 401 silencioso en la consola.
  useEffect(() => {
    const aviso = mensajeMotivoSesion(sesion.motivo)
    if (aviso) setError(aviso)
  }, [sesion.motivo])

  async function entrar(e) {
    e.preventDefault()
    setError('')
    if (fase === 'totp_google') {
      try {
        const r = await api('/auth/google/totp', { metodo: 'POST', cuerpo: { codigo: credenciales.totp } })
        if (r.estado === 200) {
          await refrescarSesion()
          window.history.replaceState(null, '', window.location.pathname)
          if (despues) despues()
          return
        }
        if (r.estado === 401 && r.datos?.detail === 'login_google_expirado') {
          setFase('clave')
          setError('El acceso con Google expiró. Vuelve a entrar con Google.')
        } else if (r.estado === 429) setError('Demasiados intentos. Espera unos minutos.')
        else setError('Código del autenticador inválido.')
      } catch {
        setError('La API no está disponible')
      }
      return
    }
    try {
      const cuerpo = {
        usuario: credenciales.usuario,
        clave: credenciales.clave,
        ...(credenciales.totp ? { totp: credenciales.totp } : {}),
      }
      const r = await api('/sesion', { metodo: 'POST', cuerpo })
      if (r.estado === 200) {
        const estado = await refrescarSesion()
        if (estado.fase !== 'ok') {
          setError(
            mensajeMotivoSesion(estado.motivo) ||
              mensajeDeError({ detail: estado.motivo }, 401) ||
              'El servidor aceptó la clave pero no pudo abrir la sesión. Revisa el despliegue.',
          )
          return
        }
        if (despues) despues()
        return
      }
      if (r.estado === 401 && r.datos?.detail === 'codigo_totp_requerido') {
        setFase('totp')
        return
      }
      if (r.estado === 429) setError('Demasiados intentos. Espera unos minutos.')
      else if (r.datos?.detail === 'código 2FA inválido') setError('Código del autenticador inválido.')
      else setError(mensajeDeError(r.datos, r.estado) || 'Credenciales inválidas o sesión no disponible.')
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <main className="login-pagina">
      <form className="tarjeta login-tarjeta formulario" onSubmit={entrar}>
        <img className="login-logo" src={LOGO.h128} alt={NOMBRE_COMERCIAL} width="160" height="128" />
        <h1 className="login-marca">{NOMBRE_COMERCIAL}</h1>
        <p className="login-subtitulo">
          {fase !== 'clave' ? 'Doble factor · código del autenticador' : 'Acceso a la plataforma'}
        </p>
        {fase === 'clave' ? (
          <>
            <label className="campo">
              <span className="campo-etiqueta">Usuario</span>
              <input
                className="entrada"
                value={credenciales.usuario}
                onChange={(e) => setCredenciales({ ...credenciales, usuario: e.target.value })}
              />
            </label>
            <CampoClave
              etiqueta="Clave"
              autoComplete="current-password"
              value={credenciales.clave}
              onChange={(e) => setCredenciales({ ...credenciales, clave: e.target.value })}
            />
          </>
        ) : (
          <>
            <p className="estado">
              Esta cuenta tiene doble factor activo. Escribe el código de 6 dígitos de Google
              Authenticator.
            </p>
            <label className="campo">
              <span className="campo-etiqueta">Código del autenticador</span>
              <input
                className="entrada"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={credenciales.totp}
                onChange={(e) => setCredenciales({ ...credenciales, totp: e.target.value })}
              />
            </label>
            <button
              type="button"
              className="boton-fantasma"
              onClick={() => {
                setFase('clave')
                if (fase === 'totp_google') window.history.replaceState(null, '', window.location.pathname)
              }}
            >
              Volver a usuario y clave
            </button>
          </>
        )}
        <button type="submit" className="boton-primario">Entrar</button>
        {googleDisponible && (
          <a className="boton-fantasma" href={urlApi('/auth/google')} data-google-reintento={ofrecerOtraCuenta ? '1' : undefined}>
            {ofrecerOtraCuenta ? 'Probar con otra cuenta de Google' : 'Entrar con Google'}
          </a>
        )}
        {error && (
          <p role="alert" className="alerta" data-aviso-sesion={sesion.motivo || 'manual'}>
            {error}
          </p>
        )}
      </form>
    </main>
  )
}
