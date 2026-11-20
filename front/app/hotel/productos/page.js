'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, Campo, CampoSelect, useSesion } from '../../../lib/api'
import { esAdminHotel } from '../../../lib/roles'
import { CATEGORIAS_PRODUCTO } from '../_componentes/selector-producto'
import { ImportarProductos } from '../_componentes/importar-productos'
import { ReposicionStock } from '../_componentes/reposicion-stock'
import css from '../_componentes/operacion.module.css'

// Pestañas internas (no agregan entradas al menú): catálogo, reposición y tres formas de cargar.
const PESTANAS = [
  ['catalogo', 'Catálogo'],
  ['reposicion', 'Stock y reposición'],
  ['factura', 'Cargar desde factura'],
  ['planilla', 'Pegar planilla'],
  ['lector', 'Lector de códigos'],
]

const NOMBRE_CATEGORIA = Object.fromEntries(CATEGORIAS_PRODUCTO)

function clave() {
  return `prd-${crypto.randomUUID().slice(0, 12)}`
}

/**
 * Productos y stock (#357): mantenedor del catálogo de cargos para la
 * administración del hotel. Precio con IVA; el cargo lo copia al asentarse.
 */
export default function Productos() {
  const sesion = useSesion()
  const esAdmin = sesion.fase === 'ok' && esAdminHotel(sesion.usuario.rol)
  const [lista, setLista] = useState(null)
  const [pestana, setPestana] = useState('catalogo')
  const [alta, setAlta] = useState({ nombre: '', categoria: 'minibar', precio_clp: '', controla_stock: false, stock: '0', stock_minimo: '0', codigo: '' })
  const [ajustes, setAjustes] = useState({})
  const [precios, setPrecios] = useState({})
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  const cargar = useCallback(async () => {
    try {
      const r = await api('/hotel/productos?inactivos=true')
      if (r.estado === 200) setLista(r.datos.productos)
      else setError(mensajeDeError(r.datos, r.estado))
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }, [])

  useEffect(() => {
    if (sesion.fase === 'ok') cargar()
  }, [sesion.fase, cargar])

  async function enviar(ruta, metodo, cuerpo, ok) {
    setError('')
    setAviso('')
    try {
      const r = await api(ruta, { metodo, cuerpo, claveIdempotencia: clave() })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        return false
      }
      setAviso(ok)
      await cargar()
      return true
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
      return false
    }
  }

  async function crear(e) {
    e.preventDefault()
    if (alta.nombre.trim().length < 2 || !(Number(alta.precio_clp) > 0)) {
      setError('Indica nombre y precio (mayor que 0).')
      return
    }
    const ok = await enviar('/hotel/productos', 'POST', {
      nombre: alta.nombre.trim(), categoria: alta.categoria, precio_clp: Number(alta.precio_clp),
      controla_stock: alta.controla_stock, stock: alta.controla_stock ? Number(alta.stock) || 0 : 0,
      stock_minimo: alta.controla_stock ? Number(alta.stock_minimo) || 0 : 0,
      ...(alta.codigo.trim() ? { codigo: alta.codigo.trim() } : {}),
    }, `Producto «${alta.nombre.trim()}» creado.`)
    if (ok) setAlta({ nombre: '', categoria: alta.categoria, precio_clp: '', controla_stock: false, stock: '0', stock_minimo: '0', codigo: '' })
  }

  function ajustar(p) {
    const a = ajustes[p.producto_id] || {}
    const delta = Number(a.delta)
    if (!Number.isInteger(delta) || delta === 0) { setError('El ajuste debe ser un entero distinto de 0 (negativo para merma).'); return }
    if (!a.motivo || a.motivo.trim().length < 3) { setError('Indica el motivo del ajuste (mínimo 3 caracteres).'); return }
    enviar(`/hotel/productos/${p.producto_id}/stock`, 'POST', { delta, motivo: a.motivo.trim() }, `Stock de «${p.nombre}» ajustado.`)
      .then((ok) => ok && setAjustes((x) => ({ ...x, [p.producto_id]: {} })))
  }

  function cambiarPrecio(p) {
    const precio = Number(precios[p.producto_id])
    if (!(precio > 0)) { setError('El precio debe ser mayor que 0.'); return }
    enviar(`/hotel/productos/${p.producto_id}`, 'PUT', { precio_clp: precio }, `Precio de «${p.nombre}» actualizado (los cargos ya asentados no cambian).`)
      .then((ok) => ok && setPrecios((x) => ({ ...x, [p.producto_id]: '' })))
  }

  if (sesion.fase === 'ok' && !esAdmin) {
    return (
      <MarcoHotel titulo="Productos y stock">
        <p className="alerta" role="alert">Solo la administración del hotel mantiene el catálogo de productos.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Productos y stock">
      <div className={css.pestanas} role="tablist" aria-label="Secciones de productos">
        {PESTANAS.map(([id, nombre]) => (
          <button key={id} type="button" role="tab" id={`pestana-${id}`} aria-controls={`panel-${id}`}
            aria-selected={pestana === id} className={css.pestana} onClick={() => setPestana(id)}>
            {nombre}
          </button>
        ))}
      </div>
      {pestana === 'reposicion' && (
        <div role="tabpanel" id="panel-reposicion" aria-labelledby="pestana-reposicion">
          <ReposicionStock alCambiar={cargar} />
        </div>
      )}
      {pestana !== 'catalogo' && pestana !== 'reposicion' && (
        <div role="tabpanel" id={`panel-${pestana}`} aria-labelledby={`pestana-${pestana}`}>
          <ImportarProductos fuente={pestana} alCargar={cargar} />
        </div>
      )}
      {pestana === 'catalogo' && (
      <div role="tabpanel" id="panel-catalogo" aria-labelledby="pestana-catalogo">
      <section className="tarjeta">
        <h2>Nuevo producto</h2>
        <form className="formulario" onSubmit={crear}>
          <Campo etiqueta="Nombre" value={alta.nombre} onChange={(e) => setAlta({ ...alta, nombre: e.target.value })} />
          <CampoSelect etiqueta="Categoría" value={alta.categoria} onChange={(e) => setAlta({ ...alta, categoria: e.target.value })}>
            {CATEGORIAS_PRODUCTO.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
          </CampoSelect>
          <Campo etiqueta="Precio con IVA (CLP)" type="number" min="1" value={alta.precio_clp} onChange={(e) => setAlta({ ...alta, precio_clp: e.target.value })} />
          <Campo etiqueta="Código (opcional)" value={alta.codigo} placeholder="Escanea o escribe" autoComplete="off"
            onChange={(e) => setAlta({ ...alta, codigo: e.target.value.replace(/\s+/g, '') })} />
          <label className="campo-check">
            <input type="checkbox" checked={alta.controla_stock} onChange={(e) => setAlta({ ...alta, controla_stock: e.target.checked })} />
            Controla stock (minibar)
          </label>
          {alta.controla_stock && (
            <>
              <Campo etiqueta="Stock inicial" type="number" min="0" value={alta.stock} onChange={(e) => setAlta({ ...alta, stock: e.target.value })} />
              <Campo etiqueta="Stock mínimo (alerta)" type="number" min="0" value={alta.stock_minimo} onChange={(e) => setAlta({ ...alta, stock_minimo: e.target.value })} />
            </>
          )}
          <button type="submit" className="boton-primario">Crear producto</button>
        </form>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      <section className="tarjeta">
        <h2>Catálogo {lista ? `(${lista.length})` : ''}</h2>
        {!lista && <p className="estado" role="status" aria-busy="true">Cargando…</p>}
        {lista && lista.length === 0 && <p className="estado estado-vacio">Aún no hay productos. Crea el primero arriba.</p>}
        <ul className="lista-aseo">
          {(lista || []).map((p) => (
            <li key={p.producto_id} className="tarjeta" data-producto={p.producto_id}>
              <div className="aseo-cabecera">
                <strong>{p.nombre}</strong>
                <span>{NOMBRE_CATEGORIA[p.categoria] || p.categoria}</span>
                <span>{clp(p.precio_clp)}</span>
                {p.codigo && <span className="nota-clave">Cód. {p.codigo}</span>}
                {p.costo_clp !== null && p.costo_clp !== undefined && <span className="nota-clave">Costo neto {clp(p.costo_clp)}</span>}
                {p.controla_stock && (
                  <span className={`reserva-estado ${p.stock > 0 ? 'estado-finalizada' : 'estado-cancelada'}`}>stock {p.stock}</span>
                )}
                {!p.activo && <span className="reserva-estado estado-cancelada">inactivo</span>}
              </div>
              <div className="acciones-aseo">
                <input className="entrada" type="number" min="1" aria-label={`Nuevo precio de ${p.nombre}`} placeholder="Nuevo precio"
                  value={precios[p.producto_id] || ''} onChange={(e) => setPrecios((x) => ({ ...x, [p.producto_id]: e.target.value }))} />
                <button type="button" className="boton-secundario" onClick={() => cambiarPrecio(p)}>Cambiar precio</button>
                <button type="button" className="boton-fantasma"
                  onClick={() => enviar(`/hotel/productos/${p.producto_id}`, 'PUT', { activo: !p.activo }, p.activo ? `«${p.nombre}» desactivado.` : `«${p.nombre}» activado.`)}>
                  {p.activo ? 'Desactivar' : 'Activar'}
                </button>
              </div>
              {p.controla_stock && (
                <div className="acciones-aseo">
                  <input className="entrada" type="number" aria-label={`Ajuste de stock de ${p.nombre}`} placeholder="+ reposición / − merma"
                    value={ajustes[p.producto_id]?.delta || ''} onChange={(e) => setAjustes((x) => ({ ...x, [p.producto_id]: { ...x[p.producto_id], delta: e.target.value } }))} />
                  <input className="entrada" aria-label={`Motivo del ajuste de ${p.nombre}`} placeholder="Motivo"
                    value={ajustes[p.producto_id]?.motivo || ''} onChange={(e) => setAjustes((x) => ({ ...x, [p.producto_id]: { ...x[p.producto_id], motivo: e.target.value } }))} />
                  <button type="button" className="boton-secundario" onClick={() => ajustar(p)}>Ajustar stock</button>
                </div>
              )}
            </li>
          ))}
        </ul>
        <p className="nota-chica">
          ¿Llegó mercadería? Usa «Cargar desde factura», «Pegar planilla» o «Lector de códigos» para sumar todo el stock de una vez.
        </p>
      </section>
      </div>
      )}
    </MarcoHotel>
  )
}
