'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, clp, mensajeDeError, Campo, CampoSelect } from '../../../lib/api'
import { CATEGORIAS_PRODUCTO } from './selector-producto'

const NOMBRE_CATEGORIA = Object.fromEntries(CATEGORIAS_PRODUCTO)
const NOMBRE_BODEGA = {
  bodega_principal: 'Bodega principal',
  minibar: 'Minibar habitaciones',
  cafeteria: 'Cafetería',
}

const ETIQUETA_NIVEL = {
  sin_stock: { texto: 'Sin stock', clase: 'estado-cancelada' },
  bajo_minimo: { texto: 'Bajo mínimo', clase: 'estado-confirmada' },
  ok: { texto: 'En nivel', clase: 'estado-finalizada' },
}

function claveOp() {
  return `stk-${crypto.randomUUID().slice(0, 12)}`
}

/**
 * Reporte transversal de stock por bodega y sugerencias de reposición (#358).
 * Consume /core/stock/reposicion y /core/stock/transferencias (compartido hotel + cafetería).
 */
export function ReposicionStock({ alCambiar }) {
  const [bodega, setBodega] = useState('')
  const [categoria, setCategoria] = useState('')
  const [soloAlertas, setSoloAlertas] = useState(false)
  const [reporte, setReporte] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [transf, setTransf] = useState({ producto_id: '', origen: 'bodega_principal', destino: 'minibar', cantidad: '1', motivo: 'Reposición interna' })
  const [enviando, setEnviando] = useState(false)

  const cargar = useCallback(async () => {
    setError('')
    const params = new URLSearchParams()
    if (bodega) params.set('bodega', bodega)
    if (categoria) params.set('categoria', categoria)
    if (soloAlertas) params.set('solo_alertas', 'true')
    try {
      const r = await api(`/core/stock/reposicion?${params}`)
      if (r.estado === 200) setReporte(r.datos)
      else setError(mensajeDeError(r.datos, r.estado))
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }, [bodega, categoria, soloAlertas])

  useEffect(() => {
    cargar()
  }, [cargar])

  async function transferir(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const cantidad = Number(transf.cantidad)
    if (!transf.producto_id) { setError('Selecciona un producto para transferir.'); return }
    if (transf.origen === transf.destino) { setError('La bodega de origen y destino deben ser distintas.'); return }
    if (!Number.isInteger(cantidad) || cantidad <= 0) { setError('La cantidad debe ser un entero mayor que 0.'); return }
    setEnviando(true)
    try {
      const r = await api('/core/stock/transferencias', {
        metodo: 'POST',
        claveIdempotencia: claveOp(),
        cuerpo: {
          producto_id: transf.producto_id,
          origen: transf.origen,
          destino: transf.destino,
          cantidad,
          motivo: transf.motivo.trim() || 'Reposición interna',
        },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
      } else {
        setAviso(`Transferencia registrada: ${cantidad} u. desde ${NOMBRE_BODEGA[transf.origen]} hacia ${NOMBRE_BODEGA[transf.destino]}.`)
        await cargar()
        if (alCambiar) alCambiar()
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setEnviando(false)
    }
  }

  const resumen = reporte?.resumen
  const bodegas = reporte?.bodegas || []
  const items = reporte?.items || []

  return (
    <div data-reposicion-stock>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      {resumen && (
        <section className="tarjeta">
          <h2>Resumen de inventario (core compartido)</h2>
          <div className="kpi-rejilla">
            <div className="kpi">
              <span className="kpi-titulo">Productos controlados</span>
              <span className="kpi-valor">{resumen.productos_controlados}</span>
            </div>
            <div className={`kpi${resumen.sin_stock > 0 ? ' kpi-alerta' : ''}`}>
              <span className="kpi-titulo">Sin stock</span>
              <span className="kpi-valor">{resumen.sin_stock}</span>
            </div>
            <div className={`kpi${resumen.bajo_minimo > 0 ? ' kpi-alerta' : ''}`}>
              <span className="kpi-titulo">Bajo mínimo</span>
              <span className="kpi-valor">{resumen.bajo_minimo}</span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">Unidades totales</span>
              <span className="kpi-valor">{resumen.unidades_totales}</span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">Valorización (costo neto)</span>
              <span className="kpi-valor">{clp(resumen.valorizacion_costo_clp)}</span>
            </div>
          </div>
        </section>
      )}

      <section className="tarjeta">
        <h2>Reporte de stock y reposición</h2>
        <div className="formulario">
          <CampoSelect etiqueta="Bodega / ubicación" value={bodega} onChange={(e) => setBodega(e.target.value)}>
            <option value="">Todas las bodegas</option>
            {bodegas.map((b) => (
              <option key={b.codigo} value={b.codigo}>{b.nombre}</option>
            ))}
          </CampoSelect>
          <CampoSelect etiqueta="Categoría" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
            <option value="">Todas</option>
            {CATEGORIAS_PRODUCTO.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
          </CampoSelect>
          <label className="campo-check">
            <input type="checkbox" checked={soloAlertas} onChange={(e) => setSoloAlertas(e.target.checked)} />
            Mostrar solo alertas de reposición
          </label>
        </div>

        {!reporte ? (
          <p className="estado" role="status" aria-busy="true">Cargando reporte…</p>
        ) : items.length === 0 ? (
          <p className="estado estado-vacio">
            {soloAlertas ? 'Sin alertas de reposición para el filtro seleccionado.' : 'No hay productos con control de stock.'}
          </p>
        ) : (
          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla de reposición de stock">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Producto</th>
                  <th>Categoría</th>
                  <th>Stock</th>
                  <th>Mínimo</th>
                  <th>Por bodega</th>
                  <th>Estado</th>
                  <th>Sugerido reponer</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => {
                  const badge = ETIQUETA_NIVEL[it.nivel] || { texto: it.nivel, clase: '' }
                  const detalleBodegas = Object.entries(it.por_bodega || {})
                    .map(([cod, cant]) => `${NOMBRE_BODEGA[cod] || cod}: ${cant}`)
                    .join(' · ')
                  return (
                    <tr key={it.producto_id}>
                      <td><strong>{it.nombre}</strong></td>
                      <td>{NOMBRE_CATEGORIA[it.categoria] || it.categoria}</td>
                      <td>{it.stock_actual}</td>
                      <td>{it.stock_minimo}</td>
                      <td>{detalleBodegas || '—'}</td>
                      <td><span className={`reserva-estado ${badge.clase}`}>{badge.texto}</span></td>
                      <td>{it.sugerido_reponer > 0 ? <strong>+{it.sugerido_reponer}</strong> : '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {items.length > 0 && (
        <section className="tarjeta">
          <h2>Transferir entre bodegas</h2>
          <p className="nota-chica">
            Mueve unidades entre Bodega principal, Minibar habitaciones y Cafetería sin alterar el inventario total.
          </p>
          <form className="formulario" onSubmit={transferir}>
            <CampoSelect etiqueta="Producto" value={transf.producto_id} onChange={(e) => setTransf({ ...transf, producto_id: e.target.value })}>
              <option value="">(Selecciona un producto)</option>
              {items.map((it) => (
                <option key={it.producto_id} value={it.producto_id}>
                  {it.nombre} (total: {it.stock_actual})
                </option>
              ))}
            </CampoSelect>
            <CampoSelect etiqueta="Desde bodega" value={transf.origen} onChange={(e) => setTransf({ ...transf, origen: e.target.value })}>
              {bodegas.map((b) => <option key={b.codigo} value={b.codigo}>{b.nombre}</option>)}
            </CampoSelect>
            <CampoSelect etiqueta="Hacia bodega" value={transf.destino} onChange={(e) => setTransf({ ...transf, destino: e.target.value })}>
              {bodegas.map((b) => <option key={b.codigo} value={b.codigo}>{b.nombre}</option>)}
            </CampoSelect>
            <Campo etiqueta="Cantidad" type="number" min="1" value={transf.cantidad} onChange={(e) => setTransf({ ...transf, cantidad: e.target.value })} />
            <Campo etiqueta="Motivo" value={transf.motivo} onChange={(e) => setTransf({ ...transf, motivo: e.target.value })} />
            <button type="submit" className="boton-primario" disabled={enviando}>
              {enviando ? 'Transfiriendo…' : 'Registrar transferencia'}
            </button>
          </form>
        </section>
      )}
    </div>
  )
}
