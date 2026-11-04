'use client'

import { useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, SalidaJson } from '../../../lib/api'

/** Bandeja de leads (V1-ISSUE-20 punto 8, spec-api-v1 «Contacto y leads de la
 *  landing»): las consultas generales del formulario propio de la landing
 *  quedan como agenda de seguimiento de recepción. Recepción o administrador
 *  marcan contactado/cerrado con nota; la gestión es idempotente por clave y
 *  queda en auditoría. Nada se borra. */
export default function Leads() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [estado, setEstado] = useState('')
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)
  const [notas, setNotas] = useState({})
  const [claveGestion, renovarGestion] = useClaveOperacion()

  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeGestionar = rol === 'recepcion' || rol === 'administrador'

  async function cargar(filtro) {
    setError('')
    try {
      const r = await api(`/hotel/leads${filtro ? `?estado=${filtro}` : ''}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setLista(r.datos.leads)
    } catch {
      setError('La API no está disponible')
    }
  }

  useEffect(() => {
    if (puedeGestionar) cargar(estado)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado, puedeGestionar])

  async function gestionar(leadId, destino) {
    setError('')
    setSalida(null)
    const nota = (notas[leadId] || '').trim() || null
    try {
      const r = await api(`/hotel/leads/${leadId}/estado`, {
        metodo: 'POST', cuerpo: { estado: destino, nota }, claveIdempotencia: claveGestion,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarGestion)
      } else {
        setSalida(r.datos)
        setNotas({ ...notas, [leadId]: '' })
        renovarGestion()
        cargar(estado)
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  if (sesion.fase === 'ok' && !puedeGestionar) {
    return (
      <MarcoHotel titulo="Leads de contacto">
        <p className="estado">La bandeja de leads es solo para recepción o administrador.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Leads de contacto">
      <section className="tarjeta">
        <div className="filtros">
          {[
            ['', 'Todos'],
            ['nuevo', 'Nuevos'],
            ['contactado', 'Contactados'],
            ['cerrado', 'Cerrados'],
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
          <p className="estado">No hay leads en este estado.</p>
        ) : (
          <div className="tabla-contenedor">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Nombre</th>
                  <th>Correo</th>
                  <th>Teléfono</th>
                  <th>Huéspedes</th>
                  <th>Llegada</th>
                  <th>Salida</th>
                  <th>Mensaje</th>
                  <th>Estado</th>
                  <th>Nota</th>
                  <th>Gestión</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((l) => (
                  <tr key={l.id}>
                    <td>{l.nombre}</td>
                    <td>{l.correo}</td>
                    <td>{l.telefono}</td>
                    <td>{l.huespedes ?? '—'}</td>
                    <td>{l.check_in ?? '—'}</td>
                    <td>{l.check_out ?? '—'}</td>
                    <td>{l.mensaje ?? '—'}</td>
                    <td>{l.estado}</td>
                    <td>{l.nota ?? '—'}</td>
                    <td>{l.gestion_por ? `${l.gestion_por} · ${l.gestion_en}` : '—'}</td>
                    <td>
                      {l.estado !== 'cerrado' ? (
                        <div className="acciones-fila">
                          <input
                            className="entrada"
                            placeholder="Nota de gestión"
                            value={notas[l.id] || ''}
                            onChange={(e) => setNotas({ ...notas, [l.id]: e.target.value })}
                          />
                          {l.estado === 'nuevo' && (
                            <button type="button" className="boton-primario" onClick={() => gestionar(l.id, 'contactado')}>
                              Contactado
                            </button>
                          )}
                          <button type="button" className="boton-secundario" onClick={() => gestionar(l.id, 'cerrado')}>
                            Cerrar
                          </button>
                        </div>
                      ) : (
                        <span className="estado">cerrado</span>
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
