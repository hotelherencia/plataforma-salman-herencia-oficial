'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, clp, mensajeDeError, Campo, CampoSelect } from '../../../lib/api'
import { fechaATexto, plural } from '../../../lib/formato'
import { nombreMedio } from '../../../lib/caja'

const ETIQUETA_ESTADO_LINEA = {
  pendiente: 'Pendiente',
  conciliado: 'Conciliado',
  parcial: 'Parcial',
}

function periodoActual() {
  const hoy = new Date()
  const y = hoy.getFullYear()
  const m = String(hoy.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}`
}

function descomponerPeriodo(periodo) {
  const [a, m] = String(periodo || periodoActual()).split('-')
  return { anio: Number(a) || new Date().getFullYear(), mes: Number(m) || (new Date().getMonth() + 1) }
}

/**
 * Conciliación bancaria (Contable 2.6 / #396) y Borrador tributario F29 (Contable 2.7 / #397).
 * Vive dentro de Caja y pagos → Libro contable, sin agregar ítems al menú lateral.
 */
export default function ConciliacionBancariaTributaria({ esAdmin = false }) {
  const [periodo, setPeriodo] = useState(periodoActual)
  const [panelBanco, setPanelBanco] = useState(null)
  const [comisiones, setComisiones] = useState([])
  const [f29, setF29] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [cargando, setCargando] = useState(false)

  // Importar cartola
  const [banco, setBanco] = useState('Banco de Chile')
  const [cuenta, setCuenta] = useState('Cta Cte Hotel')
  const [csvTexto, setCsvTexto] = useState('')
  const [previsualizacion, setPrevisualizacion] = useState(null)

  // Conciliación manual
  const [manual, setManual] = useState({
    cartola_movimiento_id: '',
    caja_movimiento_id: '',
    monto_asignado_clp: '',
    comision_clp: '0',
    justificacion: '',
  })

  const cargarTodo = useCallback(async (per = periodo) => {
    setError('')
    setCargando(true)
    const { anio, mes } = descomponerPeriodo(per)
    try {
      const [rBanco, rF29, rCom] = await Promise.all([
        api(`/hotel/contabilidad/cartolas?periodo=${encodeURIComponent(per)}`),
        api(`/hotel/contabilidad/tributario?anio=${anio}&mes=${mes}`),
        api('/hotel/contabilidad/comisiones-medios'),
      ])
      if (rBanco.estado === 403 || rF29.estado === 403) {
        setPanelBanco(null)
        setF29(null)
        return
      }
      if (rBanco.estado < 400) setPanelBanco(rBanco.datos)
      else setError(mensajeDeError(rBanco.datos, rBanco.estado))
      if (rF29.estado < 400) setF29(rF29.datos)
      if (rCom.estado < 400) {
        const mapa = rCom.datos.comisiones || {}
        setComisiones(Object.entries(mapa).map(([medio, cfg]) => ({ medio, ...cfg })))
      }
    } catch {
      setError('No se pudo cargar la conciliación bancaria ni el borrador tributario.')
    } finally {
      setCargando(false)
    }
  }, [periodo])

  useEffect(() => { cargarTodo(periodo) }, [cargarTodo, periodo])

  async function previsualizarCartola() {
    setError('')
    setAviso('')
    if (!csvTexto.trim()) { setError('Pega las filas CSV de la cartola antes de previsualizar.'); return }
    try {
      const r = await api('/hotel/contabilidad/cartolas/vista-previa', {
        metodo: 'POST',
        cuerpo: { contenido_csv: csvTexto },
      })
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
      setPrevisualizacion(r.datos)
      setAviso(
        `Vista previa lista: ${plural(r.datos.filas_validas, 'fila válida')}, ${plural(r.datos.filas_rechazadas, 'fila rechazada')}.`,
      )
    } catch {
      setError('No se pudo previsualizar la cartola bancaria.')
    }
  }

  async function importarCartola(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    if (!csvTexto.trim()) { setError('Pega las filas CSV de la cartola antes de importar.'); return }
    try {
      const r = await api('/hotel/contabilidad/cartolas', {
        metodo: 'POST',
        claveIdempotencia: `crt-${periodo}-${crypto.randomUUID().slice(0, 8)}`,
        cuerpo: {
          banco: banco.trim(),
          cuenta: cuenta.trim(),
          periodo,
          contenido_csv: csvTexto,
        },
      })
      if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); return }
      setPrevisualizacion(null)
      setCsvTexto('')
      setAviso(
        `Cartola importada: ${plural(r.datos.filas_importadas, 'movimiento')}, ${plural(r.datos.conciliados_automaticamente, 'cruce automático')}.`,
      )
      await cargarTodo(periodo)
    } catch {
      setError('No se pudo importar la cartola bancaria.')
    }
  }

  async function emparejarManual(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    if (!manual.cartola_movimiento_id || !manual.caja_movimiento_id) {
      setError('Selecciona una línea de cartola y un movimiento interno.')
      return
    }
    if (manual.justificacion.trim().length < 10) {
      setError('Explica el motivo del emparejamiento manual (mínimo 10 caracteres).')
      return
    }
    try {
      const r = await api('/hotel/contabilidad/conciliacion-bancaria/emparejar', {
        metodo: 'POST',
        claveIdempotencia: `emp-${crypto.randomUUID().slice(0, 8)}`,
        cuerpo: {
          cartola_movimiento_id: manual.cartola_movimiento_id,
          caja_movimiento_id: manual.caja_movimiento_id,
          monto_asignado_clp: Number(manual.monto_asignado_clp),
          comision_clp: Number(manual.comision_clp || 0),
          justificacion: manual.justificacion.trim(),
        },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso(`Emparejamiento manual registrado por ${clp(r.datos.monto_asignado_clp)}.`)
        setManual({
          cartola_movimiento_id: '',
          caja_movimiento_id: '',
          monto_asignado_clp: '',
          comision_clp: '0',
          justificacion: '',
        })
        await cargarTodo(periodo)
      }
    } catch {
      setError('No se pudo registrar el emparejamiento manual.')
    }
  }

  async function guardarComisiones() {
    setError('')
    setAviso('')
    try {
      const r = await api('/hotel/contabilidad/comisiones-medios', {
        metodo: 'PUT',
        claveIdempotencia: `com-${crypto.randomUUID().slice(0, 8)}`,
        cuerpo: {
          medios: comisiones.map((c) => ({
            medio: c.medio,
            proveedor: c.proveedor || 'general',
            porcentaje_comision: Number(c.porcentaje_comision),
            iva_comision: Boolean(c.iva_comision),
            dias_habiles_abono: Number(c.dias_habiles_abono),
          })),
        },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso('Comisiones y días hábiles de abono actualizados.')
        await cargarTodo(periodo)
      }
    } catch {
      setError('No se pudieron guardar las comisiones.')
    }
  }

  const { anio, mes } = descomponerPeriodo(periodo)

  return (
    <>
      <section className="tarjeta" aria-label="Conciliación bancaria y borrador tributario">
        <h2>Conciliación bancaria y borrador tributario (F29)</h2>
        <form className="formulario" onSubmit={(e) => { e.preventDefault(); cargarTodo(periodo) }}>
          <Campo etiqueta="Periodo (AAAA-MM)" type="month" value={periodo} onChange={(e) => setPeriodo(e.target.value)} />
          <button type="submit" className="boton-secundario" disabled={cargando}>
            {cargando ? 'Cargando…' : 'Consultar periodo'}
          </button>
          <a
            className="boton-secundario"
            href={`/api/hotel/contabilidad/tributario/exportar.csv?anio=${anio}&mes=${mes}`}
          >
            Exportar borrador F29 (CSV)
          </a>
        </form>
        {error && <p role="alert" className="alerta">{error}</p>}
        {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      </section>

      {f29 && (
        <section className="tarjeta" aria-label="Borrador tributario F29">
          <h3>Borrador tributario F29 — {f29.periodo}</h3>
          <p className="nota-clave">{f29.nota_legal}</p>
          <div className="kpi-rejilla">
            <div className="kpi">
              <span className="kpi-titulo">Ventas tributarias</span>
              <span className="kpi-valor">{clp(f29.borrador_f29.ventas_tributarias_total_clp)}</span>
              <span className="kpi-detalle">
                Neto {clp(f29.borrador_f29.ventas_tributarias_neto_clp)} · Débito IVA {clp(f29.borrador_f29.debito_fiscal_clp)}
              </span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">Crédito fiscal (compras)</span>
              <span className="kpi-valor">{clp(f29.compras_credito_fiscal.credito_fiscal_neto_clp)}</span>
              <span className="kpi-detalle">
                {plural(f29.compras_credito_fiscal.facturas_cantidad, 'factura')} · {plural(f29.compras_credito_fiscal.notas_credito_cantidad, 'nota de crédito')}
              </span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">IVA determinado estimado</span>
              <span className="kpi-valor">{clp(f29.borrador_f29.iva_determinado_clp)}</span>
              <span className="kpi-detalle">Débito fiscal menos crédito fiscal</span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">Ventas tarjeta en tránsito</span>
              <span className="kpi-valor">{clp(f29.borrador_f29.ventas_en_transito_total_clp)}</span>
              <span className="kpi-detalle">{plural(f29.ventas_en_transito.length, 'venta')} en IVA de este mes</span>
            </div>
          </div>

          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Resumen de ventas por documento tributario">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Tipo de documento</th>
                  <th>Documentos</th>
                  <th>Neto</th>
                  <th>IVA</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(f29.por_documento || {}).map(([doc, v]) => (
                  <tr key={doc}>
                    <td>{doc}</td>
                    <td>{v.cantidad}</td>
                    <td>{clp(v.neto_clp)}</td>
                    <td>{clp(v.iva_clp)}</td>
                    <td><strong>{clp(v.total_clp)}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {panelBanco && (
        <section className="tarjeta" aria-label="Conciliación bancaria del periodo">
          <h3>Conciliación bancaria — {panelBanco.periodo || periodo}</h3>
          <div className="kpi-rejilla">
            <div className="kpi">
              <span className="kpi-titulo">Líneas cartola conciliadas</span>
              <span className="kpi-valor">{panelBanco.resumen.conciliados}</span>
              <span className="kpi-detalle">
                {plural(panelBanco.resumen.parciales, 'parcial', 'parciales')} · {plural(panelBanco.resumen.pendientes_cartola, 'pendiente')}
              </span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">Cobros en tránsito</span>
              <span className="kpi-valor">{clp(panelBanco.resumen.en_transito_clp)}</span>
              <span className="kpi-detalle">{plural(panelBanco.resumen.en_transito_cantidad, 'movimiento')} por abonar en banco</span>
            </div>
            <div className="kpi">
              <span className="kpi-titulo">Movimientos internos pendientes</span>
              <span className="kpi-valor">{panelBanco.internos_pendientes.length}</span>
              <span className="kpi-detalle">Disponibles para cruce</span>
            </div>
          </div>

          <h4>Importar cartola bancaria (CSV)</h4>
          <form className="formulario" onSubmit={importarCartola}>
            <Campo etiqueta="Banco" value={banco} onChange={(e) => setBanco(e.target.value)} />
            <Campo etiqueta="Cuenta" value={cuenta} onChange={(e) => setCuenta(e.target.value)} />
            <label className="campo">
              <span>Contenido CSV (Fecha;Descripcion;Referencia;Monto)</span>
              <textarea
                rows={4}
                value={csvTexto}
                onChange={(e) => setCsvTexto(e.target.value)}
                placeholder="Fecha;Descripcion;Referencia;Monto&#10;2026-11-23;ABONO TRANSBANK;TBK-001;98000"
              />
            </label>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="button" className="boton-secundario" onClick={previsualizarCartola}>
                Vista previa
              </button>
              <button type="submit" className="boton-primario">
                Importar y conciliar
              </button>
            </div>
          </form>

          {previsualizacion && (
            <p className="nota-clave">
              Vista previa: {plural(previsualizacion.filas_validas, 'fila válida')} · {plural(previsualizacion.filas_rechazadas, 'fila rechazada')}
              {previsualizacion.duplicada ? ' · Cartola ya importada anteriormente.' : '.'}
            </p>
          )}

          {panelBanco.movimientos_cartola.length > 0 && (
            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Movimientos de cartola bancaria">
              <table className="tabla">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Descripción</th>
                    <th>Referencia</th>
                    <th>Monto</th>
                    <th>Pendiente</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {panelBanco.movimientos_cartola.map((l) => (
                    <tr key={l.cartola_movimiento_id}>
                      <td>{fechaATexto(l.fecha_movimiento)}</td>
                      <td>{l.descripcion}</td>
                      <td>{l.referencia || '—'}</td>
                      <td>{clp(l.monto_clp)}</td>
                      <td>{clp(l.pendiente_clp)}</td>
                      <td>{ETIQUETA_ESTADO_LINEA[l.estado] || l.estado}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h4>Conciliación manual asistida</h4>
          <form className="formulario" onSubmit={emparejarManual}>
            <CampoSelect
              etiqueta="Línea de cartola pendiente"
              value={manual.cartola_movimiento_id}
              onChange={(e) => setManual({ ...manual, cartola_movimiento_id: e.target.value })}
            >
              <option value="">Selecciona una línea…</option>
              {panelBanco.movimientos_cartola
                .filter((l) => l.pendiente_clp > 0)
                .map((l) => (
                  <option key={l.cartola_movimiento_id} value={l.cartola_movimiento_id}>
                    {l.fecha_movimiento} · {l.descripcion} ({clp(l.pendiente_clp)})
                  </option>
                ))}
            </CampoSelect>
            <CampoSelect
              etiqueta="Movimiento interno pendiente"
              value={manual.caja_movimiento_id}
              onChange={(e) => setManual({ ...manual, caja_movimiento_id: e.target.value })}
            >
              <option value="">Selecciona un movimiento…</option>
              {panelBanco.internos_pendientes.map((m) => (
                <option key={m.caja_movimiento_id} value={m.caja_movimiento_id}>
                  {m.fecha_contable} · {nombreMedio(m.medio)} ({clp(m.pendiente_clp)})
                </option>
              ))}
            </CampoSelect>
            <Campo
              etiqueta="Monto asignado (CLP)"
              type="number"
              min="1"
              value={manual.monto_asignado_clp}
              onChange={(e) => setManual({ ...manual, monto_asignado_clp: e.target.value })}
            />
            <Campo
              etiqueta="Comisión (CLP)"
              type="number"
              min="0"
              value={manual.comision_clp}
              onChange={(e) => setManual({ ...manual, comision_clp: e.target.value })}
            />
            <Campo
              etiqueta="Justificación (mínimo 10 caracteres)"
              value={manual.justificacion}
              onChange={(e) => setManual({ ...manual, justificacion: e.target.value })}
            />
            <button type="submit" className="boton-secundario">Registrar emparejamiento manual</button>
          </form>

          {esAdmin && comisiones.length > 0 && (
            <>
              <h4>Comisiones y días hábiles de abono por medio de pago</h4>
              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Tabla de comisiones bancarias por medio">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th>Medio</th>
                      <th>Comisión (%)</th>
                      <th>Días hábiles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comisiones.map((c, idx) => (
                      <tr key={c.medio}>
                        <td>{nombreMedio(c.medio)}</td>
                        <td>
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="25"
                            aria-label={`Porcentaje comisión ${nombreMedio(c.medio)}`}
                            value={c.porcentaje_comision}
                            onChange={(e) => {
                              const copia = [...comisiones]
                              copia[idx] = { ...c, porcentaje_comision: e.target.value }
                              setComisiones(copia)
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            min="0"
                            max="30"
                            aria-label={`Días hábiles abono ${nombreMedio(c.medio)}`}
                            value={c.dias_habiles_abono}
                            onChange={(e) => {
                              const copia = [...comisiones]
                              copia[idx] = { ...c, dias_habiles_abono: e.target.value }
                              setComisiones(copia)
                            }}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button type="button" className="boton-secundario" style={{ marginTop: '0.5rem' }} onClick={guardarComisiones}>
                Guardar comisiones
              </button>
            </>
          )}
        </section>
      )}
    </>
  )
}
