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
import { esAdminHotel } from '../../../../lib/roles'
import { etiquetaOrigen, rangoNoches } from '../../../../lib/tipos'

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
  const [ficha, setFicha] = useState(null)
  const [errorCarga, setErrorCarga] = useState('')
  const [edicion, setEdicion] = useState({ tipo: '', capacidad: '' })
  const [motivo, setMotivo] = useState('')
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [vigentes, setVigentes] = useState([])
  const [claveEdicion, renovarEdicion] = useClaveOperacion()
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
                        <td>{t.fecha_desde}</td>
                        <td>{t.fecha_hasta}</td>
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
                      <td>{r.inicio} → {r.fin}</td>
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

          <section className="tarjeta" aria-label="Tareas">
            <h2>Tareas de limpieza y mantenimiento</h2>
            {ficha.tareas.length === 0 ? (
              <p className="estado estado-vacio">Sin tareas registradas.</p>
            ) : (
              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)"><table className="tabla">
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
              </table></div>
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
                        <td>{a.registrada_en.slice(0, 16).replace('T', ' ')}</td>
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
