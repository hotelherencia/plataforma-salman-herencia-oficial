'use client'

import { useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, SalidaJson } from '../../../lib/api'
import { gestionaRecepcion } from '../../../lib/roles'
import Subnav from '../_componentes/subnav'
import { SUBNAV_BANDEJAS } from '../../../lib/menu-hotel'

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
  const [claveGestion, renovarGestion] = useClaveOperacion()

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
      setError('La API no está disponible')
    }
  }

  useEffect(() => {
    if (puedeGestionar) cargar(estado)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado, puedeGestionar, todos])

  // #354: fidelización deduplicada por contacto (un envío por persona).
  async function exportarContactos() {
    setError('')
    try {
      const r = await api('/hotel/leads/contactos')
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
      const celda = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
      const filas = [['nombre', 'correo', 'telefono', 'leads', 'ultimo_lead_en']]
        .concat(r.datos.contactos.map((c) => [c.nombre, c.correo, c.telefono, c.leads, c.ultimo_lead_en]))
      const csv = filas.map((f) => f.map(celda).join(',')).join('\n')
      const enlace = document.createElement('a')
      enlace.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
      enlace.download = `contactos-${new Date().toISOString().slice(0, 10)}.csv`
      enlace.click()
      URL.revokeObjectURL(enlace.href)
    } catch {
      setError('La API no está disponible')
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
      setError('La API no está disponible')
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
              ? <>Mostrando desde el <strong>{corte.desde}</strong> (últimos {corte.ventana_nuevo_dias} días).</>
              : <>Mostrando todos los leads.</>}{' '}
            «Nuevo» = sin gestión y dentro de {corte.ventana_nuevo_dias} días.
            {corte.antiguos > 0 && <> Hay <strong>{corte.antiguos}</strong> sin gestionar más antiguos (marca «Ver todos»).</>}
          </p>
        )}
        <button type="button" className="boton-secundario" onClick={exportarContactos}>Exportar contactos (sin duplicados)</button>
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
                    <td>
                      {l.situacion === 'sin_gestionar_antiguo' ? 'sin gestionar (antiguo)' : l.estado}
                      {l.leads_del_contacto > 1 && <span className="nota-clave"> · {l.leads_del_contacto} leads del mismo contacto</span>}
                    </td>
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
