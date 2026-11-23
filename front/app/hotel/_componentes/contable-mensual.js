'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, clp, mensajeDeError, Campo } from '../../../lib/api'
import { fechaATexto } from '../../../lib/formato'

/**
 * Contabilidad 2.3 (#393) y 2.4 (#394):
 * - Cuadratura diaria de ocupación, noches devengadas y abonos (anticipos).
 * - Cierre mensual y matriz habitaciones × días (equivalente a «Ocupación 2026») con descarga CSV.
 */
export default function ContableMensual({ fechaDia, esAdmin }) {
  const [cuadratura, setCuadratura] = useState(null)
  const [errCuad, setErrCuad] = useState('')

  const hoyPartes = (fechaDia || new Date().toISOString().slice(0, 10)).split('-')
  const [anio, setAnio] = useState(Number(hoyPartes[0]) || 2026)
  const [mes, setMes] = useState(Number(hoyPartes[1]) || 1)
  const [mensual, setMensual] = useState(null)
  const [errMes, setErrMes] = useState('')
  const [avisoMes, setAvisoMes] = useState('')
  const [nota, setNota] = useState('')
  const [confirma, setConfirma] = useState(false)
  const [motivoReap, setMotivoReap] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (!fechaDia) return
    let cancelado = false
    setErrCuad('')
    api(`/hotel/contabilidad/cuadratura-diaria?fecha=${encodeURIComponent(fechaDia)}`)
      .then((r) => {
        if (cancelado) return
        if (r.estado >= 400) { setErrCuad(mensajeDeError(r.datos, r.estado)); setCuadratura(null) }
        else setCuadratura(r.datos)
      })
      .catch(() => { if (!cancelado) setErrCuad('No se pudo cargar la cuadratura diaria.') })
    return () => { cancelado = true }
  }, [fechaDia])

  const cargarMes = useCallback(async (a = anio, m = mes) => {
    setErrMes('')
    setAvisoMes('')
    try {
      const r = await api(`/hotel/contabilidad/cierre-mensual?anio=${a}&mes=${m}`)
      if (r.estado >= 400) { setErrMes(mensajeDeError(r.datos, r.estado)); setMensual(null) }
      else setMensual(r.datos)
    } catch {
      setErrMes('No se pudo cargar el cierre mensual.')
    }
  }, [anio, mes])

  useEffect(() => { cargarMes(anio, mes) }, [anio, mes, cargarMes])

  async function cerrarMes(e) {
    e.preventDefault()
    setErrMes('')
    setAvisoMes('')
    if (mensual?.alertas?.length && !confirma) {
      setErrMes('Revisa las alertas del mes y marca la confirmación.')
      return
    }
    setEnviando(true)
    try {
      const r = await api('/hotel/contabilidad/cierre-mensual', {
        metodo: 'POST',
        claveIdempotencia: `cmes-${anio}-${mes}-${crypto.randomUUID().slice(0, 8)}`,
        cuerpo: { anio, mes, nota: nota.trim() || null, confirmar_alertas: confirma },
      })
      if (r.estado >= 400) setErrMes(mensajeDeError(r.datos, r.estado))
      else {
        setAvisoMes(`Mes ${r.datos.periodo} cerrado y congelado.`)
        setNota('')
        setConfirma(false)
        await cargarMes(anio, mes)
      }
    } catch {
      setErrMes('No se pudo conectar con el servidor.')
    } finally {
      setEnviando(false)
    }
  }

  async function reabrirMes(e) {
    e.preventDefault()
    setErrMes('')
    setAvisoMes('')
    if (motivoReap.trim().length < 10) {
      setErrMes('Explica el motivo de la reapertura mensual (mínimo 10 caracteres).')
      return
    }
    setEnviando(true)
    try {
      const r = await api(`/hotel/contabilidad/cierre-mensual/${anio}/${mes}/reapertura`, {
        metodo: 'POST',
        claveIdempotencia: `rmes-${anio}-${mes}-${crypto.randomUUID().slice(0, 8)}`,
        cuerpo: { motivo: motivoReap.trim() },
      })
      if (r.estado >= 400) setErrMes(mensajeDeError(r.datos, r.estado))
      else {
        setAvisoMes(`Mes ${r.datos.periodo} reabierto.`)
        setMotivoReap('')
        await cargarMes(anio, mes)
      }
    } catch {
      setErrMes('No se pudo conectar con el servidor.')
    } finally {
      setEnviando(false)
    }
  }

  const cerrado = mensual?.cierre?.estado === 'cerrado'

  return (
    <>
      <section className="tarjeta" aria-label="Cuadratura diaria de ocupación, noches y abonos">
        <h2>Cuadratura diaria de ocupación, noches y abonos ({fechaDia ? fechaATexto(fechaDia) : '—'})</h2>
        {errCuad && <p role="alert" className="alerta">{errCuad}</p>}
        {cuadratura && (
          <>
            <div className="kpi-rejilla">
              <div className="kpi">
                <span className="kpi-titulo">Noches ocupadas</span>
                <span className="kpi-valor">
                  {cuadratura.ocupacion.noches_ocupadas} / {cuadratura.ocupacion.habitaciones_disponibles}
                </span>
              </div>
              <div className="kpi">
                <span className="kpi-titulo">Alojamiento devengado</span>
                <span className="kpi-valor">{clp(cuadratura.noches.devengado_alojamiento_clp)}</span>
              </div>
              <div className="kpi">
                <span className="kpi-titulo">Imputado a la noche</span>
                <span className="kpi-valor">{clp(cuadratura.noches.imputado_noche_clp)}</span>
              </div>
              <div className="kpi">
                <span className="kpi-titulo">Abonos vigentes (pasivo)</span>
                <span className="kpi-valor">{clp(cuadratura.abonos.saldo_vigente_clp)}</span>
              </div>
              <div className="kpi">
                <span className="kpi-titulo">Tarifa promedio del día</span>
                <span className="kpi-valor">
                  {cuadratura.noches.adr_clp === null ? 'sin muestra' : clp(cuadratura.noches.adr_clp)}
                </span>
              </div>
              <div className={`kpi${cuadratura.cuadra ? '' : ' kpi-alerta'}`}>
                <span className="kpi-titulo">Estado cuadratura</span>
                <span className="kpi-valor">{cuadratura.cuadra ? 'Cuadra' : `${cuadratura.diferencias.length} dif.`}</span>
              </div>
            </div>
            {cuadratura.diferencias.length > 0 && (
              <ul className="lista-simple">
                {cuadratura.diferencias.map((d, idx) => (
                  <li key={`${d.tipo}-${idx}`}>{d.detalle}</li>
                ))}
              </ul>
            )}
          </>
        )}
      </section>

      <section className="tarjeta" aria-label="Cierre mensual y matriz habitaciones por días">
        <h2>Cierre mensual y matriz de ocupación</h2>
        <form
          className="formulario"
          onSubmit={(e) => { e.preventDefault(); cargarMes(anio, mes) }}
        >
          <Campo etiqueta="Año" type="number" min="2020" max="2100" value={String(anio)} onChange={(e) => setAnio(Number(e.target.value) || 2026)} />
          <Campo etiqueta="Mes" type="number" min="1" max="12" value={String(mes)} onChange={(e) => setMes(Number(e.target.value) || 1)} />
          <button type="submit" className="boton-secundario">Ver mes</button>
          <a
            className="boton-secundario"
            href={`/api/hotel/contabilidad/cierre-mensual/exportar.csv?anio=${anio}&mes=${mes}`}
            download={`ocupacion-${anio}-${String(mes).padStart(2, '0')}.csv`}
          >
            Exportar matriz CSV (Excel)
          </a>
        </form>

        {errMes && <p role="alert" className="alerta">{errMes}</p>}
        {avisoMes && <p role="status" className="aviso-ok">{avisoMes}</p>}

        {mensual && (
          <>
            <p className="nota-clave">
              Periodo <strong>{mensual.periodo}</strong> · Estado: <strong>{cerrado ? 'Cerrado (congelado)' : 'Abierto (en vivo)'}</strong> ·
              Ocupación: <strong>{mensual.resumen.ocupacion_pct === null ? 'sin muestra' : `${String(mensual.resumen.ocupacion_pct).replace('.', ',')} %`}</strong> ·
              Alojamiento devengado: <strong>{clp(mensual.resumen.ingreso_alojamiento_clp)}</strong> ·
              Tarifa promedio: <strong>{mensual.resumen.adr_clp === null ? 'sin muestra' : clp(mensual.resumen.adr_clp)}</strong> ·
              Ingreso por hab. disp.: <strong>{mensual.resumen.revpar_clp === null ? 'sin muestra' : clp(mensual.resumen.revpar_clp)}</strong>
            </p>

            {mensual.alertas?.length > 0 && (
              <ul className="lista-simple">
                {mensual.alertas.map((a) => <li key={a}>{a}</li>)}
              </ul>
            )}

            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Matriz habitaciones por días del mes">
              <table className="tabla">
                <thead>
                  <tr>
                    <th>Hab.</th>
                    {mensual.dias.map((d) => <th key={d}>{d.slice(-2)}</th>)}
                    <th>Noches</th>
                    <th>Ingreso</th>
                  </tr>
                </thead>
                <tbody>
                  {mensual.matriz.map((fila) => (
                    <tr key={fila.habitacion_id}>
                      <td><strong>{fila.habitacion_id}</strong></td>
                      {fila.celdas.map((c) => (
                        <td key={c.fecha} title={`${c.fecha}: ${c.estado}`}>
                          {c.codigo || '·'}
                        </td>
                      ))}
                      <td>{fila.totales.noches_ocupadas}</td>
                      <td>{clp(fila.totales.ingreso_alojamiento_clp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {!cerrado && (
              <form className="formulario" onSubmit={cerrarMes} style={{ marginTop: '0.75rem' }}>
                <Campo etiqueta="Nota del cierre mensual (opcional)" value={nota} onChange={(e) => setNota(e.target.value)} maxLength={1000} />
                {mensual.alertas?.length > 0 && (
                  <label className="campo-check">
                    <input type="checkbox" checked={confirma} onChange={(e) => setConfirma(e.target.checked)} />
                    Revisé las alertas y cierro el mes igual
                  </label>
                )}
                <button type="submit" className="boton-primario" disabled={enviando}>
                  {enviando ? 'Cerrando mes…' : `Cerrar mes ${mensual.periodo}`}
                </button>
              </form>
            )}

            {cerrado && esAdmin && (
              <form className="formulario" onSubmit={reabrirMes} style={{ marginTop: '0.75rem' }}>
                <Campo etiqueta="Motivo de reapertura mensual (mínimo 10 caracteres)" value={motivoReap} onChange={(e) => setMotivoReap(e.target.value)} maxLength={500} />
                <button type="submit" className="boton-secundario" disabled={enviando}>Reabrir mes</button>
              </form>
            )}
          </>
        )}
      </section>
    </>
  )
}
