'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError, Campo, CampoSelect } from '../../../lib/api'
import { fechaATexto, fechaHora, plural } from '../../../lib/formato'
import { BarraContextual, SelectorFila } from './barra-contextual'

const TURNOS = [
  ['manana', 'Mañana'],
  ['tarde', 'Tarde'],
  ['noche', 'Noche'],
]

const ETIQUETA_TURNO = Object.fromEntries(TURNOS)

const ETIQUETA_ESTADO_EST = {
  liberado: 'Libre',
  reservado: 'Reservado',
  ocupado: 'Ocupado',
}

function hoyChile() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Santiago' }).format(new Date())
}

/**
 * SPEC-NOV-01 (#448): Libro de novedades turno a turno, mapa de cupos de
 * estacionamiento (~14 cupos) y conteos de desayunos/bebestibles.
 * Vive dentro del Panel operativo sin agregar ítems nuevos al menú lateral.
 */
export default function LibroNovedades({ puedeOperar = false }) {
  const [fecha, setFecha] = useState(hoyChile)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  // Entrega de turno
  const [turno, setTurno] = useState('manana')
  const [resumen, setResumen] = useState('')
  const [desayunos, setDesayunos] = useState('0')

  // Estacionamiento seleccionado (patrón BarraContextual sin botones repetidos por cupo)
  const [cupoActivo, setCupoActivo] = useState(null)
  const [estForm, setEstForm] = useState({ habitacion_id: '', patente: '', estado: 'ocupado', observacion: '' })

  // Conteo F&B
  const [conteo, setConteo] = useState({ turno: 'manana', categoria: 'desayuno', cantidad: '1', observacion: '' })

  const cargar = useCallback(async (dia = fecha) => {
    setError('')
    try {
      const r = await api(`/hotel/novedades?fecha=${encodeURIComponent(dia)}`)
      if (r.estado === 403) { setDatos(null); return }
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setDatos(r.datos)
    } catch {
      setError('No se pudo cargar el libro de novedades del día.')
    }
  }, [fecha])

  useEffect(() => {
    if (puedeOperar) cargar(fecha)
  }, [puedeOperar, fecha, cargar])

  function elegirCupo(item) {
    setCupoActivo(item.cupo)
    setEstForm({
      habitacion_id: item.habitacion_id || '',
      patente: item.patente || '',
      estado: item.estado === 'liberado' ? 'ocupado' : item.estado,
      observacion: item.observacion || '',
    })
  }

  async function guardarNovedad(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    if (resumen.trim().length < 3) { setError('Escribe el resumen de novedades del turno.'); return }
    const r = await api('/hotel/novedades', {
      metodo: 'POST',
      claveIdempotencia: `nov-${fecha}-${crypto.randomUUID().slice(0, 8)}`,
      cuerpo: {
        fecha_contable: fecha,
        turno,
        resumen: resumen.trim(),
        desayunos_servidos: Math.max(0, Number(desayunos) || 0),
        bebestibles_detalle: [],
      },
    })
    if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
    else {
      setResumen('')
      setDesayunos('0')
      setAviso('Entrega de turno registrada en el libro de novedades.')
      await cargar(fecha)
    }
  }

  async function guardarCupo(e, liberar = false) {
    if (e) e.preventDefault()
    if (!cupoActivo) return
    setError('')
    setAviso('')
    const r = await api('/hotel/estacionamiento/asignacion', {
      metodo: 'PUT',
      cuerpo: {
        fecha,
        cupo: cupoActivo,
        habitacion_id: liberar ? null : (estForm.habitacion_id.trim() || null),
        patente: liberar ? '' : estForm.patente.trim(),
        estado: liberar ? 'liberado' : estForm.estado,
        observacion: liberar ? '' : estForm.observacion.trim(),
      },
    })
    if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
    else {
      setAviso(liberar ? `Cupo ${cupoActivo} liberado.` : `Cupo ${cupoActivo} actualizado.`)
      await cargar(fecha)
    }
  }

  async function guardarConteo(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const r = await api('/hotel/novedades/conteos', {
      metodo: 'POST',
      claveIdempotencia: `fnb-${fecha}-${crypto.randomUUID().slice(0, 8)}`,
      cuerpo: {
        fecha_contable: fecha,
        turno: conteo.turno,
        categoria: conteo.categoria,
        cantidad: Math.max(0, Number(conteo.cantidad) || 0),
        observacion: conteo.observacion.trim(),
      },
    })
    if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
    else {
      setConteo({ ...conteo, cantidad: '1', observacion: '' })
      setAviso('Conteo operativo registrado.')
      await cargar(fecha)
    }
  }

  if (!puedeOperar) return null

  const listaEst = datos?.estacionamiento || []
  const cupoSel = listaEst.find((c) => c.cupo === cupoActivo) || null

  return (
    <section className="tarjeta" aria-label="Libro de novedades, estacionamiento y conteos">
      <div className="tarjeta-cabecera">
        <h2>Libro de novedades, estacionamiento y desayunos</h2>
        <form className="filtros" onSubmit={(e) => { e.preventDefault(); cargar(fecha) }}>
          <Campo etiqueta="Fecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
          <button type="submit" className="boton-secundario">Ver día</button>
        </form>
      </div>

      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      {datos && (
        <>
          <div className="kpi-rejilla" style={{ marginBottom: '1rem' }}>
            <div className="kpi">
              <span className="kpi-titulo">Estacionamiento ocupado</span>
              <span className="kpi-valor">{datos.estacionamiento_ocupados} / {datos.cupos_estacionamiento}</span>
              <span className="kpi-detalle">{plural(datos.estacionamiento_libres, 'cupo libre', 'cupos libres')}</span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">Desayunos del día</span>
              <span className="kpi-valor">{datos.resumen_fnb.desayunos_total}</span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">Bebestibles registrados</span>
              <span className="kpi-valor">{datos.resumen_fnb.bebestibles_total}</span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">Entregas de turno</span>
              <span className="kpi-valor">{datos.novedades.length}</span>
            </div>
          </div>

          <h3 className="subtitulo">Entrega de turno ({fechaATexto(datos.fecha)})</h3>
          <form className="formulario" onSubmit={guardarNovedad} style={{ marginBottom: '1rem' }}>
            <CampoSelect etiqueta="Turno" value={turno} onChange={(e) => setTurno(e.target.value)}>
              {TURNOS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
            </CampoSelect>
            <Campo etiqueta="Desayunos servidos" type="number" min="0" value={desayunos} onChange={(e) => setDesayunos(e.target.value)} />
            <Campo etiqueta="Resumen de novedades" value={resumen} placeholder="Llegadas pendientes, recados, incidencias del turno" onChange={(e) => setResumen(e.target.value)} />
            <button type="submit" className="boton-primario">Registrar novedad</button>
          </form>

          {datos.novedades.length > 0 && (
            <ul className="lista-simple" style={{ marginBottom: '1rem' }}>
              {datos.novedades.map((n) => (
                <li key={n.novedad_id}>
                  <strong>{ETIQUETA_TURNO[n.turno] || n.turno}</strong> · {n.resumen}
                  {n.desayunos_servidos > 0 ? ` · ${plural(n.desayunos_servidos, 'desayuno')}` : ''}{' '}
                  <span className="nota-clave">({n.autor} · {fechaHora(n.creado_en)})</span>
                </li>
              ))}
            </ul>
          )}

          <h3 className="subtitulo">Mapa de estacionamiento ({datos.cupos_estacionamiento} cupos)</h3>
          <BarraContextual
            titulo="Asignación de estacionamiento"
            seleccionado={Boolean(cupoSel)}
            resumen={cupoSel ? `Cupo #${cupoSel.cupo} · ${ETIQUETA_ESTADO_EST[cupoSel.estado] || cupoSel.estado}` : ''}
            detalle={cupoSel ? (cupoSel.habitacion_id ? `Habitación ${cupoSel.habitacion_id}${cupoSel.patente ? ` · Patente ${cupoSel.patente}` : ''}` : 'Disponible para asignar') : ''}
            placeholder="Selecciona un cupo de estacionamiento para asignar habitación/patente o liberarlo."
            alLimpiar={() => setCupoActivo(null)}
          >
            {cupoSel && (
              <form className="formulario" onSubmit={(e) => guardarCupo(e, false)} style={{ width: '100%' }}>
                <Campo etiqueta="Habitación" placeholder="Ej.: HAB-01" value={estForm.habitacion_id} onChange={(e) => setEstForm({ ...estForm, habitacion_id: e.target.value })} />
                <Campo etiqueta="Patente" placeholder="Ej.: ABCD12" value={estForm.patente} onChange={(e) => setEstForm({ ...estForm, patente: e.target.value })} />
                <CampoSelect etiqueta="Estado" value={estForm.estado} onChange={(e) => setEstForm({ ...estForm, estado: e.target.value })}>
                  <option value="ocupado">Ocupado</option>
                  <option value="reservado">Reservado</option>
                </CampoSelect>
                <button type="submit" className="boton-primario">Guardar cupo</button>
                {cupoSel.estado !== 'liberado' && (
                  <button type="button" className="boton-secundario" onClick={() => guardarCupo(null, true)}>Liberar cupo</button>
                )}
              </form>
            )}
          </BarraContextual>

          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Cupos de estacionamiento (desliza para ver todas las columnas)">
            <table className="tabla">
              <thead>
                <tr>
                  <th className="celda-selector"><span className="sr-only">Elegir</span></th>
                  <th>Cupo</th>
                  <th>Estado</th>
                  <th>Habitación</th>
                  <th>Patente</th>
                  <th>Observación</th>
                </tr>
              </thead>
              <tbody>
                {listaEst.map((c) => {
                  const elegida = cupoActivo === c.cupo
                  return (
                    <tr
                      key={c.cupo}
                      className="fila-seleccionable"
                      data-seleccionada={elegida ? 'true' : 'false'}
                      onClick={() => elegirCupo(c)}
                    >
                      <td className="celda-selector">
                        <SelectorFila
                          nombreGrupo="estacionamiento-cupo"
                          elegido={elegida}
                          etiqueta={`Seleccionar cupo de estacionamiento ${c.cupo}`}
                          alElegir={() => elegirCupo(c)}
                        />
                      </td>
                      <td><strong>#{c.cupo}</strong></td>
                      <td>
                        <span className={`reserva-estado ${c.estado === 'liberado' ? 'estado-finalizada' : 'estado-confirmada'}`}>
                          {ETIQUETA_ESTADO_EST[c.estado] || c.estado}
                        </span>
                      </td>
                      <td>{c.habitacion_id || '—'}</td>
                      <td>{c.patente || '—'}</td>
                      <td>{c.observacion || '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <h3 className="subtitulo">Conteo de desayunos y bebestibles</h3>
          <form className="formulario" onSubmit={guardarConteo}>
            <CampoSelect etiqueta="Turno" value={conteo.turno} onChange={(e) => setConteo({ ...conteo, turno: e.target.value })}>
              {TURNOS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
            </CampoSelect>
            <CampoSelect etiqueta="Categoría" value={conteo.categoria} onChange={(e) => setConteo({ ...conteo, categoria: e.target.value })}>
              <option value="desayuno">Desayuno</option>
              <option value="bebestible">Bebestible</option>
            </CampoSelect>
            <Campo etiqueta="Cantidad" type="number" min="0" value={conteo.cantidad} onChange={(e) => setConteo({ ...conteo, cantidad: e.target.value })} />
            <Campo etiqueta="Detalle / observación" value={conteo.observacion} placeholder="Ej.: Jugo natural, café, agua" onChange={(e) => setConteo({ ...conteo, observacion: e.target.value })} />
            <button type="submit" className="boton-secundario">Agregar conteo</button>
          </form>
        </>
      )}
    </section>
  )
}
