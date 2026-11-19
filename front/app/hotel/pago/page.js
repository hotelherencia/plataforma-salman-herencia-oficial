'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, camposFaltantes, MarcoHotel, SalidaJson, Campo, CampoSelect, useClaveOperacion, clp } from '../../../lib/api'
import { clasificarPago } from '../../../lib/caja'
import Subnav from '../_componentes/subnav'
import { SelectorReserva, FichaReserva, useDetalleReserva } from '../_componentes/selector-reserva'
import { SUBNAV_CAJA } from '../../../lib/menu-hotel'

function claveDeCobro() {
  // V1-ISSUE-32: la clave de cobro es por operación, nunca un literal fijo:
  // la API deduplica por (reserva_id, clave) y un reuso con otro monto da 409.
  return `cobro-${crypto.randomUUID().slice(0, 8)}`
}

export default function Pago() {
  const [campos, setCampos] = useState({
    reserva_id: '',
    monto_clp: '',
    clave: claveDeCobro(),
    modo: 'manual',
  })
  // #356/#364: la reserva precargada queda fija (solo lectura) hasta que se libera a propósito.
  const [fija, setFija] = useState(false)
  const [confirmaExceso, setConfirmaExceso] = useState(false)
  const [version, setVersion] = useState(0)
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [aviso503, setAviso503] = useState(false)
  const [clave, renovarClave] = useClaveOperacion()
  const detalle = useDetalleReserva(campos.reserva_id, version)
  const saldo = detalle ? detalle.cuenta.saldo_clp : null
  const clasificacion = clasificarPago(campos.monto_clp, saldo)

  // V1-ISSUE-35: precarga del detalle de reserva («Siguiente paso»).
  useEffect(() => {
    const r = new URLSearchParams(window.location.search).get('reserva_id')
    if (r) {
      setCampos((c) => ({ ...c, reserva_id: r }))
      setFija(true)
    }
  }, [])

  // #365: el monto propuesto es el saldo pendiente de la reserva elegida.
  useEffect(() => {
    if (detalle) setCampos((c) => ({ ...c, monto_clp: detalle.cuenta.saldo_clp > 0 ? String(detalle.cuenta.saldo_clp) : '' }))
    setConfirmaExceso(false)
  }, [detalle?.reserva_id])

  async function cobrar(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    setAviso503(false)
    const falta = camposFaltantes([[campos.reserva_id, 'Reserva'], [campos.monto_clp, 'Monto CLP']])
    if (falta) { setError(falta); return }
    if (clasificacion?.tipo === 'exceso' && !confirmaExceso) {
      setError(`El monto supera el saldo en ${clp(clasificacion.diferencia)}. Marca la confirmación de pago en exceso para continuar.`)
      return
    }
    try {
      const r = await api(`/hotel/reservas/${campos.reserva_id}/pagos`, {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {
          monto_clp: Number(campos.monto_clp), clave: campos.clave, modo: campos.modo,
          confirmar_exceso: clasificacion?.tipo === 'exceso' && confirmaExceso,
        },
      })
      if (r.estado === 503) setAviso503(true)
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
      } else {
        setSalida(r.datos)
        renovarClave()
        setCampos((c) => ({ ...c, clave: claveDeCobro() }))
        setVersion((v) => v + 1)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <MarcoHotel titulo="Pago">
      <Subnav items={SUBNAV_CAJA} />
      <section className="tarjeta">
        <form className="formulario" onSubmit={cobrar}>
          <SelectorReserva
            valor={campos.reserva_id}
            fijo={fija}
            alCambiar={(id) => setCampos((c) => ({ ...c, reserva_id: id }))}
            alLiberar={() => { setFija(false); setCampos((c) => ({ ...c, reserva_id: '' })) }}
          />
          <FichaReserva detalle={detalle} />
          <Campo etiqueta="Monto (CLP)" type="number" value={campos.monto_clp} onChange={(e) => { setCampos({ ...campos, monto_clp: e.target.value }); setConfirmaExceso(false) }} />
          {clasificacion?.tipo === 'parcial' && (
            <p className="estado" role="status" data-pago="parcial">
              Pago parcial: quedará un saldo pendiente de <strong>{clp(clasificacion.diferencia)}</strong>.
            </p>
          )}
          {clasificacion?.tipo === 'exceso' && (
            <div className="alerta" role="alert" data-pago="exceso">
              <p>Pago en exceso: supera el saldo en <strong>{clp(clasificacion.diferencia)}</strong>.</p>
              <label className="campo-check">
                <input type="checkbox" checked={confirmaExceso} onChange={(e) => setConfirmaExceso(e.target.checked)} />
                Confirmo que el huésped paga de más (queda saldo a favor)
              </label>
            </div>
          )}
          <Campo etiqueta="Clave del cobro" value={campos.clave} onChange={(e) => setCampos({ ...campos, clave: e.target.value })} />
          <CampoSelect etiqueta="Modo" value={campos.modo} onChange={(e) => setCampos({ ...campos, modo: e.target.value })}>
            <option value="manual">Manual de caja (efectivo/transferencia)</option>
            <option value="pasarela">Pasarela (no configurada)</option>
          </CampoSelect>
          <button type="submit" className="boton-primario">Registrar pago</button>
        </form>
        <p className="nota-chica">El abono se registra directamente en la cuenta de la reserva seleccionada.</p>
      </section>
      <span className="nota-clave nota-idempotencia" aria-hidden="true"><code>{clave}</code></span>
      <button onClick={() => { setSalida(null); setError(''); setAviso503(false); renovarClave(); setCampos((c) => ({ ...c, clave: claveDeCobro() })) }} className="boton-secundario">Nueva operación</button>
      {aviso503 && <p role="alert" className="alerta">La pasarela no está configurada: nada quedó marcado como cobrado.</p>}
      {error && <p role="alert" className="alerta">{error}</p>}
      {salida?.reintento && <p className="estado">Este pago ya estaba registrado (reintento con la misma clave): no se duplicó.</p>}
      {salida && !salida.reintento && (
        <p role="status" className="aviso-ok">
          Pago de {clp(salida.monto_clp)} registrado para <strong>{salida.huesped_nombre}</strong> (habitación {salida.habitacion_id}).
          {salida.tipo === 'parcial' && <> Saldo pendiente: <strong>{clp(salida.saldo_despues_clp)}</strong>.</>}
          {salida.tipo === 'exceso' && <> Saldo a favor del huésped: <strong>{clp(-salida.saldo_despues_clp)}</strong>.</>}
          {salida.tipo === 'total' && <> Cuenta saldada.</>}
        </p>
      )}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
