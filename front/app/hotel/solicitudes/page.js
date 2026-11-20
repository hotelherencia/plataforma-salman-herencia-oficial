'use client'

import { Fragment, useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, SalidaJson } from '../../../lib/api'
import { gestionaRecepcion } from '../../../lib/roles'
import { nombreTipo } from '../../reservar/continuidad'
import Subnav from '../_componentes/subnav'
import FormularioEdicion from '../_componentes/formulario-edicion'
import { SUBNAV_BANDEJAS } from '../../../lib/menu-hotel'

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
  const [editando, setEditando] = useState(null)
  const [claveConversion, renovarConversion] = useClaveOperacion()
  const [claveRechazo, renovarRechazo] = useClaveOperacion()

  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeGestionar = gestionaRecepcion(rol)

  async function cargar(filtro) {
    setError('')
    try {
      const r = await api(`/hotel/solicitudes${filtro ? `?estado=${filtro}` : ''}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setLista(r.datos.solicitudes)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
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
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
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
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  if (sesion.fase === 'ok' && !puedeGestionar) {
    return (
      <MarcoHotel titulo="Solicitudes de reserva">
      <Subnav items={SUBNAV_BANDEJAS} />
        <p className="estado">La bandeja de solicitudes es solo para recepción o la administración del hotel.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Solicitudes de reserva">
      <Subnav items={SUBNAV_BANDEJAS} />
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
                  <th>Tipo</th>
                  <th>Habitación asignada</th>
                  <th>Llegada</th>
                  <th>Salida</th>
                  <th>Personas</th>
                  <th>Huésped</th>
                  <th>RUT / Pasaporte</th>
                  <th>Teléfono</th>
                  <th>Correo</th>
                  <th>Origen</th>
                  <th>Estado</th>
                  <th>Reserva</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((s) => {
                  const raw = String(s.huesped_contacto || '')
                  const mTel = raw.match(/Tel:\s*([^·]+)/i)
                  const mDoc = raw.match(/Doc:\s*([^·]+)/i)
                  const parteBase = raw.split('·')[0].trim()
                  const correo = s.huesped_correo || (parteBase.includes('@') ? parteBase : '—')
                  const telefono = s.huesped_telefono || (mTel ? mTel[1].trim() : (!parteBase.includes('@') && parteBase ? parteBase : '—'))
                  const documento = s.huesped_documento || (mDoc ? mDoc[1].trim() : '—')
                  return (
                  <Fragment key={s.solicitud_id}>
                  <tr>
                    <td>{s.solicitud_id}</td>
                    <td>{nombreTipo(s.tipo)}</td>
                    <td>{s.habitacion_id || 'al convertir'}</td>
                    <td>{s.inicio}</td>
                    <td>{s.fin}</td>
                    <td>{s.personas}</td>
                    <td>{s.huesped_nombre}</td>
                    <td>{documento}</td>
                    <td>{telefono}</td>
                    <td>{correo}</td>
                    <td>{s.origen || '—'}</td>
                    <td>{s.estado}</td>
                    <td>{s.reserva_id || '—'}</td>
                    <td>
                      <button type="button" className="boton-fantasma"
                        onClick={() => setEditando(editando === s.solicitud_id ? null : s.solicitud_id)}>
                        Editar
                      </button>
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
                  {editando === s.solicitud_id && (
                    <tr>
                      <td colSpan={12}>
                        <FormularioEdicion
                          ruta={`/hotel/solicitudes/${s.solicitud_id}`}
                          inicial={s}
                          campos={[
                            { nombre: 'huesped_nombre', etiqueta: 'Huésped', requerido: true },
                            { nombre: 'huesped_contacto', etiqueta: 'Contacto', requerido: true },
                            ...(s.estado === 'recibida'
                              ? [{ nombre: 'personas', etiqueta: 'Personas', tipo: 'number', requerido: true }] : []),
                          ]}
                          armar={(v) => ({ ...v, personas: Number(v.personas ?? s.personas) })}
                          alGuardar={() => { setEditando(null); cargar(estado) }}
                          alCancelar={() => setEditando(null)}
                        />
                        <p className="nota-clave">Habitación y fechas no se editan aquí: cambian cupo y tarifa.</p>
                      </td>
                    </tr>
                  )}
                  </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )
      )}
    </MarcoHotel>
  )
}
