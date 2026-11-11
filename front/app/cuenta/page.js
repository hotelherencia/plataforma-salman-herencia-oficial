'use client'

import { useEffect, useState } from 'react'
import { api, MarcoHotel, urlApi, Campo, useClaveOperacion, refrescarSesion } from '../../lib/api'

export default function Cuenta() {
  const [sesion, setSesion] = useState(null)
  const [alta, setAlta] = useState(null)
  const [codigo, setCodigo] = useState('')
  const [exito, setExito] = useState('')
  const [error, setError] = useState('')
  const [claveActual, setClaveActual] = useState('')
  const [claveNueva, setClaveNueva] = useState('')
  const [claveReauth, setClaveReauth] = useState('')
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
    if (!claveActual) {
      setClaveError('Escribe tu clave actual.')
      return
    }
    if (claveNueva.trim().length < 6) {
      setClaveError('La clave nueva debe tener al menos 6 caracteres.')
      return
    }
    setClaveCambiando(true)
    try {
      const r = await api(`/usuarios/${sesion.id}/clave`, {
        metodo: 'POST',
        cuerpo: { clave: claveNueva, clave_actual: claveActual },
        claveIdempotencia: claveCambio,
      })
      if (r.estado >= 400) setClaveError(r.datos?.detail ?? 'No se pudo cambiar la clave')
      else {
        setClaveOk('Clave actualizada. Usa la clave nueva en tu próximo acceso.')
        setClaveActual('')
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

  // SEC-A02 (auditoría 2026-11-03, #327): con 2FA activo, reemplazar el
  // autenticador exige la clave actual (reautenticación). El alta nunca
  // desprotege la cuenta: el secreto nuevo queda pendiente hasta confirmar.
  async function reemplazar() {
    setError('')
    setExito('')
    if (!claveReauth) {
      setError('Escribe tu clave actual para confirmar el reemplazo.')
      return
    }
    try {
      const r = await api('/cuenta/2fa', { metodo: 'POST', cuerpo: { clave: claveReauth } })
      if (r.estado >= 400) setError(r.datos?.detail ?? 'No se pudo iniciar el reemplazo')
      else {
        setAlta(r.datos)
        setExito('Autenticador nuevo pendiente: confírmalo con el código. El anterior sigue activo.')
      }
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
    // SEC-A02 (#327): además exige la clave actual (reautenticación).
    if (!window.confirm('¿Desactivar el doble factor? El acceso quedará solo con usuario y clave.')) return
    setError('')
    setExito('')
    if (!claveReauth) {
      setError('Escribe tu clave actual para confirmar.')
      return
    }
    try {
      const r = await api('/cuenta/2fa', { metodo: 'DELETE', cuerpo: { clave: claveReauth } })
      if (r.estado >= 400) setError(r.datos?.detail ?? 'No se pudo desactivar')
      else {
        setExito('Doble factor desactivado.')
        setClaveReauth('')
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
              etiqueta="Clave actual"
              type="password"
              autoComplete="current-password"
              value={claveActual}
              onChange={(e) => setClaveActual(e.target.value)}
            />
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
          <p className="nota-clave nota-tecnica">
            Clave de idempotencia (reintenta con la misma para no duplicar): <code>{claveCambio}</code>
          </p>
          {claveOk && <p role="status" className="aviso-ok">{claveOk}</p>}
          {claveError && <p role="alert" className="alerta">{claveError}</p>}
        </section>
      )}
      {sesion?.totp_activado && !alta ? (
        <section className="tarjeta">
          <h2>Estado: activado</h2>
          <p className="estado">
            Cada inicio de sesión pide, además de la clave, el código de 6 dígitos del autenticador.
            Reemplazar el autenticador o desactivar el doble factor exige tu clave actual.
          </p>
          <label className="campo">
            <span className="campo-etiqueta">Tu clave actual (confirma cambios)</span>
            <input
              className="entrada"
              type="password"
              autoComplete="current-password"
              value={claveReauth}
              onChange={(e) => setClaveReauth(e.target.value)}
            />
          </label>
          <div className="acciones-fila">
            <button onClick={reemplazar} className="boton-fantasma">Reemplazar autenticador</button>
            <button onClick={desactivar} className="boton-fantasma">Desactivar doble factor</button>
          </div>
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
