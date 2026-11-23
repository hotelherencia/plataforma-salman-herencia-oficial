'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { api, clp, mensajeDeError, Campo, CampoSelect } from '../../../lib/api'
import { fechaATexto, plural } from '../../../lib/formato'

const ETIQUETA_TRAMO = {
  '0-30': '0 a 30 días',
  '31-60': '31 a 60 días',
  '61-90': '61 a 90 días',
  mas_90: 'Más de 90 días',
}

const ETIQUETA_POLITICA = {
  pago_al_registrarse: 'Pago al registrarse',
  credito_autorizado: 'Crédito autorizado',
  garantia_salida: 'Garantía con tarjeta a la Salida',
}

export { ETIQUETA_POLITICA }

/**
 * Listado de Cuentas por Cobrar agrupado por tramos de antigüedad (Contable 2.2 / #392).
 * Enlaza directo a cada reserva por nombre y habitación, sin JSON ni IDs crudos.
 */
export default function CuentasPorCobrar({ puedeCobrar = false }) {
  const [estadoFiltro, setEstadoFiltro] = useState('pendientes')
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [abonandoId, setAbonandoId] = useState(null)
  const [abono, setAbono] = useState({ monto_clp: '', medio: 'transferencia', comprobante: '', nota: '' })
  const [enviando, setEnviando] = useState(false)

  const cargar = useCallback(async (est = estadoFiltro) => {
    setError('')
    try {
      const r = await api(`/hotel/contabilidad/cuentas-por-cobrar?estado=${encodeURIComponent(est)}`)
      if (r.estado === 403) { setDatos(null); return }
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setDatos(r.datos)
    } catch {
      setError('No se pudo cargar el listado de cuentas por cobrar.')
    }
  }, [estadoFiltro])

  useEffect(() => {
    if (puedeCobrar) cargar(estadoFiltro)
  }, [puedeCobrar, estadoFiltro, cargar])

  async function registrarAbono(e, item) {
    e.preventDefault()
    setError('')
    setAviso('')
    const monto = Number(abono.monto_clp || item.saldo_pendiente_clp)
    if (!(monto > 0)) { setError('Indica un monto de abono mayor que $0.'); return }
    setEnviando(true)
    try {
      const r = await api(`/hotel/contabilidad/cuentas-por-cobrar/${encodeURIComponent(item.cxc_id)}/abonos`, {
        metodo: 'POST',
        claveIdempotencia: `cxc-${item.cxc_id}-${crypto.randomUUID().slice(0, 8)}`,
        cuerpo: {
          monto_clp: monto,
          medio: abono.medio,
          comprobante: abono.comprobante.trim() || null,
          nota: abono.nota.trim() || null,
        },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso(`Abono registrado por ${clp(monto)}. Nuevo saldo: ${clp(r.datos.saldo_pendiente_clp)}.`)
        setAbonandoId(null)
        setAbono({ monto_clp: '', medio: 'transferencia', comprobante: '', nota: '' })
        await cargar(estadoFiltro)
      }
    } catch {
      setError('No se pudo conectar con el servidor.')
    } finally {
      setEnviando(false)
    }
  }

  if (!puedeCobrar || !datos) return null

  return (
    <section className="tarjeta" aria-label="Cuentas por cobrar y antigüedad">
      <h2>Cuentas por cobrar (antigüedad)</h2>
      <div className="kpi-rejilla">
        <div className="kpi">
          <span className="kpi-titulo">Total por cobrar</span>
          <span className="kpi-valor">{clp(datos.total_pendiente_clp)}</span>
        </div>
        <div className={`kpi${datos.total_vencido_clp > 0 ? ' kpi-alerta' : ''}`}>
          <span className="kpi-titulo">Monto vencido</span>
          <span className="kpi-valor">{clp(datos.total_vencido_clp)}</span>
        </div>
        {Object.entries(ETIQUETA_TRAMO).map(([clave, titulo]) => (
          <div key={clave} className="kpi">
            <span className="kpi-titulo">{titulo}</span>
            <span className="kpi-valor">{clp(datos.tramos?.[clave]?.monto_clp || 0)}</span>
            <span className="kpi-detalle">{plural(datos.tramos?.[clave]?.cantidad || 0, 'cuenta')}</span>
          </div>
        ))}
      </div>

      <div className="filtros" style={{ marginTop: '0.75rem' }}>
        <CampoSelect etiqueta="Mostrar" value={estadoFiltro} onChange={(e) => setEstadoFiltro(e.target.value)}>
          <option value="pendientes">Pendientes (abiertas y parciales)</option>
          <option value="pagada">Pagadas</option>
          <option value="todos">Todas</option>
        </CampoSelect>
      </div>

      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      {datos.cuentas_por_cobrar.length === 0 ? (
        <p className="estado">No hay cuentas por cobrar en este filtro.</p>
      ) : (
        <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Listado de cuentas por cobrar">
          <table className="tabla">
            <thead>
              <tr>
                <th>Cliente / Empresa</th>
                <th>Estadía</th>
                <th>Vencimiento</th>
                <th>Tramo</th>
                <th>Original</th>
                <th>Pendiente</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {datos.cuentas_por_cobrar.map((c) => (
                <tr key={c.cxc_id}>
                  <td>
                    <strong>{c.cliente_nombre}</strong>
                    <div className="nota-clave">{c.cliente_rut} · {ETIQUETA_POLITICA[c.politica_aplicada] || c.politica_aplicada}</div>
                  </td>
                  <td>
                    <Link href={`/hotel/reservas/${encodeURIComponent(c.reserva_id)}`}>
                      Hab. {c.habitacion_id} · {c.huesped_nombre}
                    </Link>
                  </td>
                  <td>
                    {fechaATexto(c.fecha_vencimiento)}
                    {c.vencida && <div className="alerta">Vencida ({c.dias_vencido} d)</div>}
                  </td>
                  <td>{ETIQUETA_TRAMO[c.tramo_antiguedad] || c.tramo_antiguedad}</td>
                  <td>{clp(c.monto_original_clp)}</td>
                  <td><strong>{clp(c.saldo_pendiente_clp)}</strong></td>
                  <td>
                    {c.saldo_pendiente_clp > 0 && (
                      abonandoId === c.cxc_id ? (
                        <form className="formulario" onSubmit={(e) => registrarAbono(e, c)}>
                          <Campo etiqueta="Monto (CLP)" type="number" min="1" max={c.saldo_pendiente_clp}
                            placeholder={String(c.saldo_pendiente_clp)} value={abono.monto_clp}
                            onChange={(e) => setAbono({ ...abono, monto_clp: e.target.value })} />
                          <CampoSelect etiqueta="Medio" value={abono.medio} onChange={(e) => setAbono({ ...abono, medio: e.target.value })}>
                            <option value="transferencia">Transferencia</option>
                            <option value="efectivo">Efectivo</option>
                            <option value="debito">Débito</option>
                            <option value="credito">Crédito</option>
                          </CampoSelect>
                          <Campo etiqueta="Comprobante" value={abono.comprobante}
                            onChange={(e) => setAbono({ ...abono, comprobante: e.target.value })} />
                          <button type="submit" className="boton-primario" disabled={enviando}>Guardar abono</button>
                          <button type="button" className="boton-fantasma" onClick={() => setAbonandoId(null)}>Cancelar</button>
                        </form>
                      ) : (
                        <button type="button" className="boton-secundario" onClick={() => setAbonandoId(c.cxc_id)}>
                          Registrar abono
                        </button>
                      )
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
