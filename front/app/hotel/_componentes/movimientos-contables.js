'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { api, alRechazar, clp, mensajeDeError, Campo, CampoSelect, useClaveOperacion } from '../../../lib/api'
import { CATEGORIAS_DIRECTAS, DOCUMENTOS, MEDIOS, esTarjeta, nombreMedio, validarDatosPago } from '../../../lib/caja'
import { formatearRut, rotuloMovimiento } from '../../../lib/contabilidad'
import { fechaHora } from '../../../lib/formato'
import { SelectorProducto } from './selector-producto'
import { BarraContextual, SelectorFila } from './barra-contextual'
import ConciliacionBancariaTributaria from './conciliacion-bancaria-tributaria'
import css from './operacion.module.css'

const ROTULO_DOC = { boleta: 'Boleta', factura: 'Factura', sin_documento: 'Sin documento', pendiente: 'Por indicar' }
const SIN_CONEXION = 'No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.'

/**
 * Libro contable (cargos, reversos, cobros de reservas y movimientos directos sin habitación).
 * No depende de que la caja esté abierta: todo cargo o venta directa queda registrado aquí y suma
 * en la contabilidad y en el cierre diario.
 */
export default function MovimientosContables({ hoy, esAdmin = false }) {
  const [desde, setDesde] = useState(hoy)
  const [hasta, setHasta] = useState(hoy)
  const [datos, setDatos] = useState(null)
  const [resumen, setResumen] = useState(null)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [cargando, setCargando] = useState(false)
  const [mostrarForm, setMostrarForm] = useState(false)
  const [seleccionadoKey, setSeleccionadoKey] = useState(null)
  const [cobrando, setCobrando] = useState(null)
  const [reversando, setReversando] = useState(null)

  const consultar = useCallback(async (d, h) => {
    setError('')
    setCargando(true)
    try {
      const r = await api(`/hotel/contabilidad/movimientos?desde=${d}&hasta=${h}`)
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        setDatos(null)
        setResumen(null)
      } else {
        setDatos(r.datos.movimientos)
        setResumen(r.datos.resumen || null)
      }
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => { consultar(hoy, hoy) }, [consultar, hoy])

  return (
    <>
      <section className="tarjeta" aria-label="Libro contable de cargos, cobros y movimientos directos">
        <div className={css.acciones}>
          <form className="formulario" onSubmit={(e) => { e.preventDefault(); consultar(desde, hasta) }}>
            <Campo etiqueta="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
            <Campo etiqueta="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
            <button type="submit" className="boton-secundario" disabled={cargando}>
              {cargando ? 'Cargando…' : 'Ver libro contable'}
            </button>
          </form>
          <button
            type="button"
            className="boton-primario"
            onClick={() => { setMostrarForm((v) => !v); setOk('') }}
          >
            {mostrarForm ? 'Cerrar formulario' : 'Registrar movimiento sin habitación'}
          </button>
        </div>
        <p className="nota-clave">
          Incluye cargos y cobros de reservas más ventas directas, servicios y egresos sin habitación. Opera aunque el
          turno de caja esté cerrado y suma siempre a la contabilidad y al cierre diario.
        </p>
        {ok && <p role="status" className="aviso-ok">{ok}</p>}
        {error && <p role="alert" className="alerta">{error}</p>}
      </section>

      {mostrarForm && (
        <FormularioMovimientoDirecto
          alRegistrar={(m) => {
            setMostrarForm(false)
            setOk(
              `Movimiento directo registrado (${m.concepto} · ${clp(m.monto_clp)} · ${
                m.estado_cobro === 'cobrado' ? `cobrado por ${nombreMedio(m.medio)}` : 'pendiente de cobro'
              }).`,
            )
            consultar(desde, hasta)
          }}
        />
      )}

      {cobrando && (
        <FormularioCobrarDirecto
          movimiento={cobrando}
          alCancelar={() => setCobrando(null)}
          alCobrar={(m) => {
            setCobrando(null)
            setOk(`Cobro registrado para «${m.concepto}» (${clp(m.monto_clp)} · ${nombreMedio(m.medio)}).`)
            consultar(desde, hasta)
          }}
        />
      )}

      {reversando && (
        <FormularioReversoDirecto
          movimiento={reversando}
          alCancelar={() => setReversando(null)}
          alReversar={(m) => {
            setReversando(null)
            setOk(`Reverso registrado: ${m.concepto} (${clp(m.monto_clp)}).`)
            consultar(desde, hasta)
          }}
        />
      )}

      {resumen && (
        <section className="tarjeta" aria-label="Resumen contable del rango">
          <dl className={css.cifras}>
            <div className={css.cifra}>
              <dt>Total devengado (IVA incl.)</dt>
              <dd><strong>{clp(resumen.total_devengado_clp)}</strong></dd>
            </div>
            <div className={css.cifra}>
              <dt>Cargos en reservas</dt>
              <dd>{clp(resumen.cargos_reservas_clp)}</dd>
            </div>
            <div className={css.cifra}>
              <dt>Cargos directos (sin habitación)</dt>
              <dd>{clp(resumen.cargos_directos_clp)}</dd>
            </div>
            <div className={css.cifra}>
              <dt>Total cobrado</dt>
              <dd><strong>{clp(resumen.total_cobrado_clp)}</strong></dd>
            </div>
            {resumen.pendiente_directo_clp > 0 && (
              <div className={`${css.cifra} ${css.cifraDestacada}`}>
                <dt>Directos pendientes de cobro</dt>
                <dd><strong>{clp(resumen.pendiente_directo_clp)}</strong></dd>
              </div>
            )}
            {resumen.egresos_operacionales_clp > 0 && (
              <div className={css.cifra}>
                <dt>Egresos operacionales</dt>
                <dd>{clp(resumen.egresos_operacionales_clp)}</dd>
              </div>
            )}
          </dl>
        </section>
      )}

      <section className="tarjeta" aria-label="Detalle de movimientos contables">
        {cargando && !datos && <p className="estado" role="status" aria-busy="true">Cargando el libro contable…</p>}
        {datos && datos.length === 0 && <p className="estado estado-vacio">Sin movimientos en estas fechas.</p>}
        {datos && datos.length > 0 && (() => {
          const claveFila = (m, i) => `${m.movimiento_directo_id || m.fecha_hora}-${i}`
          const activo = datos.find((m, i) => claveFila(m, i) === seleccionadoKey) || null
          const operable = activo && activo.movimiento_directo_id && activo.tipo !== 'reverso_directo' && !activo.reversado
          return (
            <>
              <BarraContextual
                titulo="Acciones de movimiento contable"
                seleccionado={Boolean(activo)}
                resumen={activo ? `${rotuloMovimiento(activo.tipo)} · ${activo.concepto} · ${clp(activo.monto_clp)}` : ''}
                detalle={activo ? (operable ? 'Movimiento directo operable' : (activo.reversado ? 'Movimiento ya reversado' : 'Movimiento de reserva (gestionar desde la ficha de reserva)')) : ''}
                placeholder="Selecciona un movimiento directo de la tabla para cobrarlo o reversarlo."
                alLimpiar={() => setSeleccionadoKey(null)}
              >
                {activo && operable && (
                  <>
                    {activo.estado_cobro === 'pendiente' && (
                      <button type="button" className="boton-primario" onClick={() => setCobrando(activo)}>
                        Cobrar movimiento
                      </button>
                    )}
                    {esAdmin && (
                      <button type="button" className="boton-secundario boton-peligro" onClick={() => setReversando(activo)}>
                        Reversar movimiento
                      </button>
                    )}
                  </>
                )}
              </BarraContextual>

              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Libro contable (desliza para ver todas las columnas)">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th className="celda-selector"><span className="sr-only">Elegir</span></th>
                      <th>Fecha y hora</th>
                      <th>Movimiento</th>
                      <th>Detalle</th>
                      <th>Huésped / Origen</th>
                      <th>Habitación</th>
                      <th>Monto (IVA incl.)</th>
                      <th>Medio / Estado</th>
                      <th>Documento</th>
                      <th>Registrado por</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datos.map((m, i) => {
                      const k = claveFila(m, i)
                      const elegida = seleccionadoKey === k
                      return (
                        <tr
                          key={k}
                          className="fila-seleccionable"
                          data-seleccionada={elegida ? 'true' : 'false'}
                          onClick={() => setSeleccionadoKey(k)}
                        >
                          <td className="celda-selector">
                            <SelectorFila
                              nombreGrupo="mov-contable-activo"
                              elegido={elegida}
                              etiqueta={`Seleccionar movimiento ${m.concepto} de ${clp(m.monto_clp)}`}
                              alElegir={() => setSeleccionadoKey(k)}
                            />
                          </td>
                          <td className="celda-fecha">{fechaHora(m.fecha_hora)}</td>
                          <td>{rotuloMovimiento(m.tipo)}</td>
                          <td>{m.concepto}{m.cantidad ? ` × ${m.cantidad}` : ''}</td>
                          <td>
                            {m.reserva_id
                              ? <Link href={`/hotel/reservas/${m.reserva_id}`} onClick={(e) => e.stopPropagation()}>{m.huesped_nombre || m.reserva_id}</Link>
                              : 'Sin habitación (directo)'}
                          </td>
                          <td>{m.habitacion_id || '—'}</td>
                          <td>{clp(m.monto_clp)}</td>
                          <td>
                            {m.reversado
                              ? 'Reversado'
                              : m.medio
                                ? nombreMedio(m.medio)
                                : m.estado_cobro === 'pendiente'
                                  ? 'Pendiente de cobro'
                                  : '—'}
                          </td>
                          <td>
                            {m.documento_tipo && m.documento_tipo !== 'pendiente'
                              ? `${ROTULO_DOC[m.documento_tipo] || 'Documento'}${m.documento_folio ? ` N° ${m.documento_folio}` : ''}`
                              : m.estado_cobro === 'cobrado'
                                ? 'Por indicar'
                                : '—'}
                          </td>
                          <td>{m.actor || '—'}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )
        })()}
      </section>
      <ConciliacionBancariaTributaria esAdmin={esAdmin} />
    </>
  )
}

function FormularioMovimientoDirecto({ alRegistrar }) {
  const [tipo, setTipo] = useState('cargo_directo')
  const [usarProducto, setUsarProducto] = useState(false)
  const [producto, setProducto] = useState(null)
  const [cantidad, setCantidad] = useState('1')
  const [categoria, setCategoria] = useState('cafeteria')
  const [concepto, setConcepto] = useState('')
  const [monto, setMonto] = useState('')
  const [estadoCobro, setEstadoCobro] = useState('cobrado')
  const [medio, setMedio] = useState('transferencia')
  const [documento, setDocumento] = useState('boleta')
  const [voucher, setVoucher] = useState({ codigo: '', ultimos4: '', marca: '', comprobante: '' })
  const [receptor, setReceptor] = useState({ rut: '', razon_social: '', giro: '', direccion: '', comuna: '', correo: '' })
  const [nota, setNota] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [clave, renovar] = useClaveOperacion()

  async function enviar(e) {
    e.preventDefault()
    if (enviando) return
    setError('')
    const esProducto = tipo === 'cargo_directo' && usarProducto
    if (esProducto && !producto?.producto_id) { setError('Elige un producto del catálogo.'); return }
    if (!esProducto && !concepto.trim()) { setError('Indica el concepto del movimiento.'); return }
    if (!esProducto && !(Number(monto) > 0)) { setError('Indica un monto mayor que $0.'); return }
    if (estadoCobro === 'cobrado') {
      const invalido = validarDatosPago({ medio, codigo: voucher.codigo, ultimos4: voucher.ultimos4, documento, receptor })
      if (invalido) { setError(invalido); return }
    }
    setEnviando(true)
    try {
      const cuerpo = {
        tipo,
        categoria: tipo === 'egreso_operacional' ? 'gasto_operacional' : categoria,
        ...(esProducto
          ? { producto_id: producto.producto_id, cantidad: Math.max(1, Number(cantidad) || 1) }
          : { concepto: concepto.trim(), monto_clp: Number(monto) }),
        estado_cobro: estadoCobro,
        ...(estadoCobro === 'cobrado' ? {
          medio,
          documento_tipo: documento,
          ...(documento === 'factura' ? {
            receptor: Object.fromEntries(Object.entries(receptor).map(([k, v]) => [k, v.trim() || null])),
          } : {}),
          ...(esTarjeta(medio) ? {
            codigo_autorizacion: voucher.codigo.trim(),
            tarjeta_ultimos4: voucher.ultimos4.trim() || null,
            tarjeta_marca: voucher.marca.trim() || null,
          } : {}),
          ...(medio === 'transferencia' && voucher.comprobante.trim() ? { comprobante: voucher.comprobante.trim() } : {}),
        } : {}),
        nota: nota.trim() || null,
      }
      const r = await api('/hotel/contabilidad/movimientos-directos', {
        metodo: 'POST', cuerpo, claveIdempotencia: clave,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovar)
      } else {
        renovar()
        alRegistrar(r.datos)
      }
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="tarjeta" aria-label="Registrar movimiento directo">
      <h2>Movimiento directo (sin habitación ni reserva)</h2>
      <p className="nota-clave">
        Úsalo para ventas de mostrador, cafetería, estacionamiento o gastos menores. Si la caja está cerrada y es en
        efectivo, puedes asentarlo como <strong>Pendiente de cobro</strong> para que quede en la contabilidad de inmediato
        y cobrarlo al abrir el turno.
      </p>
      <form className="formulario" onSubmit={enviar}>
        <CampoSelect etiqueta="Tipo de movimiento" value={tipo} onChange={(e) => {
          const v = e.target.value
          setTipo(v)
          if (v === 'egreso_operacional') { setUsarProducto(false); setCategoria('gasto_operacional') }
          else if (categoria === 'gasto_operacional') setCategoria('cafeteria')
        }}>
          <option value="cargo_directo">Ingreso / cargo directo (sin habitación)</option>
          <option value="egreso_operacional">Egreso operacional (gasto menor)</option>
        </CampoSelect>

        {tipo === 'cargo_directo' && (
          <CampoSelect etiqueta="Categoría" value={categoria} onChange={(e) => setCategoria(e.target.value)}>
            {CATEGORIAS_DIRECTAS.filter(([k]) => k !== 'gasto_operacional').map(([v, n]) => (
              <option key={v} value={v}>{n}</option>
            ))}
          </CampoSelect>
        )}

        {tipo === 'cargo_directo' && (
          <label className="campo-check">
            <input type="checkbox" checked={usarProducto} onChange={(e) => setUsarProducto(e.target.checked)} />
            Seleccionar producto del catálogo (descuenta stock)
          </label>
        )}

        {tipo === 'cargo_directo' && usarProducto ? (
          <>
            <SelectorProducto elegido={producto} alElegir={setProducto} />
            <Campo etiqueta="Cantidad" type="number" min="1" value={cantidad} onChange={(e) => setCantidad(e.target.value)} />
          </>
        ) : (
          <>
            <Campo etiqueta="Concepto" value={concepto} maxLength={200} onChange={(e) => setConcepto(e.target.value)} />
            <Campo etiqueta="Monto total con IVA (CLP)" type="number" min="1" inputMode="numeric" value={monto} onChange={(e) => setMonto(e.target.value)} />
          </>
        )}

        <CampoSelect etiqueta="Estado de cobro / pago" value={estadoCobro} onChange={(e) => setEstadoCobro(e.target.value)}>
          <option value="cobrado">Cobrado / pagado ahora</option>
          <option value="pendiente">Pendiente de cobro (asentar en contabilidad ahora)</option>
        </CampoSelect>

        {estadoCobro === 'cobrado' && (
          <>
            <CampoSelect etiqueta="Medio de pago" value={medio} onChange={(e) => setMedio(e.target.value)}>
              {MEDIOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
            </CampoSelect>
            <CampoSelect etiqueta="¿Boleta o factura?" value={documento} onChange={(e) => setDocumento(e.target.value)}>
              {DOCUMENTOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
            </CampoSelect>
            {esTarjeta(medio) && (
              <>
                <Campo etiqueta="Código de autorización del voucher" value={voucher.codigo} maxLength={20}
                  onChange={(e) => setVoucher({ ...voucher, codigo: e.target.value })} />
                <Campo etiqueta="Últimos 4 dígitos (opcional)" value={voucher.ultimos4} maxLength={4} inputMode="numeric"
                  onChange={(e) => setVoucher({ ...voucher, ultimos4: e.target.value.replace(/\D/g, '') })} />
                <Campo etiqueta="Marca (opcional)" value={voucher.marca} maxLength={30}
                  onChange={(e) => setVoucher({ ...voucher, marca: e.target.value })} />
              </>
            )}
            {medio === 'transferencia' && (
              <Campo etiqueta="N° de comprobante (opcional)" value={voucher.comprobante} maxLength={60}
                onChange={(e) => setVoucher({ ...voucher, comprobante: e.target.value })} />
            )}
            {documento === 'factura' && (
              <fieldset className="tarjeta">
                <legend>Datos para la factura</legend>
                {[['rut', 'RUT de la empresa'], ['razon_social', 'Razón social'], ['giro', 'Giro'],
                  ['direccion', 'Dirección'], ['comuna', 'Comuna'], ['correo', 'Correo (opcional)']].map(([k, et]) => (
                  <Campo key={k} etiqueta={et} value={receptor[k]} maxLength={k === 'direccion' ? 160 : 120}
                    onChange={(e) => setReceptor({ ...receptor, [k]: e.target.value })}
                    onBlur={k === 'rut' ? () => { const f = formatearRut(receptor.rut); if (f) setReceptor((r) => ({ ...r, rut: f })) } : undefined} />
                ))}
              </fieldset>
            )}
          </>
        )}

        <Campo etiqueta="Nota (opcional)" value={nota} maxLength={500} onChange={(e) => setNota(e.target.value)} />
        <button type="submit" className="boton-primario" disabled={enviando}>
          {enviando ? 'Registrando…' : 'Registrar en contabilidad'}
        </button>
      </form>
      {error && <p role="alert" className="alerta">{error}</p>}
    </section>
  )
}

function FormularioCobrarDirecto({ movimiento, alCancelar, alCobrar }) {
  const [medio, setMedio] = useState('efectivo')
  const [documento, setDocumento] = useState('boleta')
  const [voucher, setVoucher] = useState({ codigo: '', ultimos4: '', marca: '', comprobante: '' })
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [clave, renovar] = useClaveOperacion()

  async function enviar(e) {
    e.preventDefault()
    if (enviando) return
    setError('')
    const invalido = validarDatosPago({ medio, codigo: voucher.codigo, ultimos4: voucher.ultimos4, documento, receptor: {} })
    if (invalido) { setError(invalido); return }
    setEnviando(true)
    try {
      const r = await api(`/hotel/contabilidad/movimientos-directos/${encodeURIComponent(movimiento.movimiento_directo_id)}/cobrar`, {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {
          medio,
          documento_tipo: documento,
          ...(esTarjeta(medio) ? {
            codigo_autorizacion: voucher.codigo.trim(),
            tarjeta_ultimos4: voucher.ultimos4.trim() || null,
            tarjeta_marca: voucher.marca.trim() || null,
          } : {}),
          ...(medio === 'transferencia' && voucher.comprobante.trim() ? { comprobante: voucher.comprobante.trim() } : {}),
        },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovar)
      } else {
        renovar()
        alCobrar(r.datos)
      }
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="tarjeta" aria-label="Cobrar movimiento directo pendiente">
      <h2>Cobrar «{movimiento.concepto}» ({clp(Math.abs(movimiento.monto_clp))})</h2>
      <form className="formulario" onSubmit={enviar}>
        <CampoSelect etiqueta="Medio de pago" value={medio} onChange={(e) => setMedio(e.target.value)}>
          {MEDIOS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </CampoSelect>
        <CampoSelect etiqueta="Documento" value={documento} onChange={(e) => setDocumento(e.target.value)}>
          {DOCUMENTOS.filter(([v]) => v !== 'factura').map(([v, n]) => <option key={v} value={v}>{n}</option>)}
        </CampoSelect>
        {esTarjeta(medio) && (
          <Campo etiqueta="Código de autorización del voucher" value={voucher.codigo} maxLength={20}
            onChange={(e) => setVoucher({ ...voucher, codigo: e.target.value })} />
        )}
        {medio === 'transferencia' && (
          <Campo etiqueta="N° de comprobante (opcional)" value={voucher.comprobante} maxLength={60}
            onChange={(e) => setVoucher({ ...voucher, comprobante: e.target.value })} />
        )}
        <div className={css.acciones}>
          <button type="submit" className="boton-primario" disabled={enviando}>
            {enviando ? 'Registrando…' : 'Confirmar cobro'}
          </button>
          <button type="button" className="boton-secundario" onClick={alCancelar}>Cancelar</button>
        </div>
      </form>
      {error && <p role="alert" className="alerta">{error}</p>}
    </section>
  )
}

function FormularioReversoDirecto({ movimiento, alCancelar, alReversar }) {
  const [motivo, setMotivo] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [clave, renovar] = useClaveOperacion()

  async function enviar(e) {
    e.preventDefault()
    if (enviando) return
    setError('')
    if (motivo.trim().length < 10) { setError('Explica el motivo del reverso (mínimo 10 caracteres).'); return }
    setEnviando(true)
    try {
      const r = await api(`/hotel/contabilidad/movimientos-directos/${encodeURIComponent(movimiento.movimiento_directo_id)}/reverso`, {
        metodo: 'POST', claveIdempotencia: clave, cuerpo: { motivo: motivo.trim() },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovar)
      } else {
        renovar()
        alReversar(r.datos)
      }
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <section className="tarjeta" aria-label="Reversar movimiento directo">
      <h2>Reversar «{movimiento.concepto}» ({clp(Math.abs(movimiento.monto_clp))})</h2>
      <p className="nota-clave">El registro original no se borra: se asienta un reverso inmutable y, si era producto con stock, el stock se devuelve.</p>
      <form className="formulario" onSubmit={enviar}>
        <Campo etiqueta="Motivo del reverso" value={motivo} maxLength={300} onChange={(e) => setMotivo(e.target.value)} />
        <div className={css.acciones}>
          <button type="submit" className="boton-primario" disabled={enviando}>Confirmar reverso</button>
          <button type="button" className="boton-secundario" onClick={alCancelar}>Cancelar</button>
        </div>
      </form>
      {error && <p role="alert" className="alerta">{error}</p>}
    </section>
  )
}
