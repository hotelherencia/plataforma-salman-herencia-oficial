'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, Campo, CampoSelect, Definicion, useSesion } from '../../../lib/api'

/**
 * Panel operativo (spec-hotel-operacion-v1 §4): dibuja GET /hotel/indicadores
 * tal como llega. Ningún valor se recalcula aquí; cada indicador muestra la
 * fórmula, unidad, fuente y limitaciones que declara la API, y un valor null
 * se presenta como «sin muestra», nunca como cero. Los atajos de periodo se
 * cuentan desde la fecha de corte del servidor, no desde el reloj del
 * navegador.
 */

function sumarDias(isoFecha, dias) {
  const d = new Date(`${isoFecha}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + dias)
  return d.toISOString().slice(0, 10)
}

function porcentaje(valor) {
  return valor === null || valor === undefined ? 'sin muestra' : `${(valor * 100).toFixed(1)} %`
}

const SITUACION = [
  ['llegadas_hoy', 'Llegadas de hoy'],
  ['salidas_hoy', 'Salidas de hoy'],
  ['en_casa', 'Huéspedes en casa'],
  ['llegadas_vencidas', 'Llegadas vencidas sin check-in', true],
  ['salidas_vencidas', 'Salidas vencidas sin check-out', true],
]

const HABITACIONES = [
  ['habitaciones_total', 'Habitaciones registradas'],
  ['habitaciones_vendibles', 'Vendibles'],
  ['habitaciones_ocupadas', 'Ocupadas ahora'],
  ['habitaciones_sucias', 'Sucias'],
  ['limpiezas_pendientes', 'Limpiezas pendientes'],
  ['en_mantenimiento', 'En mantenimiento'],
  ['fuera_de_servicio', 'Fuera de servicio'],
]

function Tarjeta({ titulo, indicador, alerta, valor }) {
  if (!indicador) return null
  const mostrar = valor !== undefined ? valor : indicador.valor
  return (
    <div className={`kpi${alerta && indicador.valor > 0 ? ' kpi-alerta' : ''}`}>
      <span className="kpi-titulo">{titulo}</span>
      <span className="kpi-valor">{mostrar}</span>
      {Array.isArray(indicador.reservas) && indicador.reservas.length > 0 && (
        <span className="kpi-reservas">
          {indicador.reservas.map((id) => (
            <Link key={id} href={`/hotel/reservas/${id}`}>
              {id}
            </Link>
          ))}
        </span>
      )}
      <Definicion indicador={indicador} />
    </div>
  )
}

export default function Panel() {
  const sesion = useSesion()
  const [filtros, setFiltros] = useState({ desde: '', hasta: '', tipo: '' })
  const [tipos, setTipos] = useState([])
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(false)

  async function cargar(f) {
    setError('')
    setCargando(true)
    const params = new URLSearchParams()
    if (f.desde) params.set('desde', f.desde)
    if (f.hasta) params.set('hasta', f.hasta)
    if (f.tipo) params.set('tipo', f.tipo)
    try {
      const r = await api(`/hotel/indicadores?${params}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setDatos(r.datos)
        setFiltros({ desde: r.datos.periodo.desde, hasta: r.datos.periodo.hasta, tipo: f.tipo })
      }
    } catch {
      setError('La API no está disponible')
    } finally {
      setCargando(false)
    }
  }

  useEffect(() => {
    if (sesion.fase !== 'ok') return
    cargar({ desde: '', hasta: '', tipo: '' })
    api('/hotel/habitaciones')
      .then((r) => {
        if (r.estado === 200) setTipos([...new Set(r.datos.habitaciones.map((h) => h.tipo))].sort())
      })
      .catch(() => {})
  }, [sesion.fase])

  const corte = datos?.fecha_corte
  const atajo = (desde, hasta) => cargar({ ...filtros, desde, hasta })
  const p = datos?.periodo_indicadores

  return (
    <MarcoHotel titulo="Panel operativo">
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
          <CampoSelect etiqueta="Tipo de habitación" value={filtros.tipo} onChange={(e) => setFiltros({ ...filtros, tipo: e.target.value })}>
            <option value="">(todos)</option>
            {tipos.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </CampoSelect>
          <button type="submit" className="boton-primario">Actualizar</button>
        </form>
        {corte && (
          <div className="atajos">
            <button type="button" className="boton-fantasma" onClick={() => atajo(corte, sumarDias(corte, 1))}>Hoy</button>
            <button type="button" className="boton-fantasma" onClick={() => atajo(sumarDias(corte, -7), sumarDias(corte, 1))}>Últimos 7 días</button>
            <button type="button" className="boton-fantasma" onClick={() => atajo(sumarDias(corte, -30), sumarDias(corte, 1))}>Últimos 30 días</button>
            <button type="button" className="boton-fantasma" onClick={() => atajo(corte, sumarDias(corte, 14))}>Próximos 14 días</button>
          </div>
        )}
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}
      {cargando && <p className="estado">Calculando…</p>}

      {datos && (
        <>
          <p className="nota-clave">
            Fecha de corte del servidor: <strong>{datos.fecha_corte}</strong> · periodo {datos.periodo.desde} → {datos.periodo.hasta} ({datos.periodo.noches} noche(s))
            {datos.filtros.tipo ? ` · tipo ${datos.filtros.tipo}` : ''}
          </p>

          <section className="tarjeta" aria-label="Situación de hoy">
            <h2>Situación de hoy</h2>
            <div className="kpi-rejilla">
              {SITUACION.map(([clave, titulo, alerta]) => (
                <Tarjeta key={clave} titulo={titulo} indicador={datos.hoy[clave]} alerta={alerta} />
              ))}
            </div>
            <h3 className="subtitulo">Habitaciones</h3>
            <div className="kpi-rejilla">
              {HABITACIONES.map(([clave, titulo]) => (
                <Tarjeta key={clave} titulo={titulo} indicador={datos.hoy[clave]} />
              ))}
            </div>
          </section>

          <section className="tarjeta" aria-label="Indicadores del periodo">
            <h2>Indicadores del periodo</h2>
            <div className="kpi-rejilla">
              <Tarjeta titulo="Ocupación (estadías reales)" indicador={p.ocupacion} valor={porcentaje(p.ocupacion.valor)} />
              <Tarjeta titulo="Ocupación reservada" indicador={p.ocupacion_reservada} valor={porcentaje(p.ocupacion_reservada.valor)} />
              <Tarjeta titulo="Noches ocupadas" indicador={p.noches_ocupadas} />
              <Tarjeta titulo="Noches reservadas" indicador={p.noches_reservadas} />
              <Tarjeta titulo="Unidades-noche" indicador={p.unidades_noche} />
              <Tarjeta
                titulo="Reservas canceladas"
                indicador={p.reservas_canceladas}
                valor={`${p.reservas_canceladas.valor} (${p.reservas_canceladas.noches} noches)`}
              />
              <Tarjeta titulo="Reservas registradas" indicador={p.reservas_registradas} />
            </div>
            {Object.keys(p.reservas_registradas.por_estado).length > 0 && (
              <p className="nota-clave">
                Registradas por estado actual:{' '}
                {Object.entries(p.reservas_registradas.por_estado)
                  .map(([estado, n]) => `${estado} ${n}`)
                  .join(' · ')}
              </p>
            )}
            <div className="tabla-contenedor">
            <table className="tabla serie">
              <thead>
                <tr>
                  <th>Noche</th>
                  <th>Unidades</th>
                  <th>Ocupadas</th>
                  <th>Reservadas</th>
                </tr>
              </thead>
              <tbody>
                {datos.serie.map((s) => (
                  <tr key={s.fecha}>
                    <td>{s.fecha}</td>
                    <td>{s.unidades}</td>
                    <td>{s.ocupadas === null ? 'futura' : s.ocupadas}</td>
                    <td>{s.reservadas}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </section>

          <section className="tarjeta" aria-label="Indicadores no disponibles">
            <h2>No disponibles en esta versión</h2>
            <ul className="no-disponibles">
              {datos.no_disponibles.map((x) => (
                <li key={x.indicador}>
                  <strong>{x.indicador}:</strong> {x.motivo}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </MarcoHotel>
  )
}
