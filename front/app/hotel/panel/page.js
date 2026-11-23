'use client'

import Link from 'next/link'
import { Fragment, useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, Campo, CampoSelect, Definicion, useSesion, clp } from '../../../lib/api'
import { Explicacion } from '../_componentes/explicacion'
import { AUN_NO_DISPONIBLES, EXPLICACIONES } from '../../../lib/explicaciones'
import { Insignia, useContadorSolicitudes } from '../_componentes/contador-solicitudes'
import Atencion from '../_componentes/atencion'
import Mantenciones from '../_componentes/mantenciones'
import Comunicados from '../_componentes/comunicados'
import Turnos from '../_componentes/turnos'
import Biblioteca from '../_componentes/biblioteca'
import { esAdminHotel, gestionaRecepcion } from '../../../lib/roles'
import { fechaCorta, plural, porcentaje } from '../../../lib/formato'
import { BotonExportar } from '../_componentes/boton-exportar'
import { rangoSemana, rangoMes, resumenSerie, puntosLinea } from '../../../lib/panel-serie'

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

const SITUACION = [
  ['llegadas_hoy', 'Llegadas de hoy'],
  ['salidas_hoy', 'Salidas de hoy'],
  ['en_casa', 'Huéspedes en casa'],
  ['llegadas_vencidas', 'Llegadas atrasadas sin registrar', true],
  ['salidas_vencidas', 'Salidas atrasadas sin cerrar', true],
]

const HABITACIONES = [
  ['habitaciones_total', 'Habitaciones registradas'],
  ['habitaciones_vendibles', 'Vendibles'],
  ['habitaciones_ocupadas', 'Ocupadas ahora'],
  ['habitaciones_sucias', 'Sucias'],
  ['habitaciones_en_limpieza', 'En limpieza'],
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
  terminada: { label: 'Finalizadas (Salida registrada)', color: '#4b5563', bg: '#f3f4f6' },
  finalizada: { label: 'Finalizadas (Salida registrada)', color: '#4b5563', bg: '#f3f4f6' },
  en_estadia: { label: 'En estadía (alojados)', color: '#173326', bg: '#eef4ef' },
  cancelada: { label: 'Canceladas', color: '#b91c1c', bg: '#fef2f2' },
}

const ETIQUETAS_CANAL = {
  recepcion: { label: 'Recepción', color: '#173326' },
  landing: { label: 'Sitio web', color: '#9d5d3f' },
  directo: { label: 'Directo', color: '#2b5b44' },
  google: { label: 'Google', color: '#1d4ed8' },
  ota: { label: 'Agencia externa (OTA)', color: '#7c3aed' },
  telefono: { label: 'Teléfono', color: '#b45309' },
  whatsapp: { label: 'WhatsApp', color: '#15803d' },
  otro: { label: 'Otro', color: '#5f6158' },
}

function Tarjeta({ clave, titulo, indicador, alerta, valor, detalle }) {
  if (!indicador) return null
  const mostrar = valor !== undefined ? valor : indicador.valor
  const reservasDetalle = Array.isArray(indicador.reservas_detalle) && indicador.reservas_detalle.length > 0
    ? indicador.reservas_detalle
    : Array.isArray(indicador.reservas)
      ? indicador.reservas.map((id) => ({ reserva_id: id, huesped_nombre: '' }))
      : []
  return (
    <div className={`kpi${alerta && indicador.valor > 0 ? ' kpi-alerta' : ''}`}>
      <span className="kpi-titulo">{titulo}</span>
      <span className="kpi-valor">{mostrar}</span>
      {detalle && <span className="kpi-detalle">{detalle}</span>}
      {reservasDetalle.length > 0 && (
        <span className="kpi-reservas">
          {reservasDetalle.map((item) => {
            const nombre = item.huesped_nombre && item.huesped_nombre.trim() ? item.huesped_nombre.trim() : 'Sin nombre'
            const codigoCorto = `#${item.reserva_id.replace(/^RSV-/, '').slice(0, 8)}`
            return (
              <Link
                key={item.reserva_id}
                href={`/hotel/reservas/${item.reserva_id}`}
                className="kpi-enlace-reserva"
                title={`Reserva ${item.reserva_id} · ${nombre}`}
              >
                {nombre}
              </Link>
            )
          })}
        </span>
      )}
      {EXPLICACIONES[clave] ? <Explicacion clave={clave} titulo={titulo} /> : <Definicion indicador={indicador} />}
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
      {error && <p role="alert" className="alerta">{error}</p>}
      {cargando && <p className="estado" role="status" aria-busy="true">Calculando…</p>}

      {datos && (
        <>
          <Atencion atencion={datos.atencion} />
          <Mantenciones puedeGestionar={gestionaRecepcion(sesion.usuario.rol)} />
          <Comunicados puedePublicar={esAdminHotel(sesion.usuario.rol)} />
          <Turnos usuario={sesion.usuario.usuario} puedeAdministrar={esAdminHotel(sesion.usuario.rol)} />
          <Biblioteca puedeAdministrar={esAdminHotel(sesion.usuario.rol)} />
          <p className="panel-corte">
            Datos al <strong>{formatearFecha(datos.fecha_corte)}</strong>
          </p>

          {solicitudesPendientes > 0 && (
            <p className="estado" role="status" data-solicitudes-pendientes>
              <Link href="/hotel/solicitudes">{plural(solicitudesPendientes, 'solicitud', 'solicitudes')} de reserva por responder</Link>
              <Insignia valor={solicitudesPendientes} />
            </p>
          )}
          <section className="tarjeta" aria-label="Situación de hoy">
            <h2>Situación de hoy</h2>
            <div className="kpi-rejilla">
              {SITUACION.map(([clave, titulo, alerta]) => (
                <Tarjeta key={clave} clave={clave} titulo={titulo} indicador={datos.hoy[clave]} alerta={alerta} />
              ))}
            </div>
            <h3 className="subtitulo">Habitaciones</h3>
            <div className="kpi-rejilla">
              {HABITACIONES.map(([clave, titulo]) => (
                <Tarjeta key={clave} clave={clave} titulo={titulo} indicador={datos.hoy[clave]} />
              ))}
            </div>
          </section>
        </>
      )}

      <section className="tarjeta" aria-label="Indicadores del periodo">
        <div className="tarjeta-cabecera">
          <h2>Indicadores del periodo</h2>
          {datos && (
            <p className="nota-clave" data-periodo>
              Del {formatearFecha(datos.periodo.desde)} al {formatearFecha(datos.periodo.hasta)} ({plural(datos.periodo.noches, 'noche')})
              {datos.filtros.tipo ? ` · tipo ${datos.filtros.tipo}` : ''}
            </p>
          )}
        </div>
        <div className="panel-filtros">
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
            {datos && datos.serie && datos.serie.length > 0 && (
              <BotonExportar
                titulo="Panel operativo — Ocupación y reservas por noche"
                filtros={`${datos.periodo.desde} a ${datos.periodo.hasta}${datos.filtros.tipo ? ` · tipo ${datos.filtros.tipo}` : ''}`}
                columnas={['Noche', 'Capacidad', 'En casa', 'Reservadas']}
                filas={datos.serie.map((s) => [formatearFecha(s.fecha), s.unidades, s.ocupadas_estadias === null ? 'futura' : s.ocupadas_estadias, s.reservadas])}
                nombreArchivo={`herencia-panel-${datos.periodo.desde}_a_${datos.periodo.hasta}.csv`}
              />
            )}
          </form>
          {corte && (
            <div className="atajos">
              <button type="button" className="boton-fantasma" onClick={() => atajo(corte, sumarDias(corte, 1))}>Hoy</button>
              <button type="button" className="boton-fantasma" onClick={() => { const r = rangoSemana(corte); atajo(r.desde, r.hasta) }}>Esta semana</button>
              <button type="button" className="boton-fantasma" onClick={() => atajo(corte, sumarDias(corte, 7))}>Próximos 7 días</button>
              <button type="button" className="boton-fantasma" onClick={() => { const r = rangoMes(corte); atajo(r.desde, r.hasta) }}>Este mes</button>
              <button type="button" className="boton-fantasma" onClick={() => atajo(sumarDias(corte, -7), sumarDias(corte, 1))}>Últimos 7 días</button>
              <button type="button" className="boton-fantasma" onClick={() => atajo(sumarDias(corte, -30), sumarDias(corte, 1))}>Últimos 30 días</button>
              <button type="button" className="boton-fantasma" onClick={() => atajo(corte, sumarDias(corte, 14))}>Próximos 14 días</button>
            </div>
          )}
        </div>
        {datos && (
        <>
            <div className="kpi-rejilla">
              <Tarjeta titulo="Ocupación (estadías reales)" clave="ocupacion" indicador={p.ocupacion} valor={porcentaje(p.ocupacion.valor)} />
              <Tarjeta titulo="Ocupación reservada" clave="ocupacion_reservada" indicador={p.ocupacion_reservada} valor={porcentaje(p.ocupacion_reservada.valor)} />
              <Tarjeta titulo="Noches ocupadas" clave="noches_ocupadas" indicador={p.noches_ocupadas} />
              <Tarjeta titulo="Noches reservadas" clave="noches_reservadas" indicador={p.noches_reservadas} />
              {p.ingresos_periodo_clp && (
                <Tarjeta titulo="Recaudación del periodo (cobros)" clave="ingresos_periodo_clp" indicador={p.ingresos_periodo_clp} valor={clp(p.ingresos_periodo_clp.valor)} />
              )}
              {p.ingreso_alojamiento_clp && (
                <Tarjeta
                  titulo="Ingreso de alojamiento devengado"
                  clave="ingreso_alojamiento_clp"
                  indicador={p.ingreso_alojamiento_clp}
                  valor={p.ingreso_alojamiento_clp.valor === null ? 'sin muestra' : clp(p.ingreso_alojamiento_clp.valor)}
                  detalle={p.ingreso_alojamiento_clp.neto_clp !== null ? `Neto: ${clp(p.ingreso_alojamiento_clp.neto_clp)}` : undefined}
                />
              )}
              {p.adr_clp && (
                <Tarjeta
                  titulo="Tarifa promedio diaria (ADR)"
                  clave="adr_clp"
                  indicador={p.adr_clp}
                  valor={p.adr_clp.valor === null ? 'sin muestra' : clp(p.adr_clp.valor)}
                  detalle={p.adr_clp.neto_clp !== null ? `Neto: ${clp(p.adr_clp.neto_clp)}` : undefined}
                />
              )}
              {p.revpar_clp && (
                <Tarjeta
                  titulo="Ingreso por habitación disponible (RevPAR)"
                  clave="revpar_clp"
                  indicador={p.revpar_clp}
                  valor={p.revpar_clp.valor === null ? 'sin muestra' : clp(p.revpar_clp.valor)}
                  detalle={p.revpar_clp.neto_clp !== null ? `Neto: ${clp(p.revpar_clp.neto_clp)}` : undefined}
                />
              )}
              <Tarjeta titulo="Unidades-noche" clave="unidades_noche" indicador={p.unidades_noche} />
              <Tarjeta
                titulo="Reservas canceladas"
                clave="reservas_canceladas" indicador={p.reservas_canceladas}
                detalle={plural(p.reservas_canceladas.noches, 'noche')}
              />
              <Tarjeta titulo="Reservas registradas" clave="reservas_registradas" indicador={p.reservas_registradas} />
            </div>
            <details className="aun-no-disponibles">
              <summary>Indicadores que todavía no se calculan</summary>
              <ul>
                {AUN_NO_DISPONIBLES.map((i) => (
                  <li key={i.nombre}><strong>{i.nombre}.</strong> {i.texto}</li>
                ))}
              </ul>
            </details>
            {p.ingresos_por_canal && (
              <div className="grafico-estados-bloque" data-ingresos-por-canal>
                <div className="serie-cabecera">
                  <h3 className="subtitulo">Recaudación por canal</h3>
                  <Explicacion clave="ingresos_por_canal" titulo="Recaudación por canal" />
                </div>
                {p.ingresos_por_canal.por_canal?.length > 0 ? (
                  <>
                    <div className="barra-proporcion">
                      {p.ingresos_por_canal.por_canal.map((item) => {
                        const cfg = ETIQUETAS_CANAL[item.canal] || { label: item.canal, color: '#5f6158' }
                        const peso = Math.max(0, item.ingresos_clp)
                        if (peso === 0) return null
                        return (
                          <div
                            key={item.canal}
                            className="segmento-proporcion"
                            style={{ flex: peso, backgroundColor: cfg.color }}
                            title={`${cfg.label}: ${clp(item.ingresos_clp)} (${porcentaje(item.participacion)})`}
                          />
                        )
                      })}
                    </div>
                    <div className="grid-estados">
                      {p.ingresos_por_canal.por_canal.map((item) => {
                        const cfg = ETIQUETAS_CANAL[item.canal] || { label: item.canal, color: '#5f6158' }
                        return (
                          <div key={item.canal} className="tarjeta-estado" style={{ borderLeftColor: cfg.color }}>
                            <span className="estado-nombre">{cfg.label}</span>
                            <div className="estado-conteo">
                              <span className="estado-cantidad">{clp(item.ingresos_clp)}</span>
                              <span className="estado-pct">
                                {plural(item.reservas, 'reserva')} · {porcentaje(item.participacion)}
                              </span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </>
                ) : (
                  <p className="nota-chica">Sin cobros confirmados en el periodo seleccionado.</p>
                )}
              </div>
            )}

            {Object.keys(p.reservas_registradas.por_estado).length > 0 && (
              <div className="grafico-estados-bloque">
                <h3 className="subtitulo">Distribución de reservas por estado</h3>
                <div className="barra-proporcion">
                  {Object.entries(p.reservas_registradas.por_estado).map(([estado, n]) => {
                    const total = p.reservas_registradas.valor || 1
                    const pct = porcentaje((n / total) * 100)
                    const cfg = ETIQUETAS_ESTADO[estado] || { label: estado, color: '#5f6158' }
                    return (
                      <div
                        key={estado}
                        className="segmento-proporcion"
                        style={{ flex: n, backgroundColor: cfg.color }}
                        title={`${cfg.label}: ${n} (${pct})`}
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
                          <span className="estado-pct">{pct} %</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {datos.serie && datos.serie.length > 0 && (() => {
              const noches = datos.periodo?.noches || datos.serie.length
              const esHoy = datos.periodo?.desde === datos.fecha_corte && noches === 1
              const contextoPeriodo = esHoy
                ? `Distribución actual (${formatearFecha(datos.fecha_corte)})`
                : noches === 1
                  ? `Vista: Día (${formatearFecha(datos.periodo.desde)})`
                  : noches === 7
                    ? `Vista: Semana (${formatearFecha(datos.periodo.desde)} → ${formatearFecha(datos.periodo.hasta)})`
                    : noches >= 28 && noches <= 31
                      ? `Vista: Mes (${formatearFecha(datos.periodo.desde)} → ${formatearFecha(datos.periodo.hasta)})`
                      : `Vista: Periodo (${plural(noches, 'noche')})`
              const totalEnCasa = datos.serie.reduce((acc, s) => acc + (s.ocupadas_estadias ?? 0), 0)
              const totalReservadas = datos.serie.reduce((acc, s) => {
                const oc = s.ocupadas_estadias ?? 0
                return acc + Math.max(0, (s.reservadas || 0) - oc)
              }, 0)
              const totalDisponibles = datos.serie.reduce((acc, s) => {
                const max = s.unidades || 0
                const oc = s.ocupadas_estadias ?? 0
                const res = Math.max(0, (s.reservadas || 0) - oc)
                return acc + Math.max(0, max - oc - res)
              }, 0)
              return (
                <div className="grafico-serie-bloque">
                  <div className="serie-cabecera">
                    <div>
                      <h3 className="subtitulo">Ocupación y reservas por noche</h3>
                      <span className="estado-pct" data-contexto-periodo>{contextoPeriodo}</span>
                    </div>
                    <div className="serie-leyenda">
                      <span className="leyenda-item"><span className="punto punto-ocupada"></span> En casa: <strong>{totalEnCasa}</strong></span>
                      <span className="leyenda-item"><span className="punto punto-reservada"></span> Reservadas: <strong>{totalReservadas}</strong></span>
                      <span className="leyenda-item"><span className="punto punto-disponible"></span> Disponibles: <strong>{totalDisponibles}</strong></span>
                    </div>
                  </div>
                  {(() => {
                    const res = resumenSerie(datos.serie)
                    if (!res) return null
                    const pts = puntosLinea(res.puntos)
                    const linea = pts.map((q) => `${q.x},${q.y}`).join(' ')
                    return (
                      <div className="serie-resumen" data-resumen-serie>
                        <div className="serie-datos">
                          <div><span className="serie-dato-valor">{res.promedio} %</span><span className="serie-dato-etiqueta">Ocupación promedio (en casa + reservadas)</span></div>
                          <div><span className="serie-dato-valor">{res.pico.pct} %</span><span className="serie-dato-etiqueta">Noche más llena: {diaSemana(res.pico.fecha)} {fechaCorta(res.pico.fecha)}</span></div>
                          <div><span className="serie-dato-valor">{res.valle.pct} %</span><span className="serie-dato-etiqueta">Noche más libre: {diaSemana(res.valle.fecha)} {fechaCorta(res.valle.fecha)}</span></div>
                        </div>
                        {pts.length > 1 && (
                          <svg className="serie-linea" viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={`Ocupación por noche, promedio ${res.promedio} por ciento`}>
                            <line x1="0" y1="50" x2="100" y2="50" className="serie-guia" />
                            <polygon points={`0,100 ${linea} 100,100`} className="serie-area" />
                            <polyline points={linea} className="serie-trazo" vectorEffect="non-scaling-stroke" />
                          </svg>
                        )}
                      </div>
                    )
                  })()}
                  <div className="grafico-barras-contenedor">
                    <div className="grafico-barras">
                      {datos.serie.map((s) => {
                        const max = s.unidades || 1
                        const ocupadas = s.ocupadas_estadias ?? 0
                        const reservadas = Math.max(0, (s.reservadas || 0) - ocupadas)
                        const libres = Math.max(0, max - ocupadas - reservadas)
                        const pctOcupadas = Math.min(100, (ocupadas / max) * 100)
                        const pctReservadas = Math.min(100 - pctOcupadas, (reservadas / max) * 100)
                        const pctLibre = Math.max(0, 100 - pctOcupadas - pctReservadas)
                        const dia = diaSemana(s.fecha)
                        const fechaCortaNoche = fechaCorta(s.fecha)
                        return (
                          <div key={s.fecha} className="columna-noche">
                            <div className="barra-pila" title={`${formatearFecha(s.fecha)}: ${ocupadas} en casa, ${reservadas} reservadas, ${libres} disponibles de ${max} unidades`}>
                              {libres > 0 && <div className="barra-porcion porcion-libre" style={{ height: `${pctLibre}%`, minHeight: '1.15rem' }}>{libres}</div>}
                              {reservadas > 0 && <div className="barra-porcion porcion-reservada" style={{ height: `${pctReservadas}%`, minHeight: '1.15rem' }}>{reservadas}</div>}
                              {ocupadas > 0 && <div className="barra-porcion porcion-ocupada" style={{ height: `${pctOcupadas}%`, minHeight: '1.15rem' }}>{ocupadas}</div>}
                            </div>
                            <div className="columna-fecha">
                              <span className="columna-dia">{dia}</span>
                              <span className="columna-dia-num">{fechaCortaNoche}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )
            })()}

            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)">
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
                  <Fragment key={s.fecha}>
                    <tr>
                      <td><strong>{formatearFecha(s.fecha)}</strong> <span className="noche-dia">({diaSemana(s.fecha)})</span></td>
                      <td>{s.unidades}</td>
                      <td>{s.ocupadas_estadias === null ? 'futura' : s.ocupadas_estadias}</td>
                      <td>{s.reservadas}</td>
                    </tr>
                    {Array.isArray(s.detalle_por_tipo) && s.detalle_por_tipo.map((d) => (
                      <tr key={`${s.fecha}-${d.tipo_habitacion}`} style={{ fontSize: '0.88em', opacity: 0.85 }}>
                        <td style={{ paddingLeft: '1.5rem' }}>↳ {d.tipo_habitacion}</td>
                        <td>{d.capacidad_total}</td>
                        <td>{d.en_casa}</td>
                        <td>{d.reservadas} (disp: {d.disponibles})</td>
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
            </div>
        </>
        )}
      </section>
    </MarcoHotel>
  )
}
