'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, MarcoHotel, useClaveOperacion } from '../../../lib/api'
import { bloqueoSalida, resumenSalida } from '../../../lib/estadias'
import { BuscadorEstadias, FichaEstadia, estilosOperacion as css } from '../_componentes/buscador-estadias'
import { useDetalleReserva } from '../_componentes/selector-reserva'

/**
 * Salida (2026-11-19): se busca al huésped por nombre, habitación, documento
 * o código (sin texto, aparecen las Salidas de hoy). Se elige una tarjeta, se
 * revisa la cuenta y se registra la Salida. Con saldo, se ofrece el pago.
 */
export default function SalidaPage() {
  const [reservaId, setReservaId] = useState('')
  const [version, setVersion] = useState(0)
  const [liquidacion, setLiquidacion] = useState(null)
  const [liquidado, setLiquidado] = useState(null)
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [clave, renovarClave] = useClaveOperacion()
  const detalle = useDetalleReserva(reservaId, version)

  // V1-ISSUE-35: precarga desde el detalle de la reserva («Siguiente paso»).
  useEffect(() => {
    const r = new URLSearchParams(window.location.search).get('reserva_id')
    if (r) setReservaId(r)
  }, [])

  const bloqueo = bloqueoSalida(detalle)

  function elegir(estadia) {
    setError('')
    setLiquidacion(null)
    setReservaId(estadia.reserva_id)
    setVersion((v) => v + 1)
  }

  function otra() {
    setReservaId('')
    setLiquidacion(null)
    setLiquidado(null)
    setError('')
    renovarClave()
  }

  async function registrarSalida() {
    if (!detalle || enviando) return
    setError('')
    setEnviando(true)
    try {
      const r = await api(`/hotel/reservas/${encodeURIComponent(detalle.reserva_id)}/salida`, {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {},
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
      } else {
        setLiquidado(detalle)
        setLiquidacion(r.datos)
        renovarClave()
        setVersion((v) => v + 1)
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setEnviando(false)
    }
  }

  if (liquidacion) {
    return (
      <MarcoHotel titulo="Salida">
        <div className="confirmacion-operacion-contenedor" role="status">
          <span className="confirmacion-icono" aria-hidden="true">✓</span>
          <div className="confirmacion-cuerpo">
            <p className="operacion-confirmada">{resumenSalida(liquidacion, liquidado)}</p>
          </div>
        </div>
        <div className={css.acciones}>
          <button type="button" className="boton-primario" onClick={otra}>Registrar otra Salida</button>
          <Link className="boton-secundario" href={`/hotel/reservas/${liquidacion.reserva_id}`}>Ver la cuenta liquidada</Link>
          <Link className="boton-fantasma" href="/hotel/aseo">Ir a Aseo</Link>
        </div>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Salida">
      {!detalle && (
        <section className="tarjeta">
          <h2>¿Quién se va?</h2>
          <BuscadorEstadias alcance="salida" alElegir={elegir} elegidaId={reservaId} autoFocus />
        </section>
      )}
      {detalle && (
        <section className="tarjeta">
          <h2>Revisar y registrar la Salida</h2>
          <FichaEstadia detalle={detalle} alCambiar={otra}>
            {bloqueo && <p className="alerta" role="alert" data-bloqueo-salida>{bloqueo}</p>}
            <div className={css.acciones}>
              {detalle.cuenta.saldo_clp > 0 && detalle.estado !== 'finalizada' && (
                <Link className="boton-primario" href={`/hotel/pago?reserva_id=${encodeURIComponent(detalle.reserva_id)}&volver=salida`}>
                  Registrar pago del saldo
                </Link>
              )}
              <button
                type="button"
                className={detalle.cuenta.saldo_clp > 0 ? 'boton-secundario' : 'boton-primario'}
                onClick={registrarSalida}
                disabled={Boolean(bloqueo) || enviando}
              >
                {enviando ? 'Registrando…' : 'Registrar Salida y liquidar cuenta'}
              </button>
              <Link className="boton-fantasma" href={`/hotel/reservas/${detalle.reserva_id}`}>Ver detalle de la cuenta</Link>
            </div>
          </FichaEstadia>
        </section>
      )}
      {error && <p role="alert" className="alerta">{error}</p>}
    </MarcoHotel>
  )
}
