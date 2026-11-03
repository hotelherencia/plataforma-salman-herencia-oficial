'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useCallback, useEffect, useState } from 'react'
import {
  api,
  camposFaltantes,
  clp,
  mensajeDeError,
  MarcoHotel,
  SalidaJson,
  Campo,
  useClaveOperacion,
  useSesion,
} from '../../../../lib/api'

/**
 * Ficha de la habitación (spec-hotel-operacion-v1 §2.3–2.6). Muestra lo que
 * devuelve GET /hotel/habitaciones/{id}; las acciones del administrador
 * (editar tipo/capacidad, tarifa nueva, retirar o reincorporar) van a la API
 * con su propia clave de idempotencia. Las reglas —qué campos se pueden
 * cambiar, la vigencia de tarifas, cuándo se puede retirar— las aplica el
 * servidor; aquí solo se explican y se muestran sus respuestas.
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
  const esAdmin = sesion.fase === 'ok' && sesion.usuario.rol === 'administrador'
  const [ficha, setFicha] = useState(null)
  const [errorCarga, setErrorCarga] = useState('')
  const [edicion, setEdicion] = useState({ tipo: '', capacidad: '' })
  const [tarifa, setTarifa] = useState({ fecha_desde: '', fecha_hasta: '', tarifa_noche_clp: '' })
  const [motivo, setMotivo] = useState('')
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [vigentes, setVigentes] = useState([])
  const [claveEdicion, renovarEdicion] = useClaveOperacion()
  const [claveTarifa, renovarTarifa] = useClaveOperacion()
  const [claveServicio, renovarServicio] = useClaveOperacion()

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
      setErrorCarga('La API no está disponible')
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
        if (Array.isArray(r.datos.reservas_vigentes)) setVigentes(r.datos.reservas_vigentes)
      } else {
        setSalida(r.datos)
        renovar()
        cargar()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  const guardarEdicion = (e) =>
    enviar(
      e,
      `/hotel/habitaciones/${encodeURIComponent(habitacionId)}`,
      { metodo: 'PUT', cuerpo: { tipo: edicion.tipo, capacidad: Number(edicion.capacidad) }, claveIdempotencia: claveEdicion },
      renovarEdicion
    )

  const guardarTarifa = (e) => {
    const falta = camposFaltantes([
      [tarifa.fecha_desde, 'Desde'],
      [tarifa.fecha_hasta, 'Hasta'],
      [tarifa.tarifa_noche_clp, 'Tarifa por noche'],
    ])
    if (falta) {
      e.preventDefault()
      return setError(falta)
    }
    return enviar(
      e,
      '/hotel/tarifas',
      {
        metodo: 'PUT',
        cuerpo: { habitacion_id: habitacionId, ...tarifa, tarifa_noche_clp: Number(tarifa.tarifa_noche_clp) },
        claveIdempotencia: claveTarifa,
      },
      renovarTarifa
    )
  }

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
              <dd>{ficha.capacidad} persona(s)</dd>
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
                <span className={`reserva-estado preparacion-${ficha.estado_preparacion}`}>{ficha.estado_preparacion}</span>
              </dd>
              <dt>Mantenimiento</dt>
              <dd>{ficha.mantenimiento ? 'abierto (fuera del cupo)' : 'no'}</dd>
              <dt>Tarifa vigente hoy</dt>
              <dd>{ficha.tarifa_vigente_hoy_clp ? `${clp(ficha.tarifa_vigente_hoy_clp)}/noche` : 'sin tarifa hoy'}</dd>
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
                  fechas, estado y tarifa aceptada). El identificador no se puede cambiar. La reserva no guarda la cantidad
                  de personas, así que bajar la capacidad no se valida contra reservas futuras.
                </p>
                <form className="formulario" onSubmit={guardarEdicion}>
                  <Campo etiqueta="Tipo" value={edicion.tipo} onChange={(e) => setEdicion({ ...edicion, tipo: e.target.value })} />
                  <Campo etiqueta="Capacidad" type="number" min="1" max="30" value={edicion.capacidad} onChange={(e) => setEdicion({ ...edicion, capacidad: e.target.value })} />
                  <button type="submit" className="boton-primario">Guardar cambios</button>
                </form>
                <p className="nota-clave nota-tecnica">Clave: <code>{claveEdicion}</code></p>
              </section>

              <section className="tarjeta" aria-label="Tarifa nueva">
                <h2>Registrar tarifa nueva</h2>
                <p className="nota-clave">
                  Las tarifas no se editan ni se borran: una nueva reemplaza el precio de las noches que cubre. En cada noche
                  rige la de inicio más reciente; si dos empiezan el mismo día, la registrada después. Las reservas ya
                  confirmadas mantienen su tarifa.
                </p>
                <form className="formulario" onSubmit={guardarTarifa}>
                  <Campo etiqueta="Desde" type="date" value={tarifa.fecha_desde} onChange={(e) => setTarifa({ ...tarifa, fecha_desde: e.target.value })} />
                  <Campo etiqueta="Hasta (sin incluir)" type="date" value={tarifa.fecha_hasta} onChange={(e) => setTarifa({ ...tarifa, fecha_hasta: e.target.value })} />
                  <Campo etiqueta="Tarifa por noche (CLP)" type="number" min="1" value={tarifa.tarifa_noche_clp} onChange={(e) => setTarifa({ ...tarifa, tarifa_noche_clp: e.target.value })} />
                  <button type="submit" className="boton-primario">Guardar tarifa</button>
                </form>
                <p className="nota-clave nota-tecnica">Clave: <code>{claveTarifa}</code></p>
              </section>

              <section className="tarjeta" aria-label="Servicio">
                <h2>{ficha.en_servicio ? 'Retirar de operación' : 'Reincorporar a la operación'}</h2>
                {ficha.en_servicio ? (
                  <>
                    <p className="nota-clave">
                      Baja lógica: la habitación queda fuera de servicio y deja de ofrecerse, pero nada se borra (reservas,
                      cargos, pagos, tarifas e historial siguen consultables). Se rechaza si tiene reservas confirmadas o
                      en estadía: cancélalas o termínalas antes.
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
                <p className="nota-clave nota-tecnica">Clave: <code>{claveServicio}</code></p>
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
          <SalidaJson datos={salida} />

          <section className="tarjeta" aria-label="Historial de tarifas">
            <h2>Historial de tarifas</h2>
            {ficha.tarifas.length === 0 ? (
              <p className="estado">Sin tarifas: la habitación no se ofrece.</p>
            ) : (
              <table className="tabla">
                <thead>
                  <tr>
                    <th>Desde</th>
                    <th>Hasta (sin incluir)</th>
                    <th>Por noche</th>
                    <th>Registrada</th>
                    <th>Hoy</th>
                  </tr>
                </thead>
                <tbody>
                  {ficha.tarifas.map((t) => (
                    <tr key={t.tarifa_id}>
                      <td>{t.fecha_desde}</td>
                      <td>{t.fecha_hasta}</td>
                      <td>{clp(t.tarifa_noche_clp)}</td>
                      <td>{t.registrada_en.slice(0, 16).replace('T', ' ')}</td>
                      <td>{t.vigente_hoy ? 'vigente' : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="tarjeta" aria-label="Reservas de la habitación">
            <h2>Reservas de la habitación</h2>
            {ficha.reservas.length === 0 ? (
              <p className="estado">Sin reservas.</p>
            ) : (
              <table className="tabla">
                <thead>
                  <tr>
                    <th>Reserva</th>
                    <th>Huésped</th>
                    <th>Fechas</th>
                    <th>Noches</th>
                    <th>Estado</th>
                    <th>Tarifa aceptada</th>
                  </tr>
                </thead>
                <tbody>
                  {ficha.reservas.map((r) => (
                    <tr key={r.reserva_id}>
                      <td>
                        <Link href={`/hotel/reservas/${r.reserva_id}`}>{r.reserva_id}</Link>
                      </td>
                      <td>{r.huesped_nombre}</td>
                      <td>{r.inicio} → {r.fin}</td>
                      <td>{r.noches}</td>
                      <td>
                        <span className={`reserva-estado estado-${r.estado}`}>{ETIQUETA_ESTADO[r.estado] || r.estado}</span>
                      </td>
                      <td>{clp(r.tarifa_noche_aceptada_clp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="tarjeta" aria-label="Tareas">
            <h2>Tareas de limpieza y mantenimiento</h2>
            {ficha.tareas.length === 0 ? (
              <p className="estado">Sin tareas registradas.</p>
            ) : (
              <table className="tabla">
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Estado</th>
                    <th>Creada</th>
                    <th>Completada</th>
                  </tr>
                </thead>
                <tbody>
                  {ficha.tareas.map((t) => (
                    <tr key={t.tarea_id}>
                      <td>{t.tipo}</td>
                      <td>{t.estado}</td>
                      <td>{t.creada_en.slice(0, 16).replace('T', ' ')}</td>
                      <td>{t.completada_en ? t.completada_en.slice(0, 16).replace('T', ' ') : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {Array.isArray(ficha.auditoria) && (
            <section className="tarjeta" aria-label="Auditoría">
              <h2>Historial de cambios (auditoría)</h2>
              {ficha.auditoria.length === 0 ? (
                <p className="estado">Sin cambios registrados.</p>
              ) : (
                <table className="tabla">
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
                        <td>{a.registrada_en.slice(0, 16).replace('T', ' ')}</td>
                        <td>{a.actor}</td>
                        <td>{a.accion}</td>
                        <td>{a.resultado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          )}
        </>
      )}
    </MarcoHotel>
  )
}
