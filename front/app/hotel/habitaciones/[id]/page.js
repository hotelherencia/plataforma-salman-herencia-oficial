'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import {
  api,
  alRechazar,
  clp,
  mensajeDeError,
  MarcoHotel,
  SalidaJson,
  Campo,
  useClaveOperacion,
  useSesion,
} from '../../../../lib/api'
import { esAdminHotel, gestionaRecepcion } from '../../../../lib/roles'
import {
  ETIQUETA_GRAVEDAD,
  etiquetaPreparacion,
  progresoSubtareas,
} from '../../../../lib/operacion-corte1'
import { etiquetaOrigen, rangoNoches } from '../../../../lib/tipos'
import { fechaATexto, fechaHora, plural } from '../../../../lib/formato'

/**
 * Ficha de la habitación (spec-hotel-operacion-v1 §2.3–2.6). Muestra lo que
 * devuelve GET /hotel/habitaciones/{id}; las acciones de la administración
 * del hotel (editar tipo/capacidad, retirar o reincorporar) van a la API con
 * su propia clave de idempotencia. El precio NO se edita aquí (entrega 1A.2):
 * se muestra el de hoy, su origen y las excepciones que la alcanzan, con un
 * enlace al único mantenedor de precios (/hotel/tipos).
 */

const ETIQUETA_ESTADO = {
  confirmada: 'confirmada',
  en_estadia: 'en estadía',
  finalizada: 'finalizada',
  cancelada: 'cancelada',
}

export default function FichaHabitacion() {
  const { id } = useParams()
  const habitacionId = decodeURIComponent(id)
  const sesion = useSesion()
  const esAdmin = sesion.fase === 'ok' && esAdminHotel(sesion.usuario.rol)
  const puedeGestionar = sesion.fase === 'ok' && gestionaRecepcion(sesion.usuario.rol)
  const [ficha, setFicha] = useState(null)
  const [errorCarga, setErrorCarga] = useState('')
  const [edicion, setEdicion] = useState({ tipo: '', capacidad: '' })
  const [motivo, setMotivo] = useState('')
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [vigentes, setVigentes] = useState([])
  const [claveEdicion, renovarEdicion] = useClaveOperacion()
  const [claveServicio, renovarServicio] = useClaveOperacion()
  const [incForm, setIncForm] = useState({
    titulo: '',
    descripcion: '',
    gravedad: 'media',
    plazo: '',
    bloquea_disponibilidad: false,
    evidencia_base64: '',
    evidencia_nombre: '',
  })

  const cargar = useCallback(async () => {
    try {
      const r = await api(`/hotel/habitaciones/${encodeURIComponent(habitacionId)}`)
      if (r.estado >= 400) {
        setErrorCarga(r.estado === 403 ? 'No existe esa habitación o no tienes acceso a ella.' : mensajeDeError(r.datos, r.estado))
        return
      }
      setFicha(r.datos)
      setEdicion({ tipo: r.datos.tipo, capacidad: r.datos.capacidad })
    } catch {
      setErrorCarga('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }, [habitacionId])

  useEffect(() => {
    if (sesion.fase === 'ok') cargar()
  }, [sesion.fase, cargar])

  async function enviar(e, ruta, opciones, renovar) {
    e.preventDefault()
    setError('')
    setSalida(null)
    setVigentes([])
    try {
      const r = await api(ruta, opciones)
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovar)
        if (Array.isArray(r.datos.reservas_vigentes)) setVigentes(r.datos.reservas_vigentes)
      } else {
        setSalida(r.datos)
        renovar()
        cargar()
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  const guardarEdicion = (e) =>
    enviar(
      e,
      `/hotel/habitaciones/${encodeURIComponent(habitacionId)}`,
      { metodo: 'PUT', cuerpo: { tipo: edicion.tipo, capacidad: Number(edicion.capacidad) }, claveIdempotencia: claveEdicion },
      renovarEdicion
    )

  const cambiarServicio = (e, enServicio) =>
    enviar(
      e,
      `/hotel/habitaciones/${encodeURIComponent(habitacionId)}/servicio`,
      { metodo: 'POST', cuerpo: enServicio ? { en_servicio: true } : { en_servicio: false, motivo }, claveIdempotencia: claveServicio },
      () => {
        renovarServicio()
        setMotivo('')
      }
    )

  async function accionOperativa(ruta, cuerpo, metodo = 'POST') {
    setError('')
    try {
      const r = await api(ruta, { metodo, cuerpo, claveIdempotencia: `hab-${crypto.randomUUID().slice(0, 12)}` })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else await cargar()
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  const manejarFotoIncidencia = (e) => {
    const archivo = e.target.files?.[0]
    if (!archivo) return
    if (archivo.size > 5 * 1024 * 1024) {
      setError('La foto supera el límite de 5 MB.')
      return
    }
    const lector = new FileReader()
    lector.onload = () => setIncForm((f) => ({ ...f, evidencia_base64: String(lector.result || ''), evidencia_nombre: archivo.name }))
    lector.readAsDataURL(archivo)
  }

  const reportarIncidencia = async (e) => {
    e.preventDefault()
    await accionOperativa('/hotel/incidencias', {
      habitacion_id: habitacionId,
      area: 'habitacion',
      titulo: incForm.titulo.trim(),
      descripcion: incForm.descripcion.trim(),
      gravedad: incForm.gravedad,
      plazo: incForm.plazo || null,
      bloquea_disponibilidad: incForm.bloquea_disponibilidad,
      ...(incForm.evidencia_base64
        ? { evidencia_base64: incForm.evidencia_base64, evidencia_nombre: incForm.evidencia_nombre || 'foto.jpg' }
        : {}),
    })
    setIncForm({ titulo: '', descripcion: '', gravedad: 'media', plazo: '', bloquea_disponibilidad: false, evidencia_base64: '', evidencia_nombre: '' })
  }

  return (
    <MarcoHotel titulo={`Habitación ${habitacionId}`}>
      <p className="migas">
        <Link href="/hotel/habitaciones">← Inventario</Link> · <Link href="/hotel/ocupacion">Ocupación</Link>
      </p>
      {errorCarga && <p role="alert" className="alerta">{errorCarga}</p>}
      {ficha && (
        <>
          <section className="tarjeta" aria-label="Datos y estado">
            <h2>Datos y estado actual</h2>
            <dl className="ficha-datos">
              <dt>Tipo</dt>
              <dd>{ficha.tipo}</dd>
              <dt>Capacidad</dt>
              <dd>{plural(ficha.capacidad, 'persona')}</dd>
              <dt>Operación</dt>
              <dd>
                <span className={`reserva-estado estado-${ficha.estado_operativo}`}>{ficha.estado_operativo.replaceAll('_', ' ')}</span>
                {!ficha.en_servicio && (
                  <span className="ficha-motivo">
                    {' '}desde {ficha.fuera_de_servicio_desde?.slice(0, 10)} — motivo: {ficha.motivo_fuera_de_servicio}
                  </span>
                )}
              </dd>
              <dt>Preparación</dt>
              <dd>
                <span className={`reserva-estado preparacion-${ficha.estado_preparacion}`}>{etiquetaPreparacion(ficha.estado_preparacion)}</span>
                {ficha.estado_preparacion === 'sucia' && (
                  <>
                    {' '}
                    <button
                      type="button"
                      className="boton-secundario"
                      onClick={() => accionOperativa(`/hotel/habitaciones/${encodeURIComponent(habitacionId)}/limpieza/iniciar`, { aplicar_plantilla: true })}
                    >
                      Iniciar limpieza
                    </button>
                  </>
                )}
              </dd>
              <dt>Mantenimiento</dt>
              <dd>{ficha.mantenimiento ? 'abierto (fuera del cupo)' : 'no'}</dd>
              <dt>Precio hoy</dt>
              <dd>
                {ficha.tarifa_vigente_hoy_clp ? `${clp(ficha.tarifa_vigente_hoy_clp)}/noche (IVA incl.)` : 'sin precio hoy: no se ofrece'}
                {' '}<span className={`origen origen-${(ficha.origen_precio_hoy || 'ninguno').split(':')[0]}`}>
                  {etiquetaOrigen((ficha.origen_precio_hoy || '').split(':')[0] || null)}
                </span>
              </dd>
              <dt>Precio base del tipo</dt>
              <dd>{ficha.precio_base_tipo_clp ? clp(ficha.precio_base_tipo_clp) : 'sin precio base'}{ficha.tipo_nombre ? ` · ${ficha.tipo_nombre}` : ''}</dd>
              <dt>Precio propio</dt>
              <dd>{ficha.precio_propio_clp ? clp(ficha.precio_propio_clp) : 'no (hereda la base del tipo)'}</dd>
              <dt>Registrada</dt>
              <dd>{ficha.creado_en.slice(0, 10)}</dd>
            </dl>
          </section>

          {esAdmin && (
            <>
              <section className="tarjeta" aria-label="Editar datos">
                <h2>Editar datos</h2>
                <p className="nota-clave">
                  Se pueden cambiar tipo y capacidad aunque haya reservas: las reservas existentes no cambian (conservan
                  fechas, estado y precio aceptado). El identificador no se puede cambiar. La reserva no guarda la cantidad
                  de personas, así que bajar la capacidad no se valida contra reservas futuras.
                </p>
                <form className="formulario" onSubmit={guardarEdicion}>
                  <Campo etiqueta="Tipo" value={edicion.tipo} onChange={(e) => setEdicion({ ...edicion, tipo: e.target.value })} />
                  <Campo etiqueta="Capacidad" type="number" min="1" max="30" value={edicion.capacidad} onChange={(e) => setEdicion({ ...edicion, capacidad: e.target.value })} />
                  <button type="submit" className="boton-primario">Guardar cambios</button>
                </form>
                <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveEdicion}</code></span>
              </section>

              <section className="tarjeta" aria-label="Servicio">
                <h2>{ficha.en_servicio ? 'Retirar de operación' : 'Reincorporar a la operación'}</h2>
                {ficha.en_servicio ? (
                  <>
                    <p className="nota-chica">
                      Baja lógica: la habitación queda fuera de servicio y deja de ofrecerse, pero su historial de reservas,
                      cargos y pagos se preserva.
                    </p>
                    <form className="formulario" onSubmit={(e) => cambiarServicio(e, false)}>
                      <Campo etiqueta="Motivo" value={motivo} placeholder="p. ej. remodelación del baño" onChange={(e) => setMotivo(e.target.value)} />
                      <button type="submit" className="boton-secundario">Retirar de operación</button>
                    </form>
                  </>
                ) : (
                  <form className="formulario" onSubmit={(e) => cambiarServicio(e, true)}>
                    <button type="submit" className="boton-primario">Reincorporar a la operación</button>
                  </form>
                )}
                <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveServicio}</code></span>
              </section>
            </>
          )}

          {error && (
            <div role="alert" className="alerta">
              {error}
              {vigentes.length > 0 && (
                <>
                  {' '}Reservas vigentes:{' '}
                  {vigentes.map((rid) => (
                    <Link key={rid} href={`/hotel/reservas/${rid}`} className="enlace-reserva">
                      {rid}
                    </Link>
                  ))}
                </>
              )}
            </div>
          )}
          <button onClick={() => { setSalida(null); setError(''); setVigentes([]); renovarEdicion(); renovarServicio() }} className="boton-secundario">Nueva operación</button>
          <SalidaJson datos={salida} />

          <section className="tarjeta" aria-label="Precio y excepciones por fecha">
            <h2>Precio y excepciones por fecha</h2>
            <p className="nota-clave">
              El precio de esta habitación se define en{' '}
              <Link href="/hotel/tipos">Tipos, habitaciones y precios</Link>: precio base del tipo, precio propio opcional y
              excepciones por fecha (temporadas, feriados o cierres). Las reservas confirmadas conservan su precio.
            </p>
            {ficha.excepciones.length === 0 ? (
              <p className="estado">Sin excepciones vigentes ni futuras: rige {ficha.precio_propio_clp ? 'su precio propio' : 'el precio base del tipo'}.</p>
            ) : (
              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)"><table className="tabla">
                <thead>
                  <tr>
                    <th>Noches</th>
                    <th>Aplica a</th>
                    <th>Por noche</th>
                    <th>Motivo</th>
                    <th>Hoy</th>
                  </tr>
                </thead>
                <tbody>
                  {ficha.excepciones.map((e) => (
                    <tr key={e.excepcion_id}>
                      <td>{rangoNoches(e.fecha_desde, e.fecha_hasta)}</td>
                      <td>{e.alcance === 'tipo' ? 'todo el tipo' : 'esta habitación'}</td>
                      <td>{e.precio_clp ? clp(e.precio_clp) : 'sin venta'}</td>
                      <td>{e.motivo || '—'}</td>
                      <td>{e.aplicada_hoy ? 'aplica hoy' : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            )}
            {ficha.tarifas_archivadas.length > 0 && (
              <details className="json-detalle">
                <summary>Tarifas antiguas archivadas ({ficha.tarifas_archivadas.length}, solo consulta)</summary>
                <p className="nota-chica">
                  Registradas con el editor anterior. La migración 0022 las convirtió en precio base, precio propio o
                  excepciones con los mismos montos y ya no se aplican.
                </p>
                <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)"><table className="tabla">
                  <thead>
                    <tr><th>Desde</th><th>Hasta (sin incluir)</th><th>Por noche</th><th>Registrada</th><th>Archivada</th></tr>
                  </thead>
                  <tbody>
                    {ficha.tarifas_archivadas.map((t) => (
                      <tr key={t.tarifa_id}>
                        <td className="celda-fecha">{fechaATexto(t.fecha_desde) || t.fecha_desde}</td>
                        <td className="celda-fecha">{fechaATexto(t.fecha_hasta) || t.fecha_hasta}</td>
                        <td>{clp(t.tarifa_noche_clp)}</td>
                        <td>{t.registrada_en.slice(0, 10)}</td>
                        <td>{t.archivada_en ? t.archivada_en.slice(0, 10) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              </details>
            )}
          </section>

          <section className="tarjeta" aria-label="Reservas de la habitación">
            <h2>Reservas de la habitación</h2>
            {ficha.reservas.length === 0 ? (
              <p className="estado estado-vacio">Sin reservas.</p>
            ) : (
              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)"><table className="tabla">
                <thead>
                  <tr>
                    <th>Reserva</th>
                    <th>Huésped</th>
                    <th>Fechas</th>
                    <th>Noches</th>
                    <th>Estado</th>
                    <th>Precio aceptado</th>
                  </tr>
                </thead>
                <tbody>
                  {ficha.reservas.map((r) => (
                    <tr key={r.reserva_id}>
                      <td>
                        <Link href={`/hotel/reservas/${r.reserva_id}`}>{r.reserva_id}</Link>
                      </td>
                      <td>{r.huesped_nombre}</td>
                      <td className="celda-fecha">{fechaATexto(r.inicio)} → {fechaATexto(r.fin)}</td>
                      <td>{r.noches}</td>
                      <td>
                        <span className={`reserva-estado estado-${r.estado}`}>{ETIQUETA_ESTADO[r.estado] || r.estado}</span>
                      </td>
                      <td>{clp(r.tarifa_noche_aceptada_clp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            )}
          </section>

          <section className="tarjeta" aria-label="Incidencias de la habitación">
            <h2>Incidencias de la habitación</h2>
            {Array.isArray(ficha.incidencias) && ficha.incidencias.length > 0 ? (
              <ul className="lista-aseo">
                {ficha.incidencias.map((inc) => (
                  <li key={inc.incidencia_id} className={`tarjeta tarjeta-aseo${inc.estado === 'abierta' || inc.estado === 'en_progreso' ? ' pendiente' : ''}`}>
                    <div className="aseo-cabecera">
                      <strong>{inc.titulo}</strong>
                      <span className="reserva-estado">Gravedad: {ETIQUETA_GRAVEDAD[inc.gravedad] || inc.gravedad}</span>
                      <span className="reserva-estado">{inc.estado.replace('_', ' ')}</span>
                      {inc.bloquea_disponibilidad && <span className="badge-bloquea">Bloquea disponibilidad</span>}
                    </div>
                    <p>{inc.descripcion}</p>
                    <div className="acciones-aseo">
                      {inc.tiene_evidencia && (
                        <a className="boton-fantasma" href={`/api/hotel/incidencias/${inc.incidencia_id}/evidencia`} target="_blank" rel="noopener noreferrer">
                          Ver foto evidencia
                        </a>
                      )}
                      {puedeGestionar && (inc.estado === 'abierta' || inc.estado === 'en_progreso') && (
                        <button
                          type="button"
                          className="boton-secundario"
                          onClick={() => accionOperativa(`/hotel/incidencias/${inc.incidencia_id}/cierre`, { estado_final: 'cerrada', resolucion: 'Cerrada desde ficha de habitación' })}
                        >
                          Cerrar incidencia
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="estado estado-vacio">Sin incidencias registradas.</p>
            )}
            <form className="formulario-incidencia-rapida" onSubmit={reportarIncidencia}>
              <h3>Reportar incidencia rápida</h3>
              <input
                className="entrada"
                required
                minLength={3}
                maxLength={160}
                placeholder="Título del desperfecto"
                value={incForm.titulo}
                onChange={(e) => setIncForm((f) => ({ ...f, titulo: e.target.value }))}
              />
              <textarea
                className="entrada"
                required
                minLength={3}
                rows={2}
                placeholder="Descripción breve"
                value={incForm.descripcion}
                onChange={(e) => setIncForm((f) => ({ ...f, descripcion: e.target.value }))}
              />
              <div className="acciones-aseo">
                <select className="entrada" value={incForm.gravedad} onChange={(e) => setIncForm((f) => ({ ...f, gravedad: e.target.value }))}>
                  {Object.entries(ETIQUETA_GRAVEDAD).map(([k, v]) => <option key={k} value={k}>Gravedad: {v}</option>)}
                </select>
                <Campo
                  etiqueta="Plazo"
                  type="date"
                  value={incForm.plazo}
                  onChange={(e) => setIncForm((f) => ({ ...f, plazo: e.target.value }))}
                />
                <label className="campo-check">
                  <input type="checkbox" checked={incForm.bloquea_disponibilidad} onChange={(e) => setIncForm((f) => ({ ...f, bloquea_disponibilidad: e.target.checked }))} />
                  Bloquea disponibilidad
                </label>
              </div>
              <label className="campo-archivo">
                <span>Evidencia móvil (JPG/PNG/WebP):</span>
                <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={manejarFotoIncidencia} />
              </label>
              <button type="submit" className="boton-primario">Registrar incidencia</button>
            </form>
          </section>

          <section className="tarjeta" aria-label="Tareas">
            <h2>Tareas y checklists</h2>
            {ficha.tareas.length === 0 ? (
              <p className="estado estado-vacio">Sin tareas registradas.</p>
            ) : (
              <ul className="lista-aseo">
                {ficha.tareas.map((t) => {
                  const prog = progresoSubtareas(t.subtareas)
                  const abierta = t.estado === 'pendiente' || t.estado === 'en_proceso'
                  return (
                    <li key={t.tarea_id} className={`tarjeta tarjeta-aseo${abierta ? ' pendiente' : ''}`}>
                      <div className="aseo-cabecera">
                        <strong>{t.titulo || t.tipo}</strong>
                        <span className="reserva-estado">{t.estado.replace('_', ' ')}</span>
                        <span className="nota-clave">Creada: {t.creada_en.slice(0, 16).replace('T', ' ')}</span>
                        {t.completada_en && <span className="nota-clave">Completada: {t.completada_en.slice(0, 16).replace('T', ' ')}</span>}
                      </div>
                      {Array.isArray(t.subtareas) && t.subtareas.length > 0 && (
                        <ul className="checklist-subtareas">
                          {t.subtareas.map((sub) => (
                            <li key={sub.subtarea_id}>
                              <label className={`subtarea-item${sub.completada ? ' completada' : ''}`}>
                                <input
                                  type="checkbox"
                                  disabled={!abierta}
                                  checked={Boolean(sub.completada)}
                                  onChange={() => accionOperativa(`/hotel/tareas/${t.tarea_id}/subtareas/${sub.subtarea_id}`, { completada: !sub.completada })}
                                />
                                <span>{sub.descripcion}{sub.obligatoria && <em className="subtarea-req"> *</em>}</span>
                              </label>
                            </li>
                          ))}
                        </ul>
                      )}
                      {abierta && (
                        <div className="acciones-aseo">
                          <button
                            type="button"
                            className="boton-primario"
                            disabled={!prog.puedeCerrar}
                            onClick={() => accionOperativa(`/hotel/tareas/${t.tarea_id}`, { estado: 'completada' }, 'PUT')}
                          >
                            Completar tarea
                          </button>
                        </div>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </section>

          {Array.isArray(ficha.auditoria) && (
            <section className="tarjeta" aria-label="Auditoría">
              <h2>Historial de cambios (auditoría)</h2>
              {ficha.auditoria.length === 0 ? (
                <p className="estado estado-vacio">Sin cambios registrados.</p>
              ) : (
                <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)"><table className="tabla">
                  <thead>
                    <tr>
                      <th>Cuándo</th>
                      <th>Quién</th>
                      <th>Acción</th>
                      <th>Resultado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ficha.auditoria.map((a, i) => (
                      <tr key={`${a.registrada_en}-${i}`}>
                        <td className="celda-fecha">{fechaHora(a.registrada_en)}</td>
                        <td>{a.actor}</td>
                        <td>{a.accion}</td>
                        <td>{a.resultado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table></div>
              )}
            </section>
          )}
        </>
      )}
    </MarcoHotel>
  )
}
