'use client'

import Link from 'next/link'
import { useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, Campo, useSesion } from '../../../lib/api'
import { esAdminHotel } from '../../../lib/roles'
import Subnav from '../_componentes/subnav'
import { SUBNAV_CAJA } from '../../../lib/menu-hotel'

export default function Caja() {
  const sesion = useSesion()
  const hoy = new Date().toISOString().slice(0, 10)
  const [fecha, setFecha] = useState(hoy)
  const [caja, setCaja] = useState(null)
  const [error, setError] = useState('')

  // spec-api-v1: GET /hotel/caja es para caja o administrador.
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  if (sesion.fase === 'ok' && rol !== 'caja' && !esAdminHotel(rol)) {
    return (
      <MarcoHotel titulo="Caja del día">
      <Subnav items={SUBNAV_CAJA} />
        <p className="estado">La caja del día es solo para caja o la administración del hotel.</p>
      </MarcoHotel>
    )
  }

  async function consultar(e) {
    e.preventDefault()
    setError('')
    setCaja(null)
    try {
      const r = await api(`/hotel/caja?fecha=${fecha}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setCaja(r.datos)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <MarcoHotel titulo="Caja del día">
      <Subnav items={SUBNAV_CAJA} />
      <section className="tarjeta">
        <form className="formulario" onSubmit={consultar}>
          <Campo etiqueta="Fecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
          <button type="submit" className="boton-primario">Ver caja</button>
        </form>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      {caja && (
        <>
          <p className="resumen">
            Total del día: <strong>{clp(caja.total_clp)}</strong>
          </p>
          {caja.pagos.length > 0 ? (
            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Huésped</th>
                  <th>Habitación</th>
                  <th>Pago</th>
                  <th>Reserva</th>
                  <th>Monto</th>
                  <th>Modo</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {caja.pagos.map((p) => (
                  <tr key={p.pago_id}>
                    <td>{p.huesped_nombre || '—'}</td>
                    <td>{p.habitacion_id}</td>
                    <td className="nota-tecnica">{p.pago_id}</td>
                    <td><Link href={`/hotel/reservas/${p.reserva_id}`}>{p.reserva_id}</Link></td>
                    <td>{clp(p.monto_clp)}</td>
                    <td>{p.modo}</td>
                    <td>{p.estado}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          ) : (
            <p className="estado estado-vacio">Sin pagos registrados en esta fecha.</p>
          )}
        </>
      )}
    </MarcoHotel>
  )
}
