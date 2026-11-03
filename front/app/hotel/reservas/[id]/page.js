'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useEffect, useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, useSesion } from '../../../../lib/api'

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
  confirmada: [['/hotel/estadia', 'Check-in, cargo o cancelación'], ['/hotel/pago', 'Registrar pago']],
  en_estadia: [['/hotel/estadia', 'Asentar un cargo'], ['/hotel/pago', 'Registrar pago'], ['/hotel/salida', 'Salida y liquidación']],
}

export default function DetalleReserva() {
  const { id } = useParams()
  const reservaId = decodeURIComponent(id)
  const sesion = useSesion()
  const [reserva, setReserva] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (sesion.fase !== 'ok') return
    api(`/hotel/reservas/${encodeURIComponent(reservaId)}`)
      .then((r) => {
        if (r.estado === 403) setError('No existe esa reserva o no pertenece a tu empresa.')
        else if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
        else setReserva(r.datos)
      })
      .catch(() => setError('La API no está disponible'))
  }, [sesion.fase, reservaId])

  return (
    <MarcoHotel titulo={`Reserva ${reservaId}`}>
      <p className="migas">
        <Link href="/hotel/reservas">← Reservas</Link> · <Link href="/hotel/ocupacion">Ocupación</Link>
      </p>
      {error && <p role="alert" className="alerta">{error}</p>}
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
                {reserva.inicio} → {reserva.fin} · {reserva.noches} noche(s)
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
            <h2>Cuenta</h2>
            <div className="kpi-rejilla">
              <div className="kpi">
                <span className="kpi-titulo">Cargos netos</span>
                <span className="kpi-valor">{clp(reserva.cuenta.cargos_netos_clp)}</span>
              </div>
              <div className="kpi">
                <span className="kpi-titulo">Pagado</span>
                <span className="kpi-valor">{clp(reserva.cuenta.pagado_clp)}</span>
              </div>
              <div className={`kpi${reserva.cuenta.saldo_clp !== 0 ? ' kpi-alerta' : ''}`}>
                <span className="kpi-titulo">Saldo</span>
                <span className="kpi-valor">{clp(reserva.cuenta.saldo_clp)}</span>
              </div>
            </div>
            <p className="nota-clave">
              Saldo = cargos − reversos − pagos confirmados, calculado por el servidor. La salida solo procede con saldo 0.
            </p>
            <h3 className="subtitulo">Cargos y reversos</h3>
            <div className="tabla-contenedor"><table className="tabla">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Tipo</th>
                  <th>Concepto</th>
                  <th>Monto</th>
                </tr>
              </thead>
              <tbody>
                {reserva.cargos.map((c) => (
                  <tr key={c.cargo_id}>
                    <td>{c.registrado_en.slice(0, 16).replace('T', ' ')}</td>
                    <td>{c.tipo}</td>
                    <td>{c.concepto}</td>
                    <td>{c.tipo === 'reverso' ? `−${clp(c.monto_clp)}` : clp(c.monto_clp)}</td>
                  </tr>
                ))}
              </tbody>
            </table></div>
            <h3 className="subtitulo">Pagos</h3>
            {reserva.pagos.length === 0 ? (
              <p className="estado">Sin pagos.</p>
            ) : (
              <div className="tabla-contenedor"><table className="tabla">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Modo</th>
                    <th>Estado</th>
                    <th>Monto</th>
                  </tr>
                </thead>
                <tbody>
                  {reserva.pagos.map((g) => (
                    <tr key={g.pago_id}>
                      <td>{g.registrado_en.slice(0, 16).replace('T', ' ')}</td>
                      <td>{g.modo}</td>
                      <td>{g.estado}</td>
                      <td>{clp(g.monto_clp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            )}
            {reserva.liquidacion && (
              <p className="nota-clave">
                Liquidada el {reserva.liquidacion.liquidada_en.slice(0, 10)} ({reserva.liquidacion.liquidacion_id}): total{' '}
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
