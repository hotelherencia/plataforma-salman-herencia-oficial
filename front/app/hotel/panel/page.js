'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, Campo, CampoSelect, Definicion, useSesion, clp } from '../../../lib/api'
import { Insignia, useContadorSolicitudes } from '../_componentes/contador-solicitudes'
import { gestionaRecepcion } from '../../../lib/roles'

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

function formatearFecha(isoFecha) {
  if (!isoFecha || typeof isoFecha !== 'string') return ''
  const partes = isoFecha.split('-')
  if (partes.length === 3) {
    return `${partes[2]}/${partes[1]}/${partes[0]}`
  }
  return isoFecha
}

function diaSemana(isoFecha) {
  try {
    const d = new Date(`${isoFecha}T12:00:00Z`)
    const dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
    return dias[d.getUTCDay()]
  } catch {
    return ''
  }
}

const ETIQUETAS_ESTADO = {
  confirmada: { label: 'Confirmadas', color: '#9d5d3f', bg: '#fdf8f5' },
  en_casa: { label: 'En estadía (alojados)', color: '#173326', bg: '#eef4ef' },
  terminada: { label: 'Finalizadas (check-out)', color: '#4b5563', bg: '#f3f4f6' },
  cancelada: { label: 'Canceladas', color: '#b91c1c', bg: '#fef2f2' },
}

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
            <Link key={id} href={`/hotel/reservas/${id}`} className="kpi-enlace-reserva" title={`Ver detalle de reserva ${id}`}>
              #{id.replace(/^RSV-/, '').slice(0, 8)}
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
  const solicitudesPendientes = useContadorSolicitudes(sesion.fase === 'ok' && gestionaRecepcion(sesion.usuario.rol))
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
      if (r.estado >= 400) {
        setDatos(null)
        setError(mensajeDeError(r.datos, r.estado))
      } else {
        setDatos(r.datos)
        setFiltros({ desde: r.datos.periodo.desde, hasta: r.datos.periodo.hasta, tipo: f.tipo })
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
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

          {solicitudesPendientes > 0 && (
            <p className="estado" role="status" data-solicitudes-pendientes>
              <a href="/hotel/solicitudes">{solicitudesPendientes} solicitud(es) de reserva por responder</a>
              <Insignia valor={solicitudesPendientes} />
            </p>
          )}
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
              {p.ingresos_periodo_clp && (
                <Tarjeta titulo="Ingresos del periodo" indicador={p.ingresos_periodo_clp} valor={clp(p.ingresos_periodo_clp.valor)} />
              )}
              <Tarjeta titulo="Unidades-noche" indicador={p.unidades_noche} />
              <Tarjeta
                titulo="Reservas canceladas"
                indicador={p.reservas_canceladas}
                valor={`${p.reservas_canceladas.valor} (${p.reservas_canceladas.noches} noches)`}
              />
              <Tarjeta titulo="Reservas registradas" indicador={p.reservas_registradas} />
            </div>
            {Object.keys(p.reservas_registradas.por_estado).length > 0 && (
              <div className="grafico-estados-bloque">
                <h3 className="subtitulo">Distribución de reservas por estado</h3>
                <div className="barra-proporcion">
                  {Object.entries(p.reservas_registradas.por_estado).map(([estado, n]) => {
                    const total = p.reservas_registradas.valor || 1
                    const pct = Math.max(3, Math.round((n / total) * 100))
                    const cfg = ETIQUETAS_ESTADO[estado] || { label: estado, color: '#5f6158' }
                    return (
                      <div
                        key={estado}
                        className="segmento-proporcion"
                        style={{ width: `${pct}%`, backgroundColor: cfg.color }}
                        title={`${cfg.label}: ${n} (${pct}%)`}
                      />
                    )
                  })}
                </div>
                <div className="grid-estados">
                  {Object.entries(p.reservas_registradas.por_estado).map(([estado, n]) => {
                    const total = p.reservas_registradas.valor || 1
                    const pct = ((n / total) * 100).toFixed(0)
                    const cfg = ETIQUETAS_ESTADO[estado] || { label: estado, color: '#5f6158', bg: '#f5f5f5' }
                    return (
                      <div key={estado} className="tarjeta-estado" style={{ borderLeftColor: cfg.color }}>
                        <span className="estado-nombre">{cfg.label}</span>
                        <div className="estado-conteo">
                          <span className="estado-cantidad">{n}</span>
                          <span className="estado-pct">{pct}%</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {datos.serie && datos.serie.length > 0 && (
              <div className="grafico-serie-bloque">
                <div className="serie-cabecera">
                  <h3 className="subtitulo">Ocupación y reservas por noche</h3>
                  <div className="serie-leyenda">
                    <span className="leyenda-item"><span className="punto punto-ocupada"></span> En casa</span>
                    <span className="leyenda-item"><span className="punto punto-reservada"></span> Reservadas</span>
                    <span className="leyenda-item"><span className="punto punto-disponible"></span> Disponibles</span>
                  </div>
                </div>
                <div className="grafico-barras-contenedor">
                  <div className="grafico-barras">
                    {datos.serie.map((s) => {
                      const max = s.unidades || 1
                      const ocupadas = s.ocupadas_estadias ?? 0
                      const reservadas = s.reservadas || 0
                      const pctOcupadas = Math.min(100, (ocupadas / max) * 100)
                      const pctReservadas = Math.min(100 - pctOcupadas, (reservadas / max) * 100)
                      const pctLibre = Math.max(0, 100 - pctOcupadas - pctReservadas)
                      const dia = diaSemana(s.fecha)
                      const fechaCorta = s.fecha.slice(5).replace('-', '/')
                      return (
                        <div key={s.fecha} className="columna-noche">
                          <div className="barra-pila" title={`${formatearFecha(s.fecha)}: ${ocupadas} ocupadas, ${reservadas} reservadas de ${max} unidades`}>
                            {pctLibre > 0 && <div className="barra-porcion porcion-libre" style={{ height: `${pctLibre}%` }}></div>}
                            {pctReservadas > 0 && <div className="barra-porcion porcion-reservada" style={{ height: `${pctReservadas}%` }}></div>}
                            {pctOcupadas > 0 && <div className="barra-porcion porcion-ocupada" style={{ height: `${pctOcupadas}%` }}></div>}
                          </div>
                          <div className="columna-fecha">
                            <span className="columna-dia">{dia}</span>
                            <span className="columna-dia-num">{fechaCorta}</span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            )}

            <div className="tabla-contenedor">
            <table className="tabla serie">
              <thead>
                <tr>
                  <th>Noche</th>
                  <th>Capacidad</th>
                  <th>Ocupadas</th>
                  <th>Reservadas</th>
                </tr>
              </thead>
              <tbody>
                {datos.serie.map((s) => (
                  <tr key={s.fecha}>
                    <td><strong>{formatearFecha(s.fecha)}</strong> <span className="noche-dia">({diaSemana(s.fecha)})</span></td>
                    <td>{s.unidades}</td>
                    <td>{s.ocupadas_estadias === null ? 'futura' : s.ocupadas_estadias}</td>
                    <td>{s.reservadas}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </section>
        </>
      )}
    </MarcoHotel>
  )
}
