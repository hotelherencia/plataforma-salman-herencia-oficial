'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { api, alRechazar, clp, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, useClaveOperacion, useSesion } from '../../../lib/api'

const ETIQUETA_ESTADO = {
  confirmada: 'confirmada',
  en_estadia: 'en estadía',
  finalizada: 'finalizada',
  cancelada: 'cancelada',
}

export default function Estadia() {
  const sesion = useSesion()
  const [reservaId, setReservaId] = useState('')
  const [detalleReserva, setDetalleReserva] = useState(null)
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [claveEntrada, renovarClaveEntrada] = useClaveOperacion()
  const [claveCancela, renovarClaveCancela] = useClaveOperacion()
  const [claveCargo, renovarClaveCargo] = useClaveOperacion()
  const [cargo, setCargo] = useState({ reserva_id: '', concepto: 'minibar', monto_clp: '5000' })
  const [enviando, setEnviando] = useState(false)
  const enVueloRef = useRef(false)

  // V1-ISSUE-35 / V1-ISSUE-40: precarga desde ?reserva_id= tanto en entrada/
  // cancelación como en cargo, sin disparar ninguna mutación al abrir o recargar.
  useEffect(() => {
    const r = new URLSearchParams(window.location.search).get('reserva_id')
    if (r) {
      setReservaId(r)
      setCargo((prev) => ({ ...prev, reserva_id: prev.reserva_id || r }))
    }
  }, [])

  async function refrescarDetalle(idObjetivo) {
    const limpio = (idObjetivo || '').trim()
    if (!limpio || sesion.fase !== 'ok') return
    try {
      const r = await api(`/hotel/reservas/${encodeURIComponent(limpio)}`)
      if (r.estado === 200) setDetalleReserva(r.datos)
      else if (detalleReserva?.reserva_id === limpio) setDetalleReserva(null)
    } catch {
      // Si la lectura auxiliar falla, el formulario conserva el manejo de error en el submit.
    }
  }

  useEffect(() => {
    const limpio = reservaId.trim()
    if (sesion.fase !== 'ok' || !/^RSV-[A-Za-z0-9_-]+$/.test(limpio)) {
      setDetalleReserva(null)
      return
    }
    let cancelado = false
    api(`/hotel/reservas/${encodeURIComponent(limpio)}`)
      .then((r) => {
        if (cancelado) return
        if (r.estado === 200) setDetalleReserva(r.datos)
        else setDetalleReserva(null)
      })
      .catch(() => {
        if (!cancelado) setDetalleReserva(null)
      })
    return () => {
      cancelado = true
    }
  }, [sesion.fase, reservaId])

  // spec-api-v1: la cancelación la ejecutan recepción o administrador. La
  // acción se oculta a otros roles (la API igual la rechazaría con 403).
  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puedeCancelar = rol === 'recepcion' || rol === 'administrador'

  const detalleActivo = detalleReserva && detalleReserva.reserva_id === reservaId.trim() ? detalleReserva : null
  const detalleCargoActivo =
    detalleReserva && detalleReserva.reserva_id === (cargo.reserva_id || '').trim() ? detalleReserva : null
  const noAdmiteEntrada = Boolean(detalleActivo && detalleActivo.estado !== 'confirmada')
  const noAdmiteCancelacion = Boolean(detalleActivo && detalleActivo.estado !== 'confirmada')
  const noAdmiteCargo = Boolean(
    detalleCargoActivo && !['confirmada', 'en_estadia'].includes(detalleCargoActivo.estado)
  )

  async function checkIn(e) {
    e.preventDefault()
    if (enVueloRef.current) return
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[reservaId, 'ID de la reserva']])
    if (falta) { setError(falta); return }
    enVueloRef.current = true
    setEnviando(true)
    try {
      const r = await api(`/hotel/reservas/${reservaId.trim()}/entrada`, {
        metodo: 'POST',
        claveIdempotencia: claveEntrada,
        cuerpo: {},
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClaveEntrada)
      }
      else {
        setSalida(r.datos)
        renovarClaveEntrada()
        await refrescarDetalle(reservaId)
      }
    } catch {
      setError('La API no está disponible')
    } finally {
      enVueloRef.current = false
      setEnviando(false)
    }
  }

  async function cancelar(e) {
    e.preventDefault()
    if (enVueloRef.current) return
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[reservaId, 'ID de la reserva']])
    if (falta) { setError(falta); return }
    if (!window.confirm('¿Cancelar esta reserva? Se reversan los cargos sin pagar y, fuera de plazo, se carga la primera noche.')) return
    enVueloRef.current = true
    setEnviando(true)
    try {
      const r = await api(`/hotel/reservas/${reservaId.trim()}/cancelacion`, {
        metodo: 'POST',
        claveIdempotencia: claveCancela,
        cuerpo: {},
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClaveCancela)
      }
      else {
        setSalida(r.datos)
        renovarClaveCancela()
        await refrescarDetalle(reservaId)
      }
    } catch {
      setError('La API no está disponible')
    } finally {
      enVueloRef.current = false
      setEnviando(false)
    }
  }

  async function asentarCargo(e) {
    e.preventDefault()
    if (enVueloRef.current) return
    setError('')
    setSalida(null)
    const falta = camposFaltantes([[cargo.reserva_id, 'ID de la reserva'], [cargo.monto_clp, 'Monto CLP']])
    if (falta) { setError(falta); return }
    enVueloRef.current = true
    setEnviando(true)
    try {
      const r = await api(`/hotel/reservas/${cargo.reserva_id.trim()}/cargos`, {
        metodo: 'POST',
        claveIdempotencia: claveCargo,
        cuerpo: { concepto: cargo.concepto, monto_clp: Number(cargo.monto_clp) },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClaveCargo)
      }
      else {
        setSalida(r.datos)
        renovarClaveCargo()
        await refrescarDetalle(cargo.reserva_id)
      }
    } catch {
      setError('La API no está disponible')
    } finally {
      enVueloRef.current = false
      setEnviando(false)
    }
  }

  return (
    <MarcoHotel titulo="Estadía: entrada, cancelación y cargos">
      {detalleActivo && (
        <section className="tarjeta" aria-label="Contexto operativo">
          <h2>
            Reserva {detalleActivo.reserva_id}: {detalleActivo.huesped_nombre}{' '}
            <span className={`reserva-estado estado-${detalleActivo.estado}`}>
              {ETIQUETA_ESTADO[detalleActivo.estado] || detalleActivo.estado}
            </span>
          </h2>
          <p className="nota-clave">
            Habitación <strong>{detalleActivo.habitacion_id}</strong> ({detalleActivo.tipo_habitacion}) ·{' '}
            {detalleActivo.inicio} → {detalleActivo.fin} ({detalleActivo.noches} noche(s)) · Cargos netos:{' '}
            <strong>{clp(detalleActivo.cuenta.cargos_netos_clp)}</strong> · Pagado:{' '}
            <strong>{clp(detalleActivo.cuenta.pagado_clp)}</strong> · Saldo:{' '}
            <strong>{clp(detalleActivo.cuenta.saldo_clp)}</strong> ·{' '}
            <Link href={`/hotel/reservas/${detalleActivo.reserva_id}`}>Ver detalle y cuenta</Link>
          </p>
        </section>
      )}
      <section className="tarjeta">
        <h2>Check-in (entrada a la estadía)</h2>
        <form className="formulario" onSubmit={checkIn}>
          <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
          <button type="submit" className="boton-primario" disabled={enviando || noAdmiteEntrada}>
            {enviando ? "Procesando…" : "Registrar entrada"}
          </button>
        </form>
        {noAdmiteEntrada && (
          <p className="nota-clave">
            La reserva está «{ETIQUETA_ESTADO[detalleActivo.estado] || detalleActivo.estado}»: el check-in solo procede desde «confirmada».
          </p>
        )}
        <p className="nota-clave">Clave: <code>{claveEntrada}</code></p>
      </section>
      {puedeCancelar && (
        <section className="tarjeta">
          <h2>Cancelar reserva (recepción o administrador)</h2>
          <form className="formulario" onSubmit={cancelar}>
            <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
            <button type="submit" className="boton-primario" disabled={enviando || noAdmiteCancelacion}>
              {enviando ? "Procesando…" : "Cancelar reserva"}
            </button>
          </form>
          {noAdmiteCancelacion && (
            <p className="nota-clave">
              La reserva ya está «{ETIQUETA_ESTADO[detalleActivo.estado] || detalleActivo.estado}»: la cancelación solo procede desde «confirmada».
            </p>
          )}
          <p className="nota-clave">Clave: <code>{claveCancela}</code></p>
        </section>
      )}
      <section className="tarjeta">
        <h2>Asentar cargo (minibar, consumo, extra)</h2>
        <form className="formulario" onSubmit={asentarCargo}>
          <Campo etiqueta="Reserva" value={cargo.reserva_id} onChange={(e) => setCargo({ ...cargo, reserva_id: e.target.value })} />
          <Campo etiqueta="Concepto" value={cargo.concepto} onChange={(e) => setCargo({ ...cargo, concepto: e.target.value })} />
          <Campo etiqueta="Monto (CLP)" type="number" value={cargo.monto_clp} onChange={(e) => setCargo({ ...cargo, monto_clp: e.target.value })} />
          <button type="submit" className="boton-primario" disabled={enviando || noAdmiteCargo}>
            {enviando ? "Procesando…" : "Asentar cargo"}
          </button>
        </form>
        {noAdmiteCargo && (
          <p className="nota-clave">
            La reserva está «{ETIQUETA_ESTADO[detalleCargoActivo.estado] || detalleCargoActivo.estado}» (cuenta cerrada): solo se admiten cargos en «confirmada» o «en estadía».
          </p>
        )}
        <p className="nota-clave">Clave: <code>{claveCargo}</code></p>
      </section>
      <button onClick={() => { setSalida(null); setError(''); renovarClaveEntrada(); renovarClaveCancela(); renovarClaveCargo() }} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
