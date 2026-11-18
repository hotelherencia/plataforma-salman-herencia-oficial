'use client'

import { useEffect, useState } from 'react'
import { api, clp } from '../../../lib/api'

export const CATEGORIAS_PRODUCTO = [
  ['minibar', 'Minibar'],
  ['cafeteria', 'Cafetería'],
  ['servicio', 'Servicio'],
  ['extra', 'Extra'],
]

/**
 * Selector de producto (#357): búsqueda incremental por palabra y filtro por
 * categoría; al elegir, el precio aparece de inmediato. `alCambiar` recibe el
 * producto completo (o null).
 */
export function SelectorProducto({ valor, alCambiar }) {
  const [texto, setTexto] = useState('')
  const [categoria, setCategoria] = useState('')
  const [productos, setProductos] = useState([])
  const [estado, setEstado] = useState('Cargando productos…')

  useEffect(() => {
    let cancelado = false
    const t = setTimeout(async () => {
      try {
        const q = new URLSearchParams()
        if (texto.trim()) q.set('texto', texto.trim())
        if (categoria) q.set('categoria', categoria)
        const r = await api(`/hotel/productos?${q}`)
        if (cancelado) return
        const lista = r.estado === 200 ? r.datos.productos : []
        setProductos(lista)
        setEstado(lista.length ? '' : 'Sin productos que coincidan')
      } catch {
        if (!cancelado) setEstado('La API no está disponible')
      }
    }, 200)
    return () => { cancelado = true; clearTimeout(t) }
  }, [texto, categoria])

  return (
    <div className="selector-producto">
      <label className="campo">
        <span className="campo-etiqueta">Buscar producto</span>
        <input className="entrada" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Ej.: agua, cerveza, lavandería" />
      </label>
      <label className="campo">
        <span className="campo-etiqueta">Categoría</span>
        <select className="entrada" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
          <option value="">Todas</option>
          {CATEGORIAS_PRODUCTO.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
        </select>
      </label>
      <label className="campo">
        <span className="campo-etiqueta">Producto</span>
        <select
          className="entrada"
          value={valor?.producto_id || ''}
          onChange={(e) => alCambiar(productos.find((p) => p.producto_id === e.target.value) || null)}
        >
          <option value="">{estado || 'Elige un producto'}</option>
          {productos.map((p) => (
            <option key={p.producto_id} value={p.producto_id} disabled={p.controla_stock && p.stock <= 0}>
              {p.nombre} · {clp(p.precio_clp)}{p.controla_stock ? ` · stock ${p.stock}` : ''}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}
