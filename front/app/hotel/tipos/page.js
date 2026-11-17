'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

/** La configuración del hotel unificó esta pantalla (entrega 1A.3). */
export default function RedirigirTipos() {
  const router = useRouter()
  useEffect(() => {
    router.replace('/hotel/configuracion?seccion=tipos')
  }, [router])
  return <p className="estado">Redirigiendo a Configuración del hotel…</p>
}
