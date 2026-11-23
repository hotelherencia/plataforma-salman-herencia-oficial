'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, alRechazar, clp, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, CampoSelect, useClaveOperacion } from '../../../lib/api'
import Subnav from '../_componentes/subnav'
import { CampoDocumento, SelectorUnidad } from '../_componentes/campos-recepcion'
import { validarDocumento } from '../../../lib/documento'
import { SUBNAV_RESERVAS } from '../../../lib/menu-hotel'

function filaHabitacion(inicio = '', fin = '', titularAloja = false) {
  return {
    idLocal: Math.random().toString(36).slice(2, 9),
    habitacion_id: '',
    inicio,
    fin,
    adultos: '1',
    ninos: '0',
    titular_aloja: titularAloja,
  }
}

export default function Reserva() {
  // V1-ISSUE-35: sin defaults inválidos; si viene de la oferta u otra
  // pantalla, la query precarga habitación y fechas.
  const [modo, setModo] = useState('individual')
  const [campos, setCampos] = useState({
    habitacion_id: '',
    inicio: '',
    fin: '',
    hora_llegada: '',
    hora_salida: '',
    nombre: '',
    personas: '2',
    documento_tipo: 'rut',
    documento: '',
    correo: '',
    telefono: '',
    canal: 'recepcion',
    notas_grupo: '',
    upgrade_a_single: false,
  })
  const [habitacionesGrupo, setHabitacionesGrupo] = useState([
    filaHabitacion('', '', true),
    filaHabitacion('', '', false),
  ])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const ini = params.get('inicio') || ''
    const fin = params.get('fin') || ''
    const hab = params.get('habitacion_id') || ''
    setCampos((c) => ({
      ...c,
      habitacion_id: hab || c.habitacion_id,
      inicio: ini || c.inicio,
      fin: fin || c.fin,
      hora_llegada: params.get('hora_llegada') || c.hora_llegada,
      hora_salida: params.get('hora_salida') || c.hora_salida,
    }))
    if (ini || fin || hab) {
      setHabitacionesGrupo((prev) => prev.map((f, idx) => ({
        ...f,
        inicio: ini || f.inicio,
        fin: fin || f.fin,
        habitacion_id: idx === 0 && hab ? hab : f.habitacion_id,
      })))
    }
  }, [])

  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [clave, renovarClave] = useClaveOperacion()

  function actualizarFila(indice, patch) {
    setHabitacionesGrupo((prev) => prev.map((f, i) => (i === indice ? { ...f, ...patch } : f)))
  }

  function agregarFilaGrupo() {
    const base = habitacionesGrupo[0] || {}
    setHabitacionesGrupo((prev) => [...prev, filaHabitacion(base.inicio || campos.inicio, base.fin || campos.fin, false)])
  }

  function quitarFilaGrupo(indice) {
    setHabitacionesGrupo((prev) => (prev.length > 2 ? prev.filter((_, i) => i !== indice) : prev))
  }

  async function confirmarIndividual(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[campos.inicio, 'Llegada'], [campos.fin, 'Salida'], [campos.habitacion_id, 'Habitación'], [campos.nombre, 'Nombre del huésped']])
    if (falta) { setError(falta); return }
    // #367: el documento es obligatorio y se valida antes de enviar.
    const doc = validarDocumento(campos.documento_tipo, campos.documento)
    if (!doc.ok) { setError(doc.error); return }
    // #454: contacto opcional, pero si se escribe debe ser válido.
    const correo = campos.correo.trim()
    if (correo && !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(correo)) { setError('Revisa el correo: parece incompleto.'); return }
    const telefono = campos.telefono.trim()
    const digitos = telefono.replace(/\D/g, '')
    if (telefono && (digitos.length < 8 || digitos.length > 15)) { setError('El teléfono debe tener entre 8 y 15 dígitos.'); return }
    try {
      const r = await api('/hotel/reservas', {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {
          habitacion_id: campos.habitacion_id,
          inicio: campos.inicio,
          fin: campos.fin,
          personas: Number(campos.personas) || undefined,
          canal: campos.canal || 'recepcion',
          huesped: { nombre: campos.nombre, documento: doc.valor, documento_tipo: campos.documento_tipo, ...(correo ? { correo } : {}), ...(telefono ? { telefono } : {}) },
          ...(campos.upgrade_a_single && Number(campos.personas) === 1 ? { upgrade_a_single: true } : {}),
          ...(campos.hora_llegada ? { hora_llegada: campos.hora_llegada } : {}),
          ...(campos.hora_salida ? { hora_salida: campos.hora_salida } : {}),
        },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave) // 4xx definitivo: clave nueva (V1-ISSUE-13)
      } else {
        setSalida(r.datos)
        renovarClave() // 2xx: clave nueva para la operación siguiente
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  async function confirmarGrupo(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[campos.nombre, 'Nombre del titular']])
    if (falta) { setError(falta); return }
    const doc = validarDocumento(campos.documento_tipo, campos.documento)
    if (!doc.ok) { setError(doc.error); return }
    for (let i = 0; i < habitacionesGrupo.length; i += 1) {
      const h = habitacionesGrupo[i]
      if (!h.inicio || !h.fin || !h.habitacion_id) {
        setError(`Completa Llegada, Salida y habitación en la fila ${i + 1}.`)
        return
      }
    }
    try {
      const r = await api('/hotel/grupos', {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {
          titular: { nombre: campos.nombre, documento: doc.valor, documento_tipo: campos.documento_tipo },
          canal: campos.canal || 'recepcion',
          ...(campos.notas_grupo.trim() ? { notas: campos.notas_grupo.trim() } : {}),
          habitaciones: habitacionesGrupo.map((h) => ({
            habitacion_id: h.habitacion_id,
            inicio: h.inicio,
            fin: h.fin,
            adultos: Math.max(1, Number(h.adultos) || 1),
            ninos: Math.max(0, Number(h.ninos) || 0),
            titular_aloja: Boolean(h.titular_aloja),
            ...(campos.hora_llegada ? { hora_llegada: campos.hora_llegada } : {}),
            ...(campos.hora_salida ? { hora_salida: campos.hora_salida } : {}),
          })),
        },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
      } else {
        setSalida(r.datos)
        renovarClave()
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  function nuevaOperacion() {
    setSalida(null)
    setError('')
    renovarClave()
  }

  return (
    <MarcoHotel titulo="Reservar">
      <Subnav items={SUBNAV_RESERVAS} />
      <div className="subnav" role="tablist" aria-label="Modalidad de reserva">
        <button
          type="button"
          role="tab"
          aria-selected={modo === 'individual'}
          className={modo === 'individual' ? 'subnav-item activo' : 'subnav-item'}
          onClick={() => { setModo('individual'); setError(''); setSalida(null); renovarClave() }}
        >
          1 habitación
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={modo === 'grupo'}
          className={modo === 'grupo' ? 'subnav-item activo' : 'subnav-item'}
          onClick={() => { setModo('grupo'); setError(''); setSalida(null); renovarClave() }}
        >
          Varias habitaciones (mismo titular)
        </button>
      </div>

      {modo === 'individual' ? (
        <section className="tarjeta">
          <form className="formulario" onSubmit={confirmarIndividual}>
            <Campo etiqueta="Llegada" type="date" value={campos.inicio} onChange={(e) => setCampos({ ...campos, inicio: e.target.value })} />
            <Campo etiqueta="Salida" type="date" value={campos.fin} onChange={(e) => setCampos({ ...campos, fin: e.target.value })} />
            <Campo etiqueta="Personas" type="number" min="1" max="30" value={campos.personas} onChange={(e) => setCampos({ ...campos, personas: e.target.value })} />
            <SelectorUnidad
              inicio={campos.inicio}
              fin={campos.fin}
              personas={campos.personas}
              valor={campos.habitacion_id}
              incluir={campos.habitacion_id || undefined}
              alCambiar={(id) => setCampos((c) => ({ ...c, habitacion_id: id }))}
            />
            {Number(campos.personas) === 1 && (
              <label className="campo-check">
                <input
                  type="checkbox"
                  checked={campos.upgrade_a_single}
                  onChange={(e) => setCampos({ ...campos, upgrade_a_single: e.target.checked })}
                />{' '}
                Upgrade a tarifa Single (sin Single disponible: habitación superior al precio de Single)
              </label>
            )}
            <Campo etiqueta="Hora de llegada" type="time" value={campos.hora_llegada} onChange={(e) => setCampos({ ...campos, hora_llegada: e.target.value })} />
            <Campo etiqueta="Hora de salida" type="time" value={campos.hora_salida} onChange={(e) => setCampos({ ...campos, hora_salida: e.target.value })} />
            <Campo etiqueta="Huésped" value={campos.nombre} onChange={(e) => setCampos({ ...campos, nombre: e.target.value })} />
            <Campo etiqueta="Correo del huésped (para confirmar)" type="email" inputMode="email" autoComplete="email" value={campos.correo} onChange={(e) => setCampos({ ...campos, correo: e.target.value })} />
            <Campo etiqueta="Teléfono / WhatsApp" type="tel" inputMode="tel" autoComplete="tel" value={campos.telefono} onChange={(e) => setCampos({ ...campos, telefono: e.target.value })} />
            <CampoSelect etiqueta="Canal de origen" value={campos.canal} onChange={(e) => setCampos({ ...campos, canal: e.target.value })}>
              <option value="recepcion">Recepción (presencial)</option>
              <option value="telefono">Teléfono</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="directo">Directo / correo</option>
              <option value="google">Google</option>
              <option value="ota">Agencia externa (OTA)</option>
              <option value="otro">Otro</option>
            </CampoSelect>
            <CampoDocumento
              tipo={campos.documento_tipo}
              numero={campos.documento}
              alCambiar={({ tipo, numero }) => setCampos((c) => ({ ...c, documento_tipo: tipo, documento: numero }))}
            />
            <button type="submit" className="boton-primario">Confirmar reserva</button>
          </form>
        </section>
      ) : (
        <section className="tarjeta" aria-label="Reserva de varias habitaciones">
          <h2>Varias habitaciones bajo un titular</h2>
          <p className="nota-clave">
            Ideal para familias (4+ personas en habitaciones comunicadas) o delegaciones. Cada habitación mantiene su propia cuenta sin duplicar cargos.
          </p>
          <form className="formulario" onSubmit={confirmarGrupo}>
            <Campo etiqueta="Nombre del titular" value={campos.nombre} onChange={(e) => setCampos({ ...campos, nombre: e.target.value })} />
            <CampoDocumento
              tipo={campos.documento_tipo}
              numero={campos.documento}
              alCambiar={({ tipo, numero }) => setCampos((c) => ({ ...c, documento_tipo: tipo, documento: numero }))}
            />
            <CampoSelect etiqueta="Canal de origen" value={campos.canal} onChange={(e) => setCampos({ ...campos, canal: e.target.value })}>
              <option value="recepcion">Recepción (presencial)</option>
              <option value="telefono">Teléfono</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="directo">Directo / correo</option>
              <option value="google">Google</option>
              <option value="ota">Agencia externa (OTA)</option>
              <option value="otro">Otro</option>
            </CampoSelect>
            <Campo etiqueta="Hora de llegada" type="time" value={campos.hora_llegada} onChange={(e) => setCampos({ ...campos, hora_llegada: e.target.value })} />
            <Campo etiqueta="Hora de salida" type="time" value={campos.hora_salida} onChange={(e) => setCampos({ ...campos, hora_salida: e.target.value })} />
            <Campo
              etiqueta="Notas del grupo (opcional)"
              value={campos.notas_grupo}
              placeholder="Ej.: habitaciones comunicadas por balcón"
              onChange={(e) => setCampos({ ...campos, notas_grupo: e.target.value })}
            />

            {habitacionesGrupo.map((fila, idx) => {
              const totalPersonas = Math.max(1, (Number(fila.adultos) || 1) + (Number(fila.ninos) || 0))
              return (
                <fieldset key={fila.idLocal} className="grupo-documento">
                  <legend className="campo-etiqueta">Habitación {idx + 1}</legend>
                  <Campo etiqueta="Llegada" type="date" value={fila.inicio} onChange={(e) => actualizarFila(idx, { inicio: e.target.value })} />
                  <Campo etiqueta="Salida" type="date" value={fila.fin} onChange={(e) => actualizarFila(idx, { fin: e.target.value })} />
                  <Campo etiqueta="Adultos" type="number" min="1" max="30" value={fila.adultos} onChange={(e) => actualizarFila(idx, { adultos: e.target.value })} />
                  <Campo etiqueta="Niños" type="number" min="0" max="30" value={fila.ninos} onChange={(e) => actualizarFila(idx, { ninos: e.target.value })} />
                  <SelectorUnidad
                    etiqueta={`Habitación ${idx + 1}`}
                    inicio={fila.inicio}
                    fin={fila.fin}
                    personas={totalPersonas}
                    valor={fila.habitacion_id}
                    alCambiar={(id) => actualizarFila(idx, { habitacion_id: id })}
                  />
                  <label className="campo-check">
                    <input
                      type="checkbox"
                      checked={fila.titular_aloja}
                      onChange={(e) => actualizarFila(idx, { titular_aloja: e.target.checked })}
                    />{' '}
                    El titular se aloja en esta habitación
                  </label>
                  {habitacionesGrupo.length > 2 && (
                    <button type="button" className="boton-fantasma" onClick={() => quitarFilaGrupo(idx)}>
                      Quitar habitación {idx + 1}
                    </button>
                  )}
                </fieldset>
              )
            })}

            <button type="button" className="boton-secundario" onClick={agregarFilaGrupo}>
              + Agregar otra habitación
            </button>
            <button type="submit" className="boton-primario">
              Confirmar grupo ({habitacionesGrupo.length} habitaciones)
            </button>
          </form>
        </section>
      )}

      {salida && salida.grupo_id && (
        <section className="tarjeta" aria-label="Grupo confirmado">
          <h2>Grupo {salida.grupo_id} confirmado</h2>
          <p className="nota-clave">
            Total grupo (IVA incl.): <strong>{clp(salida.resumen?.total_aceptado_clp || 0)}</strong>
          </p>
          <ul className="lista-operacion">
            {(salida.reservas || []).map((r) => (
              <li key={r.reserva_id} className="fila-operacion">
                <strong>{r.habitacion_id}</strong> ({r.reserva_id}) ·{' '}
                <Link href={`/hotel/reservas/${encodeURIComponent(r.reserva_id)}`}>Ver ficha</Link> ·{' '}
                <Link href={`/hotel/estadia?reserva_id=${encodeURIComponent(r.reserva_id)}`}>Ir a Llegada</Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{clave}</code></span>
      <button onClick={nuevaOperacion} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
