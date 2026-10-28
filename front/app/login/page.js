'use client'

import { useState } from 'react'
import { api } from '../../lib/api'

export default function Login() {
  const [credenciales, setCredenciales] = useState({ usuario: 'admin', clave: '' })
  const [error, setError] = useState('')

  async function entrar(e) {
    e.preventDefault()
    setError('')
    try {
      const r = await api('/sesion', { metodo: 'POST', cuerpo: credenciales })
      if (r.estado === 200) window.location.href = '/hotel/oferta'
      else if (r.estado === 429) setError('Demasiados intentos. Espera unos minutos.')
      else setError('Credenciales inválidas o sesión no disponible.')
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <main>
      <h1>Plataforma Herencia — acceso</h1>
      <form onSubmit={entrar}>
        <label style={{ display: 'block', marginBottom: '0.5rem' }}>
          Usuario{' '}
          <input value={credenciales.usuario} onChange={(e) => setCredenciales({ ...credenciales, usuario: e.target.value })} />
        </label>
        <label style={{ display: 'block', marginBottom: '0.5rem' }}>
          Clave{' '}
          <input type="password" value={credenciales.clave} onChange={(e) => setCredenciales({ ...credenciales, clave: e.target.value })} />
        </label>
        <button type="submit">Entrar</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </main>
  )
}
