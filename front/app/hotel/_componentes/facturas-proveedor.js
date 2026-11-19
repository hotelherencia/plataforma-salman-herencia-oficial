'use client'

// Bandeja de facturas de proveedores (2026-11-19), dentro de la pestaña
// «Cargar desde factura»: foto desde el celular, PDF, XML o correo de
// intercambio. Nada suma stock hasta que se confirma la revisión.

import { useCallback, useEffect, useRef, useState } from 'react'
import { api, mensajeDeError, urlApi, useClaveOperacion, alRechazar } from '../../../lib/api'
import { fechaCorta, pesos } from '../../../lib/estadias'
import { fechaATexto, plural } from '../../../lib/formato'
import { decodificarXml } from '../../../lib/importacion'
import {
  CALIDAD_FOTO, LADO_MAXIMO_FOTO, accionesDocumento, clasificarArchivo, dimensionesReducidas, etiquetaClase, etiquetaEstado,
  etiquetaLectura, etiquetaOrigen, lineaManualVacia, lineasManuales, proveedorDocumento, resumenCorreo, tituloDocumento,
} from '../../../lib/facturas'
import { Revision } from './importar-productos'
import css from './operacion.module.css'

const TONO = { exito: css.chipExito, aviso: css.chipAviso, info: css.chipInfo, neutro: '', error: css.chipError }
const SIN_CONEXION = 'No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.'

/** Reduce la foto en el navegador (lado mayor 3200 px, JPEG 0,9): liviana y con el timbre legible. */
async function comprimirFoto(archivo) {
  if (typeof createImageBitmap !== 'function') return archivo
  let imagen
  try {
    imagen = await createImageBitmap(archivo, { imageOrientation: 'from-image' })
  } catch {
    return archivo // HEIC u otro formato que el navegador no abre: el servidor decide
  }
  const { ancho, alto, reducida } = dimensionesReducidas(imagen.width, imagen.height, LADO_MAXIMO_FOTO)
  if (!reducida && archivo.type === 'image/jpeg' && archivo.size < 4_000_000) return archivo
  const lienzo = document.createElement('canvas')
  lienzo.width = ancho
  lienzo.height = alto
  lienzo.getContext('2d').drawImage(imagen, 0, 0, ancho, alto)
  const blob = await new Promise((ok) => lienzo.toBlob(ok, 'image/jpeg', CALIDAD_FOTO))
  return blob || archivo
}

function Chip({ tono, children, ...resto }) {
  return <span className={`${css.chip} ${TONO[tono] || ''}`} {...resto}>{children}</span>
}

/** Botones de carga: cámara del celular, PDF/foto y XML. */
function Cargar({ alCargar }) {
  const [estado, setEstado] = useState('')
  const [error, setError] = useState('')
  const [arrastre, setArrastre] = useState(false)

  async function subir(archivo, entrada) {
    setError('')
    if (!archivo) return
    const tipo = clasificarArchivo(archivo.name, archivo.type, archivo.size)
    if (tipo.error) { setError(tipo.error); return }
    try {
      let r
      if (tipo.tipo === 'xml') {
        setEstado('Leyendo el XML…')
        const xml = decodificarXml(new Uint8Array(await archivo.arrayBuffer()))
        r = await api('/hotel/productos/documentos/xml', { metodo: 'POST', cuerpo: { xml } })
      } else {
        setEstado(tipo.tipo === 'foto' ? 'Preparando la foto…' : 'Subiendo el PDF…')
        const cuerpo = tipo.tipo === 'foto' ? await comprimirFoto(archivo) : archivo
        if (cuerpo.size > 10 * 1024 * 1024) { setError('El archivo sigue siendo muy grande (máximo 10 MB).'); return }
        setEstado('Leyendo la factura… (puede tardar unos segundos)')
        r = await api('/hotel/productos/documentos/archivo', {
          metodo: 'POST', binario: cuerpo, timeoutMs: 120_000,
          cabeceras: { 'X-Nombre-Archivo': encodeURIComponent(archivo.name || 'foto.jpg').slice(0, 200) },
        })
      }
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
      const doc = r.datos.documento_id ? r.datos : r.datos.documento
      if (doc) alCargar(doc, r.datos.repetido || (r.datos.repetidos?.length > 0 && !r.datos.creados?.length))
      else if (r.datos.ya_importada) setError(`Esa factura ya se cargó el ${fechaCorta(r.datos.ya_importada.registrada_en)}.`)
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setEstado('')
      if (entrada) entrada.value = ''
    }
  }

  return (
    <section className="tarjeta">
      <h2>Cargar desde la factura del proveedor</h2>
      <p className={css.ayuda}>
        Saca una foto a la factura en papel, sube el PDF o el XML del SII. Con la foto se lee el timbre electrónico
        (proveedor, folio y total) y, si está activa la lectura automática, cada producto. Revisas todo antes de sumar stock.
      </p>
      <div className={css.botonesCarga}>
        <label className={`boton-primario ${css.botonArchivo}`}>
          Fotografiar factura
          <input className={css.ocultoVisual} type="file" accept="image/*" capture="environment"
            aria-label="Fotografiar factura" disabled={Boolean(estado)} onChange={(e) => subir(e.target.files?.[0], e.target)} />
        </label>
        <label className={`boton-secundario ${css.botonArchivo}`}>
          Subir PDF o foto
          <input className={css.ocultoVisual} type="file" accept="application/pdf,image/*"
            aria-label="PDF o foto de la factura" disabled={Boolean(estado)} onChange={(e) => subir(e.target.files?.[0], e.target)} />
        </label>
      </div>
      <label
        className={`${css.zonaArchivo} ${arrastre ? css.zonaArchivoActiva : ''}`}
        onDragOver={(e) => { e.preventDefault(); setArrastre(true) }}
        onDragLeave={() => setArrastre(false)}
        onDrop={(e) => { e.preventDefault(); setArrastre(false); subir(e.dataTransfer.files?.[0]) }}
      >
        <span className={css.zonaTitulo}>{estado || 'Arrastra aquí el XML de la factura'}</span>
        <span className={css.ayuda}>o haz clic para elegir el archivo (también acepta PDF o foto)</span>
        <input className={css.ocultoVisual} type="file" accept=".xml,text/xml,application/xml"
          aria-label="Archivo XML de la factura" disabled={Boolean(estado)} onChange={(e) => subir(e.target.files?.[0], e.target)} />
      </label>
      {estado && <p className={css.ayuda} role="status">{estado}</p>}
      {error && <p className="alerta" role="alert">{error}</p>}
    </section>
  )
}

/** Lista de documentos por revisar (y pedidos en borrador). */
function Bandeja({ version, alAbrir, alCambiar }) {
  const [datos, setDatos] = useState(null)
  const [aviso, setAviso] = useState('')
  const [error, setError] = useState('')
  const [revisando, setRevisando] = useState(false)

  const cargar = useCallback(async () => {
    try {
      const r = await api('/hotel/productos/documentos')
      if (r.estado === 200) setDatos(r.datos)
      else setError(mensajeDeError(r.datos, r.estado))
    } catch {
      setError(SIN_CONEXION)
    }
  }, [])
  useEffect(() => { cargar() }, [cargar, version])

  async function revisarCorreo() {
    setRevisando(true)
    setAviso('')
    setError('')
    try {
      const r = await api('/hotel/productos/recepcion-correo', { metodo: 'POST', timeoutMs: 120_000 })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else { setAviso(resumenCorreo(r.datos)); await cargar() }
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setRevisando(false)
    }
  }

  async function descartar(d) {
    const texto = d.clase === 'nota_credito' ? '¿Archivar esta nota de crédito?' : '¿Descartar este documento? No suma stock.'
    if (!window.confirm(texto)) return
    const r = await api(`/hotel/productos/documentos/${encodeURIComponent(d.documento_id)}/descarte`, { metodo: 'POST' }).catch(() => null)
    if (!r) setError(SIN_CONEXION)
    else if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
    else { await cargar(); alCambiar?.() }
  }

  if (!datos) return error ? <p className="alerta" role="alert">{error}</p> : null
  const docs = datos.documentos
  return (
    <section className="tarjeta" aria-label="Documentos por revisar">
      <div className="tarjeta-cabecera">
        <h2>Por revisar</h2>
        {datos.buzon_recepcion && (
          <button type="button" className="boton-secundario" onClick={revisarCorreo} disabled={revisando}>
            {revisando ? 'Revisando el correo…' : 'Revisar correo ahora'}
          </button>
        )}
      </div>
      <p className="nota-chica" data-lectura-automatica={datos.lectura_automatica.activa ? 'activa' : 'inactiva'}>
        {datos.lectura_automatica.activa
          ? 'Lectura automática de fotos activa: revisa siempre cantidades y costos.'
          : 'Lectura automática de fotos desactivada: de la foto se lee el timbre del SII y las líneas se escriben a mano.'}
        {datos.buzon_recepcion ? ' Las facturas que llegan al correo de intercambio aparecen aquí solas.' : ''}
      </p>
      {aviso && <p className="aviso" role="status">{aviso}</p>}
      {error && <p className="alerta" role="alert">{error}</p>}
      {!docs.length ? (
        <p className={css.ayuda}>No hay facturas ni pedidos pendientes.</p>
      ) : (
        <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Facturas y pedidos por revisar">
          <table className="tabla">
            <thead><tr><th>Documento</th><th>Proveedor</th><th>Fecha</th><th>Total</th><th>Estado</th><th></th></tr></thead>
            <tbody>
              {docs.map((d) => {
                const est = etiquetaEstado(d.estado)
                const acc = accionesDocumento(d)
                return (
                  <tr key={d.documento_id} data-documento={d.documento_id} data-clase={d.clase}>
                    <td>
                      {tituloDocumento(d)}
                      <div className={css.chips}>
                        <Chip tono="info">{etiquetaOrigen(d.origen)}</Chip>
                        {d.discrepancias.length > 0 && <Chip tono="aviso">{plural(d.discrepancias.length, 'aviso')}</Chip>}
                      </div>
                    </td>
                    <td>{proveedorDocumento(d)}</td>
                    <td>{fechaATexto(d.fecha_emision) || fechaCorta(d.creado_en)}</td>
                    <td>{d.monto_total_clp != null ? pesos(d.monto_total_clp) : '—'}</td>
                    <td><Chip tono={est.tono}>{est.texto}</Chip></td>
                    <td>
                      <div className={css.acciones}>
                        <button type="button" className="boton-secundario" onClick={() => alAbrir(d.documento_id)}>Revisar</button>
                        {acc.descartar && (
                          <button type="button" className="boton-fantasma" onClick={() => descartar(d)}>
                            {d.clase === 'nota_credito' ? 'Archivar' : 'Descartar'}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

/** Datos de cabecera que faltan (foto sin timbre) y clase del documento. */
function Cabecera({ doc, alGuardar }) {
  const bloqueado = doc.lectura === 'xml' || Boolean(doc.ted)
  const [campos, setCampos] = useState({
    clase: doc.clase, emisor_rut: doc.emisor_rut || '', emisor_razon_social: doc.emisor_razon_social || '',
    folio: doc.folio || '', monto_total_clp: doc.monto_total_clp ?? '',
  })
  const cambio = (k) => (e) => setCampos((c) => ({ ...c, [k]: e.target.value }))
  function guardar(e) {
    e.preventDefault()
    const cuerpo = { clase: campos.clase }
    if (!bloqueado) {
      if (campos.emisor_rut.trim()) cuerpo.emisor_rut = campos.emisor_rut.trim()
      if (campos.emisor_razon_social.trim()) cuerpo.emisor_razon_social = campos.emisor_razon_social.trim()
      if (String(campos.folio).trim()) cuerpo.folio = String(campos.folio).trim()
      if (campos.monto_total_clp !== '') cuerpo.monto_total_clp = Math.round(Number(campos.monto_total_clp) || 0)
    }
    alGuardar(cuerpo)
  }
  return (
    <form className="formulario" onSubmit={guardar} aria-label="Datos del documento">
      <label className="campo">
        <span>Tipo de documento</span>
        <select className="entrada" value={campos.clase} onChange={cambio('clase')}>
          <option value="factura">Factura</option>
          <option value="nota_credito">Nota de crédito</option>
          <option value="pedido">Pedido u orden de compra (no suma stock)</option>
          <option value="desconocido">Por identificar</option>
        </select>
      </label>
      {!bloqueado && (
        <>
          <label className="campo"><span>RUT del proveedor</span>
            <input className="entrada" value={campos.emisor_rut} onChange={cambio('emisor_rut')} placeholder="76.123.456-7" /></label>
          <label className="campo"><span>Nombre del proveedor</span>
            <input className="entrada" value={campos.emisor_razon_social} onChange={cambio('emisor_razon_social')} /></label>
          <label className="campo"><span>Folio</span>
            <input className="entrada" value={campos.folio} onChange={cambio('folio')} inputMode="numeric" /></label>
          <label className="campo"><span>Total del documento</span>
            <input className="entrada" type="number" min="0" value={campos.monto_total_clp} onChange={cambio('monto_total_clp')} /></label>
        </>
      )}
      {bloqueado && <p className={css.ayuda}>Proveedor, folio y total vienen del timbre o del XML del SII y no se editan.</p>}
      <p><button type="submit" className="boton-secundario">Guardar datos</button></p>
    </form>
  )
}

/** Líneas escritas a mano cuando no hay lectura automática (o para corregirla). */
function EditorLineas({ inicial, alGuardar }) {
  const [filas, setFilas] = useState(() => (inicial.length
    ? inicial.map((l) => ({ nombre: l.nombre || '', codigo: l.codigo || '', cantidad: l.cantidad ?? '', unidad: l.unidad || '', costo: l.costo_unitario_clp ?? '' }))
    : [lineaManualVacia(), lineaManualVacia(), lineaManualVacia()]))
  const [error, setError] = useState('')
  const cambiar = (i, k, v) => setFilas((fs) => fs.map((f, j) => (j === i ? { ...f, [k]: v } : f)))
  function guardar() {
    const r = lineasManuales(filas)
    if (r.error) { setError(r.error); return }
    setError('')
    alGuardar(r.lineas)
  }
  return (
    <div aria-label="Líneas del documento">
      <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Escribir las líneas de la factura">
        <table className={`tabla ${css.editorLineas}`}>
          <thead><tr><th>Descripción</th><th>Código</th><th>Cantidad</th><th>Unidad</th><th>Costo neto unitario</th></tr></thead>
          <tbody>
            {filas.map((f, i) => (
              <tr key={i}>
                <td><input className="entrada" aria-label={`Descripción línea ${i + 1}`} value={f.nombre} onChange={(e) => cambiar(i, 'nombre', e.target.value)} /></td>
                <td><input className="entrada" aria-label={`Código línea ${i + 1}`} value={f.codigo} onChange={(e) => cambiar(i, 'codigo', e.target.value)} /></td>
                <td><input className="entrada" type="number" min="0" step="any" aria-label={`Cantidad línea ${i + 1}`} value={f.cantidad} onChange={(e) => cambiar(i, 'cantidad', e.target.value)} /></td>
                <td><input className="entrada" aria-label={`Unidad línea ${i + 1}`} value={f.unidad} onChange={(e) => cambiar(i, 'unidad', e.target.value)} /></td>
                <td><input className="entrada" type="number" min="0" aria-label={`Costo línea ${i + 1}`} value={f.costo} onChange={(e) => cambiar(i, 'costo', e.target.value)} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {error && <p className="alerta" role="alert">{error}</p>}
      <div className={css.acciones}>
        <button type="button" className="boton-fantasma" onClick={() => setFilas((fs) => [...fs, lineaManualVacia()])}>Agregar línea</button>
        <button type="button" className="boton-primario" onClick={guardar}>Guardar líneas</button>
      </div>
    </div>
  )
}

/** Un documento abierto: foto, avisos, datos y la revisión común. */
function Documento({ documentoId, catalogo, alVolver, alTerminar }) {
  const [doc, setDoc] = useState(null)
  const [error, setError] = useState('')
  const [editando, setEditando] = useState(false)
  const [version, setVersion] = useState(0)

  const cargar = useCallback(async () => {
    try {
      const r = await api(`/hotel/productos/documentos/${encodeURIComponent(documentoId)}`)
      if (r.estado === 200) setDoc(r.datos)
      else setError(mensajeDeError(r.datos, r.estado))
    } catch {
      setError(SIN_CONEXION)
    }
  }, [documentoId])
  useEffect(() => { cargar() }, [cargar])

  async function guardar(cuerpo) {
    setError('')
    const r = await api(`/hotel/productos/documentos/${encodeURIComponent(documentoId)}`, { metodo: 'PUT', cuerpo }).catch(() => null)
    if (!r) { setError(SIN_CONEXION); return }
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
    setEditando(false)
    await cargar()
    setVersion((v) => v + 1)
  }

  if (!doc) return error ? <p className="alerta" role="alert">{error}</p> : null
  const acc = accionesDocumento(doc)
  const esImagen = doc.origen === 'foto'
  const sinLineas = !doc.lineas.length
  const previa = {
    origen: 'documento', lineas: doc.lineas, ya_importada: doc.ya_importada,
    documento: { ...doc, tipo_nombre: doc.tipo_nombre || etiquetaClase(doc.clase) },
  }
  return (
    <>
      <section className="tarjeta" aria-label="Documento del proveedor" data-documento-abierto={doc.documento_id}>
        <div className="tarjeta-cabecera">
          <h2>{tituloDocumento(doc)}</h2>
          <button type="button" className="boton-fantasma" onClick={alVolver}>Volver a la bandeja</button>
        </div>
        <div className={css.chips}>
          <Chip tono="info">{etiquetaOrigen(doc.origen)}</Chip>
          <Chip tono={etiquetaEstado(doc.estado).tono}>{etiquetaEstado(doc.estado).texto}</Chip>
          {doc.lectura && <Chip>{etiquetaLectura(doc.lectura)}</Chip>}
          {doc.ted && <Chip tono="exito" data-timbre>Timbre SII leído</Chip>}
        </div>
        {doc.discrepancias.length > 0 && (
          <div className="aviso" role="status" data-discrepancias>
            <strong>Revisa antes de cargar:</strong>
            <ul className={css.discrepancias}>
              {doc.discrepancias.map((d) => <li key={d.codigo + d.mensaje}>{d.mensaje}</li>)}
            </ul>
          </div>
        )}
        {acc.texto && <p className={css.ayuda}>{acc.texto}</p>}
        {doc.tiene_archivo && (
          esImagen
            ? <img className={css.vistaFactura} src={urlApi(`/hotel/productos/documentos/${encodeURIComponent(doc.documento_id)}/archivo`)} alt={`Foto de ${tituloDocumento(doc)}`} />
            : <p><a href={urlApi(`/hotel/productos/documentos/${encodeURIComponent(doc.documento_id)}/archivo`)} target="_blank" rel="noopener noreferrer">Ver el archivo original</a></p>
        )}
        {error && <p className="alerta" role="alert">{error}</p>}
        {doc.estado === 'pendiente' || doc.estado === 'borrador' ? (
          <>
            <Cabecera key={`c${version}`} doc={doc} alGuardar={guardar} />
            {doc.lectura !== 'xml' && (sinLineas || editando) && (
              <>
                <h3>{sinLineas ? 'Escribe las líneas de la factura' : 'Corregir líneas'}</h3>
                <p className={css.ayuda}>Copia de la foto la descripción, cantidad y costo neto de cada producto. Lo que no aparezca, déjalo en blanco.</p>
                <EditorLineas key={`e${version}`} inicial={doc.lineas} alGuardar={(lineas) => guardar({ lineas })} />
              </>
            )}
            {doc.lectura !== 'xml' && !sinLineas && !editando && (
              <p><button type="button" className="boton-fantasma" onClick={() => setEditando(true)}>Corregir las líneas</button></p>
            )}
          </>
        ) : null}
      </section>
      {(acc.cargar || doc.ya_importada) && !sinLineas && !editando && (
        <Revision key={`r${version}`} previa={previa} catalogo={catalogo} documentoId={doc.documento_id}
          pedidoSugerido={doc.pedido_sugerido} textoCancelar="Volver a la bandeja"
          alCancelar={alVolver} alTerminar={alTerminar} />
      )}
    </>
  )
}

/** Unidades por envase y producto recordados por proveedor (editables). */
function Equivalencias({ version, catalogo }) {
  const [items, setItems] = useState(null)
  const [cambios, setCambios] = useState({})
  const [error, setError] = useState('')
  const cargar = useCallback(() => {
    api('/hotel/productos/equivalencias').then((r) => setItems(r.estado === 200 ? r.datos.equivalencias : [])).catch(() => setItems([]))
  }, [])
  useEffect(() => { cargar() }, [cargar, version])
  if (!items || !items.length) return null

  async function guardar(e) {
    const c = cambios[e.equivalencia_id] || {}
    const cuerpo = {}
    if (c.unidades_por_paquete !== undefined) cuerpo.unidades_por_paquete = Math.round(Number(c.unidades_por_paquete))
    if (c.producto_id) cuerpo.producto_id = c.producto_id
    if (cuerpo.unidades_por_paquete !== undefined && !(cuerpo.unidades_por_paquete >= 1)) { setError('Las unidades por envase deben ser 1 o más.'); return }
    const r = await api(`/hotel/productos/equivalencias/${encodeURIComponent(e.equivalencia_id)}`, { metodo: 'PUT', cuerpo }).catch(() => null)
    if (!r || r.estado >= 400) { setError(r ? mensajeDeError(r.datos, r.estado) : SIN_CONEXION); return }
    setError('')
    setCambios((x) => ({ ...x, [e.equivalencia_id]: undefined }))
    cargar()
  }
  async function olvidar(e) {
    if (!window.confirm(`¿Olvidar «${e.descripcion}»? La próxima factura se volverá a revisar a mano.`)) return
    const r = await api(`/hotel/productos/equivalencias/${encodeURIComponent(e.equivalencia_id)}`, { metodo: 'DELETE' }).catch(() => null)
    if (!r || r.estado >= 400) setError(r ? mensajeDeError(r.datos, r.estado) : SIN_CONEXION)
    else cargar()
  }
  return (
    <details className="tarjeta">
      <summary><strong>Productos recordados por proveedor</strong> ({items.length})</summary>
      <p className={css.ayuda}>Cada vez que cargas una factura se recuerda a qué producto corresponde cada ítem del proveedor y cuántas unidades trae su envase.</p>
      {error && <p className="alerta" role="alert">{error}</p>}
      <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Productos recordados por proveedor">
        <table className="tabla">
          <thead><tr><th>Proveedor</th><th>Como viene en la factura</th><th>Producto</th><th>Unidades por envase</th><th></th></tr></thead>
          <tbody>
            {items.map((e) => {
              const c = cambios[e.equivalencia_id] || {}
              return (
                <tr key={e.equivalencia_id} data-equivalencia={e.equivalencia_id}>
                  <td>{e.emisor_razon_social || e.emisor_rut}</td>
                  <td>{e.descripcion}</td>
                  <td>
                    <select className="entrada" aria-label={`Producto para ${e.descripcion}`} value={c.producto_id || e.producto_id}
                      onChange={(ev) => setCambios((x) => ({ ...x, [e.equivalencia_id]: { ...c, producto_id: ev.target.value } }))}>
                      {catalogo.filter((p) => p.activo || p.producto_id === e.producto_id).map((p) => <option key={p.producto_id} value={p.producto_id}>{p.nombre}</option>)}
                    </select>
                  </td>
                  <td>
                    <input className="entrada" type="number" min="1" step="1" aria-label={`Unidades por envase de ${e.descripcion}`}
                      value={c.unidades_por_paquete ?? e.unidades_por_paquete}
                      onChange={(ev) => setCambios((x) => ({ ...x, [e.equivalencia_id]: { ...c, unidades_por_paquete: ev.target.value } }))} />
                  </td>
                  <td>
                    <div className={css.acciones}>
                      <button type="button" className="boton-secundario" onClick={() => guardar(e)} disabled={!cambios[e.equivalencia_id]}>Guardar</button>
                      <button type="button" className="boton-fantasma" onClick={() => olvidar(e)}>Olvidar</button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </details>
  )
}

/** Pestaña «Cargar desde factura» completa. */
export function FacturasProveedor({ catalogo, version, alTerminar }) {
  const [abierto, setAbierto] = useState(null)
  const [aviso, setAviso] = useState('')
  const [local, setLocal] = useState(0)
  const arriba = useRef(null)

  const abrir = (id) => { setAbierto(id); setAviso(''); arriba.current?.scrollIntoView?.({ block: 'start' }) }

  if (abierto) {
    return (
      <div ref={arriba}>
        {aviso && <p className="aviso" role="status">{aviso}</p>}
        <Documento key={abierto} documentoId={abierto} catalogo={catalogo}
          alVolver={() => { setAbierto(null); setLocal((v) => v + 1) }}
          alTerminar={(r) => { setAbierto(null); setLocal((v) => v + 1); alTerminar(r) }} />
      </div>
    )
  }
  return (
    <div ref={arriba}>
      <Cargar alCargar={(doc, repetido) => {
        abrir(doc.documento_id)
        if (repetido) setAviso(`${tituloDocumento(doc)} ya estaba en la bandeja: se abrió la misma.`)
      }} />
      {aviso && <p className="aviso" role="status">{aviso}</p>}
      <Bandeja version={version + local} alAbrir={abrir} alCambiar={() => setLocal((v) => v + 1)} />
      <Equivalencias version={version + local} catalogo={catalogo} />
    </div>
  )
}
