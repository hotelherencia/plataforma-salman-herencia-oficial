'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { api, Campo, mensajeDeError, MarcoHotel, useSesion } from '../../../lib/api'
import { plural } from '../../../lib/formato'
import { esAdminHotel, gestionaRecepcion } from '../../../lib/roles'
import {
  ETIQUETA_AREA,
  ETIQUETA_GRAVEDAD,
  ETIQUETA_PRIORIDAD,
  ETIQUETA_TIPO_TAREA,
  etiquetaPreparacion,
  progresoSubtareas,
} from '../../../lib/operacion-corte1'
import { nombreTipo } from '../../reservar/continuidad'

const SITUACION = {
  ocupada: 'Ocupada',
  sale_hoy: 'Sale hoy',
  llega_hoy: 'Llega hoy',
  libre: 'Libre',
}

function clave(prefijo) {
  return `${prefijo}-${crypto.randomUUID().slice(0, 12)}`
}

function leerArchivoBase64(archivo) {
  return new Promise((resolve, reject) => {
    const lector = new FileReader()
    lector.onload = () => resolve(String(lector.result || ''))
    lector.onerror = () => reject(new Error('No se pudo leer la imagen.'))
    lector.readAsDataURL(archivo)
  })
}

/**
 * Aseo y operación diaria (#362, #363, #415, #416):
 * - Habitaciones: estado «En limpieza», checklist interactivo de subtareas, confirmación y verificación.
 * - Tareas y checklists: baños, lavandería, desayunos, mantención y áreas comunes.
 * - Incidencias: reporte rápido desde móvil con evidencia fotográfica y bloqueo automático de disponibilidad.
 * Sin ítems nuevos en el menú lateral.
 */
export default function Aseo() {
  const sesion = useSesion()
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const verifica = esAdminHotel(rol)
  const anota = gestionaRecepcion(rol)
  const [pestana, setPestana] = useState('habitaciones')
  const [datos, setDatos] = useState(null)
  const [tareasData, setTareasData] = useState(null)
  const [incidenciasData, setIncidenciasData] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [notas, setNotas] = useState({})
  const [soloPendientes, setSoloPendientes] = useState(false)
  const [reporteHab, setReporteHab] = useState(null)
  const [incForm, setIncForm] = useState({
    habitacion_id: '',
    area: 'habitacion',
    titulo: '',
    descripcion: '',
    gravedad: 'media',
    responsable: '',
    plazo: '',
    bloquea_disponibilidad: false,
    evidencia_base64: '',
    evidencia_nombre: '',
  })
  const [tareaForm, setTareaForm] = useState({
    tipo: 'banos',
    titulo: '',
    habitacion_id: '',
    area: 'banos',
    prioridad: 'media',
    responsable: '',
    vence_en: '',
    observacion: '',
    aplicar_plantilla: true,
  })
  const [nuevaSub, setNuevaSub] = useState({})

  const cargar = useCallback(async () => {
    try {
      const [rAseo, rTareas, rInc] = await Promise.all([
        api('/hotel/aseo'),
        api('/hotel/tareas?solo_abiertas=false'),
        api('/hotel/incidencias'),
      ])
      if (rAseo.estado === 200) setDatos(rAseo.datos)
      else setError(mensajeDeError(rAseo.datos, rAseo.estado))
      if (rTareas.estado === 200) setTareasData(rTareas.datos)
      if (rInc.estado === 200) setIncidenciasData(rInc.datos)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }, [])

  useEffect(() => {
    if (sesion.fase === 'ok') cargar()
  }, [sesion.fase, cargar])

  async function enviar(ruta, cuerpo, ok, metodo = 'POST') {
    setError('')
    setAviso('')
    try {
      const r = await api(ruta, { metodo, claveIdempotencia: clave('oper'), cuerpo })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        return false
      }
      setAviso(ok)
      await cargar()
      return true
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
      return false
    }
  }

  const iniciarLimpieza = (h) =>
    enviar(
      `/hotel/habitaciones/${h.habitacion_id}/limpieza/iniciar`,
      { aplicar_plantilla: true },
      `${h.habitacion_id} marcada «En limpieza» con checklist activo.`,
    )

  const limpiar = (h) =>
    enviar(`/hotel/habitaciones/${h.habitacion_id}/limpieza`, {}, `${h.habitacion_id} marcada como limpia.`)

  const alternarSubtarea = (tareaId, sub) =>
    enviar(
      `/hotel/tareas/${tareaId}/subtareas/${sub.subtarea_id}`,
      { completada: !sub.completada },
      sub.completada ? 'Subtarea desmarcada.' : 'Subtarea completada.',
    )

  const agregarSubtarea = async (tareaId) => {
    const desc = (nuevaSub[tareaId] || '').trim()
    if (desc.length < 2) {
      setError('Escribe al menos 2 caracteres para la subtarea.')
      return
    }
    const ok = await enviar(
      `/hotel/tareas/${tareaId}/subtareas`,
      { descripcion: desc, obligatoria: true },
      'Subtarea agregada al checklist.',
    )
    if (ok) setNuevaSub((prev) => ({ ...prev, [tareaId]: '' }))
  }

  const atender = (h, o) =>
    enviar(`/hotel/habitaciones/${h.habitacion_id}/observaciones/${o.observacion_id}/atendida`, {}, 'Observación atendida.')

  const verificar = (h, aprobada) => {
    const nota = (notas[h.habitacion_id] || '').trim()
    if (!aprobada && !nota) {
      setError('Para rechazar la limpieza escribe la observación para aseo.')
      return
    }
    enviar(
      `/hotel/limpiezas/${h.ultima_limpieza.tarea_id}/verificacion`,
      { aprobada, observacion: nota || null },
      aprobada ? `Limpieza de ${h.habitacion_id} verificada.` : `Limpieza de ${h.habitacion_id} rechazada: vuelve a aseo.`,
    ).then((ok) => ok && setNotas((n) => ({ ...n, [h.habitacion_id]: '' })))
  }

  const anotar = (h) => {
    const nota = (notas[h.habitacion_id] || '').trim()
    if (nota.length < 2) {
      setError('Escribe la observación (mínimo 2 caracteres).')
      return
    }
    enviar(`/hotel/habitaciones/${h.habitacion_id}/observaciones`, { texto: nota }, `Observación agregada a ${h.habitacion_id}.`)
      .then((ok) => ok && setNotas((n) => ({ ...n, [h.habitacion_id]: '' })))
  }

  const abrirReporteRapido = (habitacionId) => {
    setReporteHab(habitacionId)
    setIncForm({
      habitacion_id: habitacionId || '',
      area: habitacionId ? 'habitacion' : 'pasillo',
      titulo: '',
      descripcion: '',
      gravedad: 'media',
      responsable: '',
      plazo: '',
      bloquea_disponibilidad: false,
      evidencia_base64: '',
      evidencia_nombre: '',
    })
  }

  const manejarFoto = async (e) => {
    const archivo = e.target.files?.[0]
    if (!archivo) return
    if (archivo.size > 5 * 1024 * 1024) {
      setError('La foto supera el límite de 5 MB.')
      return
    }
    try {
      const b64 = await leerArchivoBase64(archivo)
      setIncForm((f) => ({ ...f, evidencia_base64: b64, evidencia_nombre: archivo.name }))
    } catch {
      setError('No se pudo leer la foto seleccionada.')
    }
  }

  const enviarIncidencia = async (e) => {
    e.preventDefault()
    const cuerpo = {
      titulo: incForm.titulo.trim(),
      descripcion: incForm.descripcion.trim(),
      habitacion_id: incForm.habitacion_id || null,
      area: incForm.habitacion_id ? 'habitacion' : incForm.area,
      gravedad: incForm.gravedad,
      responsable: incForm.responsable.trim() || null,
      plazo: incForm.plazo || null,
      bloquea_disponibilidad: Boolean(incForm.habitacion_id && incForm.bloquea_disponibilidad),
      ...(incForm.evidencia_base64
        ? { evidencia_base64: incForm.evidencia_base64, evidencia_nombre: incForm.evidencia_nombre || 'foto.jpg' }
        : {}),
    }
    const ok = await enviar('/hotel/incidencias', cuerpo, 'Incidencia registrada.')
    if (ok) {
      setReporteHab(null)
      setIncForm({
        habitacion_id: '',
        area: 'pasillo',
        titulo: '',
        descripcion: '',
        gravedad: 'media',
        responsable: '',
        plazo: '',
        bloquea_disponibilidad: false,
        evidencia_base64: '',
        evidencia_nombre: '',
      })
    }
  }

  const cerrarIncidencia = (inc) =>
    enviar(
      `/hotel/incidencias/${inc.incidencia_id}/cierre`,
      { estado_final: 'cerrada', resolucion: 'Cerrada desde operación diaria' },
      `Incidencia ${inc.incidencia_id} cerrada.`,
    )

  const crearTarea = async (e) => {
    e.preventDefault()
    const cuerpo = {
      tipo: tareaForm.tipo,
      titulo: tareaForm.titulo.trim(),
      habitacion_id: tareaForm.habitacion_id || null,
      area: tareaForm.habitacion_id ? 'habitacion' : tareaForm.area,
      prioridad: tareaForm.prioridad,
      responsable: tareaForm.responsable.trim() || null,
      vence_en: tareaForm.vence_en ? new Date(tareaForm.vence_en).toISOString() : null,
      observacion: tareaForm.observacion.trim() || null,
      aplicar_plantilla: tareaForm.aplicar_plantilla,
    }
    const ok = await enviar('/hotel/tareas', cuerpo, 'Tarea operativa creada.')
    if (ok) {
      setTareaForm((t) => ({ ...t, titulo: '', observacion: '', vence_en: '' }))
    }
  }

  const cambiarEstadoTarea = (t, estado) =>
    enviar(`/hotel/tareas/${t.tarea_id}`, { estado }, `Tarea actualizada a ${estado.replace('_', ' ')}.`, 'PUT')

  const lista = (datos?.habitaciones || []).filter((h) => !soloPendientes || h.limpieza_pendiente || h.observaciones.length || (h.incidencias_abiertas || []).length > 0)
  const abiertasInc = incidenciasData?.abiertas || 0
  const abiertasTareas = tareasData?.abiertas || 0

  return (
    <MarcoHotel titulo="Aseo y operación">
      <nav className="pestanas-aseo" aria-label="Vistas operativas">
        <button type="button" className={pestana === 'habitaciones' ? 'boton-primario' : 'boton-secundario'} onClick={() => setPestana('habitaciones')}>
          Habitaciones {datos ? `(${datos.pendientes})` : ''}
        </button>
        <button type="button" className={pestana === 'tareas' ? 'boton-primario' : 'boton-secundario'} onClick={() => setPestana('tareas')}>
          Tareas y checklists ({abiertasTareas})
        </button>
        <button type="button" className={pestana === 'incidencias' ? 'boton-primario' : 'boton-secundario'} onClick={() => setPestana('incidencias')}>
          Incidencias ({abiertasInc})
        </button>
      </nav>

      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      {!datos && !error && <p className="estado" role="status" aria-busy="true">Cargando…</p>}

      {pestana === 'habitaciones' && datos && (
        <>
          <section className="tarjeta">
            <h2>Habitaciones por limpiar ({datos.pendientes})</h2>
            <p className="nota-clave">
              Pulsa «Iniciar limpieza» para pasar a «En limpieza» con checklist móvil, marca las subtareas obligatorias y luego «Marcar limpia».
              {verifica && ' Como administración, verifica cada limpieza o recházala con una observación.'}
            </p>
            <label className="campo-check">
              <input type="checkbox" checked={soloPendientes} onChange={(e) => setSoloPendientes(e.target.checked)} />
              Solo pendientes, con observaciones o incidencias
            </label>
            {verifica && datos?.por_verificar?.length > 0 && (
              <p className="estado" role="status">Por verificar: {datos.por_verificar.join(', ')}</p>
            )}
          </section>

          <ul className="lista-aseo">
            {lista.map((h) => {
              const ultima = h.ultima_limpieza
              const porVerificar = ultima && !ultima.verificacion
              const prog = progresoSubtareas(h.subtareas)
              return (
                <li key={h.habitacion_id} className={`tarjeta tarjeta-aseo${h.limpieza_pendiente ? ' pendiente' : ''}`} data-habitacion={h.habitacion_id}>
                  <div className="aseo-cabecera">
                    <strong>
                      <Link href={`/hotel/habitaciones/${h.habitacion_id}`}>{h.habitacion_id}</Link>
                    </strong>
                    <span>{nombreTipo(h.tipo)}</span>
                    <span className="reserva-estado">{SITUACION[h.situacion] || h.situacion}</span>
                    <span className={`reserva-estado preparacion-${h.estado_preparacion}`}>
                      {etiquetaPreparacion(h.estado_preparacion)}
                    </span>
                    {h.mantenimiento_hoy && <span className="reserva-estado estado-cancelada">mantenimiento</span>}
                    {(h.incidencias_abiertas || []).length > 0 && (
                      <span className="badge-bloquea">
                        {plural(h.incidencias_abiertas.length, 'incidencia', 'incidencias')}
                      </span>
                    )}
                  </div>

                  {h.subtareas && h.subtareas.length > 0 && (
                    <div className="checklist-bloque">
                      <p className="nota-clave">
                        Checklist: {prog.completadas}/{prog.total}
                        {prog.obligatoriasPendientes > 0
                          ? ` · faltan ${plural(prog.obligatoriasPendientes, 'obligatoria', 'obligatorias')}`
                          : ' · listo para cerrar'}
                      </p>
                      <ul className="checklist-subtareas">
                        {h.subtareas.map((sub) => (
                          <li key={sub.subtarea_id}>
                            <label className={`subtarea-item${sub.completada ? ' completada' : ''}`}>
                              <input
                                type="checkbox"
                                checked={Boolean(sub.completada)}
                                onChange={() => alternarSubtarea(h.tarea_limpieza_id, sub)}
                              />
                              <span>
                                {sub.descripcion}
                                {sub.obligatoria && <em className="subtarea-req"> *</em>}
                              </span>
                            </label>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {h.observaciones.length > 0 && (
                    <ul className="lista-simple">
                      {h.observaciones.map((o) => (
                        <li key={o.observacion_id}>
                          <em>{o.texto}</em> ({o.autor}){' '}
                          <button type="button" className="boton-fantasma" onClick={() => atender(h, o)}>Atendida</button>
                        </li>
                      ))}
                    </ul>
                  )}

                  {ultima && (
                    <p className="nota-clave">
                      Última limpieza: {ultima.completada_en ? ultima.completada_en.slice(0, 16).replace('T', ' ') : '—'}
                      {ultima.completada_por ? ` por ${ultima.completada_por}` : ''}
                      {ultima.verificacion ? ` · ${ultima.verificacion}${ultima.verificada_por ? ` por ${ultima.verificada_por}` : ''}` : ' · sin verificar'}
                    </p>
                  )}

                  <div className="acciones-aseo">
                    {h.limpieza_pendiente && !h.limpieza_en_curso && (
                      <button type="button" className="boton-secundario" onClick={() => iniciarLimpieza(h)}>
                        Iniciar limpieza
                      </button>
                    )}
                    {h.limpieza_pendiente && (
                      <button
                        type="button"
                        className="boton-primario"
                        disabled={!prog.puedeCerrar}
                        title={prog.puedeCerrar ? 'Marcar habitación como limpia' : 'Completa primero las subtareas obligatorias'}
                        onClick={() => limpiar(h)}
                      >
                        Limpia
                      </button>
                    )}
                    <button
                      type="button"
                      className="boton-fantasma"
                      onClick={() => abrirReporteRapido(reporteHab === h.habitacion_id ? null : h.habitacion_id)}
                    >
                      Reportar incidencia
                    </button>
                    {anota && (
                      <input
                        className="entrada"
                        aria-label={`Observación para ${h.habitacion_id}`}
                        placeholder="Observación para aseo"
                        value={notas[h.habitacion_id] || ''}
                        onChange={(e) => setNotas((n) => ({ ...n, [h.habitacion_id]: e.target.value }))}
                      />
                    )}
                    {anota && <button type="button" className="boton-secundario" onClick={() => anotar(h)}>Anotar</button>}
                    {verifica && porVerificar && (
                      <>
                        <button type="button" className="boton-secundario" onClick={() => verificar(h, true)}>Verificar</button>
                        <button type="button" className="boton-fantasma" onClick={() => verificar(h, false)}>Rechazar</button>
                      </>
                    )}
                  </div>

                  {reporteHab === h.habitacion_id && (
                    <form className="formulario-incidencia-rapida" onSubmit={enviarIncidencia}>
                      <h4>Reportar incidencia en {h.habitacion_id}</h4>
                      <input
                        className="entrada"
                        required
                        minLength={3}
                        maxLength={160}
                        placeholder="Ej.: Fuga en llave de lavamanos"
                        value={incForm.titulo}
                        onChange={(e) => setIncForm((f) => ({ ...f, titulo: e.target.value }))}
                      />
                      <textarea
                        className="entrada"
                        required
                        minLength={3}
                        rows={2}
                        placeholder="Describe el desperfecto o requerimiento"
                        value={incForm.descripcion}
                        onChange={(e) => setIncForm((f) => ({ ...f, descripcion: e.target.value }))}
                      />
                      <div className="acciones-aseo">
                        <select
                          className="entrada"
                          value={incForm.gravedad}
                          onChange={(e) => setIncForm((f) => ({ ...f, gravedad: e.target.value }))}
                        >
                          {Object.entries(ETIQUETA_GRAVEDAD).map(([k, v]) => (
                            <option key={k} value={k}>Gravedad: {v}</option>
                          ))}
                        </select>
                        <label className="campo-check">
                          <input
                            type="checkbox"
                            checked={incForm.bloquea_disponibilidad}
                            onChange={(e) => setIncForm((f) => ({ ...f, bloquea_disponibilidad: e.target.checked }))}
                          />
                          Bloquea disponibilidad
                        </label>
                      </div>
                      <label className="campo-archivo">
                        <span>Foto desde móvil (opcional, JPG/PNG/WebP):</span>
                        <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={manejarFoto} />
                      </label>
                      <div className="acciones-aseo">
                        <button type="submit" className="boton-primario">Guardar incidencia</button>
                        <button type="button" className="boton-fantasma" onClick={() => setReporteHab(null)}>Cancelar</button>
                      </div>
                    </form>
                  )}
                </li>
              )
            })}
          </ul>
        </>
      )}

      {pestana === 'tareas' && (
        <>
          <section className="tarjeta">
            <h2>Nueva tarea operativa o checklist</h2>
            <form className="formulario" onSubmit={crearTarea}>
              <label className="campo">
                <span>Tipo</span>
                <select className="entrada" value={tareaForm.tipo} onChange={(e) => setTareaForm((f) => ({ ...f, tipo: e.target.value, area: e.target.value }))}>
                  {Object.entries(ETIQUETA_TIPO_TAREA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              <label className="campo">
                <span>Título</span>
                <input className="entrada" required minLength={3} maxLength={160} placeholder="Ej.: Revisión baños primer piso" value={tareaForm.titulo} onChange={(e) => setTareaForm((f) => ({ ...f, titulo: e.target.value }))} />
              </label>
              <label className="campo">
                <span>Habitación (opcional)</span>
                <select className="entrada" value={tareaForm.habitacion_id} onChange={(e) => setTareaForm((f) => ({ ...f, habitacion_id: e.target.value }))}>
                  <option value="">Área común</option>
                  {(datos?.habitaciones || []).map((h) => <option key={h.habitacion_id} value={h.habitacion_id}>{h.habitacion_id}</option>)}
                </select>
              </label>
              <label className="campo">
                <span>Prioridad</span>
                <select className="entrada" value={tareaForm.prioridad} onChange={(e) => setTareaForm((f) => ({ ...f, prioridad: e.target.value }))}>
                  {Object.entries(ETIQUETA_PRIORIDAD).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              <label className="campo">
                <span>Responsable</span>
                <input className="entrada" maxLength={100} placeholder="Opcional" value={tareaForm.responsable} onChange={(e) => setTareaForm((f) => ({ ...f, responsable: e.target.value }))} />
              </label>
              <label className="campo">
                <span>Vencimiento</span>
                <input className="entrada" type="datetime-local" value={tareaForm.vence_en} onChange={(e) => setTareaForm((f) => ({ ...f, vence_en: e.target.value }))} />
              </label>
              <label className="campo-check">
                <input type="checkbox" checked={tareaForm.aplicar_plantilla} onChange={(e) => setTareaForm((f) => ({ ...f, aplicar_plantilla: e.target.checked }))} />
                Cargar checklist base del tipo
              </label>
              <button type="submit" className="boton-primario">Crear tarea</button>
            </form>
          </section>

          <ul className="lista-aseo">
            {(tareasData?.tareas || []).map((t) => {
              const prog = progresoSubtareas(t.subtareas)
              const abierta = t.estado === 'pendiente' || t.estado === 'en_proceso'
              return (
                <li key={t.tarea_id} className={`tarjeta tarjeta-aseo${abierta ? ' pendiente' : ''}`}>
                  <div className="aseo-cabecera">
                    <strong>{t.titulo}</strong>
                    <span className="reserva-estado">{ETIQUETA_TIPO_TAREA[t.tipo] || t.tipo}</span>
                    <span className="reserva-estado">{t.habitacion_id || t.area}</span>
                    <span className="reserva-estado">Prioridad: {ETIQUETA_PRIORIDAD[t.prioridad] || t.prioridad}</span>
                    <span className="reserva-estado">{t.estado.replace('_', ' ')}</span>
                  </div>
                  <p className="nota-clave">
                    {t.responsable ? `Responsable: ${t.responsable} · ` : ''}
                    {t.vence_en ? `Vence: ${t.vence_en.slice(0, 16).replace('T', ' ')} · ` : ''}
                    Checklist: {prog.completadas}/{prog.total}
                    {prog.obligatoriasPendientes > 0
                      ? ` (${plural(prog.obligatoriasPendientes, 'obligatoria pendiente', 'obligatorias pendientes')})`
                      : ''}
                  </p>
                  {t.subtareas.length > 0 && (
                    <ul className="checklist-subtareas">
                      {t.subtareas.map((sub) => (
                        <li key={sub.subtarea_id}>
                          <label className={`subtarea-item${sub.completada ? ' completada' : ''}`}>
                            <input
                              type="checkbox"
                              disabled={!abierta}
                              checked={Boolean(sub.completada)}
                              onChange={() => alternarSubtarea(t.tarea_id, sub)}
                            />
                            <span>{sub.descripcion}{sub.obligatoria && <em className="subtarea-req"> *</em>}</span>
                          </label>
                        </li>
                      ))}
                    </ul>
                  )}
                  {abierta && (
                    <div className="acciones-aseo">
                      {t.estado === 'pendiente' && (
                        <button type="button" className="boton-secundario" onClick={() => cambiarEstadoTarea(t, 'en_proceso')}>
                          Iniciar
                        </button>
                      )}
                      <button
                        type="button"
                        className="boton-primario"
                        disabled={!prog.puedeCerrar}
                        onClick={() => cambiarEstadoTarea(t, 'completada')}
                      >
                        Completar
                      </button>
                      <input
                        className="entrada"
                        placeholder="Agregar subtarea obligatoria"
                        value={nuevaSub[t.tarea_id] || ''}
                        onChange={(e) => setNuevaSub((prev) => ({ ...prev, [t.tarea_id]: e.target.value }))}
                      />
                      <button type="button" className="boton-fantasma" onClick={() => agregarSubtarea(t.tarea_id)}>
                        + Subtarea
                      </button>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </>
      )}

      {pestana === 'incidencias' && (
        <>
          <section className="tarjeta">
            <h2>Reportar incidencia (habitación o área común)</h2>
            <form className="formulario" onSubmit={enviarIncidencia}>
              <label className="campo">
                <span>Habitación (opcional)</span>
                <select className="entrada" value={incForm.habitacion_id} onChange={(e) => setIncForm((f) => ({ ...f, habitacion_id: e.target.value, area: e.target.value ? 'habitacion' : f.area }))}>
                  <option value="">Área común</option>
                  {(datos?.habitaciones || []).map((h) => <option key={h.habitacion_id} value={h.habitacion_id}>{h.habitacion_id}</option>)}
                </select>
              </label>
              {!incForm.habitacion_id && (
                <label className="campo">
                  <span>Área</span>
                  <select className="entrada" value={incForm.area} onChange={(e) => setIncForm((f) => ({ ...f, area: e.target.value }))}>
                    {Object.entries(ETIQUETA_AREA).filter(([k]) => k !== 'habitacion').map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </label>
              )}
              <label className="campo">
                <span>Título</span>
                <input className="entrada" required minLength={3} maxLength={160} value={incForm.titulo} onChange={(e) => setIncForm((f) => ({ ...f, titulo: e.target.value }))} />
              </label>
              <label className="campo">
                <span>Descripción</span>
                <textarea className="entrada" required minLength={3} rows={2} value={incForm.descripcion} onChange={(e) => setIncForm((f) => ({ ...f, descripcion: e.target.value }))} />
              </label>
              <label className="campo">
                <span>Gravedad</span>
                <select className="entrada" value={incForm.gravedad} onChange={(e) => setIncForm((f) => ({ ...f, gravedad: e.target.value }))}>
                  {Object.entries(ETIQUETA_GRAVEDAD).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              <Campo
                etiqueta="Plazo"
                type="date"
                value={incForm.plazo}
                onChange={(e) => setIncForm((f) => ({ ...f, plazo: e.target.value }))}
              />
              {incForm.habitacion_id && (
                <label className="campo-check">
                  <input type="checkbox" checked={incForm.bloquea_disponibilidad} onChange={(e) => setIncForm((f) => ({ ...f, bloquea_disponibilidad: e.target.checked }))} />
                  Bloquea disponibilidad de la habitación
                </label>
              )}
              <label className="campo-archivo">
                <span>Evidencia fotográfica (móvil, opcional)</span>
                <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={manejarFoto} />
              </label>
              <button type="submit" className="boton-primario">Registrar incidencia</button>
            </form>
          </section>

          <ul className="lista-aseo">
            {(incidenciasData?.incidencias || []).map((inc) => (
              <li key={inc.incidencia_id} className={`tarjeta tarjeta-aseo${inc.estado === 'abierta' || inc.estado === 'en_progreso' ? ' pendiente' : ''}`}>
                <div className="aseo-cabecera">
                  <strong>{inc.titulo}</strong>
                  <span>{inc.habitacion_id ? <Link href={`/hotel/habitaciones/${inc.habitacion_id}`}>{inc.habitacion_id}</Link> : (ETIQUETA_AREA[inc.area] || inc.area)}</span>
                  <span className="reserva-estado">Gravedad: {ETIQUETA_GRAVEDAD[inc.gravedad] || inc.gravedad}</span>
                  <span className="reserva-estado">{inc.estado.replace('_', ' ')}</span>
                  {inc.bloquea_disponibilidad && <span className="badge-bloquea">Bloquea disponibilidad</span>}
                </div>
                <p>{inc.descripcion}</p>
                <p className="nota-clave">
                  Reportada por {inc.reportada_por}
                  {inc.responsable ? ` · Responsable: ${inc.responsable}` : ''}
                  {inc.plazo ? ` · Plazo: ${inc.plazo}` : ''}
                  {inc.costo_clp != null ? ` · Costo: $${inc.costo_clp.toLocaleString('es-CL')}` : ''}
                </p>
                <div className="acciones-aseo">
                  {inc.tiene_evidencia && (
                    <a className="boton-fantasma" href={`/api/hotel/incidencias/${inc.incidencia_id}/evidencia`} target="_blank" rel="noopener noreferrer">
                      Ver foto evidencia
                    </a>
                  )}
                  {anota && (inc.estado === 'abierta' || inc.estado === 'en_progreso') && (
                    <button type="button" className="boton-secundario" onClick={() => cerrarIncidencia(inc)}>
                      Cerrar incidencia
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </MarcoHotel>
  )
}
