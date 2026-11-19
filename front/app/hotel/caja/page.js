'use client'

import Link from 'next/link'
import { Suspense, useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { api, clp, mensajeDeError, MarcoHotel, Campo, useSesion } from '../../../lib/api'
import { esAdminHotel } from '../../../lib/roles'
import { horaChile } from '../../../lib/estadias'
import { nombreDocumento, nombreMedio } from '../../../lib/caja'
import { fechaATexto } from '../../../lib/formato'
import Subnav from '../_componentes/subnav'
import MovimientosContables from '../_componentes/movimientos-contables'
import { hoyChile, PestanaCierreDiario, PestanaMovimientos, PestanaTurno } from '../_componentes/caja-contable'
import css from '../_componentes/operacion.module.css'
import { PESTANAS_CAJA, SUBNAV_CAJA } from '../../../lib/menu-hotel'

// Fase 1 contable (2026-11-19): pestañas dentro de Caja y pagos (sin ítem de
// menú nuevo). Caja y administración ven todo; recepción opera el turno.
const POR_ROL = {
  caja: ['dia', 'turno', 'movimientos', 'cuenta', 'depositos', 'cierre'],
  recepcion: ['turno', 'movimientos', 'depositos'],
}

export default function Caja() {
  return <Suspense fallback={null}><CajaConPestanas /></Suspense>
}

function CajaConPestanas() {
  const sesion = useSesion()
  const router = useRouter()
  const params = useSearchParams()
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const esAdmin = esAdminHotel(rol)
  const visibles = esAdmin ? POR_ROL.caja : (POR_ROL[rol] || [])
  const pestanas = PESTANAS_CAJA.filter(([id]) => visibles.includes(id))
  const pedida = params.get('pestana')
  const pestana = visibles.includes(pedida) ? pedida : visibles[0]

  if (sesion.fase === 'ok' && visibles.length === 0) {
    return (
      <MarcoHotel titulo="Caja y pagos">
        <Subnav items={SUBNAV_CAJA} />
        <p className="estado">La caja es para caja, recepción o la administración del hotel.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Caja y pagos">
      <Subnav items={SUBNAV_CAJA} />
      <div className={css.pestanas} role="tablist" aria-label="Secciones de la caja">
        {pestanas.map(([id, nombre]) => (
          <button key={id} type="button" role="tab" id={`pestana-${id}`} aria-controls="panel-caja"
            aria-selected={pestana === id} className={css.pestana}
            onClick={() => router.replace(`/hotel/caja?pestana=${id}`, { scroll: false })}>
            {nombre}
          </button>
        ))}
      </div>
      <div role="tabpanel" id="panel-caja" aria-labelledby={`pestana-${pestana}`}>
      {sesion.fase === 'ok' && pestana === 'dia' && <CajaDelDia />}
      {sesion.fase === 'ok' && pestana === 'cuenta' && <MovimientosContables hoy={hoyChile()} />}
      {sesion.fase === 'ok' && pestana === 'turno' && <PestanaTurno esAdmin={esAdmin} />}
      {sesion.fase === 'ok' && pestana === 'movimientos' && <PestanaMovimientos esAdmin={esAdmin} />}
      {sesion.fase === 'ok' && pestana === 'depositos' && <PestanaMovimientos esAdmin={esAdmin} soloDepositos />}
      {sesion.fase === 'ok' && pestana === 'cierre' && <PestanaCierreDiario esAdmin={esAdmin} />}
      </div>
    </MarcoHotel>
  )
}

function CajaDelDia() {
  const [fecha, setFecha] = useState(hoyChile)
  const [caja, setCaja] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { consultar(fecha) }, [])

  return (
    <>
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
            Total del {fechaATexto(caja.fecha)}: <strong>{clp(caja.total_clp)}</strong>
            {' '}· {caja.pagos.length === 1 ? '1 pago' : `${caja.pagos.length} pagos`}
            {Object.entries(caja.por_medio || {}).map(([m, monto]) => ` · ${nombreMedio(m)} ${clp(monto)}`).join('')}
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
                    <th>Documento</th>
                  </tr>
                </thead>
                <tbody>
                  {caja.pagos.map((p) => (
                    <tr key={p.pago_id}>
                      <td>{p.registrado_en ? horaChile(p.registrado_en) : '—'}</td>
                      <td>{p.huesped_nombre || '—'}</td>
                      <td>{p.habitacion_id}</td>
                      <td><Link href={`/hotel/reservas/${p.reserva_id}`}>{p.reserva_id}</Link></td>
                      <td>{clp(p.monto_clp)}{p.tipo === 'reverso' ? ' (reverso)' : ''}{p.es_anticipo ? ' (anticipo)' : ''}</td>
                      <td>{nombreMedio(p.medio)}</td>
                      <td>{p.tipo === 'reverso' ? '—' : nombreDocumento(p.documento_tipo)}</td>
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
    </>
  )
}
