'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useDestacada } from '../_componentes/destacada'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, SalidaJson } from '../../../lib/api'
import { gestionaRecepcion } from '../../../lib/roles'
import { nombreTipo } from '../../reservar/continuidad'
import Subnav from '../_componentes/subnav'
import FormularioEdicion from '../_componentes/formulario-edicion'
import { BarraContextual, SelectorFila } from '../_componentes/barra-contextual'
import { SUBNAV_BANDEJAS } from '../../../lib/menu-hotel'
import { fechaATexto } from '../../../lib/formato'
import { BotonExportar } from '../_componentes/boton-exportar'

const ESTADO_SOLICITUD = { recibida: 'Recibida', convertida: 'Convertida', rechazada: 'Rechazada' }

/** Bandeja de solicitudes públicas: selección de solicitud activa + barra
 *  contextual única (sin repetir botones ni inputs en cada fila). */
export default function Solicitudes() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [estado, setEstado] = useState('')
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)
  const [seleccionadaId, setSeleccionadaId] = useState(null)
  const [motivoRechazo, setMotivoRechazo] = useState('')
  const [editando, setEditando] = useState(false)
  const [claveConversion, renovarConversion] = useClaveOperacion()
  const [claveRechazo, renovarRechazo] = useClaveOperacion()

  const destacada = useDestacada(lista)
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeGestionar = gestionaRecepcion(rol)

  const activa = (lista || []).find((s) => s.solicitud_id === seleccionadaId) || null

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

  function elegirSolicitud(sol) {
    setSeleccionadaId(sol.solicitud_id)
    setEditando(false)
    setMotivoRechazo('')
    setError('')
  }

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
    const motivo = motivoRechazo.trim()
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
        setMotivoRechazo('')
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
          {lista && lista.length > 0 && (
            <BotonExportar
              titulo="Solicitudes de reserva"
              filtros={estado ? `estado ${estado}` : 'todas'}
              columnas={['ID', 'Huésped', 'Contacto', 'Tipo', 'Llegada', 'Salida', 'Personas', 'Estado', 'Reserva']}
              filas={lista.map((s) => [s.solicitud_id, s.huesped_nombre, s.huesped_contacto, nombreTipo(s.tipo_habitacion || s.tipo), fechaATexto(s.inicio), fechaATexto(s.fin), s.personas, ESTADO_SOLICITUD[s.estado] || s.estado, s.reserva_id || ''])}
              nombreArchivo="herencia-solicitudes.csv"
            />
          )}
        </div>
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}
      {salida && <SalidaJson datos={salida} />}

      {lista && (
        lista.length === 0 ? (
          <p className="estado estado-vacio">No hay solicitudes en este estado.</p>
        ) : (
          <>
            <BarraContextual
              titulo="Acciones de solicitud"
              seleccionado={Boolean(activa)}
              resumen={activa ? `${activa.huesped_nombre} · ${nombreTipo(activa.tipo)}` : ''}
              detalle={activa ? `${activa.solicitud_id} · Llegada ${fechaATexto(activa.inicio)} · Salida ${fechaATexto(activa.fin)} · ${ESTADO_SOLICITUD[activa.estado] || activa.estado}` : ''}
              placeholder="Selecciona una solicitud de la tabla para convertirla en reserva, rechazarla o editarla."
              alLimpiar={() => { setSeleccionadaId(null); setEditando(false) }}
            >
              {activa && (
                <>
                  <button
                    type="button"
                    className="boton-secundario"
                    aria-expanded={editando}
                    onClick={() => setEditando((v) => !v)}
                  >
                    {editando ? 'Cerrar edición' : 'Editar'}
                  </button>
                  {activa.estado === 'recibida' && (
                    <>
                      <button type="button" className="boton-primario" onClick={() => convertir(activa.solicitud_id)}>
                        Convertir en reserva
                      </button>
                      <input
                        className="entrada"
                        aria-label={`Motivo de rechazo para ${activa.solicitud_id}`}
                        placeholder="Motivo del rechazo"
                        value={motivoRechazo}
                        onChange={(e) => setMotivoRechazo(e.target.value)}
                      />
                      <button type="button" className="boton-secundario boton-peligro" onClick={() => rechazar(activa.solicitud_id)}>
                        Rechazar
                      </button>
                    </>
                  )}
                </>
              )}
            </BarraContextual>

            {activa && editando && (
              <div style={{ marginBottom: '0.75rem' }}>
                <FormularioEdicion
                  key={activa.solicitud_id}
                  ruta={`/hotel/solicitudes/${activa.solicitud_id}`}
                  tituloAria={`Editar solicitud ${activa.solicitud_id}`}
                  inicial={activa}
                  campos={[
                    { nombre: 'huesped_nombre', etiqueta: 'Huésped', requerido: true },
                    { nombre: 'huesped_contacto', etiqueta: 'Contacto (correo o teléfono)', requerido: true },
                    ...(activa.estado === 'recibida'
                      ? [{ nombre: 'personas', etiqueta: 'Personas', tipo: 'number', requerido: true }] : []),
                  ]}
                  armar={(v) => ({
                    huesped_nombre: v.huesped_nombre.trim(),
                    huesped_contacto: v.huesped_contacto.trim(),
                    personas: Number(v.personas ?? activa.personas),
                  })}
                  alGuardar={() => { setEditando(false); cargar(estado) }}
                  alCancelar={() => setEditando(false)}
                />
                <p className="nota-clave">Tipo, habitación y fechas no se editan aquí: cambian cupo y tarifa.</p>
              </div>
            )}

            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Solicitudes de reserva (desliza para ver todas las columnas)">
              <table className="tabla">
                <thead>
                  <tr>
                    <th className="celda-selector"><span className="sr-only">Elegir</span></th>
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
                  </tr>
                </thead>
                <tbody>
                  {lista.map((item) => {
                    const raw = String(item.huesped_contacto || '')
                    const mTel = raw.match(/Tel:\s*([^·]+)/i)
                    const mDoc = raw.match(/Doc:\s*([^·]+)/i)
                    const parteBase = raw.split('·')[0].trim()
                    const correo = item.huesped_correo || (parteBase.includes('@') ? parteBase : '—')
                    const telefono = item.huesped_telefono || (mTel ? mTel[1].trim() : (!parteBase.includes('@') && parteBase ? parteBase : '—'))
                    const documento = item.huesped_documento || (mDoc ? mDoc[1].trim() : '—')
                    const elegida = activa?.solicitud_id === item.solicitud_id
                    return (
                      <tr
                        key={item.solicitud_id}
                        {...destacada.props(item.solicitud_id)}
                        className="fila-seleccionable"
                        data-seleccionada={elegida ? 'true' : 'false'}
                        onClick={() => elegirSolicitud(item)}
                      >
                        <td className="celda-selector">
                          <SelectorFila
                            nombreGrupo="solicitud-activa"
                            elegido={elegida}
                            etiqueta={`Seleccionar solicitud ${item.solicitud_id} de ${item.huesped_nombre}`}
                            alElegir={() => elegirSolicitud(item)}
                          />
                        </td>
                        <td>{item.solicitud_id}</td>
                        <td>{nombreTipo(item.tipo)}</td>
                        <td>{item.habitacion_id || 'Al convertir'}</td>
                        <td className="celda-fecha">{fechaATexto(item.inicio) || item.inicio}</td>
                        <td className="celda-fecha">{fechaATexto(item.fin) || item.fin}</td>
                        <td>{item.personas}</td>
                        <td>{item.huesped_nombre}</td>
                        <td>{documento}</td>
                        <td>{telefono}</td>
                        <td>{correo}</td>
                        <td>{item.origen || '—'}</td>
                        <td><span className={`reserva-estado solicitud-${item.estado}`}>{ESTADO_SOLICITUD[item.estado] || item.estado}</span></td>
                        <td>
                          {item.reserva_id
                            ? <Link href={`/hotel/reservas/${item.reserva_id}`} onClick={(e) => e.stopPropagation()}>{item.reserva_id}</Link>
                            : '—'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )
      )}
    </MarcoHotel>
  )
}
