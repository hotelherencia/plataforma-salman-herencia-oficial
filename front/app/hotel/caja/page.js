'use client'

import { useState } from 'react'
import { api, mensajeDeError, MarcoHotel, Campo } from '../../../lib/api'

export default function Caja() {
  const hoy = new Date().toISOString().slice(0, 10)
  const [fecha, setFecha] = useState(hoy)
  const [caja, setCaja] = useState(null)
  const [error, setError] = useState('')

  async function consultar(e) {
    e.preventDefault()
    setError('')
    setCaja(null)
    try {
      const r = await api(`/hotel/caja?fecha=${fecha}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setCaja(r.datos)
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Caja del día">
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
            Total del día: <strong>${caja.total_clp}</strong>
          </p>
          {caja.pagos.length > 0 ? (
            <table className="tabla">
              <thead>
                <tr>
                  <th>Pago</th>
                  <th>Reserva</th>
                  <th>Habitación</th>
                  <th>Monto</th>
                  <th>Modo</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {caja.pagos.map((p) => (
                  <tr key={p.pago_id}>
                    <td>{p.pago_id}</td>
                    <td>{p.reserva_id}</td>
                    <td>{p.habitacion_id}</td>
                    <td>${p.monto_clp}</td>
                    <td>{p.modo}</td>
                    <td>{p.estado}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="estado">Sin pagos registrados en esta fecha.</p>
          )}
        </>
      )}
    </MarcoHotel>
  )
}
