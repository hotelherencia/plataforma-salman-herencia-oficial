'use client'

import { useEffect, useState } from 'react'

const ESTILO = { outline: '2px solid var(--c-verde)', outlineOffset: '-2px', background: 'var(--c-verde-suave)' }

/**
 * Enlace directo desde un aviso por correo (`?id=SOL-…` o `?id=LEAD-…`):
 * marca esa fila y la deja a la vista cuando la lista termina de cargar.
 */
export function useDestacada(lista) {
  const [id, setId] = useState(null)
  useEffect(() => {
    setId(new URLSearchParams(window.location.search).get('id'))
  }, [])
  useEffect(() => {
    if (!id || !lista) return
    const fila = document.querySelector(`[data-destacada="true"]`)
    if (fila) fila.scrollIntoView({ block: 'center', behavior: 'smooth' })
  }, [id, lista])
  return {
    id,
    props: (filaId) => (id && filaId === id ? { 'data-destacada': 'true', 'aria-current': 'true', style: ESTILO } : {}),
  }
}
