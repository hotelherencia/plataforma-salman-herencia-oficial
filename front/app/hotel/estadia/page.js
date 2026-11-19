'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { api, alRechazar, clp, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, useClaveOperacion, useSesion } from '../../../lib/api'
import { SelectorReserva } from '../_componentes/selector-reserva'
import { BuscadorEstadias } from '../_componentes/buscador-estadias'
import { CampoDocumento, SelectorUnidad } from '../_componentes/campos-recepcion'
import { SelectorProducto } from '../_componentes/selector-producto'
import { esAdminHotel } from '../../../lib/roles'
import { validarDocumento } from '../../../lib/documento'
import { gestionaRecepcion } from '../../../lib/roles'
import { fechaATexto, plural } from '../../../lib/formato'

const ETIQUETA_ESTADO = {
  confirmada: 'confirmada',
  en_estadia: 'en estadía',
  finalizada: 'finalizada',
  cancelada: 'cancelada',
}

export default function Estadia() {
  const sesion = useSesion()
  const puedeConceptoLibre = sesion.fase === 'ok' && esAdminHotel(sesion.usuario.rol)
  const [reservaId, setReservaId] = useState('')
  const [detalleReserva, setDetalleReserva] = useState(null)
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [claveEntrada, renovarClaveEntrada] = useClaveOperacion()
  const [claveCancela, renovarClaveCancela] = useClaveOperacion()
  const [claveCargo, renovarClaveCargo] = useClaveOperacion()
  // #357: el cargo es un producto del catálogo (precio automático); el concepto
  // libre queda solo para la administración y exige motivo.
  const [cargo, setCargo] = useState({ reserva_id: '', producto: null, cantidad: '1', libre: false, concepto: '', monto_clp: '', motivo: '' })
  // #356: la reserva del cargo precargada queda fija; solo se cambia a propósito.
  const [cargoFijo, setCargoFijo] = useState(false)
  // #360/#367: unidad confirmada al llegar y documento validado si falta.
  const [unidadLlegada, setUnidadLlegada] = useState('')
  const [docEntrada, setDocEntrada] = useState({ tipo: 'rut', numero: '' })
  const [enviando, setEnviando] = useState(false)
  const enVueloRef = useRef(false)

  // V1-ISSUE-35 / V1-ISSUE-40: precarga desde ?reserva_id= tanto en entrada/
  // cancelación como en cargo, sin disparar ninguna mutación al abrir o recargar.
  useEffect(() => {
    const r = new URLSearchParams(window.location.search).get('reserva_id')
    if (r) {
      setReservaId(r)
      setCargo((prev) => ({ ...prev, reserva_id: prev.reserva_id || r }))
      setCargoFijo(true)
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
  const puedeCancelar = gestionaRecepcion(rol)

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
    const falta = camposFaltantes([[reservaId, 'el huésped (búscalo por nombre, habitación o documento)']])
    if (falta) { setError(falta); return }
    // D-ENT-01 (2026-11-06): la entrada exige documento del huésped. Si la
    // reserva no lo trae (p. ej. conversión de solicitud pública), se pide
    // aquí y se reintenta con el cuerpo.
    const cuerpo = {}
    if (detalleActivo && !detalleActivo.huesped_documento) {
      const doc = validarDocumento(docEntrada.tipo, docEntrada.numero)
      if (!doc.ok) { setError(`Documento del huésped: ${doc.error}`); return }
      cuerpo.documento = doc.valor
      cuerpo.documento_tipo = docEntrada.tipo
    }
    if (detalleActivo && unidadLlegada && unidadLlegada !== detalleActivo.habitacion_id) cuerpo.habitacion_id = unidadLlegada
    enVueloRef.current = true
    setEnviando(true)
    try {
      const r = await api(`/hotel/reservas/${reservaId.trim()}/entrada`, {
        metodo: 'POST',
        claveIdempotencia: claveEntrada,
        cuerpo,
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
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
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
    const falta = camposFaltantes([[reservaId, 'el huésped (búscalo por nombre, habitación o documento)']])
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
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
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
    const falta = camposFaltantes(cargo.libre
      ? [[cargo.reserva_id, 'Reserva'], [cargo.concepto, 'Concepto'], [cargo.monto_clp, 'Monto CLP'], [cargo.motivo, 'Motivo']]
      : [[cargo.reserva_id, 'Reserva'], [cargo.producto?.producto_id, 'Producto']])
    if (falta) { setError(falta); return }
    const cantidad = Math.max(1, Number(cargo.cantidad) || 1)
    const cuerpoCargo = cargo.libre
      ? { concepto: `${cargo.concepto.trim()} (motivo: ${cargo.motivo.trim()})`.slice(0, 200), monto_clp: Number(cargo.monto_clp) }
      : { producto_id: cargo.producto.producto_id, cantidad }
    enVueloRef.current = true
    setEnviando(true)
    try {
      const r = await api(`/hotel/reservas/${cargo.reserva_id.trim()}/cargos`, {
        metodo: 'POST',
        claveIdempotencia: claveCargo,
        cuerpo: cuerpoCargo,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClaveCargo)
      }
      else {
        setSalida(r.datos)
        renovarClaveCargo()
        setCargo((c) => ({ ...c, producto: null, cantidad: '1', concepto: '', monto_clp: '', motivo: '' }))
        await refrescarDetalle(cargo.reserva_id)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      enVueloRef.current = false
      setEnviando(false)
    }
  }

  return (
    <MarcoHotel titulo="Llegada, cancelación y cargos">
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
            {fechaATexto(detalleActivo.inicio)} → {fechaATexto(detalleActivo.fin)} ({plural(detalleActivo.noches, 'noche')}) · Total cargos (IVA incl.):{' '}
            <strong>{clp(detalleActivo.cuenta.cargos_netos_clp)}</strong> · Pagado:{' '}
            <strong>{clp(detalleActivo.cuenta.pagado_clp)}</strong> · Saldo:{' '}
            <strong>{clp(detalleActivo.cuenta.saldo_clp)}</strong> ·{' '}
            <Link href={`/hotel/reservas/${detalleActivo.reserva_id}`}>Ver detalle y cuenta</Link>
          </p>
        </section>
      )}
      <section className="tarjeta">
        <h2>Registrar Llegada</h2>
        {puedeCancelar && !detalleActivo && (
          <BuscadorEstadias alcance="llegada" elegidaId={reservaId} alElegir={(r) => { setError(''); setSalida(null); setReservaId(r.reserva_id) }} />
        )}
        <form className="formulario" onSubmit={checkIn}>
          {puedeCancelar && detalleActivo ? (
            <div className="campo" data-reserva-fija>
              <span className="campo-etiqueta">Huésped</span>
              <span className="reserva-fija">
                <strong>{detalleActivo.huesped_nombre}</strong> · habitación {detalleActivo.habitacion_id}
                <button type="button" className="boton-fantasma" onClick={() => { setReservaId(''); setUnidadLlegada(''); setError('') }}>
                  Cambiar huésped
                </button>
              </span>
            </div>
          ) : !puedeCancelar && (
            <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
          )}
          {detalleActivo && detalleActivo.estado === 'confirmada' && (
            <SelectorUnidad
              etiqueta="Habitación al llegar (confirma o cambia)"
              inicio={detalleActivo.inicio}
              fin={detalleActivo.fin}
              personas={detalleActivo.personas || 1}
              incluir={detalleActivo.habitacion_id}
              valor={unidadLlegada || detalleActivo.habitacion_id}
              alCambiar={setUnidadLlegada}
            />
          )}
          {detalleActivo && detalleActivo.estado === 'confirmada' && !detalleActivo.huesped_documento && (
            <CampoDocumento tipo={docEntrada.tipo} numero={docEntrada.numero} alCambiar={setDocEntrada} />
          )}
          <button type="submit" className="boton-primario" disabled={enviando || noAdmiteEntrada}>
            {enviando ? "Procesando…" : "Registrar Llegada"}
          </button>
        </form>
        {noAdmiteEntrada && (
          <p className="nota-clave">
            La reserva está «{ETIQUETA_ESTADO[detalleActivo.estado] || detalleActivo.estado}»: la Llegada solo se registra desde «confirmada».
          </p>
        )}
        <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveEntrada}</code></span>
      </section>
      {puedeCancelar && (
        <section className="tarjeta">
          <h2>Cancelar reserva (recepción o administración del hotel)</h2>
          <form className="formulario" onSubmit={cancelar}>
            <Campo etiqueta="Reserva" value={reservaId} onChange={(e) => setReservaId(e.target.value)} />
            <button type="submit" className="boton-secundario boton-peligro" disabled={enviando || noAdmiteCancelacion}>
              {enviando ? "Procesando…" : "Cancelar reserva"}
            </button>
          </form>
          {noAdmiteCancelacion && (
            <p className="nota-clave">
              La reserva ya está «{ETIQUETA_ESTADO[detalleActivo.estado] || detalleActivo.estado}»: la cancelación solo procede desde «confirmada».
            </p>
          )}
          <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveCancela}</code></span>
        </section>
      )}
      <section className="tarjeta">
        <h2>Asentar cargo (minibar, consumo, extra)</h2>
        <form className="formulario" onSubmit={asentarCargo}>
          <SelectorReserva
            valor={cargo.reserva_id}
            fijo={cargoFijo}
            alCambiar={(id) => { setCargo((c) => ({ ...c, reserva_id: id })); if (id) refrescarDetalle(id) }}
            alLiberar={() => { setCargoFijo(false); setCargo((c) => ({ ...c, reserva_id: '' })) }}
          />
          {detalleCargoActivo && (
            <p className="nota-clave" data-cargo-huesped>
              Huésped <strong>{detalleCargoActivo.huesped_nombre}</strong> · habitación {detalleCargoActivo.habitacion_id}
            </p>
          )}
          {!cargo.libre && (
            <>
              <SelectorProducto valor={cargo.producto} alCambiar={(p) => setCargo((c) => ({ ...c, producto: p }))} />
              <Campo etiqueta="Cantidad" type="number" min="1" max="100" value={cargo.cantidad} onChange={(e) => setCargo({ ...cargo, cantidad: e.target.value })} />
              {cargo.producto && (
                <p className="estado" role="status" data-cargo-total>
                  {cargo.producto.nombre}: {clp(cargo.producto.precio_clp)} × {Math.max(1, Number(cargo.cantidad) || 1)} ={' '}
                  <strong>{clp(cargo.producto.precio_clp * Math.max(1, Number(cargo.cantidad) || 1))}</strong>
                  {cargo.producto.controla_stock && <> · quedan {cargo.producto.stock}</>}
                </p>
              )}
            </>
          )}
          {puedeConceptoLibre && (
            <label className="campo-check">
              <input type="checkbox" checked={cargo.libre} onChange={(e) => setCargo({ ...cargo, libre: e.target.checked })} />
              Concepto libre (solo administración, con motivo)
            </label>
          )}
          {cargo.libre && (
            <>
              <Campo etiqueta="Concepto" value={cargo.concepto} onChange={(e) => setCargo({ ...cargo, concepto: e.target.value })} />
              <Campo etiqueta="Monto (CLP)" type="number" value={cargo.monto_clp} onChange={(e) => setCargo({ ...cargo, monto_clp: e.target.value })} />
              <Campo etiqueta="Motivo" value={cargo.motivo} onChange={(e) => setCargo({ ...cargo, motivo: e.target.value })} />
            </>
          )}
          <button type="submit" className="boton-primario" disabled={enviando || noAdmiteCargo}>
            {enviando ? "Procesando…" : "Asentar cargo"}
          </button>
        </form>
        {noAdmiteCargo && (
          <p className="nota-clave">
            La reserva está «{ETIQUETA_ESTADO[detalleCargoActivo.estado] || detalleCargoActivo.estado}» (cuenta cerrada): solo se admiten cargos en «confirmada» o «en estadía».
          </p>
        )}
        <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{claveCargo}</code></span>
      </section>
      <button onClick={() => { setSalida(null); setError(''); renovarClaveEntrada(); renovarClaveCancela(); renovarClaveCargo() }} className="boton-secundario">Nueva operación</button>
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
