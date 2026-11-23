'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError, Campo } from '../../../lib/api'
import { fechaCorta } from '../../../lib/formato'
import { rangoSemana } from '../../../lib/panel-serie'

const AREAS = [
  ['recepcion', 'Recepción'],
  ['aseo', 'Aseo'],
  ['desayunos', 'Desayunos'],
  ['mantencion', 'Mantención'],
]
const NOMBRE_AREA = Object.fromEntries(AREAS)
const DIAS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

function sumar(iso, dias) {
  const d = new Date(`${iso}T12:00:00Z`)
  d.setUTCDate(d.getUTCDate() + dias)
  return d.toISOString().slice(0, 10)
}

function clave(prefijo) {
  return `${prefijo}-${crypto.randomUUID().slice(0, 12)}`
}

/** #418: rol semanal de turnos por área, cambios de turno y su aprobación. */
export default function Turnos({ usuario, puedeAdministrar = false }) {
  const [semana, setSemana] = useState(null) // { desde, hasta }
  const [datos, setDatos] = useState(null)
  const [cambios, setCambios] = useState([])
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [nuevo, setNuevo] = useState({ fecha: '', area: 'aseo', usuario: '', hora_inicio: '08:00', hora_fin: '16:00' })
  const [pedido, setPedido] = useState(null) // { turnoId, propuesto, motivo }

  const cargar = useCallback(async (rango) => {
    const q = rango ? `?desde=${rango.desde}&hasta=${rango.hasta}` : ''
    try {
      const r = await api(`/hotel/turnos${q}`)
      if (r.estado === 200) {
        setDatos(r.datos)
        setSemana(rango || rangoSemana(r.datos.desde))
      }
      if (puedeAdministrar) {
        const c = await api('/hotel/turnos/cambios?estado=pendiente')
        if (c.estado === 200) setCambios(c.datos.cambios)
      }
    } catch {
      /* bloque secundario */
    }
  }, [puedeAdministrar])

  useEffect(() => {
    cargar(null)
  }, [cargar])

  async function enviar(ruta, cuerpo, prefijo, mensaje) {
    setError('')
    setAviso('')
    const r = await api(ruta, { metodo: 'POST', claveIdempotencia: clave(prefijo), cuerpo })
    if (r.estado >= 400) {
      setError(mensajeDeError(r.datos, r.estado))
      return false
    }
    setAviso(mensaje)
    await cargar(semana)
    return true
  }

  if (!datos) return null
  const hayAlgo = datos.dias.some((d) => d.turnos.length > 0)
  if (!hayAlgo && !puedeAdministrar) return null

  return (
    <section className="tarjeta" aria-label="Turnos de la semana" data-turnos>
      <div className="serie-cabecera">
        <h2>Turnos · {fechaCorta(datos.desde)} al {fechaCorta(sumar(datos.hasta, -1))}</h2>
        <div className="atajos">
          <button type="button" className="boton-fantasma" onClick={() => cargar({ desde: sumar(datos.desde, -7), hasta: datos.desde })}>Semana anterior</button>
          <button type="button" className="boton-fantasma" onClick={() => cargar(null)}>Hoy</button>
          <button type="button" className="boton-fantasma" onClick={() => cargar({ desde: datos.hasta, hasta: sumar(datos.hasta, 7) })}>Semana siguiente</button>
        </div>
      </div>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="estado">{aviso}</p>}
      <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Turnos (desliza para ver todos los días)">
        <table className="tabla">
          <thead>
            <tr><th>Día</th><th>Turnos</th></tr>
          </thead>
          <tbody>
            {datos.dias.map((d) => (
              <tr key={d.fecha}>
                <td><strong>{DIAS[new Date(`${d.fecha}T12:00:00Z`).getUTCDay()]}</strong> {fechaCorta(d.fecha)}</td>
                <td>
                  {d.turnos.length === 0 && <span className="estado">—</span>}
                  {d.turnos.map((t) => (
                    <div key={t.id}>
                      {t.hora_inicio}–{t.hora_fin} · {NOMBRE_AREA[t.area]} · <strong>{t.usuario}</strong>
                      {(t.usuario === usuario || puedeAdministrar) && d.fecha >= datos.desde && (
                        <button type="button" className="boton-fantasma" onClick={() => setPedido({ turnoId: t.id, propuesto: '', motivo: '' })}>
                          Pedir cambio
                        </button>
                      )}
                    </div>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pedido && (
        <form
          className="formulario"
          onSubmit={async (e) => {
            e.preventDefault()
            if (await enviar(`/hotel/turnos/${pedido.turnoId}/cambio`, { propuesto: pedido.propuesto.trim(), motivo: pedido.motivo.trim() }, 'tcm', 'Cambio solicitado: queda pendiente de aprobación.')) setPedido(null)
          }}
        >
          <h3 className="subtitulo">Pedir cambio de turno</h3>
          <label className="campo">¿Quién lo cubre? (usuario)
            <input value={pedido.propuesto} onChange={(e) => setPedido({ ...pedido, propuesto: e.target.value })} />
          </label>
          <label className="campo">Motivo
            <input value={pedido.motivo} maxLength={300} onChange={(e) => setPedido({ ...pedido, motivo: e.target.value })} />
          </label>
          <button type="submit" className="boton-primario">Enviar solicitud</button>
          <button type="button" className="boton-fantasma" onClick={() => setPedido(null)}>Cancelar</button>
        </form>
      )}
      {puedeAdministrar && cambios.length > 0 && (
        <div data-cambios-pendientes>
          <h3 className="subtitulo">Cambios por aprobar ({cambios.length})</h3>
          <ul className="lista-simple">
            {cambios.map((c) => (
              <li key={c.id}>
                {fechaCorta(c.fecha)} {c.hora_inicio}–{c.hora_fin} · {NOMBRE_AREA[c.area]}: {c.solicitante} → <strong>{c.propuesto}</strong> ({c.motivo}){' '}
                <button type="button" className="boton-primario" onClick={() => enviar(`/hotel/turnos/cambios/${c.id}/resolucion`, { aprobar: true }, 'tra', 'Cambio aprobado.')}>Aprobar</button>
                <button type="button" className="boton-fantasma" onClick={() => enviar(`/hotel/turnos/cambios/${c.id}/resolucion`, { aprobar: false }, 'trr', 'Cambio rechazado.')}>Rechazar</button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {puedeAdministrar && (
        <form
          className="formulario"
          onSubmit={async (e) => {
            e.preventDefault()
            if (!nuevo.fecha || !nuevo.usuario.trim()) return setError('Indica el día y la persona.')
            await enviar('/hotel/turnos', { ...nuevo, usuario: nuevo.usuario.trim() }, 'tur', 'Turno agregado.')
          }}
        >
          <h3 className="subtitulo">Agregar turno</h3>
          <Campo etiqueta="Día" type="date" value={nuevo.fecha} onChange={(e) => setNuevo({ ...nuevo, fecha: e.target.value })} />
          <label className="campo">Área
            <select value={nuevo.area} onChange={(e) => setNuevo({ ...nuevo, area: e.target.value })}>
              {AREAS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
            </select>
          </label>
          <label className="campo">Persona (usuario)
            <input value={nuevo.usuario} onChange={(e) => setNuevo({ ...nuevo, usuario: e.target.value })} />
          </label>
          <label className="campo">Desde
            <input type="time" value={nuevo.hora_inicio} onChange={(e) => setNuevo({ ...nuevo, hora_inicio: e.target.value })} />
          </label>
          <label className="campo">Hasta
            <input type="time" value={nuevo.hora_fin} onChange={(e) => setNuevo({ ...nuevo, hora_fin: e.target.value })} />
          </label>
          <button type="submit" className="boton-primario">Agregar</button>
        </form>
      )}
    </section>
  )
}
