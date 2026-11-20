'use client'

import { Fragment, useEffect, useState } from 'react'
import { useDestacada } from '../_componentes/destacada'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, SalidaJson, Campo } from '../../../lib/api'
import { gestionaRecepcion } from '../../../lib/roles'
import Subnav from '../_componentes/subnav'
import FormularioEdicion from '../_componentes/formulario-edicion'
import { SUBNAV_BANDEJAS } from '../../../lib/menu-hotel'
import { fechaATexto, fechaHora } from '../../../lib/formato'
import { aCsv, errorRango, parametrosRango, sufijoRango } from '../../../lib/exportacion'

/** Bandeja de leads (V1-ISSUE-20 punto 8, spec-api-v1 «Contacto y leads de la
 *  landing»): las consultas generales del formulario propio de la landing
 *  quedan como agenda de seguimiento de recepción. Recepción o administrador
 *  marcan contactado/cerrado con nota; la gestión es idempotente por clave y
 *  queda en auditoría. Nada se borra. */
export default function Leads() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [estado, setEstado] = useState('')
  // #354: por defecto solo la ventana de «nuevo»; «Ver todos» quita el corte.
  const [todos, setTodos] = useState(false)
  const [corte, setCorte] = useState(null)
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)
  const [notas, setNotas] = useState({})
  const [editando, setEditando] = useState(null)
  const [claveGestion, renovarGestion] = useClaveOperacion()
  // Exportación por fecha o rango (2026-11-19): vacío = sin límite.
  const [expDesde, setExpDesde] = useState('')
  const [expHasta, setExpHasta] = useState('')

  // Enlace directo desde un aviso por correo (?id=…): la fila queda marcada.
  const destacada = useDestacada(lista)
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeGestionar = gestionaRecepcion(rol)

  async function cargar(filtro) {
    setError('')
    try {
      const q = new URLSearchParams()
      if (filtro) q.set('estado', filtro)
      if (todos) q.set('todos', 'true')
      const r = await api(`/hotel/leads?${q}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setLista(r.datos.leads)
        setCorte({ ...r.datos.corte, antiguos: r.datos.sin_gestionar_antiguos })
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  useEffect(() => {
    if (puedeGestionar) cargar(estado)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado, puedeGestionar, todos])

  // #354: fidelización deduplicada por contacto (un envío por persona).
  function descargar(contenido, nombre) {
    const enlace = document.createElement('a')
    enlace.href = URL.createObjectURL(new Blob([contenido], { type: 'text/csv;charset=utf-8' }))
    enlace.download = nombre
    enlace.click()
    URL.revokeObjectURL(enlace.href)
  }

  // #354: fidelización deduplicada por contacto (un envío por persona).
  async function exportarContactos() {
    setError('')
    const invalido = errorRango(expDesde, expHasta)
    if (invalido) { setError(invalido); return }
    try {
      const q = new URLSearchParams()
      if (expDesde) q.set('desde', expDesde)
      if (expHasta) q.set('hasta', expHasta)
      const r = await api(`/hotel/leads/contactos?${q}`)
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
      const filas = [['nombre', 'correo', 'telefono', 'leads', 'ultimo_lead']]
        .concat(r.datos.contactos.map((c) => [c.nombre, c.correo, c.telefono, c.leads, fechaHora(c.ultimo_lead_en)]))
      descargar(aCsv(filas), `contactos-${sufijoRango(expDesde, expHasta)}.csv`)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  // Detalle de cada lead del rango (fecha de recepción, estado y gestión).
  async function exportarLeads() {
    setError('')
    const invalido = errorRango(expDesde, expHasta)
    if (invalido) { setError(invalido); return }
    try {
      const r = await api(`/hotel/leads?${parametrosRango(expDesde, expHasta)}`)
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
      const filas = [['recibido', 'nombre', 'correo', 'telefono', 'huespedes', 'llegada', 'salida', 'estado', 'nota', 'mensaje']]
        .concat(r.datos.leads.map((l) => [fechaHora(l.creado_en), l.nombre, l.correo, l.telefono, l.huespedes,
          fechaATexto(l.check_in), fechaATexto(l.check_out), l.estado, l.nota, l.mensaje]))
      descargar(aCsv(filas), `leads-${sufijoRango(expDesde, expHasta)}.csv`)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

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
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  if (sesion.fase === 'ok' && !puedeGestionar) {
    return (
      <MarcoHotel titulo="Leads de contacto">
      <Subnav items={SUBNAV_BANDEJAS} />
        <p className="estado">La bandeja de leads es solo para recepción o la administración del hotel.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Leads de contacto">
      <Subnav items={SUBNAV_BANDEJAS} />
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
        <label className="campo-check">
          <input type="checkbox" checked={todos} onChange={(e) => setTodos(e.target.checked)} />
          Ver todos (sin corte de fecha)
        </label>
        {corte && (
          <p className="nota-clave" data-corte-leads>
            {corte.desde
              ? <>Mostrando desde el <strong>{fechaATexto(corte.desde) || corte.desde}</strong> (últimos {corte.ventana_nuevo_dias} días).</>
              : <>Mostrando todos los leads.</>}{' '}
            «Nuevo» = sin gestión y dentro de {corte.ventana_nuevo_dias} días.
            {corte.antiguos > 0 && <> Hay <strong>{corte.antiguos}</strong> sin gestionar más antiguos (marca «Ver todos»).</>}
          </p>
        )}
        <fieldset className="formulario" aria-label="Exportar por fecha o rango">
          <legend>Exportar por fecha (vacío = todo)</legend>
          <Campo etiqueta="Desde" type="date" value={expDesde} onChange={(e) => setExpDesde(e.target.value)} />
          <Campo etiqueta="Hasta" type="date" value={expHasta} onChange={(e) => setExpHasta(e.target.value)} />
          <div className="filtros">
            <button type="button" className="boton-secundario" onClick={exportarLeads}>Exportar leads (CSV)</button>
            <button type="button" className="boton-secundario" onClick={exportarContactos}>Exportar contactos sin duplicados (CSV)</button>
          </div>
        </fieldset>
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}
      {salida && <SalidaJson datos={salida} />}

      {lista && (
        lista.length === 0 ? (
          <p className="estado estado-vacio">No hay leads en este estado.</p>
        ) : (
          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla (desliza para ver todas las columnas)">
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
                  <Fragment key={l.id}>
                  <tr {...destacada.props(l.id)}>
                    <td>{l.nombre}</td>
                    <td>{l.correo}</td>
                    <td>{l.telefono}</td>
                    <td>{l.huespedes ?? '—'}</td>
                    <td>{l.check_in ?? '—'}</td>
                    <td>{l.check_out ?? '—'}</td>
                    <td>{l.mensaje ?? '—'}</td>
                    <td>
                      {l.situacion === 'sin_gestionar_antiguo' ? 'sin gestionar (antiguo)' : l.estado}
                      {l.leads_del_contacto > 1 && <span className="nota-clave"> · {l.leads_del_contacto} leads del mismo contacto</span>}
                    </td>
                    <td>{l.nota ?? '—'}</td>
                    <td>{l.gestion_por ? `${l.gestion_por === 'auto:correo' ? 'automático (correo)' : l.gestion_por} · ${fechaHora(l.gestion_en)}` : '—'}</td>
                    <td>
                      <button type="button" className="boton-fantasma" aria-expanded={editando === l.id}
                        onClick={() => setEditando(editando === l.id ? null : l.id)}>
                        Editar
                      </button>
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
                          {l.estado === 'contactado' && l.gestion_por === 'auto:correo' && (
                            <button type="button" className="boton-fantasma" title="Marcado por la revisión de correo"
                              onClick={() => gestionar(l.id, 'nuevo')}>
                              Deshacer (automático)
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
                  {editando === l.id && (
                    <tr>
                      <td colSpan={11}>
                        <FormularioEdicion
                          ruta={`/hotel/leads/${l.id}`}
                          inicial={l}
                          campos={[
                            { nombre: 'nombre', etiqueta: 'Nombre', requerido: true },
                            { nombre: 'correo', etiqueta: 'Correo', tipo: 'email', requerido: true },
                            { nombre: 'telefono', etiqueta: 'Teléfono', requerido: true },
                            { nombre: 'huespedes', etiqueta: 'Huéspedes', tipo: 'number' },
                            { nombre: 'check_in', etiqueta: 'Llegada', tipo: 'date' },
                            { nombre: 'check_out', etiqueta: 'Salida', tipo: 'date' },
                            { nombre: 'mensaje', etiqueta: 'Mensaje' },
                            { nombre: 'nota', etiqueta: 'Nota' },
                          ]}
                          alGuardar={() => { setEditando(null); cargar(estado) }}
                          alCancelar={() => setEditando(null)}
                        />
                        <p className="nota-clave">Corregir datos no cambia el estado del lead.</p>
                      </td>
                    </tr>
                  )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </MarcoHotel>
  )
}
