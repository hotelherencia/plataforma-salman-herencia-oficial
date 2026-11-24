'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, MarcoHotel, SalidaJson, Campo, CampoClave, CampoSelect, useClaveOperacion, useSesion } from '../../../lib/api'
import { ListaUsuarios, UsuariosVacios } from '../../hotel/_componentes/lista-usuarios'
import { ETIQUETAS_ROL, ROLES, apruebaCambiosDeRol, esAdminPlataforma } from '../../../lib/roles'
import { useMensajes } from '../../_componentes/centro-mensajes'
import CambiosDeRol from '../_componentes/cambios-de-rol'

export default function Usuarios() {
  const sesion = useSesion()
  const { confirmar } = useMensajes()
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
  const [catalogoRoles, setCatalogoRoles] = useState(null)
  const [rolesCreables, setRolesCreables] = useState(null)
  const [claveAlta, renovarClaveAlta] = useClaveOperacion()
  const [claveCambioOp, renovarClaveCambio] = useClaveOperacion()
  const [claveRevocacion, renovarClaveRevocacion] = useClaveOperacion()
  const [claveBaja, renovarClaveBaja] = useClaveOperacion()
  const [claveVinculo, renovarClaveVinculo] = useClaveOperacion()

  const esAdmin = sesion.fase === 'ok' && esAdminPlataforma(sesion.usuario.rol)
  // La administración del hotel no gestiona cuentas, pero valida los cambios de rol y ve quién tiene qué rol.
  const soloValida = sesion.fase === 'ok' && !esAdmin && apruebaCambiosDeRol(sesion.usuario.rol)

  async function cargarUsuarios() {
    try {
      const r = await api('/usuarios')
      if (r.estado === 200) {
        setUsuarios(r.datos.usuarios)
        setRolesCreables(r.datos.roles_que_puedes_crear || null)
      }
      else setUsuarios([])
    } catch {
      setUsuarios([])
    }
  }

  useEffect(() => {
    if (soloValida) cargarUsuarios()
    if (!esAdmin) return
    cargarUsuarios()
    api('/roles')
      .then((r) => {
        if (r.estado === 200 && Array.isArray(r.datos?.roles)) setCatalogoRoles(r.datos.roles)
      })
      .catch(() => {})
  }, [esAdmin, soloValida])

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

  if (soloValida) {
    return (
      <MarcoHotel titulo="Usuarios y cambios de rol">
        <CambiosDeRol rol={sesion.usuario.rol} />
        <section className="tarjeta">
          <h2>Usuarios de la empresa</h2>
          {usuarios === null ? (
            <p className="estado" role="status" aria-busy="true">Cargando usuarios…</p>
          ) : usuarios.length === 0 ? (
            <UsuariosVacios />
          ) : (
            <ListaUsuarios usuarios={usuarios} total={usuarios.length} />
          )}
          <p className="nota-chica">
            Aquí validas los cambios de rol que pide la administración de plataforma. Un rol administrativo o del dueño no
            queda activo hasta que lo apruebas; quien lo pidió no puede aprobarlo.
          </p>
        </section>
      </MarcoHotel>
    )
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
        <CambiosDeRol rol={sesion.fase === 'ok' ? sesion.usuario.rol : null} />
        {usuarios === null ? (
          <p className="estado" role="status" aria-busy="true">Cargando usuarios…</p>
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
            {(catalogoRoles || ROLES.map((codigo) => ({ codigo, etiqueta: ETIQUETAS_ROL[codigo] || codigo, modulo: codigo === 'administrador' || codigo === 'admin_plataforma' ? 'core' : 'hotel' }))).filter((item) => !rolesCreables || rolesCreables.includes(item.codigo)).map((item) => (
              <option key={item.codigo} value={item.codigo}>
                {item.etiqueta} ({item.modulo === 'core' ? 'Plataforma' : item.modulo === 'hotel' ? 'Hotel' : item.modulo})
              </option>
            ))}
          </CampoSelect>
          <p className="nota-chica">
            Administrador del hotel: precios, tipos, habitaciones, reservas, caja y reportes. Administrador de plataforma:
            usuarios, seguridad y ajustes del sistema (tasa de IVA). Todo rol administrativo exige doble factor.
          </p>
          <p className="nota-chica">
            Solo se ofrecen los roles que tu cuenta puede asignar. Un rol administrativo o del dueño queda pendiente hasta que lo valide
            la administración del hotel; la cuenta no puede entrar mientras tanto.
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
        <form
          className="formulario"
          onSubmit={async (e) => {
            e.preventDefault()
            const ok = await confirmar({
              titulo: 'Revocar sesiones',
              mensaje: '¿Revocar todas las sesiones activas de este usuario? Deberá iniciar sesión de nuevo.',
              textoConfirmar: 'Revocar sesiones',
              variante: 'peligro',
            })
            if (ok) postear(`/usuarios/${revocacionId}/revocacion`, {}, claveRevocacion, renovarClaveRevocacion, e)
          }}
        >
          <CampoSelect etiqueta="Usuario" value={revocacionId} onChange={(e) => setRevocacionId(e.target.value)}>
            <option value="">(Selecciona un usuario)</option>
            {usuarios?.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre} · {ETIQUETAS_ROL[u.rol] || u.rol} {!u.activo ? '(inactivo)' : ''}
              </option>
            ))}
          </CampoSelect>
          <button type="submit" className="boton-primario" disabled={enviando || !revocacionId}>Revocar sesiones</button>
        </form>
        <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveRevocacion}</code></span>
      </section>
      <section className="tarjeta">
        <h2>Baja de usuario (sobre otro usuario)</h2>
        <form
          className="formulario"
          onSubmit={async (e) => {
            e.preventDefault()
            const ok = await confirmar({
              titulo: 'Dar de baja usuario',
              mensaje: '¿Dar de baja a este usuario? Quedará inactivo y sin acceso a la plataforma.',
              textoConfirmar: 'Dar de baja',
              variante: 'peligro',
            })
            if (ok) postear(`/usuarios/${bajaId}/baja`, {}, claveBaja, renovarClaveBaja, e)
          }}
        >
          <CampoSelect etiqueta="Usuario" value={bajaId} onChange={(e) => setBajaId(e.target.value)}>
            <option value="">(Selecciona un usuario)</option>
            {usuarios?.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nombre} · {ETIQUETAS_ROL[u.rol] || u.rol} {!u.activo ? '(inactivo)' : ''}
              </option>
            ))}
          </CampoSelect>
          <button type="submit" className="boton-primario" disabled={enviando || !bajaId}>Dar de baja</button>
        </form>
        <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveBaja}</code></span>
      </section>
      <button onClick={() => { setSalida(null); setError(''); renovarClaveAlta(); renovarClaveCambio(); renovarClaveRevocacion(); renovarClaveBaja() }} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
