'use client'

// Fase 1 contable (2026-11-19): pestañas de Caja y pagos — Turno (apertura,
// retiros para depósito, arqueo y cierre), Movimientos / Depósitos (diario de
// caja, reverso por la administración) y Cierre diario (conciliación del día).

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { api, alRechazar, clp, mensajeDeError, Campo, CampoSelect, useClaveOperacion } from '../../../lib/api'
import { fechaATexto, fechaHora, plural } from '../../../lib/formato'
import {
  MEDIOS, arqueoParaApi, nombreDocumento, nombreMedio, nombreMovimiento, textoDiferencia, totalArqueo,
} from '../../../lib/caja'
import css from './operacion.module.css'
import cc from './caja.module.css'
import ContableMensual from './contable-mensual'
import { BarraContextual, SelectorFila } from './barra-contextual'

const SIN_CONEXION = 'No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.'

export function hoyChile() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Santiago' }).format(new Date())
}

function useOperacion(alTerminar) {
  const [clave, renovar] = useClaveOperacion()
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')
  async function enviar(ruta, cuerpo) {
    if (enviando) return null
    setError('')
    setEnviando(true)
    try {
      const r = await api(ruta, { metodo: 'POST', cuerpo, claveIdempotencia: clave })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        alRechazar(r.estado, renovar)
        return null
      }
      renovar()
      alTerminar?.(r.datos)
      return r.datos
    } catch {
      setError(SIN_CONEXION)
      return null
    } finally {
      setEnviando(false)
    }
  }
  return { enviar, enviando, error, setError }
}

function Mensaje({ error, ok }) {
  return (
    <>
      {error && <p role="alert" className="alerta">{error}</p>}
      {ok && <p role="status" className="aviso-ok">{ok}</p>}
    </>
  )
}

function TablaPorMedio({ porMedio, retiros, egresos, titulo = 'Cobrado en el turno' }) {
  return (
    <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Totales por medio de pago">
      <table className="tabla">
        <thead><tr><th>Medio</th><th>{titulo}</th></tr></thead>
        <tbody>
          {[...MEDIOS.map(([m]) => m), 'no_informado'].filter((m) => m !== 'no_informado' || porMedio?.[m]).map((m) => (
            <tr key={m}><td>{nombreMedio(m)}</td><td>{clp(porMedio?.[m] || 0)}</td></tr>
          ))}
          {egresos > 0 && <tr><td>Egresos operacionales pagados desde caja</td><td>{clp(-egresos)}</td></tr>}
          {retiros !== undefined && <tr><td>Retiros para depósito bancario (efectivo en tránsito)</td><td>{clp(-retiros)}</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

/* ------------------------------- Turno -------------------------------- */

export function PestanaTurno({ esAdmin }) {
  const [estado, setEstado] = useState(null)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')

  const cargar = useCallback(async () => {
    setError('')
    try {
      const r = await api('/hotel/caja/estado')
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setEstado(r.datos)
    } catch { setError(SIN_CONEXION) }
  }, [])
  useEffect(() => { cargar() }, [cargar])

  if (!estado) return <><Mensaje error={error} />{!error && <p className="estado" aria-busy="true">Cargando la caja…</p>}</>
  const { turno, parametros } = estado
  return (
    <>
      <Mensaje error={error} ok={ok} />
      {turno
        ? <TurnoAbierto turno={turno} parametros={parametros} esAdmin={esAdmin}
            alCambiar={(texto) => { setOk(texto); cargar() }} />
        : <AperturaTurno estado={estado} alAbrir={(t) => { setOk(`Turno abierto con fondo de ${clp(t.fondo_inicial_clp)}.`); cargar() }} />}
    </>
  )
}

function AperturaTurno({ estado, alAbrir }) {
  const pendiente = estado.entrega_pendiente
  const sugerido = pendiente ? pendiente.monto_clp : estado.parametros.fondo_fijo_clp
  const [fondo, setFondo] = useState(String(sugerido ?? 0))
  const [nota, setNota] = useState('')
  const op = useOperacion(alAbrir)
  const difiere = pendiente && Number(fondo) !== pendiente.monto_clp
  return (
    <section className="tarjeta">
      <h2>Abrir turno de caja</h2>
      <p className="nota-clave">
        La caja está cerrada. Para recibir efectivo, abre tu turno contando el dinero con que partes (fondo inicial).
        Fecha contable: <strong>{fechaATexto(estado.fecha_contable)}</strong>.
      </p>
      {pendiente && (
        <p className="estado" data-entrega>
          {pendiente.usuario_nombre} cerró su turno el {fechaHora(pendiente.cerrado_en)} y dejó <strong>{clp(pendiente.monto_clp)}</strong> en caja.
          Cuenta el efectivo al recibirlo.
        </p>
      )}
      <form className="formulario" onSubmit={(e) => {
        e.preventDefault()
        if (!(Number(fondo) >= 0) || fondo === '') { op.setError('Indica el fondo inicial en pesos (puede ser $0).'); return }
        op.enviar('/hotel/caja/turnos', { fondo_inicial_clp: Number(fondo), nota: nota.trim() || null })
      }}>
        <Campo etiqueta="Fondo inicial contado (CLP)" type="number" min="0" inputMode="numeric" value={fondo}
          onChange={(e) => setFondo(e.target.value)} />
        <Campo etiqueta={difiere ? 'Explica la diferencia con lo entregado (obligatorio)' : 'Nota (opcional)'}
          value={nota} onChange={(e) => setNota(e.target.value)} maxLength={500} />
        <button type="submit" className="boton-primario" disabled={op.enviando}>{op.enviando ? 'Abriendo…' : 'Abrir turno'}</button>
      </form>
      <Mensaje error={op.error} />
    </section>
  )
}

function TurnoAbierto({ turno, parametros, esAdmin, alCambiar }) {
  const t = turno.totales
  const [modo, setModo] = useState('')
  return (
    <>
      <section className="tarjeta" data-turno-abierto>
        <h2>Turno abierto</h2>
        <p className="resumen">
          {turno.usuario_nombre} · desde {fechaHora(turno.abierto_en)} · fecha contable {fechaATexto(turno.fecha_contable)}
        </p>
        <dl className={css.cifras}>
          <div className={css.cifra}><dt>Fondo inicial</dt><dd>{clp(turno.fondo_inicial_clp)}</dd></div>
          <div className={css.cifra}><dt>Cobros del turno</dt><dd>{plural(t.cobros, 'cobro')} · {clp(t.total_cobrado_clp)}</dd></div>
          <div className={css.cifra}><dt>Efectivo que debería haber en caja</dt><dd><strong>{clp(t.efectivo_esperado_clp)}</strong></dd></div>
        </dl>
        {t.recibido_sin_turno_clp > 0 && (
          <p className="estado" role="status" data-sin-turno>
            Incluye <strong>{clp(t.recibido_sin_turno_clp)}</strong> cobrados con la caja cerrada, antes de abrir este turno.
          </p>
        )}
        <TablaPorMedio porMedio={t.por_medio} retiros={t.retiros_deposito_clp} egresos={t.egresos_caja_clp} />
        <div className={css.acciones}>
          <Link className="boton-secundario" href="/hotel/pago">Registrar pago</Link>
          <button type="button" className="boton-secundario" onClick={() => setModo(modo === 'retiro' ? '' : 'retiro')}>
            Retirar efectivo para depósito
          </button>
          <button type="button" className="boton-primario" onClick={() => setModo(modo === 'cierre' ? '' : 'cierre')}>
            Cerrar turno (arqueo)
          </button>
        </div>
      </section>
      {modo === 'retiro' && <RetiroDeposito turno={turno} parametros={parametros}
        alTerminar={(r) => { setModo(''); alCambiar(`Retiro de ${clp(r.monto_clp)} registrado (comprobante ${r.comprobante}). Quedan ${clp(r.efectivo_en_caja_clp)} en caja.`) }} />}
      {modo === 'cierre' && <CierreTurno turno={turno} parametros={parametros} esAdmin={esAdmin}
        alTerminar={(c) => { setModo(''); alCambiar(`Turno cerrado. Efectivo: ${textoDiferencia(c.diferencia_clp).toLowerCase()}. Quedan ${clp(c.entrega_siguiente_clp)} para el turno siguiente.`) }} />}
    </>
  )
}

function RetiroDeposito({ turno, parametros, alTerminar }) {
  const [monto, setMonto] = useState('')
  const [comprobante, setComprobante] = useState('')
  const [banco, setBanco] = useState(parametros.banco_deposito || '')
  const [nota, setNota] = useState('')
  const op = useOperacion(alTerminar)
  return (
    <section className="tarjeta">
      <h2>Retiro de efectivo para depósito en el banco</h2>
      <p className="nota-clave">El efectivo sale de la caja y queda «en tránsito» hasta que aparece en la cartola del banco.</p>
      <form className="formulario" onSubmit={(e) => {
        e.preventDefault()
        if (!(Number(monto) > 0)) { op.setError('Indica el monto retirado (mayor que $0).'); return }
        if (!comprobante.trim()) { op.setError('Anota el número de comprobante del depósito.'); return }
        op.enviar(`/hotel/caja/turnos/${encodeURIComponent(turno.turno_id)}/retiros`, {
          monto_clp: Number(monto), comprobante: comprobante.trim(), banco: banco.trim() || null, nota: nota.trim() || null,
        })
      }}>
        <Campo etiqueta="Monto (CLP)" type="number" min="1" inputMode="numeric" value={monto} onChange={(e) => setMonto(e.target.value)} />
        <Campo etiqueta="N° de comprobante del depósito" value={comprobante} onChange={(e) => setComprobante(e.target.value)} maxLength={60} />
        <Campo etiqueta="Banco y cuenta" value={banco} onChange={(e) => setBanco(e.target.value)} maxLength={120} />
        <Campo etiqueta="Nota (opcional)" value={nota} onChange={(e) => setNota(e.target.value)} maxLength={500} />
        <button type="submit" className="boton-primario" disabled={op.enviando}>{op.enviando ? 'Registrando…' : 'Registrar retiro'}</button>
      </form>
      <Mensaje error={op.error} />
    </section>
  )
}

function CierreTurno({ turno, parametros, alTerminar }) {
  const t = turno.totales
  const [conteo, setConteo] = useState({})
  const [declarado, setDeclarado] = useState({
    debito: String(t.por_medio.debito || 0), credito: String(t.por_medio.credito || 0),
    transferencia: String(t.por_medio.transferencia || 0),
  })
  const [justificacion, setJustificacion] = useState('')
  const [deposito, setDeposito] = useState('')
  const [comprobante, setComprobante] = useState('')
  const op = useOperacion(alTerminar)
  const contado = totalArqueo(conteo)
  const difEfectivo = contado - t.efectivo_esperado_clp
  const difs = ['debito', 'credito', 'transferencia'].map((m) => (Number(declarado[m]) || 0) - (t.por_medio[m] || 0))
  const hayDiferencia = difEfectivo !== 0 || difs.some((d) => d !== 0)
  return (
    <section className="tarjeta">
      <h2>Cierre de turno: arqueo y cuadratura</h2>
      <p className="nota-clave">Cuenta los billetes y monedas. Para tarjetas, usa el total del cierre de lote del POS (Transbank).</p>
      <form className="formulario" onSubmit={(e) => {
        e.preventDefault()
        if (hayDiferencia && justificacion.trim().length < 10) {
          op.setError('Hay diferencias: explica la causa (mínimo 10 caracteres).')
          return
        }
        const dep = Number(deposito) || 0
        if (dep > 0 && !comprobante.trim()) { op.setError('Anota el comprobante del depósito al cierre.'); return }
        op.enviar(`/hotel/caja/turnos/${encodeURIComponent(turno.turno_id)}/cierre`, {
          arqueo: arqueoParaApi(conteo),
          declarado: Object.fromEntries(Object.entries(declarado).map(([k, v]) => [k, Number(v) || 0])),
          justificacion: justificacion.trim() || null,
          deposito: dep > 0 ? { monto_clp: dep, comprobante: comprobante.trim(), banco: parametros.banco_deposito || null } : null,
        })
      }}>
        <fieldset className={cc.grupo}>
          <legend>Arqueo de efectivo</legend>
          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Conteo por denominación">
            <table className="tabla">
              <thead><tr><th>Denominación</th><th>Cantidad</th><th>Subtotal</th></tr></thead>
              <tbody>
                {parametros.denominaciones.map((d) => (
                  <tr key={d}>
                    <td>{clp(d)}</td>
                    <td>
                      <input className={`entrada ${cc.entradaCorta}`} type="number" min="0" inputMode="numeric"
                        aria-label={`Cantidad de ${clp(d)}`} value={conteo[d] ?? ''}
                        onChange={(e) => setConteo({ ...conteo, [d]: e.target.value })} />
                    </td>
                    <td>{clp(d * (Number(conteo[d]) || 0))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="resumen" data-arqueo>
            Contado: <strong>{clp(contado)}</strong> · Esperado: {clp(t.efectivo_esperado_clp)} ·{' '}
            <strong className={difEfectivo === 0 ? undefined : cc.textoAlerta}>{textoDiferencia(difEfectivo)}</strong>
          </p>
        </fieldset>
        <fieldset className={cc.grupo}>
          <legend>Cuadratura de tarjetas y transferencias</legend>
          {['debito', 'credito', 'transferencia'].map((m, i) => (
            <Campo key={m} etiqueta={`${nombreMedio(m)}: según POS / banco (sistema ${clp(t.por_medio[m] || 0)})${difs[i] ? ` · ${textoDiferencia(difs[i])}` : ''}`}
              type="number" min="0" inputMode="numeric" value={declarado[m]}
              onChange={(e) => setDeclarado({ ...declarado, [m]: e.target.value })} />
          ))}
        </fieldset>
        <Campo etiqueta={hayDiferencia ? 'Justificación de la diferencia (obligatoria)' : 'Observaciones (opcional)'}
          value={justificacion} onChange={(e) => setJustificacion(e.target.value)} maxLength={1000} />
        <Campo etiqueta="Efectivo que sale al banco al cerrar (opcional, CLP)" type="number" min="0" inputMode="numeric"
          value={deposito} onChange={(e) => setDeposito(e.target.value)} />
        {Number(deposito) > 0 && (
          <Campo etiqueta="N° de comprobante del depósito" value={comprobante} onChange={(e) => setComprobante(e.target.value)} maxLength={60} />
        )}
        <p className="estado">Queda para el turno siguiente: <strong>{clp(Math.max(contado - (Number(deposito) || 0), 0))}</strong></p>
        <button type="submit" className="boton-primario" disabled={op.enviando}>{op.enviando ? 'Cerrando…' : 'Cerrar turno'}</button>
      </form>
      <Mensaje error={op.error} />
    </section>
  )
}

/* -------------------------- Movimientos / Depósitos ------------------------ */

export function PestanaMovimientos({ esAdmin, soloDepositos = false }) {
  const [desde, setDesde] = useState(hoyChile)
  const [hasta, setHasta] = useState(hoyChile)
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [seleccionadoId, setSeleccionadoId] = useState(null)
  const [reversando, setReversando] = useState(null)

  const cargar = useCallback(async (d = desde, h = hasta) => {
    setError('')
    try {
      const q = new URLSearchParams({ desde: d, hasta: h })
      if (soloDepositos) q.set('medio', 'efectivo')
      const r = await api(`/hotel/caja/movimientos?${q}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setDatos(r.datos)
    } catch { setError(SIN_CONEXION) }
  }, [desde, hasta, soloDepositos])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { cargar() }, [soloDepositos])

  const filas = (datos?.movimientos || []).filter((m) => !soloDepositos || m.tipo === 'retiro_deposito')
  const total = filas.reduce((s, m) => s + m.monto_clp, 0)
  const activo = filas.find((m) => m.movimiento_id === seleccionadoId) || null
  const puedeReversarActivo = Boolean(esAdmin && !soloDepositos && activo && activo.tipo === 'cobro' && activo.pago_id)
  return (
    <>
      <section className="tarjeta">
        <form className={`formulario ${cc.linea}`} onSubmit={(e) => { e.preventDefault(); cargar() }}>
          <Campo etiqueta="Desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
          <Campo etiqueta="Hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} />
          <button type="submit" className="boton-secundario">Ver</button>
        </form>
        {soloDepositos && (
          <p className="nota-clave">Efectivo retirado de la caja para depositar en el banco, con su comprobante. En la fase siguiente se cruza con la cartola.</p>
        )}
      </section>
      <Mensaje error={error} ok={ok} />
      {datos && (filas.length === 0
        ? <p className="estado estado-vacio">{soloDepositos ? 'Sin depósitos en estas fechas.' : 'Sin movimientos en estas fechas.'}</p>
        : (
          <>
            <p className="resumen">{plural(filas.length, 'movimiento')} · {soloDepositos ? 'Total retirado para banco (en tránsito)' : 'Flujo del periodo'}: <strong>{clp(soloDepositos ? -total : total)}</strong></p>
            {esAdmin && !soloDepositos && (
              <BarraContextual
                titulo="Acciones de movimiento de caja"
                seleccionado={Boolean(activo)}
                resumen={activo ? `${nombreMovimiento(activo.tipo)} · ${clp(activo.monto_clp)} · ${nombreMedio(activo.medio)}` : ''}
                detalle={activo ? (puedeReversarActivo ? `Pago de ${activo.huesped_nombre || 'huésped'} (${activo.habitacion_id || 'sin hab.'})` : 'Este tipo de movimiento no admite reverso de pago') : ''}
                placeholder="Selecciona un cobro de la tabla si necesitas registrar un reverso contable."
                alLimpiar={() => setSeleccionadoId(null)}
              >
                {puedeReversarActivo && (
                  <button type="button" className="boton-secundario boton-peligro" onClick={() => setReversando(activo)}>
                    Reversar pago
                  </button>
                )}
              </BarraContextual>
            )}
            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Movimientos de caja (desliza para ver todas las columnas)">
              <table className="tabla">
                <thead>
                  <tr>
                    {esAdmin && !soloDepositos && <th className="celda-selector"><span className="sr-only">Elegir</span></th>}
                    <th>Fecha</th><th>Hora</th><th>Movimiento</th><th>Medio</th><th>Monto</th>
                    {soloDepositos ? <><th>Comprobante</th><th>Banco</th></> : <><th>Huésped</th><th>Hab.</th><th>Documento</th></>}
                    <th>Registró</th>
                  </tr>
                </thead>
                <tbody>
                  {filas.map((m) => {
                    const elegida = activo?.movimiento_id === m.movimiento_id
                    return (
                      <tr
                        key={m.movimiento_id}
                        className={esAdmin && !soloDepositos ? 'fila-seleccionable' : undefined}
                        data-seleccionada={elegida ? 'true' : 'false'}
                        onClick={esAdmin && !soloDepositos ? () => setSeleccionadoId(m.movimiento_id) : undefined}
                      >
                        {esAdmin && !soloDepositos && (
                          <td className="celda-selector">
                            <SelectorFila
                              nombreGrupo="mov-caja-activo"
                              elegido={elegida}
                              etiqueta={`Seleccionar movimiento ${m.movimiento_id}`}
                              alElegir={() => setSeleccionadoId(m.movimiento_id)}
                            />
                          </td>
                        )}
                        <td className="celda-fecha">{fechaATexto(m.fecha_contable)}</td>
                        <td>{fechaHora(m.registrado_en).slice(11)}</td>
                        <td>{nombreMovimiento(m.tipo)}{m.es_anticipo ? ' (anticipo)' : ''}</td>
                        <td>{nombreMedio(m.medio)}{m.tarjeta_ultimos4 ? ` ····${m.tarjeta_ultimos4}` : ''}</td>
                        <td>{clp(soloDepositos ? -m.monto_clp : m.monto_clp)}</td>
                        {soloDepositos
                          ? <><td>{m.comprobante || '—'}</td><td>{m.banco || '—'}</td></>
                          : <>
                            <td>{m.huesped_nombre || m.nota || '—'}</td>
                            <td>{m.habitacion_id || '—'}</td>
                            <td>{m.pago_id ? nombreDocumento(m.documento_tipo) : '—'}</td>
                          </>}
                        <td>{m.actor}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        ))}
      {reversando && (
        <ReversoPago movimiento={reversando} alCancelar={() => setReversando(null)}
          alTerminar={(r) => { setReversando(null); setOk(`Pago reversado: ${clp(r.monto_clp)}. Saldo de la reserva: ${clp(r.saldo_clp)}.`); cargar() }} />
      )}
    </>
  )
}

function ReversoPago({ movimiento, alCancelar, alTerminar }) {
  const [motivo, setMotivo] = useState('')
  const op = useOperacion(alTerminar)
  return (
    <section className="tarjeta" aria-label="Reversar pago">
      <h2>Reversar pago de {clp(movimiento.monto_clp)}</h2>
      <p className="nota-clave">
        El pago original no se borra: se registra un reverso por el mismo monto y medio en el día contable abierto.
        {movimiento.medio === 'efectivo' && ' El efectivo devuelto sale del turno abierto.'}
        {(movimiento.medio === 'debito' || movimiento.medio === 'credito') && ' Anula también la venta en el POS.'}
      </p>
      <form className="formulario" onSubmit={(e) => {
        e.preventDefault()
        if (motivo.trim().length < 10) { op.setError('Explica el motivo (mínimo 10 caracteres).'); return }
        op.enviar(`/hotel/reservas/${encodeURIComponent(movimiento.reserva_id)}/pagos/${encodeURIComponent(movimiento.pago_id)}/reverso`, { motivo: motivo.trim() })
      }}>
        <Campo etiqueta="Motivo del reverso" value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={300} />
        <div className={css.acciones}>
          <button type="submit" className="boton-primario" disabled={op.enviando}>Confirmar reverso</button>
          <button type="button" className="boton-secundario" onClick={alCancelar}>Cancelar</button>
        </div>
      </form>
      <Mensaje error={op.error} />
    </section>
  )
}

/* ------------------------------ Cierre diario ------------------------------ */

const ESTADO_HAB = {
  libre: 'Libre', fuera_de_servicio: 'Fuera de servicio', sin_llegada: 'Sin Llegada (posible no-show)',
  pagada: 'Pagada', abonada: 'Con abono, saldo pendiente', pendiente: 'Sin pagos',
}

export function PestanaCierreDiario({ esAdmin }) {
  const [fecha, setFecha] = useState(hoyChile)
  const [datos, setDatos] = useState(null)
  const [historial, setHistorial] = useState(null)
  const [error, setError] = useState('')
  const [ok, setOk] = useState('')
  const [nota, setNota] = useState('')
  const [confirma, setConfirma] = useState(false)
  const [motivo, setMotivo] = useState('')

  const cargar = useCallback(async (dia = fecha) => {
    setError('')
    try {
      const [c, h] = await Promise.all([api(`/hotel/caja/conciliacion?fecha=${dia}`), api('/hotel/caja/cierres')])
      if (c.estado >= 400) { setError(mensajeDeError(c.datos, c.estado)); setDatos(null) } else setDatos(c.datos)
      if (h.estado < 400) setHistorial(h.datos)
    } catch { setError(SIN_CONEXION) }
  }, [fecha])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { cargar() }, [])

  const cierre = useOperacion((r) => { setOk(`Día ${fechaATexto(r.fecha)} cerrado. Lo que se registre desde ahora queda con fecha ${fechaATexto(r.siguiente_fecha_contable)}.`); setConfirma(false); cargar() })
  const reapertura = useOperacion((r) => { setOk(`Día ${fechaATexto(r.fecha)} reabierto.`); setMotivo(''); cargar() })
  const cerrado = datos?.cierre?.estado === 'cerrado'
  const r = datos?.resumen
  return (
    <>
      <section className="tarjeta">
        <form className={`formulario ${cc.linea}`} onSubmit={(e) => { e.preventDefault(); cargar(fecha) }}>
          <Campo etiqueta="Día" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} />
          <button type="submit" className="boton-secundario">Ver conciliación</button>
        </form>
        {historial && <p className="nota-clave">Fecha contable abierta: <strong>{fechaATexto(historial.fecha_contable)}</strong>.</p>}
      </section>
      <Mensaje error={error || cierre.error || reapertura.error} ok={ok} />
      {datos && (
        <>
          <section className="tarjeta" data-conciliacion>
            <h2>Conciliación del {fechaATexto(datos.fecha)} {cerrado && <span className="politica-badge">Cerrado</span>}</h2>
            {cerrado && <p className="estado">Cerrado por {datos.cierre.cerrado_por} el {fechaHora(datos.cierre.cerrado_en)}. Cifras congeladas al cierre.</p>}
            <dl className={css.cifras}>
              <div className={css.cifra}><dt>Ocupación</dt><dd>{r.habitaciones_ocupadas} de {r.habitaciones_disponibles} ({String(r.ocupacion_pct).replace('.', ',')} %)</dd></div>
              <div className={css.cifra}>
                <dt>Ingresos devengados del día (IVA incl.)</dt>
                <dd>
                  <strong>{clp(r.total_ingresos_devengados_clp ?? r.ingreso_alojamiento_clp)}</strong>
                  {' '}· neto (sin IVA) {clp(r.total_ingresos_neto_clp ?? r.ingreso_alojamiento_neto_clp)}
                  {r.total_iva_debito_clp !== undefined ? ` · IVA ${clp(r.total_iva_debito_clp)}` : ''}
                </dd>
              </div>
              <div className={css.cifra}>
                <dt>Desglose devengado</dt>
                <dd>
                  Alojamiento {clp(r.ingreso_alojamiento_clp)}
                  {r.ingreso_consumos_reserva_clp ? ` · Consumos ${clp(r.ingreso_consumos_reserva_clp)}` : ''}
                  {r.ingreso_directo_clp ? ` · Directos sin hab. ${clp(r.ingreso_directo_clp)}` : ''}
                </dd>
              </div>
              <div className={css.cifra}><dt>ADR / RevPAR (alojamiento)</dt><dd>{clp(r.adr_clp)} / {clp(r.revpar_clp)}</dd></div>
              <div className={css.cifra}><dt>Recaudado en el día (cobros)</dt><dd><strong>{clp(datos.cobros.total_clp)}</strong></dd></div>
              <div className={css.cifra}><dt>Retiros a banco (en tránsito)</dt><dd>{clp(datos.cobros.depositos_clp)}</dd></div>
              {r.egresos_operacionales_clp > 0 && (
                <div className={css.cifra}><dt>Egresos operacionales</dt><dd>{clp(r.egresos_operacionales_clp)}</dd></div>
              )}
              <div className={css.cifra}><dt>Anticipos recibidos hoy / vigentes</dt><dd>{clp(datos.cobros.anticipos_recibidos_clp)} / {clp(datos.cobros.anticipos_vigentes_clp)}</dd></div>
            </dl>
            <TablaPorMedio porMedio={datos.cobros.por_medio} egresos={datos.cobros.egresos_caja_clp} titulo="Cobrado en el día (descontando reversos)" />
            <p className="resumen">
              Documentos: {Object.entries(datos.documentos).filter(([, d]) => d.cantidad).map(([k, d]) => `${nombreDocumento(k)} ${d.cantidad} (${clp(d.monto_clp)})`).join(' · ') || 'sin pagos'}
            </p>
          </section>
          <section className="tarjeta">
            <h2>Habitaciones: ocupadas contra pagado</h2>
            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Conciliación por habitación (desliza para ver todas las columnas)">
              <table className="tabla">
                <thead><tr><th>Hab.</th><th>Estado</th><th>Huésped</th><th>Estadía</th><th>Noche</th><th>Total cuenta</th><th>Pagado</th><th>Anticipos</th><th>Saldo</th></tr></thead>
                <tbody>
                  {datos.habitaciones.map((h) => (
                    <tr key={h.habitacion_id} data-estado={h.estado}>
                      <td>{h.habitacion_id}</td>
                      <td>{ESTADO_HAB[h.estado] || h.estado}</td>
                      <td>{h.reserva_id ? <Link href={`/hotel/reservas/${h.reserva_id}`}>{h.huesped_nombre}</Link> : '—'}</td>
                      <td>{h.inicio ? `${fechaATexto(h.inicio)} → ${fechaATexto(h.fin)}` : '—'}</td>
                      <td>{h.reserva_id ? clp(h.tarifa_noche_clp) : '—'}</td>
                      <td>{h.reserva_id ? clp(h.cargos_clp) : '—'}</td>
                      <td>{h.reserva_id ? clp(h.pagado_clp) : '—'}</td>
                      <td>{h.reserva_id ? clp(h.anticipos_clp) : '—'}</td>
                      <td>{h.reserva_id ? clp(h.saldo_clp) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          {Array.isArray(datos.convenios_aplicados) && datos.convenios_aplicados.length > 0 && (
            <section className="tarjeta" aria-label="Convenios aplicados y diferencia de tarifa">
              <h2>Convenios aplicados y diferencia de tarifa</h2>
              <p className="nota-clave">
                Desglose diario de instituciones, delegaciones o eventos con tarifa especial frente a la tarifa lista.
              </p>
              <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Convenios aplicados en el cierre diario (desliza para ver todas las columnas)">
                <table className="tabla">
                  <thead>
                    <tr>
                      <th>Institución / convenio</th>
                      <th>Tipo</th>
                      <th>Reservas</th>
                      <th>Tarifa lista</th>
                      <th>Tarifa aplicada</th>
                      <th>Diferencia</th>
                    </tr>
                  </thead>
                  <tbody>
                    {datos.convenios_aplicados.map((conv) => (
                      <tr key={conv.convenio_id}>
                        <td><strong>{conv.convenio_nombre}</strong>{conv.cliente_nombre ? ` · ${conv.cliente_nombre}` : ''}</td>
                        <td>{conv.convenio_tipo}</td>
                        <td>{conv.reservas}</td>
                        <td>{clp(conv.tarifa_lista_total_clp)}</td>
                        <td>{clp(conv.tarifa_aplicada_total_clp)}</td>
                        <td><strong>{clp(conv.diferencia_convenio_clp)}</strong></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
          {datos.turnos.length > 0 && (
            <section className="tarjeta">
              <h2>Turnos del día</h2>
              <ul className="lista-simple">
                {datos.turnos.map((t) => (
                  <li key={t.turno_id}>
                    {t.usuario_nombre}: {t.estado === 'abierto' ? 'abierto' : `${textoDiferencia(t.diferencia_clp)}${t.justificacion ? ` — ${t.justificacion}` : ''}`}
                  </li>
                ))}
              </ul>
            </section>
          )}
          {datos.alertas.length > 0 && (
            <section className="tarjeta" role="region" aria-label="Alertas del día">
              <h2>Alertas</h2>
              <ul className="lista-simple">{datos.alertas.map((a) => <li key={a}>{a}</li>)}</ul>
            </section>
          )}
          {!cerrado && (
            <section className="tarjeta">
              <h2>Cerrar el día</h2>
              <p className="nota-clave">Al cerrar, las cifras quedan congeladas y lo que se registre después queda con la fecha del día siguiente. Para cerrar, todos los turnos de caja deben estar cerrados.</p>
              <form className="formulario" onSubmit={(e) => {
                e.preventDefault()
                if (datos.alertas.length && !confirma) { cierre.setError('Revisa las alertas y marca la confirmación.'); return }
                cierre.enviar('/hotel/caja/cierres', { fecha: datos.fecha, nota: nota.trim() || null, confirmar_alertas: confirma })
              }}>
                <Campo etiqueta="Nota del cierre (opcional)" value={nota} onChange={(e) => setNota(e.target.value)} maxLength={1000} />
                {datos.alertas.length > 0 && (
                  <label className="campo-check">
                    <input type="checkbox" checked={confirma} onChange={(e) => setConfirma(e.target.checked)} />
                    Revisé las {plural(datos.alertas.length, 'alerta')} y cierro igual
                  </label>
                )}
                <button type="submit" className="boton-primario" disabled={cierre.enviando}>Cerrar el día {fechaATexto(datos.fecha)}</button>
              </form>
            </section>
          )}
          {cerrado && esAdmin && (
            <section className="tarjeta">
              <h2>Reabrir el día</h2>
              <form className="formulario" onSubmit={(e) => {
                e.preventDefault()
                if (motivo.trim().length < 10) { reapertura.setError('Explica el motivo (mínimo 10 caracteres).'); return }
                reapertura.enviar(`/hotel/caja/cierres/${datos.fecha}/reapertura`, { motivo: motivo.trim() })
              }}>
                <Campo etiqueta="Motivo de la reapertura (queda en la auditoría)" value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={500} />
                <button type="submit" className="boton-secundario" disabled={reapertura.enviando}>Reabrir</button>
              </form>
            </section>
          )}
        </>
      )}
      {historial?.cierres?.length > 0 && (
        <section className="tarjeta">
          <h2>Últimos cierres</h2>
          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Cierres diarios">
            <table className="tabla">
              <thead><tr><th>Día</th><th>Estado</th><th>Ocupación</th><th>Cobrado</th><th>Alertas</th><th>Cerró</th></tr></thead>
              <tbody>
                {historial.cierres.map((c) => (
                  <tr key={c.fecha}>
                    <td><button type="button" className="enlace" onClick={() => { setFecha(c.fecha); cargar(c.fecha) }}>{fechaATexto(c.fecha)}</button></td>
                    <td>{c.estado === 'cerrado' ? 'Cerrado' : 'Reabierto'}</td>
                    <td>{c.resumen ? `${String(c.resumen.ocupacion_pct).replace('.', ',')} %` : '—'}</td>
                    <td>{c.cobros ? clp(c.cobros.total_clp) : '—'}</td>
                    <td>{c.alertas}</td>
                    <td>{c.cerrado_por}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
      <ContableMensual fechaDia={fecha} esAdmin={esAdmin} />
    </>
  )
}
