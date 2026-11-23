'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, useSesion } from '../../../lib/api'
import { esAdminHotel, gestionaRecepcion } from '../../../lib/roles'
import { nombreTipo } from '../../reservar/continuidad'
import { Checklists } from '../_componentes/checklists'
import { ListaIncidencias, ReporteIncidencia } from '../_componentes/incidencias'
import Mantenciones from '../_componentes/mantenciones'
import Comunicados from '../_componentes/comunicados'
import Turnos from '../_componentes/turnos'
import Biblioteca from '../_componentes/biblioteca'

const SITUACION = {
  ocupada: 'Ocupada',
  sale_hoy: 'Sale hoy',
  llega_hoy: 'Llega hoy',
  libre: 'Libre',
}

function clave(prefijo) {
  return `${prefijo}-${crypto.randomUUID().slice(0, 12)}`
}

/**
 * Aseo (#362, #363): lista de habitaciones por limpiar para el personal de
 * aseo, con confirmación de limpieza. La administración verifica (o rechaza
 * con observación) y deja notas por habitación. Sin datos del huésped.
 */
export default function Aseo() {
  const sesion = useSesion()
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const verifica = esAdminHotel(rol)
  const anota = gestionaRecepcion(rol)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [notas, setNotas] = useState({})
  const [soloPendientes, setSoloPendientes] = useState(false)
  const [versionIncidencias, setVersionIncidencias] = useState(0)

  const cargar = useCallback(async () => {
    try {
      const r = await api('/hotel/aseo')
      if (r.estado === 200) setDatos(r.datos)
      else setError(mensajeDeError(r.datos, r.estado))
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }, [])

  useEffect(() => {
    if (sesion.fase === 'ok') cargar()
  }, [sesion.fase, cargar])

  async function enviar(ruta, cuerpo, ok) {
    setError('')
    setAviso('')
    try {
      const r = await api(ruta, { metodo: 'POST', claveIdempotencia: clave('aseo'), cuerpo })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso(ok)
        await cargar()
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  const limpiar = (h) => enviar(`/hotel/habitaciones/${h.habitacion_id}/limpieza`, {}, `${h.habitacion_id} marcada como limpia.`)
  const iniciar = (h) => enviar(`/hotel/habitaciones/${h.habitacion_id}/en-limpieza`, {}, `${h.habitacion_id} figura «En limpieza».`)
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
    ).then(() => setNotas((n) => ({ ...n, [h.habitacion_id]: '' })))
  }
  const anotar = (h) => {
    const nota = (notas[h.habitacion_id] || '').trim()
    if (nota.length < 2) {
      setError('Escribe la observación (mínimo 2 caracteres).')
      return
    }
    enviar(`/hotel/habitaciones/${h.habitacion_id}/observaciones`, { texto: nota }, `Observación agregada a ${h.habitacion_id}.`)
      .then(() => setNotas((n) => ({ ...n, [h.habitacion_id]: '' })))
  }

  const lista = (datos?.habitaciones || []).filter((h) => !soloPendientes || h.limpieza_pendiente || h.observaciones.length)

  return (
    <MarcoHotel titulo="Aseo">
      <section className="tarjeta">
        <h2>Habitaciones por limpiar {datos ? `(${datos.pendientes})` : ''}</h2>
        <p className="nota-clave">
          Primero las habitaciones con limpieza pendiente. Al terminar, marca «Limpia».
          {verifica && ' Como administración, verifica cada limpieza o recházala con una observación.'}
        </p>
        <label className="campo-check">
          <input type="checkbox" checked={soloPendientes} onChange={(e) => setSoloPendientes(e.target.checked)} />
          Solo pendientes y con observaciones
        </label>
        {verifica && datos?.por_verificar?.length > 0 && (
          <p className="estado" role="status">Por verificar: {datos.por_verificar.join(', ')}</p>
        )}
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      {!datos && !error && <p className="estado" role="status" aria-busy="true">Cargando…</p>}
      <ul className="lista-aseo">
        {lista.map((h) => {
          const ultima = h.ultima_limpieza
          const porVerificar = ultima && !ultima.verificacion
          return (
            <li key={h.habitacion_id} className={`tarjeta tarjeta-aseo${h.limpieza_pendiente ? ' pendiente' : ''}`} data-habitacion={h.habitacion_id}>
              <div className="aseo-cabecera">
                <strong>{h.habitacion_id}</strong>
                <span>{nombreTipo(h.tipo)}</span>
                <span className="reserva-estado">{SITUACION[h.situacion] || h.situacion}</span>
                <span className={`reserva-estado ${h.estado_preparacion === 'sucia' ? 'estado-cancelada' : 'estado-finalizada'}`}>
                  {h.estado_preparacion}
                </span>
                {h.en_limpieza && <span className="reserva-estado">En limpieza{h.en_limpieza_por ? ` · ${h.en_limpieza_por}` : ''}</span>}
                {h.mantenimiento_hoy && <span className="reserva-estado estado-cancelada">mantenimiento</span>}
              </div>
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
                {h.limpieza_pendiente && h.estado_preparacion === 'sucia' && !h.en_limpieza && (
                  <button type="button" className="boton-secundario" onClick={() => iniciar(h)}>Empezar limpieza</button>
                )}
                {h.limpieza_pendiente && (
                  <button type="button" className="boton-primario" onClick={() => limpiar(h)}>Limpia</button>
                )}
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
            </li>
          )
        })}
      </ul>
      <Comunicados />
      <Turnos usuario={sesion.usuario.usuario} />
      <Biblioteca />
      <Mantenciones />
      <Checklists puedeCrear={anota} />
      <ReporteIncidencia alGuardar={() => setVersionIncidencias((v) => v + 1)} />
      <ListaIncidencias puedeCerrar={anota} version={versionIncidencias} />
    </MarcoHotel>
  )
}
