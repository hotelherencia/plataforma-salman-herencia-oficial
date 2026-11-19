'use client'

import { useEffect, useState } from 'react'
import { api } from '../../../lib/api'
import { plural } from '../../../lib/formato'

export const INTERVALO_CONTADOR_MS = 60_000

/**
 * #353: solicitudes `recibida` pendientes, sondeando cada 60 s mientras la
 * pestaña está visible. Devuelve null hasta la primera lectura.
 */
export function useContadorSolicitudes(activo) {
  const [contador, setContador] = useState(null)
  useEffect(() => {
    if (!activo) {
      setContador(null)
      return undefined
    }
    let cancelado = false
    async function leer() {
      if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
      try {
        const r = await api('/hotel/avisos')
        if (!cancelado && r.estado === 200) setContador(r.datos.solicitudes_recibidas)
      } catch {
        // sin red: se reintenta en el próximo ciclo
      }
    }
    leer()
    const t = setInterval(leer, INTERVALO_CONTADOR_MS)
    const alVolver = () => { if (document.visibilityState === 'visible') leer() }
    document.addEventListener('visibilitychange', alVolver)
    return () => {
      cancelado = true
      clearInterval(t)
      document.removeEventListener('visibilitychange', alVolver)
    }
  }, [activo])
  return contador
}

export function Insignia({ valor }) {
  if (!valor) return null
  return (
    <span className="insignia" aria-label={`${plural(valor, 'solicitud', 'solicitudes')} por responder`}>
      {valor > 99 ? '99+' : valor}
    </span>
  )
}
