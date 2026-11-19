'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, MarcoHotel, Campo, CampoSelect, useClaveOperacion, clp } from '../../../lib/api'
import { clasificarPago, DOCUMENTOS, MEDIOS, esTarjeta, validarDatosPago } from '../../../lib/caja'
import { resumenPago } from '../../../lib/estadias'
import Subnav from '../_componentes/subnav'
import { useDetalleReserva } from '../_componentes/selector-reserva'
import { BuscadorEstadias, FichaEstadia, estilosOperacion as css } from '../_componentes/buscador-estadias'
import { SUBNAV_CAJA } from '../../../lib/menu-hotel'

function claveDeCobro() {
  // V1-ISSUE-32: la clave de cobro es por operación, nunca un literal fijo:
  // la API deduplica por (reserva_id, clave) y un reuso con otro monto da 409.
  return `cobro-${crypto.randomUUID().slice(0, 8)}`
}

/**
 * Registrar pago (2026-11-19): se busca al huésped por nombre, documento,
 * habitación o código (sin texto: huéspedes en casa con saldo). Se ve la
 * cuenta, se propone el saldo como monto y se registra el pago.
 */
export default function Pago() {
  const [reservaId, setReservaId] = useState('')
  const [monto, setMonto] = useState('')
  const [medio, setMedio] = useState('efectivo')
  const [documento, setDocumento] = useState('boleta')
  const [receptor, setReceptor] = useState({ rut: '', razon_social: '', giro: '', direccion: '', comuna: '', correo: '' })
  const [voucher, setVoucher] = useState({ marca: '', ultimos4: '', codigo: '', comprobante: '' })
  const [caja, setCaja] = useState(null)
  const [claveCobro, setClaveCobro] = useState(claveDeCobro)
  const [volverASalida, setVolverASalida] = useState(false)
  const [confirmaExceso, setConfirmaExceso] = useState(false)
  const [version, setVersion] = useState(0)
  const [pago, setPago] = useState(null)
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [clave, renovarClave] = useClaveOperacion()
  const detalle = useDetalleReserva(reservaId, version)
  const saldo = detalle ? detalle.cuenta.saldo_clp : null
  const clasificacion = clasificarPago(monto, saldo)

  // V1-ISSUE-35: precarga desde el detalle de la reserva o desde Salida.
  useEffect(() => {
    const p = new URLSearchParams(window.location.search)
    if (p.get('reserva_id')) setReservaId(p.get('reserva_id'))
    setVolverASalida(p.get('volver') === 'salida')
  }, [])

  // Fase 1 contable: medios habilitados, documento por defecto y turno abierto.
  useEffect(() => {
    api('/hotel/caja/estado').then((r) => {
      if (r.estado < 400) {
        setCaja(r.datos)
        setDocumento(r.datos.parametros.documento_por_defecto)
        if (!r.datos.parametros.medios.includes('efectivo')) setMedio(r.datos.parametros.medios[0] || 'transferencia')
      }
    }).catch(() => {})
  }, [])
  const medios = MEDIOS.filter(([m]) => !caja || caja.parametros.medios.includes(m))
  const sinTurnoEfectivo = caja && !caja.turno && medio === 'efectivo' && caja.parametros.exigir_turno_efectivo

  // #365: el monto propuesto es el saldo pendiente de la reserva elegida.
  useEffect(() => {
    if (detalle && !pago) setMonto(detalle.cuenta.saldo_clp > 0 ? String(detalle.cuenta.saldo_clp) : '')
    setConfirmaExceso(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detalle?.reserva_id])

  function elegir(estadia) {
    setError('')
    setPago(null)
    setReservaId(estadia.reserva_id)
  }

  function nuevo({ mismoHuesped = false } = {}) {
    setPago(null)
    setError('')
    setConfirmaExceso(false)
    setClaveCobro(claveDeCobro())
    renovarClave()
    if (!mismoHuesped) {
      setReservaId('')
      setMonto('')
    } else {
      setMonto(saldo > 0 ? String(saldo) : '')
    }
  }

  async function cobrar(e) {
    e.preventDefault()
    if (enviando || !detalle) return
    setError('')
    setPago(null)
    if (!(Number(monto) > 0)) { setError('Indica el monto pagado (mayor que $0).'); return }
    const invalido = medio === 'pasarela' ? null : validarDatosPago({
      medio, codigo: voucher.codigo, ultimos4: voucher.ultimos4, documento, receptor,
    })
    if (invalido) { setError(invalido); return }
    if (clasificacion?.tipo === 'exceso' && !confirmaExceso) {
      setError(`El monto supera el saldo en ${clp(clasificacion.diferencia)}. Marca la confirmación de pago en exceso para continuar.`)
      return
    }
    setEnviando(true)
    try {
      const r = await api(`/hotel/reservas/${encodeURIComponent(detalle.reserva_id)}/pagos`, {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: medio === 'pasarela'
          ? { monto_clp: Number(monto), clave: claveCobro, modo: 'pasarela' }
          : {
            monto_clp: Number(monto), clave: claveCobro, modo: 'manual', medio,
            confirmar_exceso: clasificacion?.tipo === 'exceso' && confirmaExceso,
            documento_tipo: documento,
            ...(documento === 'factura' ? {
              receptor: Object.fromEntries(Object.entries(receptor).map(([k, v]) => [k, v.trim() || null])),
            } : {}),
            ...(esTarjeta(medio) ? {
              codigo_autorizacion: voucher.codigo.trim(),
              tarjeta_ultimos4: voucher.ultimos4.trim() || null,
              tarjeta_marca: voucher.marca.trim() || null,
            } : {}),
            ...(medio === 'transferencia' && voucher.comprobante.trim() ? { comprobante: voucher.comprobante.trim() } : {}),
          },
      })
      if (r.estado === 503) {
        setError('El pago en línea aún no está habilitado: no quedó nada cobrado. Registra el pago como efectivo o transferencia.')
        alRechazar(r.estado, renovarClave)
      } else if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
      } else {
        setPago(r.datos)
        renovarClave()
        setClaveCobro(claveDeCobro())
        setVersion((v) => v + 1)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <MarcoHotel titulo="Registrar pago">
      <Subnav items={SUBNAV_CAJA} />
      {!detalle && (
        <section className="tarjeta">
          <h2>¿Quién paga?</h2>
          <BuscadorEstadias alcance="pago" alElegir={elegir} elegidaId={reservaId} autoFocus />
        </section>
      )}
      {detalle && (
        <section className="tarjeta">
          <h2>Pago de la cuenta</h2>
          <FichaEstadia detalle={detalle} alCambiar={() => nuevo()} />
          {pago ? (
            <>
              <div className="confirmacion-operacion-contenedor" role="status">
                <span className="confirmacion-icono" aria-hidden="true">✓</span>
                <div className="confirmacion-cuerpo">
                  <p className="operacion-confirmada">
                    {pago.reintento ? 'Este pago ya estaba registrado: no se duplicó.' : resumenPago(pago)}
                  </p>
                </div>
              </div>
              <div className={css.acciones}>
                {volverASalida && saldo === 0 && (
                  <Link className="boton-primario" href={`/hotel/salida?reserva_id=${encodeURIComponent(detalle.reserva_id)}`}>
                    Continuar con la Salida
                  </Link>
                )}
                {saldo > 0 && (
                  <button type="button" className="boton-secundario" onClick={() => nuevo({ mismoHuesped: true })}>
                    Registrar otro pago para este huésped
                  </button>
                )}
                <button type="button" className={volverASalida && saldo === 0 ? 'boton-secundario' : 'boton-primario'} onClick={() => nuevo()}>
                  Registrar otro pago
                </button>
              </div>
            </>
          ) : (
            <form className="formulario" onSubmit={cobrar}>
              <Campo etiqueta="Monto pagado (CLP)" type="number" min="1" inputMode="numeric" value={monto}
                onChange={(e) => { setMonto(e.target.value); setConfirmaExceso(false) }} />
              <CampoSelect etiqueta="Medio de pago" value={medio} onChange={(e) => setMedio(e.target.value)}>
                {medios.map(([valor, nombre]) => <option key={valor} value={valor}>{nombre}</option>)}
                <option value="pasarela">Pago en línea (aún no habilitado)</option>
              </CampoSelect>
              {sinTurnoEfectivo && (
                <p className="alerta" role="alert" data-sin-turno>
                  Para recibir efectivo abre primero el turno en <Link href="/hotel/caja?pestana=turno">Caja y pagos → Turno</Link>.
                </p>
              )}
              {esTarjeta(medio) && (
                <>
                  <p className="nota-clave">La tarjeta se cobra en el POS. Aquí anota solo el código de autorización del voucher y, si quieres, la marca y los últimos 4 dígitos. Nunca el número completo ni el código de seguridad.</p>
                  <Campo etiqueta="Código de autorización del voucher" value={voucher.codigo} maxLength={20}
                    onChange={(e) => setVoucher({ ...voucher, codigo: e.target.value })} />
                  <Campo etiqueta="Últimos 4 dígitos (opcional)" value={voucher.ultimos4} maxLength={4} inputMode="numeric"
                    onChange={(e) => setVoucher({ ...voucher, ultimos4: e.target.value.replace(/\D/g, '') })} />
                  <Campo etiqueta="Marca (opcional, p. ej. Visa)" value={voucher.marca} maxLength={30}
                    onChange={(e) => setVoucher({ ...voucher, marca: e.target.value })} />
                </>
              )}
              {medio === 'transferencia' && (
                <Campo etiqueta="N° de comprobante de la transferencia (opcional)" value={voucher.comprobante} maxLength={60}
                  onChange={(e) => setVoucher({ ...voucher, comprobante: e.target.value })} />
              )}
              {medio !== 'pasarela' && (
                <CampoSelect etiqueta="¿Boleta o factura?" value={documento} onChange={(e) => setDocumento(e.target.value)}>
                  {DOCUMENTOS.map(([valor, nombre]) => <option key={valor} value={valor}>{nombre}</option>)}
                </CampoSelect>
              )}
              {medio !== 'pasarela' && documento === 'factura' && (
                <fieldset className="tarjeta">
                  <legend>Datos para la factura</legend>
                  {[['rut', 'RUT de la empresa'], ['razon_social', 'Razón social'], ['giro', 'Giro'],
                    ['direccion', 'Dirección'], ['comuna', 'Comuna'], ['correo', 'Correo para enviar la factura (opcional)']].map(([k, etiqueta]) => (
                    <Campo key={k} etiqueta={etiqueta} value={receptor[k]} maxLength={k === 'direccion' ? 160 : 120}
                      onChange={(e) => setReceptor({ ...receptor, [k]: e.target.value })} />
                  ))}
                </fieldset>
              )}
              {clasificacion?.tipo === 'parcial' && (
                <p className="estado" role="status" data-pago="parcial">
                  Pago parcial: quedará un saldo pendiente de <strong>{clp(clasificacion.diferencia)}</strong>.
                </p>
              )}
              {clasificacion?.tipo === 'total' && (
                <p className="estado" role="status" data-pago="total">Con este pago la cuenta queda saldada.</p>
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
              <button type="submit" className="boton-primario" disabled={enviando}>
                {enviando ? 'Registrando…' : 'Registrar pago'}
              </button>
            </form>
          )}
        </section>
      )}
      {error && <p role="alert" className="alerta">{error}</p>}
    </MarcoHotel>
  )
}
