'use client'

import { useEffect, useState } from 'react'
import { api, MarcoHotel, urlApi } from '../../lib/api'

export default function Cuenta() {
  const [sesion, setSesion] = useState(null)
  const [alta, setAlta] = useState(null)
  const [codigo, setCodigo] = useState('')
  const [exito, setExito] = useState('')
  const [error, setError] = useState('')

  function recargarSesion() {
    api('/sesion').then((r) => {
      if (r.estado === 200) setSesion(r.datos)
    })
  }

  useEffect(recargarSesion, [])

  async function generarAlta() {
    setError('')
    setExito('')
    try {
      const r = await api('/cuenta/2fa', { metodo: 'POST' })
      if (r.estado >= 400) setError(r.datos?.detail ?? 'No se pudo iniciar el alta')
      else setAlta(r.datos)
    } catch {
      setError('La API no está disponible')
    }
  }

  async function activar(e) {
    e.preventDefault()
    setError('')
    setExito('')
    try {
      const r = await api('/cuenta/2fa/activar', { metodo: 'POST', cuerpo: { codigo } })
      if (r.estado >= 400) setError(r.datos?.detail ?? 'Código inválido')
      else {
        setExito('Doble factor activado. Desde el próximo acceso pedirá código.')
        setAlta(null)
        setCodigo('')
        recargarSesion()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  async function desactivar() {
    setError('')
    setExito('')
    try {
      const r = await api('/cuenta/2fa', { metodo: 'DELETE' })
      if (r.estado >= 400) setError(r.datos?.detail ?? 'No se pudo desactivar')
      else {
        setExito('Doble factor desactivado.')
        recargarSesion()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Mi cuenta: doble factor (Google Authenticator)">
      {sesion?.totp_activado ? (
        <section className="tarjeta">
          <h2>Estado: activado</h2>
          <p className="estado">
            Cada inicio de sesión pide, además de la clave, el código de 6 dígitos del autenticador.
          </p>
          <button onClick={desactivar} className="boton-fantasma">Desactivar doble factor</button>
        </section>
      ) : alta ? (
        <section className="tarjeta">
          <h2>Alta del autenticador</h2>
          <ol className="pasos">
            <li>Abre <strong>Google Authenticator</strong> en el teléfono.</li>
            <li>Escanea este código QR (o usa «Introducir clave de configuración» con la clave de abajo):</li>
          </ol>
          <img
            className="qr"
            src={urlApi('/cuenta/2fa/qr')}
            alt="Código QR para Google Authenticator"
          />
          <p className="nota-clave">
            Clave manual (base32): <code className="secreto">{alta.secreto}</code>
          </p>
          <p className="nota-clave">URI de alta: <code>{alta.uri}</code></p>
          <form className="formulario" onSubmit={activar}>
            <label className="campo">
              <span className="campo-etiqueta">Código de confirmación</span>
              <input
                className="entrada"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={codigo}
                onChange={(e) => setCodigo(e.target.value)}
              />
            </label>
            <button type="submit" className="boton-primario">Confirmar y activar</button>
          </form>
        </section>
      ) : (
        <section className="tarjeta">
          <h2>Estado: desactivado</h2>
          <p className="estado">
            El acceso usa solo usuario y clave. Activa el doble factor para exigir además el código
            de Google Authenticator.
          </p>
          <button onClick={generarAlta} className="boton-primario">Activar doble factor</button>
        </section>
      )}
      {exito && <p role="status" className="aviso-ok">{exito}</p>}
      {error && <p role="alert" className="alerta">{error}</p>}
    </MarcoHotel>
  )
}
