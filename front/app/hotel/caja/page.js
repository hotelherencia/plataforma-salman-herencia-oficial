'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, Campo, useSesion } from '../../../lib/api'
import { esAdminHotel } from '../../../lib/roles'
import { horaChile, medioDePago } from '../../../lib/estadias'
import Subnav from '../_componentes/subnav'
import { SUBNAV_CAJA } from '../../../lib/menu-hotel'

function hoyChile() {
  // Fecha del día en Chile (no en UTC: de noche UTC ya es «mañana»).
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Santiago' }).format(new Date())
}

export default function Caja() {
  const sesion = useSesion()
  const [fecha, setFecha] = useState(hoyChile)
  const [caja, setCaja] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  // spec-api-v1: GET /hotel/caja es para caja o administrador.
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const permitido = rol === 'caja' || esAdminHotel(rol)

  const consultar = useCallback(async (dia) => {
    setError('')
    setCargando(true)
    try {
      const r = await api(`/hotel/caja?fecha=${dia}`)
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); setCaja(null) }
      else setCaja(r.datos)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setCargando(false)
    }
  }, [])

  // La caja del día se ve al entrar, sin apretar nada.
  useEffect(() => {
    if (sesion.fase === 'ok' && permitido) consultar(fecha)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesion.fase, permitido])

  if (sesion.fase === 'ok' && !permitido) {
    return (
      <MarcoHotel titulo="Caja del día">
        <Subnav items={SUBNAV_CAJA} />
        <p className="estado">La caja del día es solo para caja o la administración del hotel.</p>
        <p><Link className="boton-primario" href="/hotel/pago">Registrar un pago</Link></p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Caja del día">
      <Subnav items={SUBNAV_CAJA} />
      <section className="tarjeta">
        <form className="formulario" onSubmit={(e) => { e.preventDefault(); consultar(fecha) }}>
          <Campo etiqueta="Fecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
          <button type="submit" className="boton-secundario">Ver caja</button>
          <Link className="boton-primario" href="/hotel/pago">Registrar pago</Link>
        </form>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      {cargando && !caja && <p className="estado" role="status" aria-busy="true">Cargando la caja…</p>}
      {caja && (
        <>
          <p className="resumen">
            Total del día: <strong>{clp(caja.total_clp)}</strong>
            {' '}· {caja.pagos.length === 1 ? '1 pago' : `${caja.pagos.length} pagos`}
          </p>
          {caja.pagos.length > 0 ? (
            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Pagos del día (desliza para ver todas las columnas)">
              <table className="tabla">
                <thead>
                  <tr>
                    <th>Hora</th>
                    <th>Huésped</th>
                    <th>Habitación</th>
                    <th>Reserva</th>
                    <th>Monto</th>
                    <th>Medio</th>
                  </tr>
                </thead>
                <tbody>
                  {caja.pagos.map((p) => (
                    <tr key={p.pago_id}>
                      <td>{p.registrado_en ? horaChile(p.registrado_en) : '—'}</td>
                      <td>{p.huesped_nombre || '—'}</td>
                      <td>{p.habitacion_id}</td>
                      <td><Link href={`/hotel/reservas/${p.reserva_id}`}>{p.reserva_id}</Link></td>
                      <td>{clp(p.monto_clp)}</td>
                      <td>{medioDePago(p.modo)}</td>
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
