'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, clp } from '../../../lib/api'
import { porcentaje } from '../../../lib/formato'
import { rangoMes, resumenSerie, puntosLinea } from '../../../lib/panel-serie'
import { alertasDueno, flechaVariacion, mesAnterior, variacion } from '../../../lib/resumen-dueno'

const ENLACE = { cxc: '/hotel/caja', atencion: '/hotel/panel', mant: '/hotel/panel', turnos: '/hotel/panel', sug: '/hotel/panel' }

async function leer(ruta) {
  try {
    const r = await api(ruta)
    return r.estado === 200 ? r.datos : null
  } catch {
    return null
  }
}

function Kpi({ titulo, valor, pie }) {
  return (
    <div className="tarjeta-estado">
      <span className="estado-nombre">{titulo}</span>
      <div className="estado-conteo">
        <span className="estado-cantidad">{valor}</span>
      </div>
      {pie && <span className="estado-pct">{pie}</span>}
    </div>
  )
}

/** Resumen del dueño: el mes en una mirada, comparado con el anterior, más lo que pide su atención. */
export default function ResumenDueno({ corte }) {
  const [d, setD] = useState(null)

  useEffect(() => {
    if (!corte) return
    let vivo = true
    ;(async () => {
      const mes = rangoMes(corte)
      const ant = mesAnterior(mes.desde)
      const [actual, previo, cxc, cxp, mant, sug, cambios] = await Promise.all([
        leer(`/hotel/indicadores?desde=${mes.desde}&hasta=${mes.hasta}`),
        leer(`/hotel/indicadores?desde=${ant.desde}&hasta=${ant.hasta}`),
        leer('/hotel/contabilidad/cuentas-por-cobrar'),
        leer('/hotel/productos/cuentas-por-pagar?estado=pendientes'),
        leer('/hotel/mantenciones?dentro_de_dias=0'),
        leer('/hotel/sugerencias?estado=nueva'),
        leer('/hotel/turnos/cambios?estado=pendiente'),
      ])
      if (vivo) setD({ mes, actual, previo, cxc, cxp, mant, sug, cambios })
    })()
    return () => {
      vivo = false
    }
  }, [corte])

  if (!d || !d.actual) return null
  const p = d.actual.periodo_indicadores
  const q = d.previo?.periodo_indicadores
  const valorDe = (ind) => (ind ? ind.valor : null)
  const ocup = valorDe(p.ocupacion)
  const ingresos = valorDe(p.ingreso_alojamiento_clp)
  const alertas = alertasDueno({
    atencionTotal: d.actual.atencion?.total ?? 0,
    cxcVencidoClp: d.cxc?.total_vencido_clp ?? 0,
    mantencionesVencidas: (d.mant?.mantenciones || []).filter((m) => m.vencida).length,
    sugerenciasNuevas: d.sug?.sugerencias?.length ?? 0,
    cambiosTurno: d.cambios?.cambios?.length ?? 0,
  })
  const res = resumenSerie(d.actual.serie)
  const pts = res ? puntosLinea(res.puntos) : []
  const linea = pts.map((q2) => `${q2.x},${q2.y}`).join(' ')

  return (
    <section className="tarjeta" aria-label="Resumen del dueño" data-resumen-dueno>
      <h2>Resumen del mes</h2>
      <p className="nota-clave">Del {d.mes.desde} al {d.mes.hasta} (sin incluir). Cifras del servidor, comparadas con el mes anterior.</p>
      <div className="kpi-rejilla">
        <Kpi titulo="Ocupación del mes" valor={porcentaje(ocup)} pie={flechaVariacion(variacion(ocup, valorDe(q?.ocupacion)))} />
        <Kpi titulo="Ingreso por alojamiento" valor={ingresos === null ? 'sin muestra' : clp(ingresos)} pie={flechaVariacion(variacion(ingresos, valorDe(q?.ingreso_alojamiento_clp)))} />
        <Kpi titulo="Tarifa media (ADR)" valor={valorDe(p.adr_clp) === null ? 'sin muestra' : clp(valorDe(p.adr_clp))} pie={flechaVariacion(variacion(valorDe(p.adr_clp), valorDe(q?.adr_clp)))} />
        <Kpi titulo="RevPAR" valor={valorDe(p.revpar_clp) === null ? 'sin muestra' : clp(valorDe(p.revpar_clp))} pie={flechaVariacion(variacion(valorDe(p.revpar_clp), valorDe(q?.revpar_clp)))} />
        {p.ingresos_periodo_clp && <Kpi titulo="Recaudado en el mes" valor={clp(p.ingresos_periodo_clp.valor)} pie={flechaVariacion(variacion(p.ingresos_periodo_clp.valor, valorDe(q?.ingresos_periodo_clp)))} />}
        {d.cxc && <Kpi titulo="Por cobrar a clientes" valor={clp(d.cxc.total_pendiente_clp)} pie={d.cxc.total_vencido_clp > 0 ? `${clp(d.cxc.total_vencido_clp)} vencido` : 'nada vencido'} />}
        {d.cxp && <Kpi titulo="Por pagar a proveedores" valor={clp(d.cxp.total_pendiente_clp)} pie="facturas con saldo pendiente" />}
      </div>
      {res && pts.length > 1 && (
        <div className="serie-resumen">
          <h3 className="subtitulo">Ocupación noche a noche (promedio {res.promedio} %)</h3>
          <svg className="serie-linea" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`Ocupación diaria del mes, promedio ${res.promedio} por ciento`}>
            <line x1="0" y1="50" x2="100" y2="50" className="serie-guia" />
            <polygon points={`0,100 ${linea} 100,100`} className="serie-area" />
            <polyline points={linea} className="serie-trazo" vectorEffect="non-scaling-stroke" />
          </svg>
        </div>
      )}
      <h3 className="subtitulo">Lo que pide tu atención</h3>
      {alertas.length === 0 ? (
        <p className="estado" role="status">Todo al día: no hay nada pendiente para ti.</p>
      ) : (
        <ul className="lista-simple">
          {alertas.map((a) => (
            <li key={a.clave}>
              <Link href={ENLACE[a.clave]}>{a.texto}: <strong>{a.tipo === 'clp' ? clp(a.valor) : a.valor}</strong></Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
