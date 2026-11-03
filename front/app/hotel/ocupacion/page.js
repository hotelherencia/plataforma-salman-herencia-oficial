'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, Campo, useSesion } from '../../../lib/api'

/**
 * Ocupación y disponibilidad (spec-hotel-operacion-v1 §5): rejilla habitación
 * × noche de GET /hotel/ocupacion. El estado de cada noche lo decide la API
 * (con las mismas reglas que la oferta); aquí solo se pinta y se enlaza la
 * reserva. Las canceladas se listan aparte porque ya no ocupan cupo.
 */

const LEYENDA = {
  confirmada: ['Confirmada', 'reserva confirmada que ocupa el cupo'],
  en_estadia: ['En estadía', 'huésped alojado (check-in hecho)'],
  finalizada: ['Finalizada', 'noche pasada de una estadía ya liquidada'],
  disponible: ['Disponible', 'se puede vender (la oferta la incluye)'],
  sin_tarifa: ['Sin tarifa', 'libre, pero sin tarifa vigente: la oferta no la ofrece'],
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
        <span aria-label={titulo}>{contenido}</span>
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
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setDatos(r.datos)
        setFiltros({ desde: r.datos.periodo.desde, hasta: r.datos.periodo.hasta })
      }
    } catch {
      setError('La API no está disponible')
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
            Fecha de corte del servidor: <strong>{datos.fecha_corte}</strong> · {datos.periodo.noches} noche(s). La noche de una
            fecha va de ese día al siguiente.
          </p>
          <div className="rejilla-ocupacion">
            <table className="tabla ocupacion">
              <thead>
                <tr>
                  <th scope="col">Habitación</th>
                  {datos.noches.map((n) => (
                    <th key={n} scope="col" className={n === datos.fecha_corte ? 'hoy' : ''}>
                      {n.slice(5)}
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
                  <th scope="row">Disponibles / ocupadas</th>
                  {datos.resumen.map((r) => (
                    <td key={r.fecha} className="ocupacion-resumen">
                      {r.disponibles}/{r.ocupadas}
                    </td>
                  ))}
                </tr>
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
                  <Link href={`/hotel/reservas/${r.reserva_id}`}>{r.reserva_id}</Link> · {r.habitacion_id} · {r.inicio} → {r.fin} · {r.huesped_nombre}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </MarcoHotel>
  )
}
