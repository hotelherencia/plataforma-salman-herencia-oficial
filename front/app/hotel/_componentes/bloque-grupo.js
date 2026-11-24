'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, clp, mensajeDeError, Campo } from '../../../lib/api'
import { SelectorUnidad } from './campos-recepcion'
import { fechaATexto, plural } from '../../../lib/formato'
import { useMensajes } from '../../_componentes/centro-mensajes'

const ETIQUETA_ESTADO = {
  confirmada: 'confirmada',
  en_estadia: 'en estadía',
  finalizada: 'finalizada',
  cancelada: 'cancelada',
}

/**
 * Panel de grupo multi-habitación (PR B / RES-007).
 * Muestra las habitaciones hermanas bajo un mismo titular, el avance de huéspedes
 * registrados por habitación, la cuenta consolidada sin duplicación, el alta de
 * otra habitación al grupo y la Llegada en lote atómica.
 */
export default function BloqueGrupo({
  grupoId,
  reservaActualId,
  puedeEditar = false,
  enlaceBase = '/hotel/reservas',
  alCambiar,
}) {
  const { confirmar, notificarExito } = useMensajes()
  const [grupo, setGrupo] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [version, setVersion] = useState(0)
  const [mostrandoAgregar, setMostrandoAgregar] = useState(false)
  const [enviando, setEnviando] = useState(false)
  const [nueva, setNueva] = useState({
    inicio: '',
    fin: '',
    adultos: '1',
    ninos: '0',
    habitacion_id: '',
    titular_aloja: false,
  })

  useEffect(() => {
    if (!grupoId) { setGrupo(null); return }
    let cancelado = false
    api(`/hotel/grupos/${encodeURIComponent(grupoId)}`)
      .then((r) => {
        if (cancelado) return
        if (r.estado === 200) {
          setGrupo(r.datos)
          const primera = r.datos.reservas?.[0]
          if (primera) {
            setNueva((prev) => ({
              ...prev,
              inicio: prev.inicio || primera.inicio,
              fin: prev.fin || primera.fin,
            }))
          }
        } else {
          setError(mensajeDeError(r.datos, r.estado))
        }
      })
      .catch(() => {
        if (!cancelado) setError('No se pudo cargar el grupo de habitaciones.')
      })
    return () => { cancelado = true }
  }, [grupoId, version])

  async function agregarHabitacion(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    if (!nueva.inicio || !nueva.fin || !nueva.habitacion_id) {
      setError('Indica Llegada, Salida y habitación para agregar al grupo.')
      return
    }
    setEnviando(true)
    try {
      const r = await api(`/hotel/grupos/${encodeURIComponent(grupoId)}/reservas`, {
        metodo: 'POST',
        claveIdempotencia: `grp-add-${crypto.randomUUID().slice(0, 12)}`,
        cuerpo: {
          habitacion_id: nueva.habitacion_id,
          inicio: nueva.inicio,
          fin: nueva.fin,
          adultos: Math.max(1, Number(nueva.adultos) || 1),
          ninos: Math.max(0, Number(nueva.ninos) || 0),
          titular_aloja: Boolean(nueva.titular_aloja),
        },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
      } else {
        setGrupo(r.datos.grupo)
        setAviso(`Habitación agregada al grupo (${r.datos.reserva_id}).`)
        setMostrandoAgregar(false)
        setNueva((prev) => ({ ...prev, habitacion_id: '' }))
        setVersion((v) => v + 1)
        if (alCambiar) alCambiar()
      }
    } catch {
      setError('No se pudo conectar con el servidor.')
    } finally {
      setEnviando(false)
    }
  }

  async function llegadaEnLote() {
    setError('')
    setAviso('')
    const confirmado = await confirmar({
      titulo: 'Registrar Llegada en lote',
      mensaje: '¿Registrar la Llegada de todas las habitaciones confirmadas de este grupo?',
      textoConfirmar: 'Registrar Llegada',
      variante: 'primario',
    })
    if (!confirmado) return
    setEnviando(true)
    try {
      const r = await api(`/hotel/grupos/${encodeURIComponent(grupoId)}/entrada`, {
        metodo: 'POST',
        claveIdempotencia: `grp-ent-${crypto.randomUUID().slice(0, 12)}`,
        cuerpo: {},
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
      } else {
        const textoOk = `Llegada registrada en lote para ${plural(r.datos.total_procesadas, 'habitación', 'habitaciones')}.`
        setAviso(textoOk)
        notificarExito(textoOk)
        setVersion((v) => v + 1)
        if (alCambiar) alCambiar()
      }
    } catch {
      setError('No se pudo conectar con el servidor.')
    } finally {
      setEnviando(false)
    }
  }

  if (!grupoId || !grupo) return null

  const confirmadas = (grupo.reservas || []).filter((r) => r.estado === 'confirmada')
  const personasNueva = Math.max(1, (Number(nueva.adultos) || 1) + (Number(nueva.ninos) || 0))

  return (
    <section className="tarjeta" aria-label="Grupo de habitaciones">
      <h2>
        Grupo {grupo.grupo_id}: {grupo.titular_nombre}{' '}
        <span className="nota-clave">({plural(grupo.resumen.total_habitaciones, 'habitación', 'habitaciones')})</span>
      </h2>
      {grupo.notas && <p className="nota-clave">Nota del grupo: {grupo.notas}</p>}
      <p className="nota-clave">
        Total grupo (IVA incl., sin duplicar): <strong>{clp(grupo.resumen.total_aceptado_clp)}</strong> ·
        Cargos asentados: <strong>{clp(grupo.resumen.cargos_netos_clp)}</strong> ·
        Pagado: <strong>{clp(grupo.resumen.pagado_clp)}</strong> ·
        Saldo consolidado: <strong>{clp(grupo.resumen.saldo_clp)}</strong>
      </p>

      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      <ul className="lista-operacion">
        {grupo.reservas.map((item) => {
          const destino = enlaceBase === '/hotel/estadia'
            ? `/hotel/estadia?reserva_id=${encodeURIComponent(item.reserva_id)}`
            : `/hotel/reservas/${encodeURIComponent(item.reserva_id)}`
          const esActual = item.reserva_id === reservaActualId
          return (
            <li key={item.reserva_id} className="fila-operacion">
              <span>
                <strong>{item.habitacion_id}</strong> ({item.tipo_habitacion}) ·{' '}
                {fechaATexto(item.inicio)} → {fechaATexto(item.fin)} ·{' '}
                <span className={`reserva-estado estado-${item.estado}`}>
                  {ETIQUETA_ESTADO[item.estado] || item.estado}
                </span>{' '}
                · Huéspedes: {item.huespedes.registrados}/{item.huespedes.total_esperado}
                {item.titular_aloja ? ' (titular aloja)' : ' (sin titular)'} · Saldo: {clp(item.cuenta.saldo_clp)}
              </span>{' '}
              {esActual ? (
                <span className="nota-clave">(actual)</span>
              ) : (
                <Link href={destino}>Abrir</Link>
              )}
            </li>
          )
        })}
      </ul>

      {puedeEditar && (
        <div className="acciones-fila" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.75rem' }}>
          {confirmadas.length > 0 && (
            <button
              type="button"
              className="boton-primario"
              disabled={enviando}
              onClick={llegadaEnLote}
            >
              {enviando ? 'Procesando…' : `Registrar Llegada del grupo (${confirmadas.length})`}
            </button>
          )}
          <button
            type="button"
            className="boton-secundario"
            onClick={() => { setMostrandoAgregar((v) => !v); setError('') }}
          >
            {mostrandoAgregar ? 'Cancelar nueva habitación' : '+ Agregar habitación al grupo'}
          </button>
        </div>
      )}

      {puedeEditar && mostrandoAgregar && (
        <form className="formulario" onSubmit={agregarHabitacion} style={{ marginTop: '0.75rem' }}>
          <Campo etiqueta="Llegada" type="date" value={nueva.inicio} onChange={(e) => setNueva({ ...nueva, inicio: e.target.value })} />
          <Campo etiqueta="Salida" type="date" value={nueva.fin} onChange={(e) => setNueva({ ...nueva, fin: e.target.value })} />
          <Campo etiqueta="Adultos" type="number" min="1" max="30" value={nueva.adultos} onChange={(e) => setNueva({ ...nueva, adultos: e.target.value })} />
          <Campo etiqueta="Niños" type="number" min="0" max="30" value={nueva.ninos} onChange={(e) => setNueva({ ...nueva, ninos: e.target.value })} />
          <SelectorUnidad
            etiqueta="Habitación adicional"
            inicio={nueva.inicio}
            fin={nueva.fin}
            personas={personasNueva}
            valor={nueva.habitacion_id}
            alCambiar={(id) => setNueva((prev) => ({ ...prev, habitacion_id: id }))}
          />
          <label className="campo-check">
            <input
              type="checkbox"
              checked={nueva.titular_aloja}
              onChange={(e) => setNueva({ ...nueva, titular_aloja: e.target.checked })}
            />{' '}
            El titular también se aloja en esta habitación
          </label>
          <button type="submit" className="boton-primario" disabled={enviando}>
            {enviando ? 'Guardando…' : 'Agregar habitación al grupo'}
          </button>
        </form>
      )}
    </section>
  )
}
