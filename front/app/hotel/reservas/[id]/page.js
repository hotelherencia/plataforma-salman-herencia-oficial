'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, useSesion } from '../../../../lib/api'
import { esAdminHotel, gestionaRecepcion } from '../../../../lib/roles'
import { SelectorUnidad } from '../../_componentes/campos-recepcion'
import Subnav from '../../_componentes/subnav'
import { SUBNAV_RESERVAS } from '../../../../lib/menu-hotel'
import { fechaATexto, fechaHora, plural } from '../../../../lib/formato'
import { nombreDocumento, nombreMedio } from '../../../../lib/caja'

/**
 * Detalle de la reserva con su cuenta (spec-hotel-operacion-v1 §3.2). El saldo
 * viene calculado por el servidor con la misma fórmula que exige la salida
 * (cargos menos reversos menos pagos confirmados); aquí no se suma nada.
 */

const ETIQUETA_ESTADO = {
  confirmada: 'confirmada',
  en_estadia: 'en estadía',
  finalizada: 'finalizada',
  cancelada: 'cancelada',
}

const SIGUIENTE_PASO = {
  confirmada: [['/hotel/estadia', 'Llegada, cargo o cancelación'], ['/hotel/pago', 'Registrar pago']],
  en_estadia: [['/hotel/estadia', 'Asentar un cargo'], ['/hotel/pago', 'Registrar pago'], ['/hotel/salida', 'Salida y liquidación']],
}

function hoyIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function DetalleReserva() {
  const { id } = useParams()
  const reservaId = decodeURIComponent(id)
  const sesion = useSesion()
  const [reserva, setReserva] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [version, setVersion] = useState(0)
  const puedeReversar = sesion.fase === 'ok' && esAdminHotel(sesion.usuario.rol)
  const puedeMover = sesion.fase === 'ok' && gestionaRecepcion(sesion.usuario.rol)
  const [destino, setDestino] = useState('')
  const [motivoCambio, setMotivoCambio] = useState('')
  const [devolucion, setDevolucion] = useState({ monto_clp: '', medio: 'transferencia', motivo: '' })

  // #91 / Q-HOT-04: devolución formal de saldo a favor del huésped (solo administración).
  async function registrarDevolucion(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const monto = Number(devolucion.monto_clp || Math.abs(reserva?.cuenta?.saldo_clp || 0))
    if (!(monto > 0)) { setError('Indica un monto válido mayor que 0.'); return }
    if (devolucion.motivo.trim().length < 10) { setError('Indica el motivo de la devolución (mínimo 10 caracteres).'); return }
    if (!window.confirm(`¿Registrar devolución de ${clp(monto)} por ${devolucion.medio} a ${reserva.huesped_nombre}?`)) return
    try {
      const r = await api(`/hotel/reservas/${encodeURIComponent(reservaId)}/devolucion`, {
        metodo: 'POST',
        claveIdempotencia: `dev-${crypto.randomUUID().slice(0, 12)}`,
        cuerpo: { monto_clp: monto, medio: devolucion.medio, motivo: devolucion.motivo.trim() },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso(`Devolución registrada por ${clp(r.datos.monto_clp)} (${r.datos.medio}). Saldo actual: ${clp(r.datos.saldo_clp)}.`)
        setDevolucion({ monto_clp: '', medio: 'transferencia', motivo: '' })
        setVersion((v) => v + 1)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  // #361: mover al huésped a otra habitación (conserva la tarifa pactada).
  async function cambiarHabitacion(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    if (!destino || destino === reserva.habitacion_id) { setError('Elige una habitación distinta de la actual.'); return }
    if (motivoCambio.trim().length < 3) { setError('Indica el motivo del cambio (mínimo 3 caracteres).'); return }
    if (!window.confirm(`¿Mover a ${reserva.huesped_nombre} de ${reserva.habitacion_id} a ${destino}?`)) return
    try {
      const r = await api(`/hotel/reservas/${encodeURIComponent(reservaId)}/habitacion`, {
        metodo: 'POST',
        claveIdempotencia: `rea-${crypto.randomUUID().slice(0, 12)}`,
        cuerpo: { habitacion_id: destino, motivo: motivoCambio.trim() },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso(`Huésped movido de ${r.datos.desde_habitacion_id} a ${r.datos.hacia_habitacion_id}.`)
        setDestino('')
        setMotivoCambio('')
        setVersion((v) => v + 1)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  // #359: anular un cargo = asentar su reverso (movimiento contrario), nunca borrar.
  async function reversar(cargo) {
    const motivo = window.prompt(`Motivo del reverso de «${cargo.concepto}» (${clp(cargo.monto_clp)}):`)
    if (motivo === null) return
    if (motivo.trim().length < 3) { setError('Indica un motivo (mínimo 3 caracteres).'); return }
    setError('')
    setAviso('')
    try {
      const r = await api(`/hotel/reservas/${encodeURIComponent(reservaId)}/cargos/${encodeURIComponent(cargo.cargo_id)}/reverso`, {
        metodo: 'POST',
        claveIdempotencia: `rev-${cargo.cargo_id}-${crypto.randomUUID().slice(0, 6)}`,
        cuerpo: { motivo: motivo.trim() },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso(`Reverso asentado por ${clp(r.datos.monto_clp)}. Saldo: ${clp(r.datos.saldo_clp)}.`)
        setVersion((v) => v + 1)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  useEffect(() => {
    if (sesion.fase !== 'ok') return
    api(`/hotel/reservas/${encodeURIComponent(reservaId)}`)
      .then((r) => {
        if (r.estado === 403) setError('No existe esa reserva o no pertenece a tu empresa.')
        else if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
        else setReserva(r.datos)
      })
      .catch(() => setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.'))
  }, [sesion.fase, reservaId, version])

  return (
    <MarcoHotel titulo={`Reserva ${reservaId}`}>
      <Subnav items={SUBNAV_RESERVAS} />
      <p className="migas">
        <Link href="/hotel/reservas">← Reservas</Link> · <Link href="/hotel/ocupacion">Ocupación</Link>
      </p>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      {reserva && (
        <>
          <section className="tarjeta" aria-label="Reserva">
            <h2>
              {reserva.huesped_nombre}{' '}
              <span className={`reserva-estado estado-${reserva.estado}`}>{ETIQUETA_ESTADO[reserva.estado] || reserva.estado}</span>
            </h2>
            <dl className="ficha-datos">
              <dt>Habitación</dt>
              <dd>
                <Link href={`/hotel/habitaciones/${reserva.habitacion_id}`}>{reserva.habitacion_id}</Link> ({reserva.tipo_habitacion})
              </dd>
              <dt>Fechas</dt>
              <dd>
                {fechaATexto(reserva.inicio)} → {fechaATexto(reserva.fin)} · {plural(reserva.noches, 'noche')}
              </dd>
              <dt>Tarifa aceptada</dt>
              <dd>{clp(reserva.tarifa_noche_aceptada_clp)}/noche (congelada al confirmar)</dd>
              {reserva.huesped_documento !== undefined && (
                <>
                  <dt>Documento</dt>
                  <dd>{reserva.huesped_documento || '—'}</dd>
                </>
              )}
              <dt>Registrada</dt>
              <dd>{reserva.creada_en.slice(0, 16).replace('T', ' ')}</dd>
            </dl>
            {SIGUIENTE_PASO[reserva.estado] && (
              <p className="nota-clave">
                Siguiente paso:{' '}
                {SIGUIENTE_PASO[reserva.estado].map(([href, texto], i) => (
                  <span key={href}>
                    {i > 0 && ' · '}
                    <Link href={`${href}?reserva_id=${reserva.reserva_id}`}>{texto}</Link>
                  </span>
                ))}
              </p>
            )}
          </section>

          <section className="tarjeta" aria-label="Cuenta">
            <h2>Cuenta de la estadía</h2>
            <div className="kpi-rejilla">
              <div className="kpi">
                <span className="kpi-titulo">Total cargos (IVA incl.)</span>
                <span className="kpi-valor">{clp(reserva.cuenta.cargos_netos_clp)}</span>
              </div>
              <div className="kpi">
                <span className="kpi-titulo">Pagado</span>
                <span className="kpi-valor">{clp(reserva.cuenta.pagado_clp)}</span>
              </div>
              <div className={`kpi${reserva.cuenta.saldo_clp > 0 ? ' kpi-alerta' : ''}`}>
                <span className="kpi-titulo">{reserva.cuenta.saldo_clp < 0 ? 'Saldo a favor del huésped' : 'Saldo pendiente'}</span>
                <span className="kpi-valor">{clp(Math.abs(reserva.cuenta.saldo_clp))}</span>
              </div>
            </div>
            <p className="nota-clave">
              Saldo = cargos − reversos − pagos confirmados, calculado por el servidor. La salida solo procede con saldo 0.
            </p>
            {puedeReversar && reserva.cuenta.saldo_clp < 0 && reserva.estado !== 'finalizada' && (
              <form className="formulario cambio-habitacion" onSubmit={registrarDevolucion} aria-label="Registrar devolución de saldo a favor">
                <h3 className="subtitulo">Devolver saldo a favor ({clp(Math.abs(reserva.cuenta.saldo_clp))})</h3>
                <label className="campo">
                  <span className="campo-etiqueta">Monto a devolver (CLP)</span>
                  <input
                    className="entrada"
                    type="number"
                    min="1"
                    max={Math.abs(reserva.cuenta.saldo_clp)}
                    placeholder={String(Math.abs(reserva.cuenta.saldo_clp))}
                    value={devolucion.monto_clp}
                    onChange={(e) => setDevolucion({ ...devolucion, monto_clp: e.target.value })}
                  />
                </label>
                <label className="campo">
                  <span className="campo-etiqueta">Medio de devolución</span>
                  <select className="entrada" value={devolucion.medio} onChange={(e) => setDevolucion({ ...devolucion, medio: e.target.value })}>
                    <option value="transferencia">Transferencia bancaria</option>
                    <option value="efectivo">Efectivo (requiere turno de caja abierto)</option>
                  </select>
                </label>
                <label className="campo">
                  <span className="campo-etiqueta">Motivo (mínimo 10 caracteres)</span>
                  <input
                    className="entrada"
                    value={devolucion.motivo}
                    onChange={(e) => setDevolucion({ ...devolucion, motivo: e.target.value })}
                    placeholder="Ej.: devolución de anticipo por salida anticipada"
                  />
                </label>
                <button type="submit" className="boton-secundario">Registrar devolución</button>
              </form>
            )}
            {puedeMover && ['confirmada', 'en_estadia'].includes(reserva.estado) && (
              <form className="formulario cambio-habitacion" onSubmit={cambiarHabitacion} aria-label="Cambiar habitación">
                <h3 className="subtitulo">Cambiar habitación</h3>
                <SelectorUnidad
                  etiqueta="Mover a"
                  inicio={reserva.inicio > hoyIso() ? reserva.inicio : hoyIso()}
                  fin={reserva.fin}
                  personas={reserva.personas || 1}
                  valor={destino}
                  alCambiar={setDestino}
                />
                <label className="campo">
                  <span className="campo-etiqueta">Motivo</span>
                  <input className="entrada" value={motivoCambio} onChange={(e) => setMotivoCambio(e.target.value)} placeholder="Ej.: ruido, upgrade, mantención" />
                </label>
                <button type="submit" className="boton-secundario">Cambiar habitación</button>
                <p className="nota-clave">Se conserva la tarifa pactada. En estadía, la habitación de origen queda para limpieza.</p>
              </form>
            )}
            {reserva.reasignaciones?.length > 0 && (
              <>
                <h3 className="subtitulo">Cambios de habitación</h3>
                <ul className="lista-simple">
                  {reserva.reasignaciones.map((a) => (
                    <li key={a.registrado_en}>
                      {fechaHora(a.registrado_en)} · {a.desde_habitacion_id} → {a.hacia_habitacion_id} · {a.motivo} ({a.actor})
                    </li>
                  ))}
                </ul>
              </>
            )}
            <h3 className="subtitulo">Cargos y reversos</h3>
            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)"><table className="tabla">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Tipo</th>
                  <th>Concepto</th>
                  <th>Monto</th>
                  {puedeReversar && <th>Acción</th>}
                </tr>
              </thead>
              <tbody>
                  {reserva.cargos.map((c) => (
                    <tr key={c.cargo_id}>
                      <td>{fechaHora(c.registrado_en)}</td>
                      <td>{c.tipo === 'reverso' ? 'Reverso de cargo' : 'Cargo'}</td>
                      <td>{c.concepto}</td>
                      <td>{c.tipo === 'reverso' ? `−${clp(c.monto_clp)}` : clp(c.monto_clp)}</td>
                      {puedeReversar && (
                        <td>
                          {c.tipo === 'cargo' && !c.reversado && ['confirmada', 'en_estadia'].includes(reserva.estado) ? (
                            <button type="button" className="boton-fantasma" onClick={() => reversar(c)}>Reversar</button>
                          ) : c.reversado ? 'Reversado' : '—'}
                        </td>
                      )}
                    </tr>
                  ))}
              </tbody>
            </table></div>
            <h3 className="subtitulo">Pagos</h3>
            {reserva.pagos.length === 0 ? (
              <p className="estado estado-vacio">Sin pagos.</p>
            ) : (
              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)"><table className="tabla">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Medio</th>
                    <th>Documento</th>
                    <th>Estado</th>
                    <th>Monto</th>
                  </tr>
                </thead>
                <tbody>
                  {reserva.pagos.map((g) => (
                    <tr key={g.pago_id}>
                      <td>{fechaHora(g.registrado_en)}</td>
                      <td>{nombreMedio(g.medio)}{g.es_anticipo ? ' (anticipo)' : ''}</td>
                      <td>{g.tipo === 'reverso' ? 'Reverso' : nombreDocumento(g.documento_tipo)}</td>
                      <td>{g.estado === 'confirmado' ? 'Confirmado' : g.estado}</td>
                      <td>{g.tipo === 'reverso' ? `−${clp(g.monto_clp)}` : clp(g.monto_clp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            )}
            {reserva.liquidacion && (
              <p className="nota-clave">
                Liquidada el {fechaATexto(reserva.liquidacion.liquidada_en.slice(0, 10))} ({reserva.liquidacion.liquidacion_id}): total{' '}
                {clp(reserva.liquidacion.total_clp)}, pagado {clp(reserva.liquidacion.pagado_clp)}, saldo{' '}
                {clp(reserva.liquidacion.saldo_clp)}.
              </p>
            )}
          </section>
        </>
      )}
    </MarcoHotel>
  )
}
