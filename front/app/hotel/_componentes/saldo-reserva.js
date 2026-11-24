'use client'

import { useEffect, useState } from 'react'
import { api, clp } from '../../../lib/api'
import { saldoVisible } from '../../../lib/contabilidad'
import { fechaCorta } from '../../../lib/estadias'

/**
 * Saldo de la reserva siempre a la vista: total, abonado (aún sin aplicar), pagado y pendiente, con el detalle
 * por noche. Se vuelve a pedir cada vez que cambia `version` (por ejemplo, tras registrar un pago).
 */
export function useSaldoReserva(reservaId, version = 0) {
  const [estado, setEstado] = useState({ saldo: null, error: false })

  useEffect(() => {
    let vivo = true
    if (!reservaId) return undefined
    api(`/hotel/reservas/${encodeURIComponent(reservaId)}/saldo`)
      .then((r) => { if (vivo) setEstado(r.estado === 200 ? { saldo: r.datos, error: false } : { saldo: null, error: true }) })
      .catch(() => { if (vivo) setEstado({ saldo: null, error: true }) })
    return () => { vivo = false }
  }, [reservaId, version])
  return estado
}

export default function SaldoReserva({ reservaId, version = 0, conNoches = true, estado: dado }) {
  const propio = useSaldoReserva(dado ? '' : reservaId, version)
  const { saldo, error } = dado || propio
  if (error) return <p className="alerta" role="alert">No se pudo cargar el saldo de la reserva.</p>
  if (!saldo) return <p className="estado" role="status" aria-busy="true">Cargando el saldo…</p>
  const visible = saldoVisible(saldo)
  return (
    <section aria-label="Saldo de la reserva" data-saldo={visible.tono}>
      <dl className="resumen-cuenta">
        <div><dt>Total</dt><dd>{clp(saldo.total_clp)}</dd></div>
        <div><dt>Abonado (sin aplicar)</dt><dd>{clp(saldo.abonado_clp)}</dd></div>
        <div><dt>Pagado</dt><dd>{clp(saldo.pagado_clp)}</dd></div>
        <div><dt>{visible.texto}</dt><dd><strong>{clp(visible.monto)}</strong></dd></div>
      </dl>
      {conNoches && saldo.noches.length > 0 && (
        <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Pago por noche">
          <table className="tabla">
            <thead><tr><th>Noche</th><th>Precio</th><th>Pagado</th><th>Pendiente</th></tr></thead>
            <tbody>
              {saldo.noches.map((n) => (
                <tr key={n.noche}>
                  <td>{fechaCorta(n.noche)}{n.asentada ? '' : ' (aún no asentada)'}</td>
                  <td>{clp(n.precio_clp)}</td>
                  <td>{clp(n.pagado_clp)}</td>
                  <td>{clp(n.pendiente_clp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
