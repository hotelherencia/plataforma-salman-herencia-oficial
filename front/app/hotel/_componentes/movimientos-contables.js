'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { api, clp, mensajeDeError, Campo } from '../../../lib/api'
import { nombreMedio } from '../../../lib/caja'
import { rotuloMovimiento } from '../../../lib/contabilidad'
import { fechaHora } from '../../../lib/formato'

const ROTULO_DOC = { boleta: 'Boleta', factura: 'Factura', sin_documento: 'Sin documento', pendiente: 'Por indicar' }

/**
 * Movimientos de la cuenta (cargos, reversos y pagos) con quién los hizo. No dependen de que la caja esté abierta:
 * un cargo o un consumo asociado a una reserva queda aquí aunque no haya turno abierto.
 */
export default function MovimientosContables({ hoy }) {
  const [desde, setDesde] = useState(hoy)
  const [hasta, setHasta] = useState(hoy)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  const consultar = useCallback(async (d, h) => {
    setError('')
    setCargando(true)
    try {
      const r = await api(`/hotel/contabilidad/movimientos?desde=${d}&hasta=${h}`)
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); setDatos(null) } else setDatos(r.datos.movimientos)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { consultar(hoy, hoy) }, [consultar, hoy])

  return (
    <section className="tarjeta" aria-label="Movimientos de la cuenta">
      <form className="formulario" onSubmit={(e) => { e.preventDefault(); consultar(desde, hasta) }}>
        <Campo etiqueta="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
        <Campo etiqueta="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
        <button type="submit" className="boton-secundario">Ver movimientos</button>
      </form>
      {error && <p role="alert" className="alerta">{error}</p>}
      {cargando && !datos && <p className="estado" role="status" aria-busy="true">Cargando los movimientos…</p>}
      {datos && datos.length === 0 && <p className="estado estado-vacio">Sin movimientos en estas fechas.</p>}
      {datos && datos.length > 0 && (
        <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Movimientos (desliza para ver todas las columnas)">
          <table className="tabla">
            <thead>
              <tr><th>Fecha y hora</th><th>Movimiento</th><th>Detalle</th><th>Huésped</th><th>Habitación</th><th>Monto</th><th>Medio</th><th>Documento</th><th>Registrado por</th></tr>
            </thead>
            <tbody>
              {datos.map((m, i) => (
                <tr key={`${m.fecha_hora}-${i}`}>
                  <td>{fechaHora(m.fecha_hora)}</td>
                  <td>{rotuloMovimiento(m.tipo)}</td>
                  <td>{m.concepto}{m.cantidad ? ` × ${m.cantidad}` : ''}</td>
                  <td><Link href={`/hotel/reservas/${m.reserva_id}`}>{m.huesped_nombre || m.reserva_id}</Link></td>
                  <td>{m.habitacion_id}</td>
                  <td>{clp(m.monto_clp)}</td>
                  <td>{m.medio ? nombreMedio(m.medio) : '—'}</td>
                  <td>{m.documento_tipo ? `${ROTULO_DOC[m.documento_tipo] || 'Documento'}${m.documento_folio ? ` N° ${m.documento_folio}` : ''}` : '—'}</td>
                  <td>{m.actor || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
