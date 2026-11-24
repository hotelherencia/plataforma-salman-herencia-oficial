'use client'

import { useEffect, useState } from 'react'
import { api, clp, mensajeDeError } from '../../../lib/api'
import { validarDocumento } from '../../../lib/documento'
import { plural } from '../../../lib/formato'
import { useMensajes } from '../../_componentes/centro-mensajes'

const FORM_INICIAL = {
  huesped_id: null,
  nombre: '',
  documento_tipo: 'rut',
  documento: '',
  es_nino: false,
  nacionalidad: '',
  telefono: '',
  correo: '',
  notas: '',
}

export default function PestanaHuespedes({ reservaId, puedeEditar = false, alCambiar }) {
  const { confirmar, notificarExito } = useMensajes()
  const [datos, setDatos] = useState(null)
  const [politica, setPolitica] = useState(null)
  const [adultos, setAdultos] = useState('1')
  const [ninos, setNinos] = useState('0')
  const [form, setForm] = useState(FORM_INICIAL)
  const [editandoId, setEditandoId] = useState(null)
  const [busquedaDoc, setBusquedaDoc] = useState('')
  const [resultadosBusqueda, setResultadosBusqueda] = useState([])
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [cargando, setCargando] = useState(false)
  const [version, setVersion] = useState(0)

  useEffect(() => {
    if (!reservaId) return
    let cancelado = false
    api(`/hotel/reservas/${encodeURIComponent(reservaId)}/huespedes`)
      .then((r) => {
        if (cancelado) return
        if (r.estado >= 400) {
          setError(mensajeDeError(r.datos, r.estado))
          return
        }
        setDatos(r.datos)
        setAdultos(String(r.datos.adultos ?? 1))
        setNinos(String(r.datos.ninos ?? 0))
      })
      .catch(() => {
        if (!cancelado) setError('No se pudo cargar la lista de huéspedes.')
      })
    api('/hotel/politicas')
      .then((r) => {
        if (!cancelado && r.estado === 200) setPolitica(r.datos?.cuerpo?.ninos_cama || null)
      })
      .catch(() => {})
    return () => { cancelado = true }
  }, [reservaId, version])

  const abierta = Boolean(datos && ['confirmada', 'en_estadia'].includes(datos.estado))
  const editable = Boolean(puedeEditar && abierta)

  async function guardarOcupacion(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const ad = Number(adultos)
    const ni = Number(ninos)
    if (!Number.isInteger(ad) || ad < 1 || !Number.isInteger(ni) || ni < 0) {
      setError('Indica cantidades válidas de adultos (mínimo 1) y niños (0 o más).')
      return
    }
    setCargando(true)
    try {
      const r = await api(`/hotel/reservas/${encodeURIComponent(reservaId)}/ocupacion`, {
        metodo: 'PUT',
        cuerpo: { adultos: ad, ninos: ni },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        const partes = [`Ocupación actualizada: ${plural(r.datos.adultos, 'adulto')} y ${plural(r.datos.ninos, 'niño')}.`]
        if (r.datos.delta_clp > 0) partes.push(`Recargo asentado: ${clp(r.datos.delta_clp)}.`)
        else if (r.datos.delta_clp < 0) partes.push(`Ajuste aplicado: ${clp(Math.abs(r.datos.delta_clp))}.`)
        if (r.datos.avisos?.length) partes.push(r.datos.avisos.map((a) => a.mensaje).join(' '))
        setAviso(partes.join(' '))
        setVersion((v) => v + 1)
        alCambiar?.()
      }
    } catch {
      setError('No se pudo actualizar la ocupación.')
    } finally {
      setCargando(false)
    }
  }

  async function buscarExistente() {
    setError('')
    const q = busquedaDoc.trim()
    if (!q) { setResultadosBusqueda([]); return }
    try {
      const r = await api(`/hotel/huespedes/busqueda?documento=${encodeURIComponent(q)}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setResultadosBusqueda(r.datos?.huespedes || [])
    } catch {
      setError('No se pudo buscar huéspedes.')
    }
  }

  function seleccionarExistente(h) {
    setEditandoId(null)
    setForm({
      huesped_id: h.huesped_id,
      nombre: h.nombre || '',
      documento_tipo: h.documento_tipo || 'rut',
      documento: h.documento || '',
      es_nino: false,
      nacionalidad: h.nacionalidad || '',
      telefono: h.telefono || '',
      correo: h.correo || '',
      notas: h.notas || '',
    })
    setResultadosBusqueda([])
  }

  function iniciarEdicion(h) {
    setEditandoId(h.huesped_id)
    setForm({
      huesped_id: h.huesped_id,
      nombre: h.nombre || '',
      documento_tipo: h.documento_tipo || 'rut',
      documento: h.documento || '',
      es_nino: Boolean(h.es_nino),
      nacionalidad: h.nacionalidad || '',
      telefono: h.telefono || '',
      correo: h.correo || '',
      notas: h.notas || '',
    })
  }

  async function guardarHuesped(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    if (!form.huesped_id && !form.nombre.trim()) {
      setError('El nombre del huésped es obligatorio.')
      return
    }
    const cuerpo = {
      es_nino: Boolean(form.es_nino),
      nacionalidad: form.nacionalidad.trim() || null,
      telefono: form.telefono.trim() || null,
      correo: form.correo.trim() || null,
      notas: form.notas.trim() || null,
    }
    if (form.documento.trim()) {
      const doc = validarDocumento(form.documento_tipo, form.documento)
      if (!doc.ok) { setError(`Documento inválido: ${doc.error}`); return }
      cuerpo.documento_tipo = form.documento_tipo
      cuerpo.documento = doc.valor
    }
    setCargando(true)
    try {
      let r
      if (editandoId) {
        cuerpo.nombre = form.nombre.trim()
        r = await api(`/hotel/reservas/${encodeURIComponent(reservaId)}/huespedes/${encodeURIComponent(editandoId)}`, {
          metodo: 'PUT',
          cuerpo,
        })
      } else {
        if (form.huesped_id) cuerpo.huesped_id = form.huesped_id
        else cuerpo.nombre = form.nombre.trim()
        cuerpo.rol = 'acompanante'
        r = await api(`/hotel/reservas/${encodeURIComponent(reservaId)}/huespedes`, {
          metodo: 'POST',
          cuerpo,
        })
      }
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso(editandoId ? 'Huésped actualizado.' : 'Huésped registrado en la reserva.')
        setEditandoId(null)
        setForm(FORM_INICIAL)
        setVersion((v) => v + 1)
        alCambiar?.()
      }
    } catch {
      setError('No se pudo guardar el huésped.')
    } finally {
      setCargando(false)
    }
  }

  async function quitarHuesped(h) {
    const confirmado = await confirmar({
      titulo: 'Quitar acompañante',
      mensaje: `¿Quitar a ${h.nombre} de esta reserva?`,
      textoConfirmar: 'Quitar',
      variante: 'peligro',
    })
    if (!confirmado) return
    setError('')
    setAviso('')
    setCargando(true)
    try {
      const r = await api(`/hotel/reservas/${encodeURIComponent(reservaId)}/huespedes/${encodeURIComponent(h.huesped_id)}`, {
        metodo: 'DELETE',
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso('Acompañante quitado de la reserva.')
        notificarExito('Acompañante quitado de la reserva.')
        setVersion((v) => v + 1)
        alCambiar?.()
      }
    } catch {
      setError('No se pudo quitar al huésped.')
    } finally {
      setCargando(false)
    }
  }

  if (!datos) {
    return (
      <section className="tarjeta" aria-label="Huéspedes">
        {error ? <p role="alert" className="alerta">{error}</p> : <p className="estado">Cargando huéspedes…</p>}
      </section>
    )
  }

  const sinRecargoExtra = politica && politica.recargo_persona_extra_clp == null
  const sinRecargoNino = politica && !politica.recargo_nino

  return (
    <section className="tarjeta" aria-label="Huéspedes y ocupación">
      <h2>Huéspedes y ocupación real</h2>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      <div className="kpi-rejilla">
        <div className="kpi">
          <span className="kpi-titulo">Ocupación declarada</span>
          <span className="kpi-valor">{datos.adultos} ad. + {datos.ninos} ni.</span>
        </div>
        <div className="kpi">
          <span className="kpi-titulo">Capacidad habitación</span>
          <span className="kpi-valor">{datos.capacidad_habitacion}</span>
        </div>
        <div className={`kpi${datos.faltantes > 0 ? ' kpi-alerta' : ''}`}>
          <span className="kpi-titulo">Huéspedes registrados</span>
          <span className="kpi-valor">{datos.registrados} / {datos.total_esperado}</span>
        </div>
      </div>

      {datos.faltantes > 0 && (
        <p role="alert" className="alerta">
          {datos.faltantes === 1 ? 'Falta' : 'Faltan'} {plural(datos.faltantes, 'huésped', 'huéspedes')} por registrar antes de completar la Llegada.
        </p>
      )}

      {(sinRecargoExtra || sinRecargoNino) && (
        <p className="nota-clave">
          Aviso de políticas: {sinRecargoExtra ? 'recargo por persona extra sin configurar ($0)' : ''}
          {sinRecargoExtra && sinRecargoNino ? ' · ' : ''}
          {sinRecargoNino ? 'recargo por niño sin configurar ($0)' : ''}. No bloquea la Llegada.
        </p>
      )}

      {editable && (
        <form className="formulario cambio-habitacion" onSubmit={guardarOcupacion} aria-label="Editar ocupación">
          <h3 className="subtitulo">Ocupación real</h3>
          <div className="politicas-fila">
            <label className="campo">
              <span className="campo-etiqueta">Adultos</span>
              <input className="entrada" type="number" min="1" max={datos.capacidad_habitacion} value={adultos} onChange={(e) => setAdultos(e.target.value)} />
            </label>
            <label className="campo">
              <span className="campo-etiqueta">Niños {politica?.edad_nino_hasta != null ? `(hasta ${politica.edad_nino_hasta} años)` : ''}</span>
              <input className="entrada" type="number" min="0" max={datos.capacidad_habitacion - 1} value={ninos} onChange={(e) => setNinos(e.target.value)} />
            </label>
          </div>
          <button type="submit" className="boton-secundario" disabled={cargando}>
            Actualizar ocupación
          </button>
        </form>
      )}

      <h3 className="subtitulo">Lista de huéspedes</h3>
      <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Huéspedes registrados">
        <table className="tabla">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Rol</th>
              <th>Tipo</th>
              <th>Documento</th>
              <th>Contacto</th>
              {editable && <th>Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {datos.huespedes.map((h) => (
              <tr key={h.huesped_id}>
                <td>{h.nombre}</td>
                <td>{h.rol === 'titular' ? 'Titular' : 'Acompañante'}</td>
                <td>{h.es_nino ? 'Niño' : 'Adulto'}</td>
                <td>{h.documento ? `${(h.documento_tipo || '').toUpperCase()} ${h.documento}` : '—'}</td>
                <td>{[h.nacionalidad, h.telefono, h.correo].filter(Boolean).join(' · ') || '—'}</td>
                {editable && (
                  <td>
                    <button type="button" className="boton-fantasma" onClick={() => iniciarEdicion(h)}>Editar</button>
                    {h.rol !== 'titular' && (
                      <button type="button" className="boton-fantasma" onClick={() => quitarHuesped(h)}>Quitar</button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editable && (datos.faltantes > 0 || editandoId) && (
        <form className="formulario cambio-habitacion" onSubmit={guardarHuesped} aria-label={editandoId ? 'Editar huésped' : 'Registrar huésped'}>
          <h3 className="subtitulo">{editandoId ? 'Editar huésped' : 'Registrar acompañante'}</h3>
          {!editandoId && (
            <div className="politicas-fila">
              <label className="campo">
                <span className="campo-etiqueta">Buscar huésped previo por documento</span>
                <input className="entrada" value={busquedaDoc} onChange={(e) => setBusquedaDoc(e.target.value)} placeholder="Ej.: 12.345.678-5" />
              </label>
              <button type="button" className="boton-secundario" onClick={buscarExistente}>Buscar</button>
            </div>
          )}
          {resultadosBusqueda.length > 0 && (
            <ul className="lista-simple">
              {resultadosBusqueda.map((r) => (
                <li key={r.huesped_id}>
                  {r.nombre} ({r.documento_tipo?.toUpperCase()} {r.documento}){' '}
                  <button type="button" className="boton-fantasma" onClick={() => seleccionarExistente(r)}>Usar</button>
                </li>
              ))}
            </ul>
          )}
          <div className="politicas-fila">
            <label className="campo">
              <span className="campo-etiqueta">Nombre completo</span>
              <input className="entrada" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value, huesped_id: editandoId ? form.huesped_id : null })} required={!form.huesped_id} />
            </label>
            <label className="campo">
              <span className="campo-etiqueta">Tipo de documento</span>
              <select className="entrada" value={form.documento_tipo} onChange={(e) => setForm({ ...form, documento_tipo: e.target.value })}>
                <option value="rut">RUT</option>
                <option value="pasaporte">Pasaporte</option>
              </select>
            </label>
            <label className="campo">
              <span className="campo-etiqueta">Documento</span>
              <input className="entrada" value={form.documento} onChange={(e) => setForm({ ...form, documento: e.target.value })} placeholder="Opcional si es niño" />
            </label>
          </div>
          <div className="politicas-fila">
            <label className="campo">
              <span className="campo-etiqueta">Nacionalidad</span>
              <input className="entrada" value={form.nacionalidad} onChange={(e) => setForm({ ...form, nacionalidad: e.target.value })} />
            </label>
            <label className="campo">
              <span className="campo-etiqueta">Teléfono</span>
              <input className="entrada" value={form.telefono} onChange={(e) => setForm({ ...form, telefono: e.target.value })} />
            </label>
            <label className="campo">
              <span className="campo-etiqueta">Correo</span>
              <input className="entrada" type="email" value={form.correo} onChange={(e) => setForm({ ...form, correo: e.target.value })} />
            </label>
          </div>
          <label className="campo-check">
            <input type="checkbox" checked={form.es_nino} onChange={(e) => setForm({ ...form, es_nino: e.target.checked })} />
            Es niño {politica?.edad_nino_hasta != null ? `(hasta ${politica.edad_nino_hasta} años)` : ''}
          </label>
          <div className="politicas-fila">
            <button type="submit" className="boton-primario" disabled={cargando}>
              {editandoId ? 'Guardar cambios' : 'Agregar huésped'}
            </button>
            {(editandoId || form.huesped_id) && (
              <button type="button" className="boton-secundario" onClick={() => { setEditandoId(null); setForm(FORM_INICIAL) }}>
                Cancelar
              </button>
            )}
          </div>
        </form>
      )}
    </section>
  )
}
