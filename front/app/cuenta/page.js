'use client'

import { useEffect, useState } from 'react'
import { api, MarcoHotel, urlApi, Campo, useClaveOperacion, refrescarSesion } from '../../lib/api'

export default function Cuenta() {
  const [sesion, setSesion] = useState(null)
  const [alta, setAlta] = useState(null)
  const [codigo, setCodigo] = useState('')
  const [exito, setExito] = useState('')
  const [error, setError] = useState('')
  const [claveNueva, setClaveNueva] = useState('')
  const [claveOk, setClaveOk] = useState('')
  const [claveError, setClaveError] = useState('')
  const [claveCambiando, setClaveCambiando] = useState(false)
  const [claveCambio, renovarClaveCambio] = useClaveOperacion()

  function recargarSesion() {
    refrescarSesion().then((estado) => {
      if (estado.fase === 'ok') setSesion(estado.usuario)
    })
  }

  useEffect(recargarSesion, [])

  // V1-ISSUE-33: cualquier rol autenticado puede cambiar su propia clave
  // (spec-api-v1: el propio usuario o un administrador).
  async function cambiarClave(e) {
    e.preventDefault()
    setClaveError('')
    setClaveOk('')
    if (claveNueva.trim().length < 6) {
      setClaveError('La clave nueva debe tener al menos 6 caracteres.')
      return
    }
    setClaveCambiando(true)
    try {
      const r = await api(`/usuarios/${sesion.id}/clave`, {
        metodo: 'POST',
        cuerpo: { clave: claveNueva },
        claveIdempotencia: claveCambio,
      })
      if (r.estado >= 400) setClaveError(r.datos?.detail ?? 'No se pudo cambiar la clave')
      else {
        setClaveOk('Clave actualizada. Usa la clave nueva en tu próximo acceso.')
        setClaveNueva('')
        renovarClaveCambio()
      }
    } catch {
      setClaveError('La API no está disponible')
    } finally {
      setClaveCambiando(false)
    }
  }

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
    // V1-ISSUE-36: las acciones destructivas piden confirmación explícita.
    if (!window.confirm('¿Desactivar el doble factor? El acceso quedará solo con usuario y clave.')) return
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
    <MarcoHotel titulo="Mi cuenta: clave y doble factor">
      {sesion && (
        <section className="tarjeta">
          <h2>Cambiar clave</h2>
          <p className="estado">
            Usuario {sesion.usuario} · {sesion.rol}. La clave nueva reemplaza a la actual para tus
            próximos accesos.
          </p>
          <form className="formulario" onSubmit={cambiarClave}>
            <Campo
              etiqueta="Clave nueva"
              type="password"
              autoComplete="new-password"
              value={claveNueva}
              onChange={(e) => setClaveNueva(e.target.value)}
            />
            <button type="submit" className="boton-primario" disabled={claveCambiando}>
              {claveCambiando ? 'Cambiando…' : 'Cambiar clave'}
            </button>
          </form>
          <p className="nota-clave nota-tecnica">Clave: <code>{claveCambio}</code></p>
          {claveOk && <p role="status" className="aviso-ok">{claveOk}</p>}
          {claveError && <p role="alert" className="alerta">{claveError}</p>}
        </section>
      )}
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
