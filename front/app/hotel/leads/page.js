'use client'

import Link from 'next/link'
import { Fragment, useEffect, useState } from 'react'
import { useDestacada } from '../_componentes/destacada'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, SalidaJson, Campo } from '../../../lib/api'
import { gestionaRecepcion } from '../../../lib/roles'
import Subnav from '../_componentes/subnav'
import FormularioEdicion from '../_componentes/formulario-edicion'
import { SUBNAV_BANDEJAS } from '../../../lib/menu-hotel'
import { fechaATexto, fechaHora } from '../../../lib/formato'
import { aCsv, errorRango, parametrosRango, sufijoRango } from '../../../lib/exportacion'

/** Bandeja de leads (V1-ISSUE-20 punto 8, spec-api-v1 «Contacto y leads de la
 *  landing»): las consultas generales del formulario propio de la landing
 *  quedan como agenda de seguimiento de recepción. Recepción o administrador
 *  marcan contactado/cerrado con nota; la gestión es idempotente por clave y
 *  queda en auditoría. Nada se borra. */
export default function Leads() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [estado, setEstado] = useState('')
  // #354: por defecto solo la ventana de «nuevo»; «Ver todos» quita el corte.
  const [todos, setTodos] = useState(false)
  const [corte, setCorte] = useState(null)
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)
  const [notas, setNotas] = useState({})
  const [editando, setEditando] = useState(null)
  const [vinculando, setVinculando] = useState(null)
  const [vinculoForm, setVinculoForm] = useState({ cliente_id: '', solicitud_id: '' })
  const [opcionesClientes, setOpcionesClientes] = useState([])
  const [opcionesSolicitudes, setOpcionesSolicitudes] = useState([])
  const [filtroCliente, setFiltroCliente] = useState('')
  const [historialId, setHistorialId] = useState(null)
  const [historialItems, setHistorialItems] = useState({})
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const [claveGestion, renovarGestion] = useClaveOperacion()
  // Exportación por fecha o rango (2026-11-19): vacío = sin límite.
  const [expDesde, setExpDesde] = useState('')
  const [expHasta, setExpHasta] = useState('')

  // Enlace directo desde un aviso por correo (?id=…): la fila queda marcada.
  const destacada = useDestacada(lista)
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeGestionar = gestionaRecepcion(rol)

  async function cargar(filtro) {
    setError('')
    try {
      const q = new URLSearchParams()
      if (filtro) q.set('estado', filtro)
      if (todos) q.set('todos', 'true')
      const r = await api(`/hotel/leads?${q}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setLista(r.datos.leads)
        setCorte({ ...r.datos.corte, antiguos: r.datos.sin_gestionar_antiguos })
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  useEffect(() => {
    if (puedeGestionar) cargar(estado)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado, puedeGestionar, todos])

  // #354: fidelización deduplicada por contacto (un envío por persona).
  function descargar(contenido, nombre) {
    const enlace = document.createElement('a')
    enlace.href = URL.createObjectURL(new Blob([contenido], { type: 'text/csv;charset=utf-8' }))
    enlace.download = nombre
    enlace.click()
    URL.revokeObjectURL(enlace.href)
  }

  // #354: fidelización deduplicada por contacto (un envío por persona).
  async function exportarContactos() {
    setError('')
    const invalido = errorRango(expDesde, expHasta)
    if (invalido) { setError(invalido); return }
    try {
      const q = new URLSearchParams()
      if (expDesde) q.set('desde', expDesde)
      if (expHasta) q.set('hasta', expHasta)
      const r = await api(`/hotel/leads/contactos?${q}`)
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
      const filas = [['nombre', 'correo', 'telefono', 'leads', 'ultimo_lead']]
        .concat(r.datos.contactos.map((c) => [c.nombre, c.correo, c.telefono, c.leads, fechaHora(c.ultimo_lead_en)]))
      descargar(aCsv(filas), `contactos-${sufijoRango(expDesde, expHasta)}.csv`)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  // Detalle de cada lead del rango (fecha de recepción, estado y gestión).
  async function exportarLeads() {
    setError('')
    const invalido = errorRango(expDesde, expHasta)
    if (invalido) { setError(invalido); return }
    try {
      const r = await api(`/hotel/leads?${parametrosRango(expDesde, expHasta)}`)
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
      const filas = [['recibido', 'nombre', 'correo', 'telefono', 'huespedes', 'llegada', 'salida', 'estado', 'nota', 'mensaje']]
        .concat(r.datos.leads.map((l) => [fechaHora(l.creado_en), l.nombre, l.correo, l.telefono, l.huespedes,
          fechaATexto(l.check_in), fechaATexto(l.check_out), l.estado, l.nota, l.mensaje]))
      descargar(aCsv(filas), `leads-${sufijoRango(expDesde, expHasta)}.csv`)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  async function abrirVinculo(lead) {
    if (vinculando === lead.id) {
      setVinculando(null)
      return
    }
    setVinculando(lead.id)
    setVinculoForm({ cliente_id: lead.cliente_id || '', solicitud_id: lead.solicitud_id || '' })
    setFiltroCliente('')
    setError('')
    try {
      const [rc, rs] = await Promise.all([api('/hotel/clientes'), api('/hotel/solicitudes')])
      if (rc.estado === 200) setOpcionesClientes(rc.datos.clientes || [])
      if (rs.estado === 200) setOpcionesSolicitudes(rs.datos.solicitudes || [])
    } catch {
      // mantiene opciones previas
    }
  }

  async function buscarClientesVinculo(q) {
    setFiltroCliente(q)
    try {
      const r = await api(`/hotel/clientes${q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ''}`)
      if (r.estado === 200) setOpcionesClientes(r.datos.clientes || [])
    } catch {
      // ignora corte transitorio de búsqueda
    }
  }

  async function guardarVinculo(e, leadId) {
    e.preventDefault()
    setError('')
    try {
      const r = await api(`/hotel/leads/${encodeURIComponent(leadId)}/vinculo`, {
        metodo: 'PUT',
        cuerpo: {
          cliente_id: vinculoForm.cliente_id || null,
          solicitud_id: vinculoForm.solicitud_id || null,
        },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
      } else {
        setVinculando(null)
        setHistorialItems((prev) => { const copia = { ...prev }; delete copia[leadId]; return copia })
        cargar(estado)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  async function alternarHistorial(leadId) {
    if (historialId === leadId) {
      setHistorialId(null)
      return
    }
    setHistorialId(leadId)
    setCargandoHistorial(true)
    setError('')
    try {
      const r = await api(`/hotel/leads/${encodeURIComponent(leadId)}/historial`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setHistorialItems((prev) => ({ ...prev, [leadId]: r.datos.historial || [] }))
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setCargandoHistorial(false)
    }
  }

  async function gestionar(leadId, destino) {
    setError('')
    setSalida(null)
    const nota = (notas[leadId] || '').trim() || null
    try {
      const r = await api(`/hotel/leads/${leadId}/estado`, {
        metodo: 'POST', cuerpo: { estado: destino, nota }, claveIdempotencia: claveGestion,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarGestion)
      } else {
        setSalida(r.datos)
        setNotas({ ...notas, [leadId]: '' })
        renovarGestion()
        cargar(estado)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  if (sesion.fase === 'ok' && !puedeGestionar) {
    return (
      <MarcoHotel titulo="Leads de contacto">
      <Subnav items={SUBNAV_BANDEJAS} />
        <p className="estado">La bandeja de leads es solo para recepción o la administración del hotel.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Leads de contacto">
      <Subnav items={SUBNAV_BANDEJAS} />
      <section className="tarjeta">
        <div className="filtros">
          {[
            ['', 'Todos'],
            ['nuevo', 'Nuevos'],
            ['contactado', 'Contactados'],
            ['cerrado', 'Cerrados'],
          ].map(([valor, etiqueta]) => (
            <button
              key={valor}
              type="button"
              className={estado === valor ? 'boton-primario' : 'boton-secundario'}
              onClick={() => setEstado(valor)}
            >
              {etiqueta}
            </button>
          ))}
        </div>
        <label className="campo-check">
          <input type="checkbox" checked={todos} onChange={(e) => setTodos(e.target.checked)} />
          Ver todos (sin corte de fecha)
        </label>
        {corte && (
          <p className="nota-clave" data-corte-leads>
            {corte.desde
              ? <>Mostrando desde el <strong>{fechaATexto(corte.desde) || corte.desde}</strong> (últimos {corte.ventana_nuevo_dias} días).</>
              : <>Mostrando todos los leads.</>}{' '}
            «Nuevo» = sin gestión y dentro de {corte.ventana_nuevo_dias} días.
            {corte.antiguos > 0 && <> Hay <strong>{corte.antiguos}</strong> sin gestionar más antiguos (marca «Ver todos»).</>}
          </p>
        )}
        <fieldset className="formulario" aria-label="Exportar por fecha o rango">
          <legend>Exportar por fecha (vacío = todo)</legend>
          <Campo etiqueta="Desde" type="date" value={expDesde} onChange={(e) => setExpDesde(e.target.value)} />
          <Campo etiqueta="Hasta" type="date" value={expHasta} onChange={(e) => setExpHasta(e.target.value)} />
          <div className="filtros">
            <button type="button" className="boton-secundario" onClick={exportarLeads}>Exportar leads (CSV)</button>
            <button type="button" className="boton-secundario" onClick={exportarContactos}>Exportar contactos sin duplicados (CSV)</button>
          </div>
        </fieldset>
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}
      {salida && <SalidaJson datos={salida} />}

      {lista && (
        lista.length === 0 ? (
          <p className="estado estado-vacio">No hay leads en este estado.</p>
        ) : (
          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Correo</th>
                  <th>Teléfono</th>
                  <th>Huéspedes</th>
                  <th>Llegada</th>
                  <th>Salida</th>
                  <th>Mensaje</th>
                  <th>Estado</th>
                  <th>Vínculos</th>
                  <th>Nota</th>
                  <th>Gestión</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((l) => (
                  <Fragment key={l.id}>
                  <tr {...destacada.props(l.id)}>
                    <td>{l.nombre}</td>
                    <td>{l.correo}</td>
                    <td>{l.telefono}</td>
                    <td>{l.huespedes ?? '—'}</td>
                    <td>{l.check_in ?? '—'}</td>
                    <td>{l.check_out ?? '—'}</td>
                    <td>{l.mensaje ?? '—'}</td>
                    <td>
                      {l.situacion === 'sin_gestionar_antiguo' ? 'sin gestionar (antiguo)' : l.estado}
                      {l.leads_del_contacto > 1 && <span className="nota-clave"> · {l.leads_del_contacto} leads del mismo contacto</span>}
                    </td>
                    <td>
                      {!l.cliente_id && !l.solicitud_id ? '—' : (
                        <>
                          {l.cliente_id && (
                            <div>
                              <Link href="/hotel/clientes">{l.cliente_nombre || l.cliente_id}</Link>
                              {l.cliente_rut ? ` (${l.cliente_rut})` : ''}
                            </div>
                          )}
                          {l.solicitud_id && (
                            <div>
                              <Link href={`/hotel/solicitudes?id=${encodeURIComponent(l.solicitud_id)}`}>{l.solicitud_id}</Link>
                              {l.solicitud_estado ? ` · ${l.solicitud_estado}` : ''}
                            </div>
                          )}
                        </>
                      )}
                    </td>
                    <td>{l.nota ?? '—'}</td>
                    <td>{l.gestion_por ? `${l.gestion_por === 'auto:correo' ? 'automático (correo)' : l.gestion_por} · ${fechaHora(l.gestion_en)}` : '—'}</td>
                    <td>
                      <button type="button" className="boton-fantasma" aria-expanded={editando === l.id}
                        onClick={() => setEditando(editando === l.id ? null : l.id)}>
                        Editar
                      </button>
                      <button type="button" className="boton-fantasma" aria-expanded={vinculando === l.id}
                        onClick={() => abrirVinculo(l)}>
                        Vincular
                      </button>
                      <button type="button" className="boton-fantasma" aria-expanded={historialId === l.id}
                        onClick={() => alternarHistorial(l.id)}>
                        Historial
                      </button>
                      {l.estado !== 'cerrado' ? (
                        <div className="acciones-fila">
                          <input
                            className="entrada"
                            placeholder="Nota de gestión"
                            value={notas[l.id] || ''}
                            onChange={(e) => setNotas({ ...notas, [l.id]: e.target.value })}
                          />
                          {l.estado === 'nuevo' && (
                            <button type="button" className="boton-primario" onClick={() => gestionar(l.id, 'contactado')}>
                              Contactado
                            </button>
                          )}
                          {l.estado === 'contactado' && l.gestion_por === 'auto:correo' && (
                            <button type="button" className="boton-fantasma" title="Marcado por la revisión de correo"
                              onClick={() => gestionar(l.id, 'nuevo')}>
                              Deshacer (automático)
                            </button>
                          )}
                          <button type="button" className="boton-secundario" onClick={() => gestionar(l.id, 'cerrado')}>
                            Cerrar
                          </button>
                        </div>
                      ) : (
                        <span className="estado">cerrado</span>
                      )}
                    </td>
                  </tr>
                  {editando === l.id && (
                    <tr>
                      <td colSpan={12}>
                        <FormularioEdicion
                          ruta={`/hotel/leads/${l.id}`}
                          inicial={l}
                          campos={[
                            { nombre: 'nombre', etiqueta: 'Nombre', requerido: true },
                            { nombre: 'correo', etiqueta: 'Correo', tipo: 'email', requerido: true },
                            { nombre: 'telefono', etiqueta: 'Teléfono', requerido: true },
                            { nombre: 'huespedes', etiqueta: 'Huéspedes', tipo: 'number' },
                            { nombre: 'check_in', etiqueta: 'Llegada', tipo: 'date' },
                            { nombre: 'check_out', etiqueta: 'Salida', tipo: 'date' },
                            { nombre: 'mensaje', etiqueta: 'Mensaje' },
                            { nombre: 'nota', etiqueta: 'Nota' },
                          ]}
                          alGuardar={() => { setEditando(null); setHistorialItems((prev) => { const copia = { ...prev }; delete copia[l.id]; return copia }); cargar(estado) }}
                          alCancelar={() => setEditando(null)}
                        />
                        <p className="nota-clave">Corregir datos no cambia el estado del lead.</p>
                      </td>
                    </tr>
                  )}
                  {vinculando === l.id && (
                    <tr>
                      <td colSpan={12}>
                        <form className="formulario" onSubmit={(e) => guardarVinculo(e, l.id)} aria-label="Vincular lead con cliente o solicitud">
                          <label className="campo">
                            <span className="campo-etiqueta">Filtrar cliente (nombre, RUT o teléfono)</span>
                            <input className="entrada" value={filtroCliente} onChange={(e) => buscarClientesVinculo(e.target.value)} placeholder="Escribe para filtrar…" />
                          </label>
                          <label className="campo">
                            <span className="campo-etiqueta">Cliente vinculado</span>
                            <select className="entrada" value={vinculoForm.cliente_id} onChange={(e) => setVinculoForm({ ...vinculoForm, cliente_id: e.target.value })}>
                              <option value="">(Sin cliente vinculado)</option>
                              {opcionesClientes.map((c) => (
                                <option key={c.id} value={c.id}>{c.nombre} ({c.rut})</option>
                              ))}
                            </select>
                          </label>
                          <label className="campo">
                            <span className="campo-etiqueta">Solicitud vinculada</span>
                            <select className="entrada" value={vinculoForm.solicitud_id} onChange={(e) => setVinculoForm({ ...vinculoForm, solicitud_id: e.target.value })}>
                              <option value="">(Sin solicitud vinculada)</option>
                              {opcionesSolicitudes.map((s) => (
                                <option key={s.solicitud_id} value={s.solicitud_id}>
                                  {s.solicitud_id} · {s.huesped_nombre} ({s.estado})
                                </option>
                              ))}
                            </select>
                          </label>
                          <div className="acciones-fila">
                            <button type="submit" className="boton-primario">Guardar vínculos</button>
                            <button type="button" className="boton-secundario" onClick={() => setVinculando(null)}>Cancelar</button>
                          </div>
                        </form>
                      </td>
                    </tr>
                  )}
                  {historialId === l.id && (
                    <tr>
                      <td colSpan={12}>
                        <strong>Historial de ediciones y gestión</strong>
                        {cargandoHistorial && !historialItems[l.id] ? (
                          <p className="nota-clave" role="status" aria-busy="true">Cargando historial…</p>
                        ) : (historialItems[l.id] || []).length === 0 ? (
                          <p className="nota-clave">Sin ediciones ni cambios de estado registrados.</p>
                        ) : (
                          <ul className="lista-simple">
                            {(historialItems[l.id] || []).map((ev) => (
                              <li key={ev.auditoria_id}>
                                {fechaHora(ev.creado_en)} ·{' '}
                                <strong>
                                  {ev.accion === 'lead_edicion'
                                    ? 'Edición de campos'
                                    : ev.accion === 'lead_vinculo'
                                      ? 'Vínculo actualizado'
                                      : 'Cambio de estado'}
                                </strong>{' '}
                                · {ev.detalle} ({ev.actor})
                              </li>
                            ))}
                          </ul>
                        )}
                      </td>
                    </tr>
                  )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </MarcoHotel>
  )
}
