'use client'

import { useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, SalidaJson } from '../../../lib/api'

/** Bandeja del agente de reservas N0 (V1-ISSUE-30): recepción o administrador
 *  pegan la consulta entrante, el copiloto propone un borrador con las cifras
 *  del turno (las decide la API, nunca el modelo) y la bandeja aprueba, edita
 *  o descarta. Si la oferta venció, la aprobación recotiza y avisa «la oferta
 *  cambió» con un borrador nuevo. Las decisiones del modelo fuera de la lista
 *  escalan la consulta (`.motivo-escalada`). El front solo pinta lo que la
 *  API decide y copia el texto ya compuesto; no calcula cifras. */
export default function Agente() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [estado, setEstado] = useState('')
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)
  const [detalle, setDetalle] = useState(null)
  const [texto, setTexto] = useState('')
  const [canal, setCanal] = useState('manual')
  const [ediciones, setEdiciones] = useState({})
  const [motivos, setMotivos] = useState({})
  const [copiado, setCopiado] = useState('')
  const [claveConsulta, renovarConsulta] = useClaveOperacion()
  const [claveAprobacion, renovarAprobacion] = useClaveOperacion()
  const [claveDescarte, renovarDescarte] = useClaveOperacion()

  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeGestionar = rol === 'recepcion' || rol === 'administrador'

  async function cargar(filtro) {
    setError('')
    try {
      const r = await api(`/hotel/agente/consultas${filtro ? `?estado=${filtro}` : ''}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setLista(r.datos.consultas)
    } catch {
      setError('La API no está disponible')
    }
  }

  async function cargarDetalle(consultaId) {
    setError('')
    try {
      const r = await api(`/hotel/agente/consultas/${consultaId}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setDetalle(r.datos)
    } catch {
      setError('La API no está disponible')
    }
  }

  useEffect(() => {
    if (puedeGestionar) cargar(estado)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado, puedeGestionar])

  async function procesar(evento) {
    evento.preventDefault()
    setError('')
    setSalida(null)
    if (!texto.trim()) {
      setError('Pega el texto de la consulta entrante.')
      return
    }
    try {
      const r = await api('/hotel/agente/consultas', {
        metodo: 'POST', cuerpo: { canal_origen: canal, texto }, claveIdempotencia: claveConsulta,
      })
      if (r.estado === 503) {
        // «modelo no configurado»: la consulta queda pendiente para cuando el
        // puerto tenga adaptador; la bandeja la muestra en ese estado.
        setError(mensajeDeError(r.datos, r.estado))
        cargar(estado)
        return
      }
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarConsulta)
        return
      }
      renovarConsulta()
      setTexto('')
      setDetalle(r.datos.consulta)
      cargar(estado)
    } catch {
      setError('La API no está disponible')
    }
  }

  async function aprobar(borrador) {
    setError('')
    setSalida(null)
    try {
      const r = await api(`/hotel/agente/borradores/${borrador.borrador_id}/aprobacion`, {
        metodo: 'POST', cuerpo: { texto_editado: ediciones[borrador.borrador_id] || '' },
        claveIdempotencia: claveAprobacion,
      })
      if (r.estado === 409 && r.datos && r.datos.detail === 'la oferta cambió') {
        // FR-A05: la oferta venció y la cifra cambió; el servidor creó un
        // borrador nuevo. Se muestra y se aprueba ese, no el viejo. El aviso
        // se fija DESPUÉS de recargar: cargarDetalle limpia el error al inicio.
        alRechazar(r.estado, renovarAprobacion)
        await cargarDetalle(detalle.consulta_id)
        setError('la oferta cambió: el servidor generó un borrador nuevo con la oferta actual. Revisa las cifras y aprueba de nuevo.')
        return
      }
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarAprobacion)
        return
      }
      setSalida(r.datos)
      renovarAprobacion()
      await cargarDetalle(detalle.consulta_id)
      cargar(estado)
    } catch {
      setError('La API no está disponible')
    }
  }

  async function descartar(borrador) {
    setError('')
    setSalida(null)
    const motivo = (motivos[borrador.borrador_id] || '').trim()
    if (!motivo) {
      setError('Escribe el motivo del descarte.')
      return
    }
    try {
      const r = await api(`/hotel/agente/borradores/${borrador.borrador_id}/descarte`, {
        metodo: 'POST', cuerpo: { motivo }, claveIdempotencia: claveDescarte,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarDescarte)
        return
      }
      setSalida(r.datos)
      renovarDescarte()
      await cargarDetalle(detalle.consulta_id)
      cargar(estado)
    } catch {
      setError('La API no está disponible')
    }
  }

  async function copiar(borrador) {
    const textoFinal = (ediciones[borrador.borrador_id] || '').trim() || borrador.texto_compuesto
    try {
      await navigator.clipboard.writeText(textoFinal)
      setCopiado(borrador.borrador_id)
    } catch {
      setError('No se pudo copiar al portapapeles.')
    }
  }

  if (sesion.fase === 'ok' && !puedeGestionar) {
    return (
      <MarcoHotel titulo="Agente de reservas">
        <p className="estado">La bandeja del agente es solo para recepción o administrador.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Agente de reservas">
      <section className="tarjeta formulario-consulta">
        <h2>Nueva consulta</h2>
        <form className="formulario" onSubmit={procesar}>
          <label className="campo">
            <span className="campo-etiqueta">Canal</span>
            <select className="entrada" value={canal} onChange={(e) => setCanal(e.target.value)}>
              {['manual', 'landing', 'correo', 'whatsapp'].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="campo">
            <span className="campo-etiqueta">Consulta entrante</span>
            <textarea
              className="entrada"
              rows={4}
              placeholder="Pega aquí el texto que llegó por el canal (correo, WhatsApp, recepción…)"
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
            />
          </label>
          <p className="campo-ayuda">
            RUT, tarjetas, correos y teléfonos se redactan antes de persistir o enviar al modelo: lo que se guarda y se procesa es el texto redactado.
          </p>
          <button type="submit" className="boton-primario">Procesar con el agente</button>
        </form>
      </section>

      <section className="tarjeta">
        <div className="filtros">
          {[
            ['', 'Todas'],
            ['pendiente', 'Pendientes'],
            ['procesada', 'Procesadas'],
            ['escalada', 'Escaladas'],
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
          <p className="estado">No hay consultas en este estado.</p>
        ) : (
          <div className="tabla-contenedor">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Consulta</th>
                  <th>Canal</th>
                  <th>Recibida</th>
                  <th>Registrada por</th>
                  <th>Estado</th>
                  <th>Motivo</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((c) => (
                  <tr key={c.consulta_id}>
                    <td>{c.consulta_id}</td>
                    <td>{c.canal_origen}</td>
                    <td>{c.recibida_en}</td>
                    <td>{c.registrada_por}</td>
                    <td>{c.estado}</td>
                    <td>{c.motivo || '—'}</td>
                    <td>
                      <button type="button" className="boton-secundario" onClick={() => cargarDetalle(c.consulta_id)}>
                        Ver detalle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {detalle && (
        <section className="tarjeta detalle-consulta">
          <h2>Consulta {detalle.consulta_id} · estado {detalle.estado}</h2>
          <pre className="texto-redactado">{detalle.texto_redactado}</pre>
          {detalle.motivo && (
            <p className="motivo-escalada">Motivo: {detalle.motivo}</p>
          )}

          {(detalle.borradores || []).map((b) => (
            <div className="tarjeta borrador" key={b.borrador_id}>
              <p className="estado-borrador">
                Versión {b.version} · {b.plantilla} · estado: {b.estado}
                {b.vigente_hasta ? ` · vigente hasta ${b.vigente_hasta}` : ''}
              </p>
              <pre className="texto-borrador">{b.texto_compuesto}</pre>
              {b.estado === 'pendiente_aprobacion' && (
                <div className="acciones-fila">
                  <textarea
                    className="entrada"
                    rows={3}
                    placeholder="Texto editado (opcional): si lo completas, se aprueba esta versión"
                    value={ediciones[b.borrador_id] || ''}
                    onChange={(e) => setEdiciones({ ...ediciones, [b.borrador_id]: e.target.value })}
                  />
                  <button type="button" className="boton-primario" onClick={() => aprobar(b)}>
                    Aprobar
                  </button>
                  <input
                    className="entrada"
                    placeholder="Motivo del descarte"
                    value={motivos[b.borrador_id] || ''}
                    onChange={(e) => setMotivos({ ...motivos, [b.borrador_id]: e.target.value })}
                  />
                  <button type="button" className="boton-secundario" onClick={() => descartar(b)}>
                    Descartar
                  </button>
                  <button type="button" className="boton-secundario" onClick={() => copiar(b)}>
                    Copiar respuesta
                  </button>
                  {copiado === b.borrador_id && <span className="estado">Respuesta copiada.</span>}
                </div>
              )}
            </div>
          ))}

          {(detalle.traza || []).length > 0 && (
            <div className="tabla-contenedor">
              <table className="tabla tabla-traza">
                <thead>
                  <tr>
                    <th>Turno</th>
                    <th>Herramienta</th>
                    <th>Decisión</th>
                    <th>Verificación</th>
                    <th>Modelo</th>
                  </tr>
                </thead>
                <tbody>
                  {detalle.traza.map((t, i) => (
                    <tr key={i}>
                      <td>{t.turno}</td>
                      <td>{t.herramienta}</td>
                      <td>{t.decision}</td>
                      <td>{t.verificacion}</td>
                      <td>{t.modelo}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </MarcoHotel>
  )
}
