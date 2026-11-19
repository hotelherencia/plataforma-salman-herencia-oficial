'use client'

import { useEffect, useRef, useState } from 'react'
import { api, mensajeDeError, useClaveOperacion, alRechazar } from '../../../lib/api'
import { fechaCorta, pesos } from '../../../lib/estadias'
import { fechaATexto, plural } from '../../../lib/formato'
import {
  CAMPOS_PLANILLA, adivinarMapeo, etiquetaConfianza, filaRevision, lineaParaConfirmar,
  lineasDesdePlanilla, parsearPlanilla, pareceEncabezado, resumenImportacion, resumenRevision, validarRevision,
} from '../../../lib/importacion'
import {
  costoPorUnidad, extrasDocumento, lineaConfirmacionDocumento, textoOrigenUnidades, unidadesTotales, validarEnvases,
} from '../../../lib/facturas'
import { CATEGORIAS_PRODUCTO } from './selector-producto'
import { FacturasProveedor } from './facturas-proveedor'
import css from './operacion.module.css'

const TONO = { exito: css.chipExito, aviso: css.chipAviso, info: css.chipInfo, neutro: '', error: css.chipError }
const SIN_CONEXION = 'No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.'

/** Revisión común a todas las fuentes: cada línea se suma a un producto, se crea o se omite.
 *  Con `documentoId` (bandeja de facturas) agrega las unidades por envase y confirma el documento. */
export function Revision({ previa, xml, catalogo, alTerminar, alCancelar, documentoId, pedidoSugerido, textoCancelar }) {
  const conEnvases = Boolean(documentoId)
  const [filas, setFilas] = useState(() => previa.lineas.map((l) => (conEnvases ? { ...filaRevision(l), ...extrasDocumento(l) } : filaRevision(l))))
  const [cerrarPedido, setCerrarPedido] = useState(Boolean(pedidoSugerido))
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [clave, renovarClave] = useClaveOperacion()
  const resumen = resumenRevision(filas)
  const doc = previa.documento
  const porId = Object.fromEntries(catalogo.map((p) => [p.producto_id, p]))

  const cambiar = (i, cambios) => {
    setFilas((fs) => fs.map((f, j) => (j === i ? { ...f, ...cambios } : f)))
    setError('') // el aviso se recalcula al volver a «Cargar al inventario»
  }

  async function confirmar() {
    const falta = validarRevision(filas) || (conEnvases ? validarEnvases(filas) : null)
    if (falta) { setError(falta); return }
    setError('')
    setEnviando(true)
    try {
      let ruta = '/hotel/productos/importacion'
      let cuerpo
      if (conEnvases) {
        ruta = `/hotel/productos/documentos/${encodeURIComponent(documentoId)}/confirmacion`
        cuerpo = { lineas: filas.map((f) => lineaConfirmacionDocumento(f, lineaParaConfirmar(f))) }
        if (pedidoSugerido && cerrarPedido) cuerpo.pedido_id = pedidoSugerido.documento_id
      } else {
        cuerpo = { origen: previa.origen, lineas: filas.map(lineaParaConfirmar) }
        if (previa.origen === 'factura_xml') cuerpo.xml = xml
      }
      const r = await api(ruta, { metodo: 'POST', cuerpo, claveIdempotencia: clave })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovarClave)
      } else {
        renovarClave()
        alTerminar(r.datos)
      }
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="tarjeta" aria-label="Revisar la carga">
      <div className="tarjeta-cabecera">
        <h2>Revisa antes de cargar</h2>
        <button type="button" className="boton-fantasma" onClick={alCancelar}>{textoCancelar || 'Empezar de nuevo'}</button>
      </div>
      {doc && (
        <dl className={css.documento} data-documento-factura>
          <div><dt>Proveedor</dt><dd>{doc.emisor_razon_social || '—'}</dd></div>
          <div><dt>RUT</dt><dd>{doc.emisor_rut}</dd></div>
          <div><dt>{doc.tipo_nombre || 'Documento'}</dt><dd>{doc.folio ? `N° ${doc.folio}` : '—'}</dd></div>
          <div><dt>Fecha</dt><dd>{fechaATexto(doc.fecha_emision) || '—'}</dd></div>
          {doc.monto_total_clp !== null && doc.monto_total_clp !== undefined && <div><dt>Total factura</dt><dd>{pesos(doc.monto_total_clp)}</dd></div>}
        </dl>
      )}
      {previa.ya_importada && (
        <p className="alerta" role="alert" data-ya-importada>
          Esta factura ya se cargó el {fechaCorta(previa.ya_importada.registrada_en)} ({plural(previa.ya_importada.unidades, 'unidad', 'unidades')}, por {previa.ya_importada.actor}).
          No se puede cargar dos veces.
        </p>
      )}
      <p className={css.ayuda}>
        Cada línea se <strong>suma</strong> a un producto que ya tienes, se <strong>crea</strong> como producto nuevo o <strong>no se carga</strong>.
        El costo es neto (sin IVA); el precio de venta lleva IVA y es el que se cobra al huésped.
      </p>
      <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Líneas por cargar (desliza para ver todas las columnas)">
        <table className={`tabla ${css.tablaRevision}`}>
          <thead>
            <tr>
              <th>Línea leída</th>
              <th>Qué hacer</th>
              <th>Producto</th>
              <th>Cantidad</th>
              {conEnvases && <th>Unidades por envase</th>}
              <th>{conEnvases ? 'Costo neto por envase' : 'Costo neto'}</th>
              <th>Precio venta (con IVA)</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f, i) => {
              const conf = etiquetaConfianza(f)
              const actual = f.producto_id ? porId[f.producto_id] : null
              return (
                <tr key={`${f.linea}-${i}`} className={f.accion === 'omitir' ? css.filaOmitida : ''} data-linea={f.linea}>
                  <td className={css.celdaNombre}>
                    <strong>{f.nombre_factura}</strong>
                    <div className={css.chips}>
                      <span className={`${css.chip} ${TONO[conf.tono] || ''}`}>{conf.texto}</span>
                      {f.codigo && <span className={css.chip}>Cód. {f.codigo}</span>}
                    </div>
                  </td>
                  <td>
                    <select className="entrada" aria-label={`Qué hacer con ${f.nombre_factura}`} value={f.accion}
                      onChange={(e) => cambiar(i, { accion: e.target.value })}>
                      <option value="sumar">Sumar a un producto</option>
                      <option value="crear">Crear producto nuevo</option>
                      <option value="omitir">No cargar</option>
                    </select>
                  </td>
                  <td className={css.celdaNombre}>
                    {f.accion === 'sumar' && (
                      <>
                        <select className="entrada" aria-label={`Producto para ${f.nombre_factura}`} value={f.producto_id}
                          aria-invalid={!f.producto_id} onChange={(e) => cambiar(i, { producto_id: e.target.value })}>
                          <option value="">Elige el producto…</option>
                          {catalogo.map((p) => <option key={p.producto_id} value={p.producto_id}>{p.nombre}</option>)}
                        </select>
                        {actual && (
                          <span className={css.ayuda}>
                            {actual.controla_stock ? `Stock actual ${actual.stock} → ${actual.stock + (conEnvases ? unidadesTotales(f) : (Number(f.cantidad) || 0))}` : 'No controla stock: solo se actualiza el costo'}
                          </span>
                        )}
                      </>
                    )}
                    {f.accion === 'crear' && (
                      <>
                        <input className="entrada" aria-label={`Nombre del producto nuevo (${f.nombre_factura})`} value={f.nombre}
                          onChange={(e) => cambiar(i, { nombre: e.target.value })} />
                        <select className="entrada" aria-label={`Categoría de ${f.nombre_factura}`} value={f.categoria}
                          onChange={(e) => cambiar(i, { categoria: e.target.value })}>
                          {CATEGORIAS_PRODUCTO.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
                        </select>
                      </>
                    )}
                  </td>
                  <td className={css.celdaNumero}>
                    <input className="entrada" type="number" min="0" step="1" inputMode="numeric" aria-label={`Cantidad de ${f.nombre_factura}`}
                      value={f.cantidad} onChange={(e) => cambiar(i, { cantidad: e.target.value })} disabled={f.accion === 'omitir'} />
                    {f.unidad && <span className={css.ayuda}>{f.unidad}</span>}
                    {f.redondeada && <span className={css.ayuda}>Venía {String(f.cantidad_original).replace('.', ',')}: revisa</span>}
                    {conEnvases && f.nota && <span className={`${css.ayuda} ${css.ayudaBloque}`} data-nota-manuscrita>Nota a mano: «{f.nota}»</span>}
                  </td>
                  {conEnvases && (
                    <td className={css.celdaNumero}>
                      <input className="entrada" type="number" min="1" step="1" inputMode="numeric"
                        aria-label={`Unidades por envase de ${f.nombre_factura}`} value={f.unidades_por_paquete}
                        onChange={(e) => cambiar(i, { unidades_por_paquete: e.target.value, origen_unidades: null })} disabled={f.accion === 'omitir'} />
                      <span className={`${css.ayuda} ${css.ayudaBloque}`} data-unidades-stock>{plural(unidadesTotales(f), 'unidad', 'unidades')} al stock</span>
                      {f.origen_unidades && <span className={`${css.ayuda} ${css.ayudaBloque}`}>{textoOrigenUnidades(f.origen_unidades)}</span>}
                    </td>
                  )}
                  <td className={css.celdaNumero}>
                    <input className="entrada" type="number" min="0" inputMode="numeric" aria-label={`Costo neto de ${f.nombre_factura}`}
                      value={f.costo} onChange={(e) => cambiar(i, { costo: e.target.value })} disabled={f.accion === 'omitir'} />
                  </td>
                  <td className={css.celdaNumero}>
                    <input className="entrada" type="number" min="1" inputMode="numeric" aria-label={`Precio de venta de ${f.nombre_factura}`}
                      placeholder={f.accion === 'sumar' && actual ? `${pesos(actual.precio_clp)} (igual)` : 'Obligatorio'}
                      aria-invalid={f.accion === 'crear' && !(Number(f.precio) > 0)}
                      value={f.precio} onChange={(e) => cambiar(i, { precio: e.target.value })} disabled={f.accion === 'omitir'} />
                    {f.accion === 'crear' && Number(f.costo) > 0 && (
                      <span className={css.ayuda}>Costo con IVA {pesos((conEnvases ? costoPorUnidad(f) : Number(f.costo)) * 1.19)}{conEnvases && Number(f.unidades_por_paquete) > 1 ? ' por unidad' : ''}</span>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <div className={css.resumenCarga} role="status" aria-live="polite">
        <span className={`${css.chip} ${css.chipExito}`}>{resumen.sumar} a sumar</span>
        <span className={`${css.chip} ${css.chipInfo}`}>{resumen.crear} nuevos</span>
        {resumen.omitir > 0 && <span className={css.chip}>{resumen.omitir} sin cargar</span>}
        <span className={css.chip}>{plural(conEnvases ? filas.filter((f) => f.accion !== 'omitir').reduce((s, f) => s + unidadesTotales(f), 0) : resumen.unidades, 'unidad', 'unidades')} al stock</span>
      </div>
      {conEnvases && (
        <p className={css.ayuda}>Al cargar se recuerda, para este proveedor, a qué producto corresponde cada ítem y cuántas unidades trae su envase.</p>
      )}
      {pedidoSugerido && (
        <label className="campo-casilla">
          <input type="checkbox" checked={cerrarPedido} onChange={(e) => setCerrarPedido(e.target.checked)} />
          {' '}Esta factura cierra el pedido {pedidoSugerido.folio ? `N° ${pedidoSugerido.folio}` : 'en borrador'} del mismo proveedor
        </label>
      )}
      {error && <p className="alerta" role="alert">{error}</p>}
      <button type="button" className="boton-primario" onClick={confirmar} disabled={enviando || Boolean(previa.ya_importada)}>
        {enviando ? 'Cargando…' : 'Cargar al inventario'}
      </button>
    </section>
  )
}

function useCatalogo(version) {
  const [catalogo, setCatalogo] = useState([])
  useEffect(() => {
    api('/hotel/productos?inactivos=true').then((r) => r.estado === 200 && setCatalogo(r.datos.productos)).catch(() => {})
  }, [version])
  return catalogo
}

async function pedirVistaPrevia(cuerpo) {
  const r = await api('/hotel/productos/importacion/vista-previa', { metodo: 'POST', cuerpo })
  if (r.estado >= 400) return { error: mensajeDeError(r.datos, r.estado) }
  return { previa: r.datos }
}

/** Fuente 2: filas pegadas desde Excel o CSV, con mapeo de columnas. */
function FuentePlanilla({ alLeer }) {
  const [texto, setTexto] = useState('')
  const [mapeo, setMapeo] = useState([])
  const [conEncabezado, setConEncabezado] = useState(false)
  const [error, setError] = useState('')
  const [leyendo, setLeyendo] = useState(false)
  const { filas } = parsearPlanilla(texto)
  const columnas = filas.reduce((m, f) => Math.max(m, f.length), 0)

  function alPegar(valor) {
    setTexto(valor)
    const p = parsearPlanilla(valor)
    setMapeo(adivinarMapeo(p.filas))
    setConEncabezado(pareceEncabezado(p.filas[0]))
    setError('')
  }

  async function revisar() {
    const { lineas, errores } = lineasDesdePlanilla(filas, mapeo, conEncabezado)
    if (errores.length) { setError(errores.slice(0, 3).join(' ')); return }
    if (!lineas.length) { setError('No hay filas con nombre de producto para cargar.'); return }
    setLeyendo(true)
    try {
      const { previa, error: e } = await pedirVistaPrevia({ origen: 'planilla', lineas })
      if (e) setError(e)
      else alLeer(previa)
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setLeyendo(false)
    }
  }

  return (
    <section className="tarjeta">
      <h2>Pegar desde Excel o una planilla</h2>
      <p className={css.ayuda}>
        Copia las filas en Excel o Google Sheets (nombre, cantidad, costo y, si tienes, código) y pégalas aquí.
      </p>
      <label className="campo">
        <span className="campo-etiqueta">Filas copiadas</span>
        <textarea className={`entrada ${css.textoPlanilla}`} value={texto} onChange={(e) => alPegar(e.target.value)}
          placeholder={'Agua mineral 500 ml\t24\t650\nBebida cola lata\t12\t833'} />
      </label>
      {columnas > 0 && (
        <>
          <p className={css.rotuloLista}>{filas.length - (conEncabezado ? 1 : 0)} filas · indica qué trae cada columna</p>
          <div className={css.mapeo}>
            {Array.from({ length: columnas }, (_, i) => (
              <label key={i} className="campo">
                <span className="campo-etiqueta">Columna {i + 1}: «{(filas[0][i] || '').slice(0, 24)}»</span>
                <select className="entrada" value={mapeo[i] || 'ignorar'}
                  onChange={(e) => setMapeo((m) => { const n = [...m]; n[i] = e.target.value; return n })}>
                  {CAMPOS_PLANILLA.map(([id, n]) => <option key={id} value={id}>{n}</option>)}
                </select>
              </label>
            ))}
          </div>
          <label className="campo-check">
            <input type="checkbox" checked={conEncabezado} onChange={(e) => setConEncabezado(e.target.checked)} />
            La primera fila son títulos (no es un producto)
          </label>
        </>
      )}
      {error && <p className="alerta" role="alert">{error}</p>}
      <button type="button" className="boton-primario" onClick={revisar} disabled={!columnas || leyendo}>
        {leyendo ? 'Revisando…' : 'Revisar coincidencias'}
      </button>
    </section>
  )
}

/** Fuente 3: lector de códigos USB (escribe el código y un Enter). */
function FuenteLector({ alLeer }) {
  const [codigo, setCodigo] = useState('')
  const [lote, setLote] = useState([])
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [leyendo, setLeyendo] = useState(false)
  const campo = useRef(null)

  async function leerCodigo(e) {
    e.preventDefault()
    const c = codigo.trim().replace(/\s+/g, '')
    setCodigo('')
    setError('')
    if (!c) return
    if (!/^[A-Za-z0-9._/-]{1,60}$/.test(c)) { setError('Ese código tiene caracteres no válidos.'); return }
    const existente = lote.find((x) => x.codigo.toLowerCase() === c.toLowerCase())
    if (existente) {
      setLote((l) => l.map((x) => (x === existente ? { ...x, cantidad: x.cantidad + 1 } : x)))
      setAviso(`${existente.nombre || c}: ${existente.cantidad + 1} unidades`)
      return
    }
    let nombre = ''
    try {
      const r = await api(`/hotel/productos?inactivos=true&codigo=${encodeURIComponent(c)}`)
      if (r.estado === 200 && r.datos.productos.length) nombre = r.datos.productos[0].nombre
    } catch { /* sin nombre: se completa a mano */ }
    setLote((l) => [...l, { codigo: c, nombre, conocido: Boolean(nombre), cantidad: 1 }])
    setAviso(nombre ? `${nombre}: 1 unidad` : `Código nuevo ${c}: escribe el nombre del producto`)
    campo.current?.focus()
  }

  async function revisar() {
    if (!lote.length) { setError('Escanea al menos un producto.'); return }
    setLeyendo(true)
    try {
      const lineas = lote.map((x) => ({ codigo: x.codigo, nombre: x.nombre || x.codigo, cantidad: x.cantidad }))
      const { previa, error: e } = await pedirVistaPrevia({ origen: 'lector', lineas })
      if (e) setError(e)
      else alLeer(previa)
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setLeyendo(false)
    }
  }

  return (
    <section className="tarjeta">
      <h2>Ingresar con lector de códigos</h2>
      <p className={css.ayuda}>
        Con el cursor en el campo, pasa cada producto por el lector: cada lectura suma una unidad. También puedes escribir el código y presionar Enter.
      </p>
      <form className={css.busquedaFila} onSubmit={leerCodigo}>
        <label className="campo">
          <span className="campo-etiqueta">Código de barras o del proveedor</span>
          <input ref={campo} className="entrada" value={codigo} autoFocus autoComplete="off"
            onChange={(e) => setCodigo(e.target.value)} placeholder="Escanea aquí" />
        </label>
        <button type="submit" className="boton-secundario">Agregar</button>
      </form>
      <p className={css.rotuloLista} role="status" aria-live="polite">{aviso}</p>
      {error && <p className="alerta" role="alert">{error}</p>}
      {lote.length > 0 && (
        <ul className={css.lote} aria-label="Productos escaneados">
          {lote.map((x, i) => (
            <li key={x.codigo} className={css.loteItem} data-codigo={x.codigo}>
              <div>
                {x.conocido ? <strong>{x.nombre}</strong> : (
                  <input className="entrada" aria-label={`Nombre del producto con código ${x.codigo}`} placeholder="Nombre del producto nuevo"
                    value={x.nombre} onChange={(e) => setLote((l) => l.map((y, j) => (j === i ? { ...y, nombre: e.target.value } : y)))} />
                )}
                <div className={css.ayuda}>Código {x.codigo}{x.conocido ? '' : ' · nuevo'}</div>
              </div>
              <div className={css.loteControles}>
                <input className="entrada" type="number" min="1" aria-label={`Cantidad de ${x.nombre || x.codigo}`} value={x.cantidad}
                  onChange={(e) => setLote((l) => l.map((y, j) => (j === i ? { ...y, cantidad: Math.max(1, Number(e.target.value) || 1) } : y)))} />
                <button type="button" className="boton-fantasma" aria-label={`Quitar ${x.nombre || x.codigo}`}
                  onClick={() => setLote((l) => l.filter((_, j) => j !== i))}>Quitar</button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p>
        <button type="button" className="boton-primario" onClick={revisar} disabled={!lote.length || leyendo}>
          {leyendo ? 'Revisando…' : `Revisar y cargar (${plural(lote.reduce((s, x) => s + x.cantidad, 0), 'unidad', 'unidades')})`}
        </button>
      </p>
    </section>
  )
}

function Historial({ version }) {
  const [items, setItems] = useState(null)
  useEffect(() => {
    api('/hotel/productos/importaciones').then((r) => setItems(r.estado === 200 ? r.datos.importaciones : [])).catch(() => setItems([]))
  }, [version])
  if (!items || !items.length) return null
  const origen = { factura_xml: 'Factura', planilla: 'Planilla', lector: 'Lector de códigos', foto: 'Foto' }
  return (
    <section className="tarjeta">
      <h2>Últimas cargas</h2>
      <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Últimas cargas de productos">
        <table className="tabla">
          <thead><tr><th>Fecha</th><th>Origen</th><th>Detalle</th><th>Unidades</th><th>Nuevos</th><th>Por</th></tr></thead>
          <tbody>
            {items.map((x) => (
              <tr key={x.importacion_id}>
                <td>{fechaCorta(x.registrada_en)}</td>
                <td>{origen[x.origen] || x.origen}</td>
                <td>{x.folio ? `N° ${x.folio} · ${x.emisor_razon_social || x.emisor_rut}` : plural(x.lineas, 'línea')}</td>
                <td>{x.unidades}</td>
                <td>{x.productos_nuevos}</td>
                <td>{x.actor}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

/** Carga amigable de productos: bandeja de facturas (foto, PDF, XML, correo), planilla o lector, con revisión común. */
export function ImportarProductos({ fuente, alCargar }) {
  const [version, setVersion] = useState(0)
  const catalogo = useCatalogo(version)
  const [previa, setPrevia] = useState(null)
  const [xml, setXml] = useState(null)
  const [resultado, setResultado] = useState(null)

  useEffect(() => { setPrevia(null); setResultado(null) }, [fuente])

  if (resultado) {
    return (
      <>
        <div className="confirmacion-operacion-contenedor" role="status">
          <span className="confirmacion-icono" aria-hidden="true">✓</span>
          <div className="confirmacion-cuerpo">
            <p className="operacion-confirmada" data-importacion={resultado.importacion_id}>{resumenImportacion(resultado)}</p>
          </div>
        </div>
        <p>
          <button type="button" className="boton-primario" onClick={() => { setResultado(null); setPrevia(null) }}>Cargar otra</button>
        </p>
        <Historial version={version} />
      </>
    )
  }
  if (previa) {
    return (
      <Revision previa={previa} xml={xml} catalogo={catalogo}
        alCancelar={() => setPrevia(null)}
        alTerminar={(r) => { setResultado(r); setPrevia(null); setVersion((v) => v + 1); alCargar?.() }} />
    )
  }
  const alLeer = (p, x = null) => { setPrevia(p); setXml(x) }
  return (
    <>
      {fuente === 'factura' && (
        <FacturasProveedor catalogo={catalogo} version={version}
          alTerminar={(r) => { setResultado(r); setVersion((v) => v + 1); alCargar?.() }} />
      )}
      {fuente === 'planilla' && <FuentePlanilla alLeer={alLeer} />}
      {fuente === 'lector' && <FuenteLector alLeer={alLeer} />}
      <Historial version={version} />
    </>
  )
}
