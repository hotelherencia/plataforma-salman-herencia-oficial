'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, Campo, useSesion } from '../../../lib/api'
import { fechaATexto, fechaCorta, plural } from '../../../lib/formato'
import { BotonExportar } from '../_componentes/boton-exportar'

/**
 * Ocupación y disponibilidad (spec-hotel-operacion-v1 §5): rejilla habitación
 * × noche de GET /hotel/ocupacion. El estado de cada noche lo decide la API
 * (con las mismas reglas que la oferta); aquí solo se pinta y se enlaza la
 * reserva. Las canceladas se listan aparte porque ya no ocupan cupo.
 */

const LEYENDA = {
  confirmada: ['Confirmada', 'reserva confirmada que ocupa el cupo'],
  en_estadia: ['En estadía', 'huésped alojado (Llegada registrada)'],
  finalizada: ['Finalizada', 'noche pasada de una estadía ya liquidada'],
  disponible: ['Disponible', 'se puede vender (la oferta la incluye)'],
  sin_tarifa: ['Sin precio', 'libre, pero sin precio para esa noche: la oferta no la ofrece'],
  no_vendible: ['No vendible', 'mantenimiento o fuera de servicio'],
  sin_ocupar: ['Sin ocupar', 'noche pasada sin estadía'],
}

const CORTO = {
  confirmada: 'C',
  en_estadia: 'E',
  finalizada: 'F',
  disponible: '',
  sin_tarifa: '$?',
  no_vendible: '×',
  sin_ocupar: '',
}

function fechaLarga(iso) {
  if (!iso || typeof iso !== 'string') return ''
  const [a, m, d] = iso.split('-')
  return a && m && d ? `${d}/${m}/${a}` : iso
}

function Celda({ noche }) {
  const [nombre, explicacion] = LEYENDA[noche.estado] || [noche.estado, '']
  const titulo = [
    `${noche.fecha}: ${nombre}`,
    noche.reserva_id && `reserva ${noche.reserva_id}`,
    noche.motivo && `motivo ${noche.motivo.replaceAll('_', ' ')}`,
    noche.tarifa_noche_clp && `${clp(noche.tarifa_noche_clp)}/noche`,
    explicacion,
  ]
    .filter(Boolean)
    .join(' · ')
  const contenido = CORTO[noche.estado] ?? ''
  return (
    <td className={`noche noche-${noche.estado}`} title={titulo} data-estado={noche.estado}>
      {noche.reserva_id ? (
        <Link href={`/hotel/reservas/${noche.reserva_id}`} aria-label={titulo}>
          {contenido}
        </Link>
      ) : (
        <>
          <span aria-hidden="true">{contenido}</span>
          <span className="sr-only">{titulo}</span>
        </>
      )}
    </td>
  )
}

export default function Ocupacion() {
  const sesion = useSesion()
  const [filtros, setFiltros] = useState({ desde: '', hasta: '' })
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')

  async function cargar(f) {
    setError('')
    const params = new URLSearchParams()
    if (f.desde) params.set('desde', f.desde)
    if (f.hasta) params.set('hasta', f.hasta)
    try {
      const r = await api(`/hotel/ocupacion?${params}`)
      if (r.estado >= 400) {
        setDatos(null)
        setError(mensajeDeError(r.datos, r.estado))
      } else {
        setDatos(r.datos)
        setFiltros({ desde: r.datos.periodo.desde, hasta: r.datos.periodo.hasta })
      }
    } catch {
      setDatos(null)
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  useEffect(() => {
    if (sesion.fase === 'ok') cargar({ desde: '', hasta: '' })
  }, [sesion.fase])

  const canceladas = datos
    ? datos.habitaciones.flatMap((h) => h.reservas.filter((r) => r.estado === 'cancelada').map((r) => ({ ...r, habitacion_id: h.habitacion_id })))
    : []

  return (
    <MarcoHotel titulo="Ocupación y disponibilidad">
      <section className="tarjeta">
        <form
          className="formulario"
          onSubmit={(e) => {
            e.preventDefault()
            cargar(filtros)
          }}
        >
          <Campo etiqueta="Desde (noche)" type="date" value={filtros.desde} onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })} />
          <Campo etiqueta="Hasta (sin incluir)" type="date" value={filtros.hasta} onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })} />
          <button type="submit" className="boton-primario">Ver periodo</button>
          {datos && datos.habitaciones && (
            <BotonExportar
              titulo="Ocupación y disponibilidad"
              filtros={`${datos.periodo.desde} a ${datos.periodo.hasta}`}
              columnas={['Habitación', 'Tipo', 'Capacidad'].concat(datos.noches)}
              filas={datos.habitaciones.map((h) => [h.habitacion_id, h.tipo, h.capacidad].concat(h.noches.map((n) => n.reserva_id ? `${n.estado} (${n.reserva_id})` : n.estado)))}
              nombreArchivo={`herencia-ocupacion-${datos.periodo.desde}_a_${datos.periodo.hasta}.csv`}
            />
          )}
        </form>
        <ul className="leyenda" aria-label="Leyenda">
          {Object.entries(LEYENDA).map(([estado, [nombre, explicacion]]) => (
            <li key={estado}>
              <span className={`muestra noche-${estado}`}>{CORTO[estado]}</span> <strong>{nombre}</strong>: {explicacion}
            </li>
          ))}
        </ul>
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}

      {datos && (
        <section className="tarjeta">
          <p className="nota-clave">
            Datos al <strong>{fechaLarga(datos.fecha_corte)}</strong> · {plural(datos.periodo.noches, 'noche')}. La noche de una
            fecha va de ese día al siguiente.
          </p>
          <div className="rejilla-ocupacion" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)">
            <table className="tabla ocupacion">
              <thead>
                <tr>
                  <th scope="col">Habitación</th>
                  {datos.noches.map((n) => (
                    <th key={n} scope="col" className={n === datos.fecha_corte ? 'hoy' : ''}>
                      {fechaCorta(n)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {datos.habitaciones.map((h) => (
                  <tr key={h.habitacion_id}>
                    <th scope="row" className="ocupacion-habitacion">
                      <Link href={`/hotel/habitaciones/${h.habitacion_id}`}>{h.habitacion_id}</Link>
                      <span className="ocupacion-sub">
                        {h.tipo} · {h.capacidad} pers.
                        {!h.en_servicio && ' · fuera de servicio'}
                        {h.mantenimiento && ' · mantenimiento'}
                      </span>
                    </th>
                    {h.noches.map((n) => (
                      <Celda key={n.fecha} noche={n} />
                    ))}
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row">Disponibles / cupo ocupado</th>
                  {datos.resumen.map((r) => (
                    <td key={r.fecha} className="ocupacion-resumen">
                      {r.disponibles}/{r.ocupadas_cupo}
                    </td>
                  ))}
                </tr>
                {Object.entries(
                  datos.habitaciones.reduce((acc, h) => {
                    const t = h.tipo || 'Otro'
                    if (!acc[t]) acc[t] = []
                    acc[t].push(h)
                    return acc
                  }, {})
                ).map(([tipo, habsTipo]) => (
                  <tr key={tipo} style={{ fontSize: '0.86em', opacity: 0.9 }}>
                    <th scope="row" style={{ paddingLeft: '1rem' }}>↳ {tipo} ({habsTipo.length})</th>
                    {datos.noches.map((fecha) => {
                      let disp = 0
                      let ocup = 0
                      for (const h of habsTipo) {
                        const n = h.noches.find((x) => x.fecha === fecha)
                        if (!n) continue
                        if (n.estado === 'disponible') disp += 1
                        else if (n.estado === 'confirmada' || n.estado === 'en_estadia') ocup += 1
                      }
                      return (
                        <td key={fecha} className="ocupacion-resumen">
                          {disp}/{ocup}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tfoot>
            </table>
          </div>

          <h3 className="subtitulo">Canceladas que tocaban el periodo (no ocupan cupo)</h3>
          {canceladas.length === 0 ? (
            <p className="estado">Ninguna.</p>
          ) : (
            <ul className="lista-simple">
              {canceladas.map((r) => (
                <li key={r.reserva_id}>
                  <Link href={`/hotel/reservas/${r.reserva_id}`}>{r.reserva_id}</Link> · {r.habitacion_id} · {fechaATexto(r.inicio)} → {fechaATexto(r.fin)} · {r.huesped_nombre}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </MarcoHotel>
  )
}
