'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useDestacada } from '../_componentes/destacada'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, SalidaJson, Campo, CampoSelect } from '../../../lib/api'
import { gestionaRecepcion } from '../../../lib/roles'
import Subnav from '../_componentes/subnav'
import FormularioEdicion from '../_componentes/formulario-edicion'
import { BarraContextual, SelectorFila } from '../_componentes/barra-contextual'
import { SUBNAV_BANDEJAS } from '../../../lib/menu-hotel'
import { fechaATexto, fechaHora } from '../../../lib/formato'
import { errorRango, exportarFormatoUnico, parametrosRango, sufijoRango } from '../../../lib/exportacion'

const ETIQUETA_ESTADO_LEAD = {
  nuevo: 'Nuevo',
  contactado: 'Contactado',
  cerrado: 'Cerrado',
}

/** Bandeja de leads: selección de lead activo + barra contextual única (sin
 *  repetir botones ni cajas de texto en cada fila). */
export default function Leads() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [estado, setEstado] = useState('')
  const [todos, setTodos] = useState(false)
  const [corte, setCorte] = useState(null)
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)

  const [seleccionadoId, setSeleccionadoId] = useState(null)
  const [panelActivo, setPanelActivo] = useState(null) // 'editar' | 'vincular' | 'historial' | null
  const [notaGestion, setNotaGestion] = useState('')
  const [vinculoForm, setVinculoForm] = useState({ cliente_id: '', solicitud_id: '' })
  const [opcionesClientes, setOpcionesClientes] = useState([])
  const [opcionesSolicitudes, setOpcionesSolicitudes] = useState([])
  const [filtroCliente, setFiltroCliente] = useState('')
  const [historialItems, setHistorialItems] = useState({})
  const [cargandoHistorial, setCargandoHistorial] = useState(false)
  const [claveGestion, renovarGestion] = useClaveOperacion()
  const [expDesde, setExpDesde] = useState('')
  const [expHasta, setExpHasta] = useState('')

  const destacada = useDestacada(lista)
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeGestionar = gestionaRecepcion(rol)

  const activo = (lista || []).find((l) => l.id === seleccionadoId) || null

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

  function elegirLead(lead) {
    setSeleccionadoId(lead.id)
    setPanelActivo(null)
    setNotaGestion('')
    setError('')
  }

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
      exportarFormatoUnico({
        titulo: 'Contactos de leads (sin duplicados)',
        filtros: sufijoRango(expDesde, expHasta),
        columnas: ['Nombre', 'Correo', 'Teléfono', 'Cantidad de leads', 'Último lead'],
        filas: r.datos.contactos.map((c) => [c.nombre, c.correo, c.telefono, c.leads, fechaHora(c.ultimo_lead_en)]),
        nombreArchivo: `herencia-contactos-${sufijoRango(expDesde, expHasta)}.csv`,
      })
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  async function exportarLeads() {
    setError('')
    const invalido = errorRango(expDesde, expHasta)
    if (invalido) { setError(invalido); return }
    try {
      const r = await api(`/hotel/leads?${parametrosRango(expDesde, expHasta)}`)
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
      exportarFormatoUnico({
        titulo: 'Leads recibidos',
        filtros: sufijoRango(expDesde, expHasta),
        columnas: ['Recibido', 'Nombre', 'Correo', 'Teléfono', 'Huéspedes', 'Llegada', 'Salida', 'Estado', 'Nota', 'Mensaje'],
        filas: r.datos.leads.map((l) => [fechaHora(l.creado_en), l.nombre, l.correo, l.telefono, l.huespedes,
          fechaATexto(l.check_in), fechaATexto(l.check_out), l.estado, l.nota, l.mensaje]),
        nombreArchivo: `herencia-leads-${sufijoRango(expDesde, expHasta)}.csv`,
      })
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  async function alternarVinculo(lead) {
    if (panelActivo === 'vincular') {
      setPanelActivo(null)
      return
    }
    setPanelActivo('vincular')
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
      // ignora corte transitorio
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
        setPanelActivo(null)
        setHistorialItems((prev) => { const copia = { ...prev }; delete copia[leadId]; return copia })
        cargar(estado)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  async function alternarHistorial(leadId) {
    if (panelActivo === 'historial') {
      setPanelActivo(null)
      return
    }
    setPanelActivo('historial')
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
    const nota = notaGestion.trim() || null
    try {
      const r = await api(`/hotel/leads/${leadId}/estado`, {
        metodo: 'POST', cuerpo: { estado: destino, nota }, claveIdempotencia: claveGestion,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarGestion)
      } else {
        setSalida(r.datos)
        setNotaGestion('')
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
          <button type="button" className="boton-secundario" onClick={exportarLeads}>Exportar leads (CSV)</button>
          <button type="button" className="boton-secundario" onClick={exportarContactos}>Exportar contactos (CSV)</button>
        </fieldset>
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}
      {salida && <SalidaJson datos={salida} />}

      {lista && (
        lista.length === 0 ? (
          <p className="estado estado-vacio">No hay leads en este estado.</p>
        ) : (
          <>
            <BarraContextual
              titulo="Gestión del lead"
              seleccionado={Boolean(activo)}
              resumen={activo ? `${activo.nombre} · ${activo.correo}` : ''}
              detalle={activo ? `Estado: ${ETIQUETA_ESTADO_LEAD[activo.estado] || activo.estado}${activo.telefono ? ` · Tel. ${activo.telefono}` : ''}` : ''}
              placeholder="Selecciona un lead de la tabla para editarlo, vincularlo, ver su historial o cambiar su estado."
              alLimpiar={() => { setSeleccionadoId(null); setPanelActivo(null) }}
            >
              {activo && (
                <>
                  <button
                    type="button"
                    className="boton-secundario"
                    aria-expanded={panelActivo === 'editar'}
                    onClick={() => setPanelActivo(panelActivo === 'editar' ? null : 'editar')}
                  >
                    {panelActivo === 'editar' ? 'Cerrar edición' : 'Editar'}
                  </button>
                  <button
                    type="button"
                    className="boton-secundario"
                    aria-expanded={panelActivo === 'vincular'}
                    onClick={() => alternarVinculo(activo)}
                  >
                    Vincular
                  </button>
                  <button
                    type="button"
                    className="boton-fantasma"
                    aria-expanded={panelActivo === 'historial'}
                    onClick={() => alternarHistorial(activo.id)}
                  >
                    Historial
                  </button>
                  {activo.estado !== 'cerrado' && (
                    <>
                      <input
                        className="entrada"
                        aria-label={`Nota de gestión para ${activo.nombre}`}
                        placeholder="Nota de gestión (opcional)"
                        value={notaGestion}
                        onChange={(e) => setNotaGestion(e.target.value)}
                      />
                      {activo.estado === 'nuevo' && (
                        <button type="button" className="boton-primario" onClick={() => gestionar(activo.id, 'contactado')}>
                          Marcar contactado
                        </button>
                      )}
                      {activo.estado === 'contactado' && activo.gestion_por === 'auto:correo' && (
                        <button type="button" className="boton-fantasma" onClick={() => gestionar(activo.id, 'nuevo')}>
                          Deshacer automático
                        </button>
                      )}
                      <button type="button" className="boton-secundario" onClick={() => gestionar(activo.id, 'cerrado')}>
                        Cerrar lead
                      </button>
                    </>
                  )}
                </>
              )}
            </BarraContextual>

            {activo && panelActivo === 'editar' && (
              <div style={{ marginBottom: '0.75rem' }}>
                <FormularioEdicion
                  key={activo.id}
                  ruta={`/hotel/leads/${activo.id}`}
                  tituloAria={`Editar lead de ${activo.nombre}`}
                  inicial={activo}
                  campos={[
                    { nombre: 'nombre', etiqueta: 'Nombre', requerido: true },
                    { nombre: 'correo', etiqueta: 'Correo', tipo: 'email', requerido: true },
                    { nombre: 'telefono', etiqueta: 'Teléfono', tipo: 'tel', requerido: true },
                    { nombre: 'huespedes', etiqueta: 'Huéspedes', tipo: 'number' },
                    { nombre: 'check_in', etiqueta: 'Llegada', tipo: 'date' },
                    { nombre: 'check_out', etiqueta: 'Salida', tipo: 'date' },
                    { nombre: 'mensaje', etiqueta: 'Mensaje' },
                    { nombre: 'nota', etiqueta: 'Nota' },
                  ]}
                  alGuardar={() => {
                    setPanelActivo(null)
                    setHistorialItems((prev) => { const copia = { ...prev }; delete copia[activo.id]; return copia })
                    cargar(estado)
                  }}
                  alCancelar={() => setPanelActivo(null)}
                />
                <p className="nota-clave">Corregir datos no cambia el estado del lead.</p>
              </div>
            )}

            {activo && panelActivo === 'vincular' && (
              <section className="tarjeta" aria-label="Vincular lead con cliente o solicitud">
                <form className="formulario" onSubmit={(e) => guardarVinculo(e, activo.id)}>
                  <Campo
                    etiqueta="Filtrar cliente (nombre, RUT o teléfono)"
                    value={filtroCliente}
                    onChange={(e) => buscarClientesVinculo(e.target.value)}
                    placeholder="Escribe para filtrar…"
                  />
                  <CampoSelect
                    etiqueta="Cliente vinculado"
                    value={vinculoForm.cliente_id}
                    onChange={(e) => setVinculoForm({ ...vinculoForm, cliente_id: e.target.value })}
                  >
                    <option value="">Sin cliente vinculado</option>
                    {opcionesClientes.map((c) => (
                      <option key={c.id} value={c.id}>{c.nombre} ({c.rut})</option>
                    ))}
                  </CampoSelect>
                  <CampoSelect
                    etiqueta="Solicitud vinculada"
                    value={vinculoForm.solicitud_id}
                    onChange={(e) => setVinculoForm({ ...vinculoForm, solicitud_id: e.target.value })}
                  >
                    <option value="">Sin solicitud vinculada</option>
                    {opcionesSolicitudes.map((s) => (
                      <option key={s.solicitud_id} value={s.solicitud_id}>
                        {s.solicitud_id} · {s.huesped_nombre} ({s.estado})
                      </option>
                    ))}
                  </CampoSelect>
                  <div className="acciones-fila">
                    <button type="submit" className="boton-primario">Guardar vínculos</button>
                    <button type="button" className="boton-secundario" onClick={() => setPanelActivo(null)}>Cancelar</button>
                  </div>
                </form>
              </section>
            )}

            {activo && panelActivo === 'historial' && (
              <section className="tarjeta" aria-label="Historial de ediciones y gestión">
                <h3>Historial de {activo.nombre}</h3>
                {cargandoHistorial && !historialItems[activo.id] ? (
                  <p className="nota-clave" role="status" aria-busy="true">Cargando historial…</p>
                ) : (historialItems[activo.id] || []).length === 0 ? (
                  <p className="nota-clave">Sin ediciones ni cambios de estado registrados.</p>
                ) : (
                  <ul className="lista-simple">
                    {(historialItems[activo.id] || []).map((ev) => (
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
              </section>
            )}

            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Listado de leads (desliza para ver todas las columnas)">
              <table className="tabla">
                <thead>
                  <tr>
                    <th className="celda-selector"><span className="sr-only">Elegir</span></th>
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
                  </tr>
                </thead>
                <tbody>
                  {lista.map((l) => {
                    const elegida = activo?.id === l.id
                    return (
                      <tr
                        key={l.id}
                        {...destacada.props(l.id)}
                        className="fila-seleccionable"
                        data-seleccionada={elegida ? 'true' : 'false'}
                        onClick={() => elegirLead(l)}
                      >
                        <td className="celda-selector">
                          <SelectorFila
                            nombreGrupo="lead-activo"
                            elegido={elegida}
                            etiqueta={`Seleccionar lead de ${l.nombre}`}
                            alElegir={() => elegirLead(l)}
                          />
                        </td>
                        <td>{l.nombre}</td>
                        <td>{l.correo}</td>
                        <td>{l.telefono}</td>
                        <td>{l.huespedes ?? '—'}</td>
                        <td className="celda-fecha">{l.check_in ? fechaATexto(l.check_in) : '—'}</td>
                        <td className="celda-fecha">{l.check_out ? fechaATexto(l.check_out) : '—'}</td>
                        <td>{l.mensaje ?? '—'}</td>
                        <td>
                          <span className="reserva-estado">
                            {l.situacion === 'sin_gestionar_antiguo'
                              ? 'Sin gestionar (antiguo)'
                              : (ETIQUETA_ESTADO_LEAD[l.estado] || l.estado)}
                          </span>
                          {l.leads_del_contacto > 1 && <span className="nota-clave"> · {l.leads_del_contacto} leads</span>}
                        </td>
                        <td>
                          {!l.cliente_id && !l.solicitud_id ? '—' : (
                            <>
                              {l.cliente_id && (
                                <div>
                                  <Link href="/hotel/clientes" onClick={(e) => e.stopPropagation()}>
                                    {l.cliente_nombre || l.cliente_id}
                                  </Link>
                                  {l.cliente_rut ? ` (${l.cliente_rut})` : ''}
                                </div>
                              )}
                              {l.solicitud_id && (
                                <div>
                                  <Link href={`/hotel/solicitudes?id=${encodeURIComponent(l.solicitud_id)}`} onClick={(e) => e.stopPropagation()}>
                                    {l.solicitud_id}
                                  </Link>
                                  {l.solicitud_estado ? ` · ${l.solicitud_estado}` : ''}
                                </div>
                              )}
                            </>
                          )}
                        </td>
                        <td>{l.nota ?? '—'}</td>
                        <td>{l.gestion_por ? `${l.gestion_por === 'auto:correo' ? 'Automático (correo)' : l.gestion_por} · ${fechaHora(l.gestion_en)}` : '—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )
      )}
    </MarcoHotel>
  )
}
