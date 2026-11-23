'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, Campo, CampoSelect, useSesion } from '../../../lib/api'
import { esAdminHotel } from '../../../lib/roles'
import { fechaATexto, plural } from '../../../lib/formato'
import Comunicados from '../_componentes/comunicados'

const AREAS = [
  ['recepcion', 'Recepción'],
  ['aseo', 'Aseo'],
  ['desayunos', 'Desayunos'],
  ['mantencion', 'Mantención'],
]

const ETIQUETA_AREA = Object.fromEntries(AREAS)

const CATEGORIAS_DOC = [
  ['manual', 'Manual'],
  ['instructivo', 'Instructivo'],
  ['politica', 'Política'],
  ['protocolo', 'Protocolo'],
]

const ETIQUETA_PREVENTIVO = {
  al_dia: 'Al día',
  por_vencer: 'Por vencer (7 días)',
  vencido: 'Vencido',
  sin_calendario: 'Sin calendario',
}

/**
 * Coordinación de equipo — Corte 2 Operativo (#418):
 * turnos semanales y cambios aprobados, comunicados con lectura,
 * biblioteca documental por rol + buzón de sugerencias,
 * e inventario de activos por habitación con mantenimiento preventivo.
 */
export default function EquipoOperativo() {
  const sesion = useSesion()
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const esAdmin = esAdminHotel(rol)

  const [pestana, setPestana] = useState('turnos')
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  // Turnos
  const [turnosData, setTurnosData] = useState(null)
  const [areaFiltro, setAreaFiltro] = useState('')
  const [nuevoTurno, setNuevoTurno] = useState({
    usuario_nombre: '',
    area: 'recepcion',
    fecha: '',
    hora_inicio: '08:00',
    hora_fin: '16:00',
    nota: '',
  })
  const [cambioForm, setCambioForm] = useState({ turno_id: null, reemplazo_usuario: '', motivo: '' })

  // Biblioteca y buzón
  const [documentos, setDocumentos] = useState([])
  const [sugerencias, setSugerencias] = useState([])
  const [nuevoDoc, setNuevoDoc] = useState({
    titulo: '',
    categoria: 'manual',
    rol_objetivo: 'todos',
    version: '1.0',
    contenido: '',
  })
  const [nuevaSug, setNuevaSug] = useState({ categoria: 'operacion', mensaje: '', anonimo: false })

  // Activos y preventivo
  const [activosData, setActivosData] = useState(null)
  const [soloVencidos, setSoloVencidos] = useState(false)
  const [nuevoActivo, setNuevoActivo] = useState({
    nombre: '',
    categoria: 'climatizacion',
    habitacion_id: '',
    area: '',
    numero_serie: '',
    frecuencia_mantencion_dias: '90',
    notas: '',
  })
  const [mantForm, setMantForm] = useState({ activo_id: null, tipo: 'preventiva', descripcion: '', costo_clp: '0' })

  const cargarTurnos = useCallback(async (area = areaFiltro) => {
    const q = area ? `?area=${encodeURIComponent(area)}` : ''
    const r = await api(`/hotel/equipo/turnos${q}`)
    if (r.estado < 400) setTurnosData(r.datos)
    else setError(mensajeDeError(r.datos, r.estado))
  }, [areaFiltro])

  const cargarBibliotecaYSugerencias = useCallback(async () => {
    const [rDoc, rSug] = await Promise.all([
      api('/hotel/equipo/biblioteca'),
      api('/hotel/equipo/sugerencias'),
    ])
    if (rDoc.estado < 400) setDocumentos(rDoc.datos.documentos || [])
    if (rSug.estado < 400) setSugerencias(rSug.datos.sugerencias || [])
  }, [])

  const cargarActivos = useCallback(async (venc = soloVencidos) => {
    const r = await api(`/hotel/activos?solo_vencidos=${venc ? 'true' : 'false'}`)
    if (r.estado < 400) setActivosData(r.datos)
    else setError(mensajeDeError(r.datos, r.estado))
  }, [soloVencidos])

  useEffect(() => {
    if (sesion.fase !== 'ok') return
    cargarTurnos(areaFiltro)
    cargarBibliotecaYSugerencias()
    cargarActivos(soloVencidos)
  }, [sesion.fase, areaFiltro, soloVencidos, cargarTurnos, cargarBibliotecaYSugerencias, cargarActivos])

  async function crearTurno(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const r = await api('/hotel/equipo/turnos', { metodo: 'POST', cuerpo: nuevoTurno })
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
    setAviso('Turno programado correctamente.')
    setNuevoTurno({ ...nuevoTurno, usuario_nombre: '', nota: '' })
    await cargarTurnos(areaFiltro)
  }

  async function solicitarCambio(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const r = await api(`/hotel/equipo/turnos/${cambioForm.turno_id}/cambios`, {
      metodo: 'POST',
      cuerpo: { reemplazo_usuario: cambioForm.reemplazo_usuario, motivo: cambioForm.motivo },
    })
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
    setAviso('Solicitud de cambio enviada para aprobación.')
    setCambioForm({ turno_id: null, reemplazo_usuario: '', motivo: '' })
    await cargarTurnos(areaFiltro)
  }

  async function resolverCambio(cambioId, decision) {
    setError('')
    setAviso('')
    const r = await api(`/hotel/equipo/cambios-turno/${cambioId}/decision`, {
      metodo: 'POST',
      cuerpo: { decision, nota_revision: '' },
    })
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
    setAviso(`Cambio de turno ${decision}.`)
    await cargarTurnos(areaFiltro)
  }

  async function publicarDocumento(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const r = await api('/hotel/equipo/biblioteca', { metodo: 'POST', cuerpo: nuevoDoc })
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
    setAviso('Documento agregado a la biblioteca operativa.')
    setNuevoDoc({ titulo: '', categoria: 'manual', rol_objetivo: 'todos', version: '1.0', contenido: '' })
    await cargarBibliotecaYSugerencias()
  }

  async function enviarSugerencia(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const r = await api('/hotel/equipo/sugerencias', { metodo: 'POST', cuerpo: nuevaSug })
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
    setAviso('Sugerencia enviada al buzón interno.')
    setNuevaSug({ categoria: 'operacion', mensaje: '', anonimo: false })
    await cargarBibliotecaYSugerencias()
  }

  async function crearActivo(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const cuerpo = {
      nombre: nuevoActivo.nombre,
      categoria: nuevoActivo.categoria,
      habitacion_id: nuevoActivo.habitacion_id.trim() || null,
      area: nuevoActivo.area.trim() || null,
      numero_serie: nuevoActivo.numero_serie,
      frecuencia_mantencion_dias: nuevoActivo.frecuencia_mantencion_dias ? Number(nuevoActivo.frecuencia_mantencion_dias) : null,
      notas: nuevoActivo.notas,
    }
    const r = await api('/hotel/activos', { metodo: 'POST', cuerpo })
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
    setAviso('Activo registrado en el inventario preventivo.')
    setNuevoActivo({ nombre: '', categoria: 'climatizacion', habitacion_id: '', area: '', numero_serie: '', frecuencia_mantencion_dias: '90', notas: '' })
    await cargarActivos(soloVencidos)
  }

  async function registrarMantencion(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const r = await api(`/hotel/activos/${mantForm.activo_id}/mantenciones`, {
      metodo: 'POST',
      cuerpo: {
        tipo: mantForm.tipo,
        descripcion: mantForm.descripcion,
        costo_clp: Number(mantForm.costo_clp || 0),
      },
    })
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
    setAviso('Mantención registrada y próximo ciclo recalculado.')
    setMantForm({ activo_id: null, tipo: 'preventiva', descripcion: '', costo_clp: '0' })
    await cargarActivos(soloVencidos)
  }

  return (
    <MarcoHotel titulo="Equipo, turnos y mantenimiento preventivo">
      <div role="tablist" aria-label="Secciones de coordinación del equipo" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <button type="button" role="tab" aria-selected={pestana === 'turnos'} className={pestana === 'turnos' ? 'boton-primario' : 'boton-secundario'} onClick={() => setPestana('turnos')}>
          Turnos semanales
        </button>
        <button type="button" role="tab" aria-selected={pestana === 'comunicados'} className={pestana === 'comunicados' ? 'boton-primario' : 'boton-secundario'} onClick={() => setPestana('comunicados')}>
          Comunicados
        </button>
        <button type="button" role="tab" aria-selected={pestana === 'biblioteca'} className={pestana === 'biblioteca' ? 'boton-primario' : 'boton-secundario'} onClick={() => setPestana('biblioteca')}>
          Biblioteca y buzón
        </button>
        <button type="button" role="tab" aria-selected={pestana === 'activos'} className={pestana === 'activos' ? 'boton-primario' : 'boton-secundario'} onClick={() => setPestana('activos')}>
          Activos y preventivo
        </button>
      </div>

      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      {pestana === 'comunicados' && <Comunicados puedePublicar={esAdmin} />}

      {pestana === 'turnos' && (
        <>
          <section className="tarjeta" aria-label="Vista semanal de turnos">
            <h2>Vista semanal de turnos</h2>
            {turnosData && (
              <p className="nota-clave">
                Semana del {fechaATexto(turnosData.desde)} al {fechaATexto(turnosData.hasta)} · {plural(turnosData.turnos.length, 'turno')} · {plural(turnosData.cambios_pendientes, 'cambio pendiente', 'cambios pendientes')}.
              </p>
            )}
            <CampoSelect etiqueta="Filtrar por área" value={areaFiltro} onChange={(e) => setAreaFiltro(e.target.value)}>
              <option value="">Todas las áreas</option>
              {AREAS.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
            </CampoSelect>

            {turnosData && turnosData.turnos.length > 0 ? (
              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Turnos programados de la semana">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Área</th>
                      <th>Persona</th>
                      <th>Horario</th>
                      <th>Estado</th>
                      <th>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {turnosData.turnos.map((t) => (
                      <tr key={t.turno_id}>
                        <td>{fechaATexto(t.fecha)}</td>
                        <td>{ETIQUETA_AREA[t.area] || t.area}</td>
                        <td>{t.usuario_nombre}</td>
                        <td>{t.hora_inicio}–{t.hora_fin}</td>
                        <td>{t.estado}</td>
                        <td>
                          <button type="button" className="boton-secundario" onClick={() => setCambioForm({ turno_id: t.turno_id, reemplazo_usuario: '', motivo: '' })}>
                            Pedir cambio
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="estado">Sin turnos programados en este rango.</p>
            )}

            {cambioForm.turno_id && (
              <form className="formulario" onSubmit={solicitarCambio} style={{ marginTop: '1rem' }}>
                <h3>Solicitar cambio para turno #{cambioForm.turno_id}</h3>
                <Campo etiqueta="Persona de reemplazo" value={cambioForm.reemplazo_usuario} onChange={(e) => setCambioForm({ ...cambioForm, reemplazo_usuario: e.target.value })} required />
                <Campo etiqueta="Motivo" value={cambioForm.motivo} onChange={(e) => setCambioForm({ ...cambioForm, motivo: e.target.value })} required />
                <button type="submit" className="boton-primario">Enviar solicitud</button>
              </form>
            )}

            {turnosData && turnosData.cambios.length > 0 && (
              <>
                <h3>Cambios de turno</h3>
                <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Solicitudes de cambio de turno">
                  <table className="tabla">
                    <thead>
                      <tr>
                        <th>Fecha</th>
                        <th>Solicita</th>
                        <th>Reemplazo</th>
                        <th>Motivo</th>
                        <th>Estado</th>
                        {esAdmin && <th>Decisión</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {turnosData.cambios.map((c) => (
                        <tr key={c.cambio_id}>
                          <td>{fechaATexto(c.fecha)}</td>
                          <td>{c.solicitante}</td>
                          <td>{c.reemplazo_usuario}</td>
                          <td>{c.motivo}</td>
                          <td>{c.estado}</td>
                          {esAdmin && (
                            <td>
                              {c.estado === 'pendiente' ? (
                                <div style={{ display: 'flex', gap: '0.25rem' }}>
                                  <button type="button" className="boton-primario" onClick={() => resolverCambio(c.cambio_id, 'aprobado')}>Aprobar</button>
                                  <button type="button" className="boton-secundario" onClick={() => resolverCambio(c.cambio_id, 'rechazado')}>Rechazar</button>
                                </div>
                              ) : '—'}
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>

          {esAdmin && (
            <section className="tarjeta" aria-label="Programar turno">
              <h3>Programar turno semanal</h3>
              <form className="formulario" onSubmit={crearTurno}>
                <Campo etiqueta="Persona" value={nuevoTurno.usuario_nombre} onChange={(e) => setNuevoTurno({ ...nuevoTurno, usuario_nombre: e.target.value })} required />
                <CampoSelect etiqueta="Área" value={nuevoTurno.area} onChange={(e) => setNuevoTurno({ ...nuevoTurno, area: e.target.value })}>
                  {AREAS.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
                </CampoSelect>
                <Campo etiqueta="Fecha" type="date" value={nuevoTurno.fecha} onChange={(e) => setNuevoTurno({ ...nuevoTurno, fecha: e.target.value })} required />
                <Campo etiqueta="Hora inicio" type="time" value={nuevoTurno.hora_inicio} onChange={(e) => setNuevoTurno({ ...nuevoTurno, hora_inicio: e.target.value })} required />
                <Campo etiqueta="Hora término" type="time" value={nuevoTurno.hora_fin} onChange={(e) => setNuevoTurno({ ...nuevoTurno, hora_fin: e.target.value })} required />
                <Campo etiqueta="Nota" value={nuevoTurno.nota} onChange={(e) => setNuevoTurno({ ...nuevoTurno, nota: e.target.value })} />
                <button type="submit" className="boton-primario">Guardar turno</button>
              </form>
            </section>
          )}
        </>
      )}

      {pestana === 'biblioteca' && (
        <>
          <section className="tarjeta" aria-label="Biblioteca operativa por rol">
            <h2>Biblioteca documental</h2>
            {documentos.length === 0 ? (
              <p className="estado">Aún no hay documentos cargados para tu rol.</p>
            ) : (
              documentos.map((d) => (
                <article key={d.documento_id} style={{ borderBottom: '1px solid #e5e7eb', padding: '0.75rem 0' }}>
                  <h3>{d.titulo} <small>v{d.version} · {d.categoria} · rol {d.rol_objetivo}</small></h3>
                  <p style={{ whiteSpace: 'pre-wrap' }}>{d.contenido}</p>
                </article>
              ))
            )}
            {esAdmin && (
              <form className="formulario" onSubmit={publicarDocumento} style={{ marginTop: '1rem' }}>
                <h3>Publicar manual o protocolo</h3>
                <Campo etiqueta="Título" value={nuevoDoc.titulo} onChange={(e) => setNuevoDoc({ ...nuevoDoc, titulo: e.target.value })} required />
                <CampoSelect etiqueta="Categoría" value={nuevoDoc.categoria} onChange={(e) => setNuevoDoc({ ...nuevoDoc, categoria: e.target.value })}>
                  {CATEGORIAS_DOC.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
                </CampoSelect>
                <CampoSelect etiqueta="Rol destinatario" value={nuevoDoc.rol_objetivo} onChange={(e) => setNuevoDoc({ ...nuevoDoc, rol_objetivo: e.target.value })}>
                  <option value="todos">Todo el equipo</option>
                  <option value="recepcion">Recepción</option>
                  <option value="aseo">Aseo</option>
                  <option value="caja">Caja</option>
                </CampoSelect>
                <Campo etiqueta="Versión" value={nuevoDoc.version} onChange={(e) => setNuevoDoc({ ...nuevoDoc, version: e.target.value })} />
                <label className="campo">
                  <span>Contenido</span>
                  <textarea rows={4} value={nuevoDoc.contenido} onChange={(e) => setNuevoDoc({ ...nuevoDoc, contenido: e.target.value })} required />
                </label>
                <button type="submit" className="boton-primario">Publicar documento</button>
              </form>
            )}
          </section>

          <section className="tarjeta" aria-label="Buzón de sugerencias">
            <h2>Buzón de sugerencias</h2>
            <form className="formulario" onSubmit={enviarSugerencia}>
              <CampoSelect etiqueta="Categoría" value={nuevaSug.categoria} onChange={(e) => setNuevaSug({ ...nuevaSug, categoria: e.target.value })}>
                <option value="operacion">Operación</option>
                <option value="mantencion">Mantención</option>
                <option value="huespedes">Huéspedes</option>
                <option value="equipo">Equipo</option>
                <option value="otro">Otro</option>
              </CampoSelect>
              <label className="campo">
                <span>Sugerencia</span>
                <textarea rows={3} value={nuevaSug.mensaje} onChange={(e) => setNuevaSug({ ...nuevaSug, mensaje: e.target.value })} required />
              </label>
              <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <input type="checkbox" checked={nuevaSug.anonimo} onChange={(e) => setNuevaSug({ ...nuevaSug, anonimo: e.target.checked })} />
                Enviar de forma anónima
              </label>
              <button type="submit" className="boton-primario">Enviar sugerencia</button>
            </form>
            {sugerencias.length > 0 && (
              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Listado de sugerencias">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th>Categoría</th>
                      <th>Autor</th>
                      <th>Mensaje</th>
                      <th>Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sugerencias.map((s) => (
                      <tr key={s.sugerencia_id}>
                        <td>{s.categoria}</td>
                        <td>{s.anonimo ? 'Anónimo' : (s.autor || '—')}</td>
                        <td>{s.mensaje}</td>
                        <td>{s.estado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      {pestana === 'activos' && (
        <>
          <section className="tarjeta" aria-label="Inventario de activos y mantenimiento preventivo">
            <h2>Inventario de activos y mantenimiento preventivo</h2>
            {activosData && (
              <div className="kpi-rejilla">
                <div className="kpi"><span className="kpi-titulo">Activos</span><span className="kpi-valor">{activosData.resumen.total}</span></div>
                <div className={`kpi${activosData.resumen.vencidos > 0 ? ' kpi-alerta' : ''}`}><span className="kpi-titulo">Preventivos vencidos</span><span className="kpi-valor">{activosData.resumen.vencidos}</span></div>
                <div className="kpi"><span className="kpi-titulo">Por vencer (7 días)</span><span className="kpi-valor">{activosData.resumen.por_vencer}</span></div>
                <div className="kpi"><span className="kpi-titulo">Al día</span><span className="kpi-valor">{activosData.resumen.al_dia}</span></div>
              </div>
            )}
            <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginTop: '0.75rem' }}>
              <input type="checkbox" checked={soloVencidos} onChange={(e) => setSoloVencidos(e.target.checked)} />
              Mostrar solo activos vencidos o por vencer
            </label>

            {activosData && activosData.activos.length > 0 ? (
              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Listado de activos del hotel">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th>Activo</th>
                      <th>Ubicación</th>
                      <th>Última mantención</th>
                      <th>Próxima mantención</th>
                      <th>Estado preventivo</th>
                      <th>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activosData.activos.map((a) => (
                      <tr key={a.activo_id}>
                        <td><strong>{a.nombre}</strong> <small>{a.categoria}</small></td>
                        <td>{a.habitacion_id ? `Hab. ${a.habitacion_id}` : a.area}</td>
                        <td>{a.ultima_mantencion ? fechaATexto(a.ultima_mantencion) : '—'}</td>
                        <td>{a.proxima_mantencion ? fechaATexto(a.proxima_mantencion) : '—'}</td>
                        <td>{ETIQUETA_PREVENTIVO[a.estado_preventivo] || a.estado_preventivo}</td>
                        <td>
                          <button type="button" className="boton-secundario" onClick={() => setMantForm({ activo_id: a.activo_id, tipo: 'preventiva', descripcion: '', costo_clp: '0' })}>
                            Registrar mantención
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="estado">No hay activos registrados con este filtro.</p>
            )}

            {mantForm.activo_id && (
              <form className="formulario" onSubmit={registrarMantencion} style={{ marginTop: '1rem' }}>
                <h3>Registrar mantención en activo #{mantForm.activo_id}</h3>
                <CampoSelect etiqueta="Tipo" value={mantForm.tipo} onChange={(e) => setMantForm({ ...mantForm, tipo: e.target.value })}>
                  <option value="preventiva">Preventiva</option>
                  <option value="correctiva">Correctiva</option>
                </CampoSelect>
                <Campo etiqueta="Descripción del trabajo" value={mantForm.descripcion} onChange={(e) => setMantForm({ ...mantForm, descripcion: e.target.value })} required />
                <Campo etiqueta="Costo (CLP)" type="number" min="0" value={mantForm.costo_clp} onChange={(e) => setMantForm({ ...mantForm, costo_clp: e.target.value })} />
                <button type="submit" className="boton-primario">Guardar mantención</button>
              </form>
            )}
          </section>

          {esAdmin && (
            <section className="tarjeta" aria-label="Registrar activo del hotel">
              <h3>Registrar nuevo activo</h3>
              <form className="formulario" onSubmit={crearActivo}>
                <Campo etiqueta="Nombre del activo" value={nuevoActivo.nombre} onChange={(e) => setNuevoActivo({ ...nuevoActivo, nombre: e.target.value })} required />
                <Campo etiqueta="Categoría" value={nuevoActivo.categoria} onChange={(e) => setNuevoActivo({ ...nuevoActivo, categoria: e.target.value })} />
                <Campo etiqueta="Habitación (ej. HAB-10)" value={nuevoActivo.habitacion_id} onChange={(e) => setNuevoActivo({ ...nuevoActivo, habitacion_id: e.target.value })} />
                <Campo etiqueta="O área común (ej. Patio lavandería)" value={nuevoActivo.area} onChange={(e) => setNuevoActivo({ ...nuevoActivo, area: e.target.value })} />
                <Campo etiqueta="Frecuencia preventiva (días)" type="number" min="1" value={nuevoActivo.frecuencia_mantencion_dias} onChange={(e) => setNuevoActivo({ ...nuevoActivo, frecuencia_mantencion_dias: e.target.value })} />
                <Campo etiqueta="Notas" value={nuevoActivo.notas} onChange={(e) => setNuevoActivo({ ...nuevoActivo, notas: e.target.value })} />
                <button type="submit" className="boton-primario">Registrar activo</button>
              </form>
            </section>
          )}
        </>
      )}
    </MarcoHotel>
  )
}
