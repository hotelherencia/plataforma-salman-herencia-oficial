'use client'

import { useEffect, useState } from 'react'
import { api, clp, mensajeDeError, Campo, CampoSelect } from '../../../lib/api'
import { DOCUMENTOS, MEDIOS } from '../../../lib/caja'
import cc from './caja.module.css'

function clave() {
  return `aj-${crypto.randomUUID().slice(0, 12)}`
}

/**
 * Caja y medios de pago (fase 1 contable, 2026-11-19): parámetros de la caja
 * que edita la administración del hotel. Nada queda fijo en el código.
 */
export default function AjustesCaja() {
  const [caja, setCaja] = useState(null)
  const [denominaciones, setDenominaciones] = useState('')
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  function cargar(valor) {
    setCaja({
      ...valor,
      medios: Object.fromEntries(Object.entries(valor.medios).map(([m, v]) => [m, {
        ...v, comision_pct: String(v.comision_pct).replace('.', ','), dias_abono: String(v.dias_abono),
      }])),
      fondo_fijo_clp: String(valor.fondo_fijo_clp),
      tolerancia_diferencia_clp: String(valor.tolerancia_diferencia_clp),
    })
    setDenominaciones(valor.denominaciones.join(' '))
  }

  useEffect(() => {
    api('/hotel/ajustes')
      .then((r) => (r.estado === 200 ? cargar(r.datos.ajustes.caja) : setError(mensajeDeError(r.datos, r.estado))))
      .catch(() => setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.'))
  }, [])

  const medio = (m, campo, valor) => setCaja({ ...caja, medios: { ...caja.medios, [m]: { ...caja.medios[m], [campo]: valor } } })

  async function guardar(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const lista = denominaciones.split(/[\s,;]+/).map((d) => d.replace(/\./g, '')).filter(Boolean).map(Number)
    if (!lista.length || lista.some((d) => !Number.isInteger(d) || d <= 0)) {
      setError('Escribe las denominaciones como números separados por espacios, p. ej. 20000 10000 5000.')
      return
    }
    const cuerpo = {
      medios: Object.fromEntries(Object.entries(caja.medios).map(([m, v]) => [m, {
        activo: v.activo, comision_pct: Number(String(v.comision_pct).replace(',', '.')) || 0, dias_abono: Number(v.dias_abono) || 0,
      }])),
      fondo_fijo_clp: Number(caja.fondo_fijo_clp) || 0,
      tolerancia_diferencia_clp: Number(caja.tolerancia_diferencia_clp) || 0,
      denominaciones: lista,
      exigir_turno_efectivo: caja.exigir_turno_efectivo,
      exigir_documento: caja.exigir_documento,
      documento_por_defecto: caja.documento_por_defecto,
      banco_deposito: caja.banco_deposito,
    }
    try {
      const r = await api('/hotel/ajustes/caja', { metodo: 'PUT', cuerpo, claveIdempotencia: clave() })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else { cargar(r.datos.valor); setAviso('Parámetros de caja guardados.') }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <section className="tarjeta">
      <h2>Caja y medios de pago</h2>
      <p className="nota-clave">
        Medios que acepta el hotel, comisión y días de abono de cada uno según el contrato con el adquirente (Transbank u otro),
        fondo fijo de caja y reglas del turno. Lo usan la caja, el cierre diario y, más adelante, la conciliación bancaria.
      </p>
      {!caja && !error && <p className="estado" role="status" aria-busy="true">Cargando…</p>}
      {caja && (
        <form className="formulario" onSubmit={guardar}>
          <fieldset className={cc.grupo}>
            <legend>Medios de pago</legend>
            {MEDIOS.map(([m, nombre]) => (
              <div key={m} className={cc.linea}>
                <label className="campo-check">
                  <input type="checkbox" checked={caja.medios[m].activo} onChange={(e) => medio(m, 'activo', e.target.checked)} />
                  {nombre}
                </label>
                {m !== 'efectivo' && (
                  <>
                    <Campo etiqueta="Comisión (%)" inputMode="decimal" value={caja.medios[m].comision_pct}
                      onChange={(e) => medio(m, 'comision_pct', e.target.value)} />
                    <Campo etiqueta="Días hasta el abono" type="number" min="0" max="30" value={caja.medios[m].dias_abono}
                      onChange={(e) => medio(m, 'dias_abono', e.target.value)} />
                  </>
                )}
              </div>
            ))}
          </fieldset>
          <Campo etiqueta="Fondo fijo de caja sugerido al abrir (CLP)" type="number" min="0" value={caja.fondo_fijo_clp}
            onChange={(e) => setCaja({ ...caja, fondo_fijo_clp: e.target.value })} />
          <Campo etiqueta="Diferencia tolerada antes de marcar «requiere revisión» (CLP)" type="number" min="0"
            value={caja.tolerancia_diferencia_clp} onChange={(e) => setCaja({ ...caja, tolerancia_diferencia_clp: e.target.value })} />
          <Campo etiqueta="Billetes y monedas para el arqueo (separados por espacio)" value={denominaciones}
            onChange={(e) => setDenominaciones(e.target.value)} />
          <p className="estado">Se contarán: {denominaciones.split(/[\s,;]+/).filter(Boolean).map((d) => clp(Number(d.replace(/\./g, '')) || 0)).join(' · ')}</p>
          <CampoSelect etiqueta="Documento por defecto al cobrar" value={caja.documento_por_defecto}
            onChange={(e) => setCaja({ ...caja, documento_por_defecto: e.target.value })}>
            {DOCUMENTOS.map(([valor, nombre]) => <option key={valor} value={valor}>{nombre}</option>)}
          </CampoSelect>
          <Campo etiqueta="Banco y cuenta de depósito" value={caja.banco_deposito} maxLength={120}
            onChange={(e) => setCaja({ ...caja, banco_deposito: e.target.value })} />
          <label className="campo-check">
            <input type="checkbox" checked={caja.exigir_turno_efectivo} onChange={(e) => setCaja({ ...caja, exigir_turno_efectivo: e.target.checked })} />
            Exigir turno de caja abierto para recibir efectivo
          </label>
          <label className="campo-check">
            <input type="checkbox" checked={caja.exigir_documento} onChange={(e) => setCaja({ ...caja, exigir_documento: e.target.checked })} />
            Exigir indicar boleta o factura en cada pago
          </label>
          <button type="submit" className="boton-primario">Guardar</button>
        </form>
      )}
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
    </section>
  )
}
