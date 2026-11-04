'use client'

import { useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, SalidaJson } from '../../../lib/api'

/** Bandeja de solicitudes públicas (V1-ISSUE-24): recepción o administrador
 *  ven las solicitudes de la landing, las convierten en reserva por la misma
 *  operación interna (carrera por la última unidad incluida) o las rechazan
 *  con motivo. La trazabilidad es solicitud → reserva_id + auditoría. */
export default function Solicitudes() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [estado, setEstado] = useState('')
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)
  const [motivos, setMotivos] = useState({})
  const [claveConversion, renovarConversion] = useClaveOperacion()
  const [claveRechazo, renovarRechazo] = useClaveOperacion()

  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeGestionar = rol === 'recepcion' || rol === 'administrador'

  async function cargar(filtro) {
    setError('')
    try {
      const r = await api(`/hotel/solicitudes${filtro ? `?estado=${filtro}` : ''}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setLista(r.datos.solicitudes)
    } catch {
      setError('La API no está disponible')
    }
  }

  useEffect(() => {
    if (puedeGestionar) cargar(estado)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado, puedeGestionar])

  async function convertir(solicitudId) {
    setError('')
    setSalida(null)
    try {
      const r = await api(`/hotel/solicitudes/${solicitudId}/conversion`, {
        metodo: 'POST', cuerpo: {}, claveIdempotencia: claveConversion,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarConversion)
      } else {
        setSalida(r.datos)
        renovarConversion()
        cargar(estado)
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  async function rechazar(solicitudId) {
    setError('')
    setSalida(null)
    const motivo = (motivos[solicitudId] || '').trim()
    if (!motivo) {
      setError('Escribe el motivo del rechazo.')
      return
    }
    try {
      const r = await api(`/hotel/solicitudes/${solicitudId}/rechazo`, {
        metodo: 'POST', cuerpo: { motivo }, claveIdempotencia: claveRechazo,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarRechazo)
      } else {
        setSalida(r.datos)
        renovarRechazo()
        cargar(estado)
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  if (sesion.fase === 'ok' && !puedeGestionar) {
    return (
      <MarcoHotel titulo="Solicitudes de reserva">
        <p className="estado">La bandeja de solicitudes es solo para recepción o administrador.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Solicitudes de reserva">
      <section className="tarjeta">
        <div className="filtros">
          {[
            ['', 'Todas'],
            ['recibida', 'Recibidas'],
            ['convertida', 'Convertidas'],
            ['rechazada', 'Rechazadas'],
          ].map(([valor, etiqueta]) => (
            <button
              key={valor}
              type="button"
              className={estado === valor ? 'boton-primario' : 'boton-secundario'}
              onClick={() => setEstado(valor)}
            >
              {etiqueta}
            </button>
          ))}
        </div>
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}
      {salida && <SalidaJson datos={salida} />}

      {lista && (
        lista.length === 0 ? (
          <p className="estado">No hay solicitudes en este estado.</p>
        ) : (
          <div className="tabla-contenedor">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Solicitud</th>
                  <th>Habitación</th>
                  <th>Llegada</th>
                  <th>Salida</th>
                  <th>Personas</th>
                  <th>Huésped</th>
                  <th>Contacto</th>
                  <th>Estado</th>
                  <th>Reserva</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((s) => (
                  <tr key={s.solicitud_id}>
                    <td>{s.solicitud_id}</td>
                    <td>{s.habitacion_id}</td>
                    <td>{s.inicio}</td>
                    <td>{s.fin}</td>
                    <td>{s.personas}</td>
                    <td>{s.huesped_nombre}</td>
                    <td>{s.huesped_contacto}</td>
                    <td>{s.estado}</td>
                    <td>{s.reserva_id || '—'}</td>
                    <td>
                      {s.estado === 'recibida' ? (
                        <div className="acciones-fila">
                          <button type="button" className="boton-primario" onClick={() => convertir(s.solicitud_id)}>
                            Convertir en reserva
                          </button>
                          <input
                            className="entrada"
                            placeholder="Motivo del rechazo"
                            value={motivos[s.solicitud_id] || ''}
                            onChange={(e) => setMotivos({ ...motivos, [s.solicitud_id]: e.target.value })}
                          />
                          <button type="button" className="boton-secundario" onClick={() => rechazar(s.solicitud_id)}>
                            Rechazar
                          </button>
                        </div>
                      ) : (
                        <span className="estado">{s.estado}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </MarcoHotel>
  )
}
