'use client'

import { useEffect, useState } from 'react'
import { api, urlApi } from '../../lib/api'

export default function Login() {
  const [credenciales, setCredenciales] = useState({ usuario: 'admin', clave: '', totp: '' })
  const [fase, setFase] = useState('clave')
  const [error, setError] = useState('')
  const [googleDisponible, setGoogleDisponible] = useState(false)

  useEffect(() => {
    api('/auth/google/estado')
      .then((r) => setGoogleDisponible(r.estado === 200 && r.datos?.configurado === true))
      .catch(() => setGoogleDisponible(false))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('error') === 'cuenta_sin_vinculo') {
      setError('Tu cuenta de Google no está vinculada a un usuario de la plataforma.')
    } else if (params.get('error') === 'acceso_denegado') {
      setError('Acceso con Google cancelado o denegado.')
    }
  }, [])

  async function entrar(e) {
    e.preventDefault()
    setError('')
    try {
      const cuerpo = {
        usuario: credenciales.usuario,
        clave: credenciales.clave,
        ...(credenciales.totp ? { totp: credenciales.totp } : {}),
      }
      const r = await api('/sesion', { metodo: 'POST', cuerpo })
      if (r.estado === 200) {
        window.location.href = '/hotel/oferta'
        return
      }
      if (r.estado === 401 && r.datos?.detail === 'codigo_totp_requerido') {
        setFase('totp')
        return
      }
      if (r.estado === 429) setError('Demasiados intentos. Espera unos minutos.')
      else if (r.datos?.detail === 'código 2FA inválido') setError('Código del autenticador inválido.')
      else setError('Credenciales inválidas o sesión no disponible.')
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <main className="login-pagina">
      <form className="tarjeta login-tarjeta formulario" onSubmit={entrar}>
        <h1 className="login-marca">Plataforma Herencia</h1>
        <p className="login-subtitulo">
          {fase === 'totp' ? 'Doble factor · código del autenticador' : 'Acceso · Módulo hotel'}
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
            <label className="campo">
              <span className="campo-etiqueta">Clave</span>
              <input
                className="entrada"
                type="password"
                value={credenciales.clave}
                onChange={(e) => setCredenciales({ ...credenciales, clave: e.target.value })}
              />
            </label>
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
            <button type="button" className="boton-fantasma" onClick={() => setFase('clave')}>
              Volver a usuario y clave
            </button>
          </>
        )}
        <button type="submit" className="boton-primario">Entrar</button>
        {googleDisponible && (
          <a className="boton-fantasma" href={urlApi('/auth/google')}>
            Entrar con Google
          </a>
        )}
        {error && <p role="alert" className="alerta">{error}</p>}
      </form>
    </main>
  )
}
