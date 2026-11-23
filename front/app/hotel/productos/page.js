'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, Campo, CampoSelect, useSesion } from '../../../lib/api'
import { esAdminHotel } from '../../../lib/roles'
import { CATEGORIAS_PRODUCTO } from '../_componentes/selector-producto'
import { ImportarProductos } from '../_componentes/importar-productos'
import { ReposicionStock } from '../_componentes/reposicion-stock'
import { BarraContextual, SelectorFila } from '../_componentes/barra-contextual'
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
 * Productos y stock (#357): mantenedor del catálogo con selección de producto
 * activo + barra contextual única (sin repetir inputs/botones por cada producto).
 */
export default function Productos() {
  const sesion = useSesion()
  const esAdmin = sesion.fase === 'ok' && esAdminHotel(sesion.usuario.rol)
  const [lista, setLista] = useState(null)
  const [pestana, setPestana] = useState('catalogo')
  const [alta, setAlta] = useState({ nombre: '', categoria: 'minibar', precio_clp: '', controla_stock: false, stock: '0', stock_minimo: '0', codigo: '' })
  const [seleccionadoId, setSeleccionadoId] = useState(null)
  const [panelAccion, setPanelAccion] = useState(null) // 'precio' | 'stock' | null
  const [nuevoPrecio, setNuevoPrecio] = useState('')
  const [ajusteStock, setAjusteStock] = useState({ delta: '', motivo: '' })
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  const activo = (lista || []).find((p) => p.producto_id === seleccionadoId) || null

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

  function elegirProducto(p) {
    setSeleccionadoId(p.producto_id)
    setPanelAccion(null)
    setNuevoPrecio(String(p.precio_clp || ''))
    setAjusteStock({ delta: '', motivo: '' })
    setError('')
  }

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

  async function guardarPrecio(e, p) {
    e.preventDefault()
    const precio = Number(nuevoPrecio)
    if (!(precio > 0)) { setError('El precio debe ser mayor que 0.'); return }
    const ok = await enviar(
      `/hotel/productos/${p.producto_id}`,
      'PUT',
      { precio_clp: precio },
      `Precio de «${p.nombre}» actualizado (los cargos ya asentados no cambian).`,
    )
    if (ok) setPanelAccion(null)
  }

  async function guardarAjusteStock(e, p) {
    e.preventDefault()
    const delta = Number(ajusteStock.delta)
    if (!Number.isInteger(delta) || delta === 0) {
      setError('El ajuste debe ser un entero distinto de 0 (negativo para merma).')
      return
    }
    if (!ajusteStock.motivo || ajusteStock.motivo.trim().length < 3) {
      setError('Indica el motivo del ajuste (mínimo 3 caracteres).')
      return
    }
    const ok = await enviar(
      `/hotel/productos/${p.producto_id}/stock`,
      'POST',
      { delta, motivo: ajusteStock.motivo.trim() },
      `Stock de «${p.nombre}» ajustado.`,
    )
    if (ok) {
      setPanelAccion(null)
      setAjusteStock({ delta: '', motivo: '' })
    }
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
          <button
            key={id}
            type="button"
            role="tab"
            id={`pestana-${id}`}
            aria-controls={`panel-${id}`}
            aria-selected={pestana === id}
            className={css.pestana}
            onClick={() => setPestana(id)}
          >
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
              <Campo
                etiqueta="Código (opcional)"
                value={alta.codigo}
                placeholder="Escanea o escribe"
                autoComplete="off"
                onChange={(e) => setAlta({ ...alta, codigo: e.target.value.replace(/\s+/g, '') })}
              />
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

            {lista && lista.length > 0 && (
              <>
                <BarraContextual
                  titulo="Acciones de producto"
                  seleccionado={Boolean(activo)}
                  resumen={activo ? `${activo.nombre} · ${clp(activo.precio_clp)}` : ''}
                  detalle={activo ? `${NOMBRE_CATEGORIA[activo.categoria] || activo.categoria}${activo.controla_stock ? ` · Stock ${activo.stock}` : ''} · ${activo.activo ? 'Activo' : 'Inactivo'}` : ''}
                  placeholder="Selecciona un producto de la tabla para cambiar su precio, ajustar stock o activar/desactivar."
                  alLimpiar={() => { setSeleccionadoId(null); setPanelAccion(null) }}
                >
                  {activo && (
                    <>
                      <button
                        type="button"
                        className="boton-primario"
                        aria-expanded={panelAccion === 'precio'}
                        onClick={() => {
                          setNuevoPrecio(String(activo.precio_clp || ''))
                          setPanelAccion(panelAccion === 'precio' ? null : 'precio')
                        }}
                      >
                        Cambiar precio
                      </button>
                      {activo.controla_stock && (
                        <button
                          type="button"
                          className="boton-secundario"
                          aria-expanded={panelAccion === 'stock'}
                          onClick={() => setPanelAccion(panelAccion === 'stock' ? null : 'stock')}
                        >
                          Ajustar stock
                        </button>
                      )}
                      <button
                        type="button"
                        className="boton-fantasma"
                        onClick={() => enviar(
                          `/hotel/productos/${activo.producto_id}`,
                          'PUT',
                          { activo: !activo.activo },
                          activo.activo ? `«${activo.nombre}» desactivado.` : `«${activo.nombre}» activado.`,
                        )}
                      >
                        {activo.activo ? 'Desactivar' : 'Activar'}
                      </button>
                    </>
                  )}
                </BarraContextual>

                {activo && panelAccion === 'precio' && (
                  <form className="formulario" style={{ marginBottom: '0.75rem' }} onSubmit={(e) => guardarPrecio(e, activo)}>
                    <Campo
                      etiqueta={`Nuevo precio con IVA para ${activo.nombre} (CLP)`}
                      type="number"
                      min="1"
                      value={nuevoPrecio}
                      onChange={(e) => setNuevoPrecio(e.target.value)}
                    />
                    <button type="submit" className="boton-primario">Guardar precio</button>
                    <button type="button" className="boton-fantasma" onClick={() => setPanelAccion(null)}>Cancelar</button>
                  </form>
                )}

                {activo && panelAccion === 'stock' && activo.controla_stock && (
                  <form className="formulario" style={{ marginBottom: '0.75rem' }} onSubmit={(e) => guardarAjusteStock(e, activo)}>
                    <Campo
                      etiqueta="Ajuste (+ reposición / − merma)"
                      type="number"
                      placeholder="Ej.: 10 o -2"
                      value={ajusteStock.delta}
                      onChange={(e) => setAjusteStock({ ...ajusteStock, delta: e.target.value })}
                    />
                    <Campo
                      etiqueta="Motivo del ajuste"
                      placeholder="Reposición semanal o merma"
                      value={ajusteStock.motivo}
                      onChange={(e) => setAjusteStock({ ...ajusteStock, motivo: e.target.value })}
                    />
                    <button type="submit" className="boton-primario">Aplicar ajuste</button>
                    <button type="button" className="boton-fantasma" onClick={() => setPanelAccion(null)}>Cancelar</button>
                  </form>
                )}

                <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Catálogo de productos (desliza para ver todas las columnas)">
                  <table className="tabla">
                    <thead>
                      <tr>
                        <th className="celda-selector"><span className="sr-only">Elegir</span></th>
                        <th>Producto</th>
                        <th>Categoría</th>
                        <th>Código</th>
                        <th>Precio (IVA incl.)</th>
                        <th>Costo neto</th>
                        <th>Stock</th>
                        <th>Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {lista.map((p) => {
                        const elegida = activo?.producto_id === p.producto_id
                        return (
                          <tr
                            key={p.producto_id}
                            data-producto={p.producto_id}
                            className="fila-seleccionable"
                            data-seleccionada={elegida ? 'true' : 'false'}
                            onClick={() => elegirProducto(p)}
                          >
                            <td className="celda-selector">
                              <SelectorFila
                                nombreGrupo="producto-activo"
                                elegido={elegida}
                                etiqueta={`Seleccionar producto ${p.nombre}`}
                                alElegir={() => elegirProducto(p)}
                              />
                            </td>
                            <td><strong>{p.nombre}</strong></td>
                            <td>{NOMBRE_CATEGORIA[p.categoria] || p.categoria}</td>
                            <td>{p.codigo || '—'}</td>
                            <td><strong>{clp(p.precio_clp)}</strong></td>
                            <td>{p.costo_clp !== null && p.costo_clp !== undefined ? clp(p.costo_clp) : '—'}</td>
                            <td>
                              {p.controla_stock ? (
                                <span className={`reserva-estado ${p.stock > 0 ? 'estado-finalizada' : 'estado-cancelada'}`}>
                                  Stock {p.stock}
                                </span>
                              ) : 'No aplica'}
                            </td>
                            <td>
                              <span className={`reserva-estado ${p.activo ? 'estado-finalizada' : 'estado-cancelada'}`}>
                                {p.activo ? 'Activo' : 'Inactivo'}
                              </span>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            <p className="nota-chica">
              ¿Llegó mercadería? Usa «Cargar desde factura», «Pegar planilla» o «Lector de códigos» para sumar todo el stock de una vez.
            </p>
          </section>
        </div>
      )}
    </MarcoHotel>
  )
}
