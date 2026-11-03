'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, MarcoHotel, SalidaJson, Campo, CampoSelect, useClaveOperacion, useSesion } from '../../../lib/api'
import { ListaUsuarios, UsuariosVacios } from '../../hotel/_componentes/lista-usuarios'

export default function Usuarios() {
  const sesion = useSesion()
  const [alta, setAlta] = useState({ nombre: '', rol: 'recepcion', clave: '' })
  const [claveCambio, setClaveCambio] = useState({ id: '', clave: '' })
  const [revocacionId, setRevocacionId] = useState('')
  const [bajaId, setBajaId] = useState('')
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [usuarios, setUsuarios] = useState(null)
  const [claveAlta, renovarClaveAlta] = useClaveOperacion()
  const [claveCambioOp, renovarClaveCambio] = useClaveOperacion()
  const [claveRevocacion, renovarClaveRevocacion] = useClaveOperacion()
  const [claveBaja, renovarClaveBaja] = useClaveOperacion()

  const esAdmin = sesion.fase === 'ok' && sesion.usuario.rol === 'administrador'

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
      setError('La API no está disponible')
    }
  }

  function usarId(id) {
    setClaveCambio((c) => ({ ...c, id }))
    setRevocacionId(id)
    setBajaId(id)
  }

  if (sesion.fase === 'ok' && sesion.usuario.rol !== 'administrador') {
    return (
      <MarcoHotel titulo="Usuarios">
        <p className="estado">La gestión de usuarios es solo para administrador.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Gestión de usuarios (administrador)">
      <section className="tarjeta">
        <h2>Usuarios de la empresa</h2>
        {usuarios === null ? (
          <p className="estado">Cargando usuarios…</p>
        ) : usuarios.length === 0 ? (
          <UsuariosVacios />
        ) : (
          <ListaUsuarios usuarios={usuarios} total={usuarios.length} alElegir={usarId} />
        )}
        <p className="nota-clave">«Usar id» copia el identificador en los formularios de cambio de clave, revocación y baja.</p>
      </section>
      <section className="tarjeta">
        <h2>Alta de usuario</h2>
        <form className="formulario" onSubmit={(e) => postear('/usuarios', alta, claveAlta, renovarClaveAlta, e)}>
          <Campo etiqueta="Nombre" value={alta.nombre} onChange={(e) => setAlta({ ...alta, nombre: e.target.value })} />
          <CampoSelect etiqueta="Rol" value={alta.rol} onChange={(e) => setAlta({ ...alta, rol: e.target.value })}>
            <option value="recepcion">recepcion</option>
            <option value="caja">caja</option>
            <option value="administrador">administrador</option>
          </CampoSelect>
          <Campo etiqueta="Clave" type="password" value={alta.clave} onChange={(e) => setAlta({ ...alta, clave: e.target.value })} />
          <button type="submit" className="boton-primario">Crear usuario</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveAlta}</code></p>
      </section>
      <section className="tarjeta">
        <h2>Cambio de clave (el propio usuario o un administrador)</h2>
        <form className="formulario" onSubmit={(e) => postear(`/usuarios/${claveCambio.id}/clave`, { clave: claveCambio.clave }, claveCambioOp, renovarClaveCambio, e)}>
          <Campo etiqueta="Usuario (id)" value={claveCambio.id} onChange={(e) => setClaveCambio({ ...claveCambio, id: e.target.value })} />
          <Campo etiqueta="Clave nueva" type="password" value={claveCambio.clave} onChange={(e) => setClaveCambio({ ...claveCambio, clave: e.target.value })} />
          <button type="submit" className="boton-primario">Cambiar clave</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveCambioOp}</code></p>
      </section>
      <section className="tarjeta">
        <h2>Revocación de sesiones (sobre otro usuario)</h2>
        <form className="formulario" onSubmit={(e) => postear(`/usuarios/${revocacionId}/revocacion`, {}, claveRevocacion, renovarClaveRevocacion, e)}>
          <Campo etiqueta="Usuario (id)" value={revocacionId} onChange={(e) => setRevocacionId(e.target.value)} />
          <button type="submit" className="boton-primario">Revocar sesiones</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveRevocacion}</code></p>
      </section>
      <section className="tarjeta">
        <h2>Baja de usuario (sobre otro usuario)</h2>
        <form className="formulario" onSubmit={(e) => postear(`/usuarios/${bajaId}/baja`, {}, claveBaja, renovarClaveBaja, e)}>
          <Campo etiqueta="Usuario (id)" value={bajaId} onChange={(e) => setBajaId(e.target.value)} />
          <button type="submit" className="boton-primario">Dar de baja</button>
        </form>
        <p className="nota-clave">Clave: <code>{claveBaja}</code></p>
      </section>
      <button onClick={() => { setSalida(null); setError(''); renovarClaveAlta(); renovarClaveCambio(); renovarClaveRevocacion(); renovarClaveBaja() }} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
