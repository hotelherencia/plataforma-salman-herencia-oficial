'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, MarcoHotel, SalidaJson, Campo, CampoClave, CampoSelect, useClaveOperacion, useSesion } from '../../../lib/api'
import { ListaUsuarios, UsuariosVacios } from '../../hotel/_componentes/lista-usuarios'
import { ETIQUETAS_ROL, ROLES, esAdminPlataforma } from '../../../lib/roles'

export default function Usuarios() {
  const sesion = useSesion()
  const [alta, setAlta] = useState({ nombre: '', rol: 'recepcion', clave: '', email: '' })
  // #352: vincular el correo de Google de un usuario existente.
  const [vinculo, setVinculo] = useState({ id: '', email: '' })
  const [claveCambio, setClaveCambio] = useState({ id: '', clave: '' })
  const [revocacionId, setRevocacionId] = useState('')
  const [bajaId, setBajaId] = useState('')
  const [salida, setSalida] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  const [usuarios, setUsuarios] = useState(null)
  const [claveAlta, renovarClaveAlta] = useClaveOperacion()
  const [claveCambioOp, renovarClaveCambio] = useClaveOperacion()
  const [claveRevocacion, renovarClaveRevocacion] = useClaveOperacion()
  const [claveBaja, renovarClaveBaja] = useClaveOperacion()
  const [claveVinculo, renovarClaveVinculo] = useClaveOperacion()

  const esAdmin = sesion.fase === 'ok' && esAdminPlataforma(sesion.usuario.rol)

  async function cargarUsuarios() {
    try {
      const r = await api('/usuarios')
      if (r.estado === 200) setUsuarios(r.datos.usuarios)
      else setUsuarios([])
    } catch {
      setUsuarios([])
    }
  }

  useEffect(() => {
    if (esAdmin) cargarUsuarios()
  }, [esAdmin])

  async function postear(ruta, cuerpo, clave, alExito, e) {
    e.preventDefault()
    setEnviando(true)
    setError('')
    setSalida(null)
    try {
      const r = await api(ruta, { metodo: 'POST', cuerpo, claveIdempotencia: clave })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, alExito)
      } else {
        setSalida(r.datos)
        alExito()
        cargarUsuarios()
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setEnviando(false)
    }
  }

  function usarId(id) {
    setClaveCambio((c) => ({ ...c, id }))
    setRevocacionId(id)
    setBajaId(id)
    setVinculo((v) => ({ ...v, id }))
  }

  if (sesion.fase === 'ok' && !esAdminPlataforma(sesion.usuario.rol)) {
    return (
      <MarcoHotel titulo="Usuarios">
        <p className="estado">La gestión de usuarios es solo para la administración de plataforma.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Gestión de usuarios (administración de plataforma)">
      <section className="tarjeta">
        <h2>Usuarios de la empresa</h2>
        {usuarios === null ? (
          <p className="estado">Cargando usuarios…</p>
        ) : usuarios.length === 0 ? (
          <UsuariosVacios />
        ) : (
          <ListaUsuarios usuarios={usuarios} total={usuarios.length} alElegir={usarId} />
        )}
        <p className="nota-chica">Haz clic en «Seleccionar» o elige directamente en los selectores inferiores para cambiar clave, vincular Google o dar de baja.</p>
      </section>
      <section className="tarjeta">
        <h2>Alta de usuario</h2>
        <form className="formulario" onSubmit={(e) => postear('/usuarios', { nombre: alta.nombre, rol: alta.rol, clave: alta.clave, ...(alta.email.trim() ? { email: alta.email.trim() } : {}) }, claveAlta, renovarClaveAlta, e)}>
          <Campo etiqueta="Nombre" value={alta.nombre} onChange={(e) => setAlta({ ...alta, nombre: e.target.value })} />
          <CampoSelect etiqueta="Rol" value={alta.rol} onChange={(e) => setAlta({ ...alta, rol: e.target.value })}>
            {ROLES.map((rol) => <option key={rol} value={rol}>{ETIQUETAS_ROL[rol]}</option>)}
          </CampoSelect>
          <p className="nota-chica">
            Administrador del hotel: precios, tipos, habitaciones, reservas, caja y reportes. Administrador de plataforma:
            usuarios, seguridad y ajustes del sistema (tasa de IVA). Todo rol administrativo exige doble factor.
          </p>
          <CampoClave etiqueta="Clave" autoComplete="new-password" value={alta.clave} onChange={(e) => setAlta({ ...alta, clave: e.target.value })} />
          <Campo etiqueta="Correo de Google (opcional)" type="email" autoComplete="off" value={alta.email} onChange={(e) => setAlta({ ...alta, email: e.target.value })} />
          <p className="nota-chica">Con el correo, el usuario puede entrar con «Continuar con Google». Los roles administrativos enrolan el doble factor en el primer ingreso.</p>
          <button type="submit" className="boton-primario">Crear usuario</button>
        </form>
        <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveAlta}</code></span>
      </section>
      <section className="tarjeta">
        <h2>Cambio de clave de otro usuario</h2>
        <p className="estado">La administración de plataforma reemplaza la clave de otra persona. La tuya se cambia en Mi cuenta, con la clave actual.</p>
        <form className="formulario" onSubmit={(e) => postear(`/usuarios/${claveCambio.id}/clave`, { clave: claveCambio.clave }, claveCambioOp, renovarClaveCambio, e)}>
          <CampoSelect etiqueta="Usuario" value={claveCambio.id} onChange={(e) => setClaveCambio({ ...claveCambio, id: e.target.value })}>
            <option value="">(Selecciona un usuario)</option>
            {usuarios?.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre} · {ETIQUETAS_ROL[u.rol] || u.rol} {!u.activo ? '(inactivo)' : ''}
              </option>
            ))}
          </CampoSelect>
          <CampoClave etiqueta="Clave nueva" autoComplete="new-password" value={claveCambio.clave} onChange={(e) => setClaveCambio({ ...claveCambio, clave: e.target.value })} />
          <button type="submit" className="boton-primario" disabled={!claveCambio.id}>Cambiar clave</button>
        </form>
        <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveCambioOp}</code></span>
      </section>
      <section className="tarjeta">
        <h2>Correo de Google (vincular o quitar)</h2>
        <form className="formulario" onSubmit={(e) => postear(`/usuarios/${vinculo.id}/email`, { email: vinculo.email.trim() || null }, claveVinculo, renovarClaveVinculo, e)}>
          <CampoSelect etiqueta="Usuario" value={vinculo.id} onChange={(e) => setVinculo({ ...vinculo, id: e.target.value })}>
            <option value="">(Selecciona un usuario)</option>
            {usuarios?.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre} · {ETIQUETAS_ROL[u.rol] || u.rol} {!u.activo ? '(inactivo)' : ''}
              </option>
            ))}
          </CampoSelect>
          <Campo etiqueta="Correo de Google (vacío = quitar)" type="email" autoComplete="off" value={vinculo.email} onChange={(e) => setVinculo({ ...vinculo, email: e.target.value })} />
          <button type="submit" className="boton-primario" disabled={enviando || !vinculo.id}>Guardar correo</button>
        </form>
        <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveVinculo}</code></span>
      </section>
      <section className="tarjeta">
        <h2>Revocación de sesiones (sobre otro usuario)</h2>
        <form className="formulario" onSubmit={(e) => postear(`/usuarios/${revocacionId}/revocacion`, {}, claveRevocacion, renovarClaveRevocacion, e)}>
          <CampoSelect etiqueta="Usuario" value={revocacionId} onChange={(e) => setRevocacionId(e.target.value)}>
            <option value="">(Selecciona un usuario)</option>
            {usuarios?.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre} · {ETIQUETAS_ROL[u.rol] || u.rol} {!u.activo ? '(inactivo)' : ''}
              </option>
            ))}
          </CampoSelect>
          <button type="submit" className="boton-primario" disabled={enviando || !revocacionId} onClick={(e) => { if (!window.confirm('¿Revocar todas las sesiones de este usuario? Deberá iniciar sesión de nuevo.')) e.preventDefault() }}>Revocar sesiones</button>
        </form>
        <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveRevocacion}</code></span>
      </section>
      <section className="tarjeta">
        <h2>Baja de usuario (sobre otro usuario)</h2>
        <form className="formulario" onSubmit={(e) => postear(`/usuarios/${bajaId}/baja`, {}, claveBaja, renovarClaveBaja, e)}>
          <CampoSelect etiqueta="Usuario" value={bajaId} onChange={(e) => setBajaId(e.target.value)}>
            <option value="">(Selecciona un usuario)</option>
            {usuarios?.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre} · {ETIQUETAS_ROL[u.rol] || u.rol} {!u.activo ? '(inactivo)' : ''}
              </option>
            ))}
          </CampoSelect>
          <button type="submit" className="boton-primario" disabled={enviando || !bajaId} onClick={(e) => { if (!window.confirm('¿Dar de baja este usuario? Queda inactivo y sin acceso.')) e.preventDefault() }}>Dar de baja</button>
        </form>
        <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveBaja}</code></span>
      </section>
      <button onClick={() => { setSalida(null); setError(''); renovarClaveAlta(); renovarClaveCambio(); renovarClaveRevocacion(); renovarClaveBaja() }} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
