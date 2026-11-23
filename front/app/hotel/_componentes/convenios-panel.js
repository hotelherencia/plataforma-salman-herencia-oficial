'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, clp, mensajeDeError, Campo, CampoSelect, useClaveOperacion } from '../../../lib/api'
import { fechaATexto, plural } from '../../../lib/formato'
import { BarraContextual, SelectorFila } from './barra-contextual'

const ETIQUETA_TIPO = {
  empresa: 'Empresa / institución',
  evento: 'Evento anual',
  delegacion: 'Delegación',
}

function resumenReglas(reglas) {
  if (!reglas || typeof reglas !== 'object') return 'Sin reglas'
  const partes = []
  if (reglas.descuento_pct !== undefined && reglas.descuento_pct !== null) {
    partes.push(`${reglas.descuento_pct} % de descuento`)
  }
  if (reglas.por_tipo && typeof reglas.por_tipo === 'object') {
    const entradas = Object.entries(reglas.por_tipo)
    if (entradas.length > 0) {
      partes.push(entradas.map(([tipo, monto]) => `${tipo}: ${clp(monto)}`).join(' · '))
    }
  }
  return partes.join(' · ') || 'Sin reglas'
}

export default function ConveniosPanel({ esAdmin, clientes = [] }) {
  const [lista, setLista] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [creando, setCreando] = useState(false)
  const [seleccionadoId, setSeleccionadoId] = useState(null)
  const [editando, setEditando] = useState(false)
  const [claveAlta, renovarClaveAlta] = useClaveOperacion()

  const [form, setForm] = useState({
    nombre: '',
    tipo: 'empresa',
    cliente_id: '',
    vigencia_desde: '',
    vigencia_hasta: '',
    descuento_pct: '10',
    requiere_abono_pct: '50',
    notas: '',
    activo: true,
  })

  async function cargar() {
    setError('')
    try {
      const r = await api('/hotel/convenios')
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setLista(r.datos.convenios || [])
    } catch {
      setError('No se pudieron cargar los convenios tarifarios.')
    }
  }

  useEffect(() => {
    cargar()
  }, [])

  const activo = (lista || []).find((item) => item.convenio_id === seleccionadoId) || null

  function abrirEdicion(item) {
    setForm({
      nombre: item.nombre || '',
      tipo: item.tipo || 'empresa',
      cliente_id: item.cliente_id || '',
      vigencia_desde: item.vigencia_desde || '',
      vigencia_hasta: item.vigencia_hasta || '',
      descuento_pct: String(item.reglas_precio?.descuento_pct ?? ''),
      requiere_abono_pct: String(item.requiere_abono_pct ?? 50),
      notas: item.notas || '',
      activo: Boolean(item.activo),
    })
    setCreando(false)
    setEditando(true)
  }

  function abrirNuevo() {
    setForm({
      nombre: '',
      tipo: 'empresa',
      cliente_id: '',
      vigencia_desde: '',
      vigencia_hasta: '',
      descuento_pct: '10',
      requiere_abono_pct: '50',
      notas: '',
      activo: true,
    })
    setEditando(false)
    setCreando((v) => !v)
  }

  async function guardar(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const nombre = form.nombre.trim()
    if (nombre.length < 2) { setError('Indica el nombre del convenio o institución.'); return }
    if (!form.vigencia_desde || !form.vigencia_hasta) { setError('Indica fechas de vigencia desde y hasta.'); return }
    const descuentoNum = Number(form.descuento_pct)
    if (Number.isNaN(descuentoNum) || descuentoNum < 0 || descuentoNum > 100) {
      setError('El descuento debe ser un porcentaje entre 0 y 100.')
      return
    }
    const cuerpo = {
      nombre,
      tipo: form.tipo,
      cliente_id: form.cliente_id || null,
      vigencia_desde: form.vigencia_desde,
      vigencia_hasta: form.vigencia_hasta,
      reglas_precio: { descuento_pct: descuentoNum },
      requiere_abono_pct: Math.max(0, Math.min(100, Number(form.requiere_abono_pct) || 0)),
      notas: form.notas.trim() || null,
      activo: Boolean(form.activo),
    }
    try {
      const r = editando && activo
        ? await api(`/hotel/convenios/${encodeURIComponent(activo.convenio_id)}`, { metodo: 'PUT', cuerpo })
        : await api('/hotel/convenios', { metodo: 'POST', claveIdempotencia: claveAlta, cuerpo })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        if (!editando) alRechazar(r.estado, renovarClaveAlta)
      } else {
        setCreando(false)
        setEditando(false)
        if (!editando) renovarClaveAlta()
        setAviso(editando ? 'Convenio actualizado correctamente.' : 'Convenio creado correctamente.')
        cargar()
      }
    } catch {
      setError('No se pudo conectar con el servidor.')
    }
  }

  return (
    <section className="tarjeta" aria-label="Convenios tarifarios por institución y eventos">
      <div className="tarjeta-cabecera">
        <div>
          <h2>Convenios tarifarios (empresas, delegaciones y eventos)</h2>
          <p className="nota-clave">
            Tarifas especiales vigentes seleccionables en recepción. Su diferencia frente a la tarifa lista queda visible en el cierre diario de caja.
          </p>
        </div>
        {esAdmin && (
          <button type="button" className="boton-secundario" aria-expanded={creando} onClick={abrirNuevo}>
            {creando ? 'Cerrar formulario' : 'Nuevo convenio'}
          </button>
        )}
      </div>

      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      {esAdmin && (creando || (editando && activo)) && (
        <form className="formulario" onSubmit={guardar} style={{ marginBottom: '1rem' }}>
          <Campo etiqueta="Nombre del convenio o evento" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} placeholder="Ej.: Delegación BMX 2026" />
          <CampoSelect etiqueta="Tipo" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
            <option value="empresa">Empresa / institución</option>
            <option value="delegacion">Delegación</option>
            <option value="evento">Evento anual</option>
          </CampoSelect>
          <CampoSelect etiqueta="Cliente / empresa vinculada (opcional)" value={form.cliente_id} onChange={(e) => setForm({ ...form, cliente_id: e.target.value })}>
            <option value="">Sin cliente vinculado</option>
            {clientes.map((cli) => (
              <option key={cli.id} value={cli.id}>{cli.nombre} ({cli.rut})</option>
            ))}
          </CampoSelect>
          <Campo etiqueta="Vigencia desde" type="date" value={form.vigencia_desde} onChange={(e) => setForm({ ...form, vigencia_desde: e.target.value })} />
          <Campo etiqueta="Vigencia hasta" type="date" value={form.vigencia_hasta} onChange={(e) => setForm({ ...form, vigencia_hasta: e.target.value })} />
          <Campo etiqueta="Descuento (%)" type="number" min="0" max="100" step="0.5" value={form.descuento_pct} onChange={(e) => setForm({ ...form, descuento_pct: e.target.value })} />
          <Campo etiqueta="Abono requerido (%)" type="number" min="0" max="100" value={form.requiere_abono_pct} onChange={(e) => setForm({ ...form, requiere_abono_pct: e.target.value })} />
          <Campo etiqueta="Notas (opcional)" value={form.notas} onChange={(e) => setForm({ ...form, notas: e.target.value })} />
          <label className="campo-check">
            <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
            {' '}Convenio activo
          </label>
          <div className="acciones-fila">
            <button type="submit" className="boton-primario">{editando ? 'Guardar cambios' : 'Crear convenio'}</button>
            <button type="button" className="boton-fantasma" onClick={() => { setCreando(false); setEditando(false) }}>Cancelar</button>
          </div>
        </form>
      )}

      {lista && lista.length === 0 && (
        <p className="estado">Todavía no hay convenios tarifarios registrados.</p>
      )}

      {lista && lista.length > 0 && (
        <>
          <p className="nota-clave">{plural(lista.length, 'convenio registrado', 'convenios registrados')}.</p>
          {esAdmin && (
            <BarraContextual
              titulo="Acciones de convenio"
              seleccionado={Boolean(activo)}
              resumen={activo ? `${activo.nombre} · ${ETIQUETA_TIPO[activo.tipo] || activo.tipo}` : ''}
              detalle={activo ? `${fechaATexto(activo.vigencia_desde)} → ${fechaATexto(activo.vigencia_hasta)} · ${activo.activo ? 'Activo' : 'Inactivo'}` : ''}
              placeholder="Selecciona un convenio de la tabla para editar su vigencia o descuento."
              alLimpiar={() => { setSeleccionadoId(null); setEditando(false) }}
            >
              {activo && (
                <button type="button" className="boton-secundario" onClick={() => abrirEdicion(activo)}>
                  Editar convenio
                </button>
              )}
            </BarraContextual>
          )}
          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Convenios tarifarios (desliza para ver todas las columnas)">
            <table className="tabla">
              <thead>
                <tr>
                  {esAdmin && <th className="celda-selector"><span className="sr-only">Elegir</span></th>}
                  <th>Convenio / institución</th>
                  <th>Tipo</th>
                  <th>Cliente</th>
                  <th>Vigencia</th>
                  <th>Regla de tarifa</th>
                  <th>Abono</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((item) => {
                  const elegida = activo?.convenio_id === item.convenio_id
                  return (
                    <tr
                      key={item.convenio_id}
                      className={esAdmin ? 'fila-seleccionable' : undefined}
                      data-seleccionada={elegida ? 'true' : 'false'}
                      onClick={esAdmin ? () => { setSeleccionadoId(item.convenio_id); setEditando(false) } : undefined}
                    >
                      {esAdmin && (
                        <td className="celda-selector">
                          <SelectorFila
                            nombreGrupo="convenio-activo"
                            elegido={elegida}
                            etiqueta={`Seleccionar convenio ${item.nombre}`}
                            alElegir={() => { setSeleccionadoId(item.convenio_id); setEditando(false) }}
                          />
                        </td>
                      )}
                      <td><strong>{item.nombre}</strong></td>
                      <td>{ETIQUETA_TIPO[item.tipo] || item.tipo}</td>
                      <td>{item.cliente_nombre || '—'}</td>
                      <td className="celda-fecha">{fechaATexto(item.vigencia_desde)} → {fechaATexto(item.vigencia_hasta)}</td>
                      <td>{resumenReglas(item.reglas_precio)}</td>
                      <td>{item.requiere_abono_pct} %</td>
                      <td>{item.activo ? 'Activo' : 'Inactivo'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
