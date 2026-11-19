'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  api, alRechazar, clp, mensajeDeError, MarcoHotel, SalidaJson, Campo, CampoSelect, useClaveOperacion, useSesion,
} from '../../../lib/api'
import { aConIva, aumentar, desglose, tasaTexto } from '../../../lib/iva'
import {
  codigoDesdeNombre, etiquetaOrigen, idsDelLote, MAX_LOTE, montoONulo, PATRON_ID_TIPO, rangoNoches, resumenIds,
  siguienteNumero, validarExcepcion, validarLote,
} from '../../../lib/tipos'

/**
 * Tipos, habitaciones y precios (entregas 1A y 1A.2): el ÚNICO lugar donde se
 * definen precios. Precio de una noche, de mayor a menor prioridad:
 * excepción de la habitación › excepción del tipo › precio propio de la
 * habitación › precio base del tipo. Todos los precios incluyen IVA (se
 * guarda el precio con IVA; neto e IVA se derivan con la tasa vigente).
 * Administración del hotel edita precios, tipos y altas; administración de
 * plataforma fija la tasa de IVA; recepción y caja solo leen.
 */
export default function TiposHabitacionesPrecios({ seccion = 'todo', sinMarco = false } = {}) {
  const sesion = useSesion()
  const [tipos, setTipos] = useState(null)
  const [tasa, setTasa] = useState(19)
  const [permisos, setPermisos] = useState({ precios: false, iva: false })
  const [idsExistentes, setIdsExistentes] = useState([])
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)
  const [editando, setEditando] = useState(null)

  const cargar = useCallback(async () => {
    try {
      const [rt, rh] = await Promise.all([api('/hotel/tipos'), api('/hotel/habitaciones')])
      if (rt.estado === 200) {
        setTipos(rt.datos.tipos)
        setTasa(Number(rt.datos.iva?.porcentaje ?? 19))
        setPermisos({ precios: Boolean(rt.datos.puede_editar), iva: Boolean(rt.datos.puede_editar_iva) })
      } else {
        setTipos([])
        setError(mensajeDeError(rt.datos, rt.estado))
      }
      if (rh.estado === 200) setIdsExistentes(rh.datos.habitaciones.map((h) => h.habitacion_id))
    } catch {
      setTipos([])
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }, [])

  useEffect(() => {
    if (sesion.fase === 'ok') cargar()
  }, [sesion.fase, cargar])

  function alConfirmar(datos) {
    setError('')
    setSalida(datos)
    setEditando(null)
    cargar()
  }

  const totales = useMemo(() => {
    const lista = tipos || []
    const suma = (campo) => lista.reduce((s, t) => s + (t.resumen?.[campo] || 0), 0)
    return {
      tipos: lista.filter((t) => t.activo).length,
      habitaciones: suma('habitaciones'),
      enServicio: suma('en_servicio'),
      sinPrecio: suma('sin_precio_hoy'),
      excepciones: lista.reduce((s, t) => s + (t.excepciones?.length || 0), 0),
    }
  }, [tipos])

  const ctx = { tasa, puedeEditar: permisos.precios, alConfirmar, alError: setError }

  const mostrarPrecios = seccion !== 'tipos'
  const mostrarAlta = seccion !== 'precios'
  const titulo = seccion === 'precios' ? 'Precios y excepciones' : seccion === 'tipos' ? 'Tipos y habitaciones' : 'Tipos, habitaciones y precios'
  const cuerpo = (
    <>
      <section className="tarjeta">
        <p className="nota-clave">
          Aquí se definen <strong>todos</strong> los precios del hotel. Cada habitación hereda el{' '}
          <strong>precio base</strong> de su tipo: para cambiar el precio de 10 o 100 habitaciones basta con editar el
          tipo. Si una habitación vale distinto, se le da un <strong>precio propio</strong>; las temporadas, feriados o
          cierres son <strong>excepciones por fecha</strong> del tipo o de una habitación. Las reservas confirmadas
          conservan su precio noche a noche.
        </p>
        <p className="tipos-prioridad">
          Precio de una noche: excepción de la habitación › excepción del tipo › precio propio › precio base.
        </p>
        {!permisos.precios && sesion.fase === 'ok' && tipos && (
          <p className="tipos-solo-lectura" role="note">Solo lectura: los precios, tipos y altas los edita la administración del hotel.</p>
        )}
        <dl className="tipos-totales">
          <div><dt>Tipos activos</dt><dd>{tipos ? totales.tipos : '—'}</dd></div>
          <div><dt>Habitaciones</dt><dd>{tipos ? totales.habitaciones : '—'}</dd></div>
          <div><dt>En servicio</dt><dd>{tipos ? totales.enServicio : '—'}</dd></div>
          <div><dt>Excepciones vigentes o futuras</dt><dd>{tipos ? totales.excepciones : '—'}</dd></div>
          <div className={totales.sinPrecio ? 'tipos-total-alerta' : ''}>
            <dt>Sin precio hoy</dt><dd>{tipos ? totales.sinPrecio : '—'}</dd>
          </div>
        </dl>
      </section>

      {mostrarPrecios && (
        <div className="tipos-herramientas">
          <PanelIva tasa={tasa} puedeEditar={permisos.iva} alConfirmar={alConfirmar} alError={setError} />
          <CalculadoraIva tasa={tasa} tipos={tipos || []} />
        </div>
      )}

      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />

      {tipos === null ? (
        <p className="estado">Cargando tipos…</p>
      ) : tipos.length === 0 ? (
        <p className="estado">Aún no hay tipos de habitación.</p>
      ) : (
        <div className="tipos-grilla">
          {tipos.map((tipo) => (
            <TarjetaTipo
              key={tipo.tipo_id}
              tipo={tipo}
              ctx={ctx}
              editando={editando === tipo.tipo_id}
              alEditar={() => { setSalida(null); setEditando(editando === tipo.tipo_id ? null : tipo.tipo_id) }}
            />
          ))}
        </div>
      )}

      {permisos.precios && tipos && mostrarAlta && (
        <div className="tipos-formularios">
          <AltaPorLote tipos={tipos} idsExistentes={idsExistentes} alConfirmar={alConfirmar} alError={setError} />
          <NuevoTipo tasa={tasa} alConfirmar={alConfirmar} alError={setError} />
        </div>
      )}
    </>
  )
  if (sinMarco) return cuerpo
  return <MarcoHotel titulo={titulo}>{cuerpo}</MarcoHotel>
}

/* ------------------------------------------------------------------ IVA --- */

function Desglose({ precio, tasa, compacto = false }) {
  const d = desglose(precio, tasa)
  if (!d) return null
  return (
    <span className={compacto ? 'desglose desglose-compacto' : 'desglose'}>
      neto {clp(d.neto)} · IVA {clp(d.iva)}
    </span>
  )
}

/** Monto con selector «con IVA / neto» y el otro valor calculado al vuelo. */
function CampoPrecio({ etiqueta, valor, en, tasa, alCambiar, opcional = true, id }) {
  const monto = montoONulo(valor)
  const conIva = Number.isNaN(monto) ? NaN : aConIva(monto, en, tasa)
  const d = monto && !Number.isNaN(conIva) ? desglose(conIva, tasa) : null
  return (
    <div className="campo campo-precio">
      <span className="campo-etiqueta" id={`${id}-etq`}>{etiqueta}</span>
      <div className="campo-precio-fila">
        <input
          className="entrada"
          inputMode="numeric"
          aria-labelledby={`${id}-etq`}
          placeholder={opcional ? 'vacío = sin precio' : 'monto en pesos'}
          value={valor}
          onChange={(e) => alCambiar({ valor: e.target.value, en })}
        />
        <div className="selector-iva" role="radiogroup" aria-label="El monto ingresado es">
          {[['con_iva', 'con IVA'], ['neto', 'neto']].map(([clave, texto]) => (
            <button
              key={clave}
              type="button"
              role="radio"
              aria-checked={en === clave}
              className={en === clave ? 'activo' : ''}
              onClick={() => alCambiar({ valor, en: clave })}
            >
              {texto}
            </button>
          ))}
        </div>
      </div>
      <span className="campo-precio-ayuda" role="status">
        {d
          ? en === 'neto'
            ? <>Se guarda {clp(d.conIva)} con IVA (neto {clp(d.neto)} · IVA {clp(d.iva)})</>
            : <>Neto {clp(d.neto)} · IVA {clp(d.iva)}</>
          : Number.isNaN(monto) ? 'Monto entero mayor que cero' : `IVA ${tasaTexto(tasa)} % incluido`}
      </span>
    </div>
  )
}

function PanelIva({ tasa, puedeEditar, alConfirmar, alError }) {
  const [abierto, setAbierto] = useState(false)
  const [nueva, setNueva] = useState('')
  const [clave, renovar] = useClaveOperacion()

  async function guardar(e) {
    e.preventDefault()
    alError('')
    const valor = Number(String(nueva).replace(',', '.'))
    if (!Number.isFinite(valor) || valor < 0 || valor > 100) return alError('La tasa de IVA va de 0 a 100.')
    try {
      const resp = await api('/plataforma/ajustes/iva', { metodo: 'PUT', claveIdempotencia: clave, cuerpo: { iva_porcentaje: valor } })
      if (resp.estado >= 400) {
        alError(mensajeDeError(resp.datos, resp.estado))
        alRechazar(resp.estado, renovar)
      } else {
        renovar()
        setAbierto(false)
        alConfirmar(resp.datos)
      }
    } catch {
      alError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <section className="tarjeta panel-iva" aria-labelledby="titulo-iva">
      <h2 id="titulo-iva">IVA {tasaTexto(tasa)} % incluido</h2>
      <p className="nota-clave">
        Todos los precios se ingresan y se guardan <strong>con IVA</strong> (lo que paga el huésped). El neto y el IVA se
        calculan: neto = precio ÷ {(1 + tasa / 100).toFixed(2).replace('.', ',')} redondeado al peso; IVA = precio − neto.
        Puedes escribir un monto neto y se guarda su precio con IVA.
      </p>
      {puedeEditar ? (
        abierto ? (
          <form className="formulario formulario-linea" onSubmit={guardar}>
            <Campo etiqueta="Nueva tasa (%)" inputMode="decimal" value={nueva} onChange={(e) => setNueva(e.target.value)} placeholder={String(tasa)} />
            <p className="nota-chica">Cambiar la tasa no cambia los precios con IVA ya guardados; cambia su desglose neto/IVA.</p>
            <div className="acciones-linea">
              <button type="submit" className="boton-primario">Guardar tasa</button>
              <button type="button" className="boton-secundario" onClick={() => setAbierto(false)}>Cancelar</button>
            </div>
          </form>
        ) : (
          <button type="button" className="boton-secundario" onClick={() => { setNueva(String(tasa)); setAbierto(true) }}>
            Cambiar tasa de IVA
          </button>
        )
      ) : (
        <p className="nota-chica">La tasa la fija la administración de plataforma.</p>
      )}
    </section>
  )
}

function CalculadoraIva({ tasa, tipos }) {
  const [monto, setMonto] = useState('55000')
  const [en, setEn] = useState('con_iva')
  const [pct, setPct] = useState('10')
  const [sobre, setSobre] = useState('final')
  const n = montoONulo(monto)
  const precio = n && !Number.isNaN(n) ? aConIva(n, en, tasa) : null
  const base = precio ? desglose(precio, tasa) : null
  const resultado = precio ? aumentar(precio, String(pct).replace(',', '.'), sobre, tasa) : null
  const conBase = tipos.filter((t) => t.precio_base_clp)

  return (
    <section className="tarjeta calculadora-iva" aria-labelledby="titulo-calculadora">
      <h2 id="titulo-calculadora">Calculadora de IVA</h2>
      <div className="calculadora-fila">
        <CampoPrecio id="calc" etiqueta="Monto" valor={monto} en={en} tasa={tasa} opcional={false}
          alCambiar={({ valor, en: e }) => { setMonto(valor); setEn(e) }} />
        {conBase.length > 0 && (
          <CampoSelect etiqueta="O tomar el precio base de" value="" onChange={(e) => { if (e.target.value) { setMonto(e.target.value); setEn('con_iva') } }}>
            <option value="">— elegir tipo —</option>
            {conBase.map((t) => <option key={t.tipo_id} value={t.precio_base_clp}>{t.nombre} · {clp(t.precio_base_clp)}</option>)}
          </CampoSelect>
        )}
      </div>
      {base && (
        <dl className="calculadora-resultado">
          <div><dt>Con IVA</dt><dd>{clp(base.conIva)}</dd></div>
          <div><dt>Neto</dt><dd>{clp(base.neto)}</dd></div>
          <div><dt>IVA {tasaTexto(tasa)} %</dt><dd>{clp(base.iva)}</dd></div>
        </dl>
      )}
      <div className="calculadora-fila">
        <Campo etiqueta="¿Y si subo? (%)" inputMode="decimal" value={pct} onChange={(e) => setPct(e.target.value)} />
        <CampoSelect etiqueta="Sobre" value={sobre} onChange={(e) => setSobre(e.target.value)}>
          <option value="final">el precio final (con IVA)</option>
          <option value="neto">el neto</option>
        </CampoSelect>
      </div>
      {resultado && base && (
        <p className="calculadora-que-pasa" role="status">
          Quedaría en <strong>{clp(resultado.conIva)}</strong> con IVA (neto {clp(resultado.neto)} · IVA {clp(resultado.iva)}),{' '}
          {resultado.conIva >= base.conIva ? '+' : '−'}{clp(Math.abs(resultado.conIva - base.conIva))} por noche.
        </p>
      )}
    </section>
  )
}

/* ---------------------------------------------------------------- Tipos --- */

function TarjetaTipo({ tipo, ctx, editando, alEditar }) {
  const { tasa, puedeEditar } = ctx
  const r = tipo.resumen
  const rango =
    r.precio_hoy_min_clp && r.precio_hoy_max_clp !== r.precio_hoy_min_clp
      ? `${clp(r.precio_hoy_min_clp)} – ${clp(r.precio_hoy_max_clp)}`
      : clp(r.precio_hoy_min_clp)
  return (
    <article className={`tarjeta tipo-tarjeta${tipo.activo ? '' : ' tipo-inactivo'}`} aria-labelledby={`tipo-${tipo.tipo_id}`}>
      <header className="tipo-cabecera">
        <div>
          <h2 id={`tipo-${tipo.tipo_id}`}>{tipo.nombre}</h2>
          <p className="tipo-codigo">
            <code>{tipo.tipo_id}</code> · capacidad {tipo.capacidad_base} {tipo.capacidad_base === 1 ? 'persona' : 'personas'}
            {!tipo.activo && ' · inactivo'}
          </p>
        </div>
        <div className="tipo-precio">
          <span className="tipo-precio-etiqueta">Precio base</span>
          <strong>{tipo.precio_base_clp ? clp(tipo.precio_base_clp) : 'Sin precio base'}</strong>
          {tipo.precio_base_clp && <span className="tipo-precio-etiqueta">por noche, IVA incl.</span>}
          {tipo.precio_base_clp && <Desglose precio={tipo.precio_base_clp} tasa={tasa} compacto />}
        </div>
      </header>

      <ul className="tipo-cifras">
        <li><strong>{r.habitaciones}</strong> {r.habitaciones === 1 ? 'habitación' : 'habitaciones'} · {r.en_servicio} en servicio</li>
        <li>Precio hoy: <strong>{r.precio_hoy_min_clp ? rango : '—'}</strong></li>
        <li className="tipo-origenes">
          {r.heredan_precio_base > 0 && <span className="origen origen-tipo">{r.heredan_precio_base} heredan la base</span>}
          {r.con_precio_propio > 0 && <span className="origen origen-habitacion">{r.con_precio_propio} con precio propio</span>}
          {r.con_excepcion_hoy > 0 && <span className="origen origen-excepcion_tipo">{r.con_excepcion_hoy} con excepción hoy</span>}
          {r.sin_precio_hoy > 0 && <span className="origen origen-ninguno">{r.sin_precio_hoy} sin precio hoy</span>}
        </li>
      </ul>

      {tipo.habitaciones.length > 0 && (
        <details className="tipo-habitaciones">
          <summary>Habitaciones y precio propio</summary>
          <ul>
            {tipo.habitaciones.map((h) => (
              <FilaHabitacion key={h.habitacion_id} h={h} ctx={ctx} />
            ))}
          </ul>
        </details>
      )}

      <Excepciones tipo={tipo} ctx={ctx} />

      {puedeEditar && (
        <button type="button" className="boton-secundario" onClick={alEditar} aria-expanded={editando}>
          {editando ? 'Cerrar edición' : 'Editar tipo y precio base'}
        </button>
      )}
      {puedeEditar && editando && <EdicionTipo tipo={tipo} ctx={ctx} />}
    </article>
  )
}

function FilaHabitacion({ h, ctx }) {
  const { tasa, puedeEditar, alConfirmar, alError } = ctx
  const [abierta, setAbierta] = useState(false)
  const [precio, setPrecio] = useState({ valor: h.precio_propio_clp ?? '', en: 'con_iva' })
  const [clave, renovar] = useClaveOperacion()

  async function guardar(e, quitar = false) {
    e.preventDefault()
    alError('')
    const monto = quitar ? null : montoONulo(precio.valor)
    if (Number.isNaN(monto)) return alError('El precio propio debe ser un monto entero mayor que cero.')
    try {
      const resp = await api(`/hotel/habitaciones/${encodeURIComponent(h.habitacion_id)}/precio`, {
        metodo: 'PUT', claveIdempotencia: clave, cuerpo: { precio_clp: monto, precio_en: precio.en },
      })
      if (resp.estado >= 400) {
        alError(mensajeDeError(resp.datos, resp.estado))
        alRechazar(resp.estado, renovar)
      } else {
        renovar()
        setAbierta(false)
        alConfirmar(resp.datos)
      }
    } catch {
      alError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <li className={h.en_servicio ? '' : 'fuera'}>
      <div className="fila-habitacion">
        <Link href={`/hotel/habitaciones/${h.habitacion_id}`} title="Abrir ficha de la habitación">{h.habitacion_id}</Link>
        <span>{h.precio_hoy_clp ? clp(h.precio_hoy_clp) : '—'}</span>
        <span className={`origen origen-${h.origen_precio_hoy || 'ninguno'}`}>{etiquetaOrigen(h.origen_precio_hoy)}</span>
        {!h.en_servicio && <span className="tipo-fuera">fuera de servicio</span>}
        {puedeEditar && (
          <button type="button" className="enlace-boton" onClick={() => setAbierta(!abierta)} aria-expanded={abierta}>
            {h.precio_propio_clp ? `propio ${clp(h.precio_propio_clp)}` : 'precio propio'}
          </button>
        )}
      </div>
      {abierta && (
        <form className="formulario precio-propio" onSubmit={guardar}>
          <CampoPrecio id={`propio-${h.habitacion_id}`} etiqueta={`Precio propio de ${h.habitacion_id}`} valor={precio.valor}
            en={precio.en} tasa={tasa} alCambiar={setPrecio} opcional={false} />
          <div className="acciones-linea">
            <button type="submit" className="boton-primario">Guardar</button>
            {h.precio_propio_clp && (
              <button type="button" className="boton-secundario" onClick={(e) => guardar(e, true)}>Quitar (heredar la base)</button>
            )}
          </div>
        </form>
      )}
    </li>
  )
}

function Excepciones({ tipo, ctx }) {
  const { tasa, puedeEditar, alConfirmar, alError } = ctx
  const [abierta, setAbierta] = useState(false)
  const [clave, renovar] = useClaveOperacion()
  const lista = tipo.excepciones || []

  async function retirar(excepcion) {
    alError('')
    try {
      const resp = await api(`/hotel/precios/excepciones/${encodeURIComponent(excepcion.excepcion_id)}/retiro`, {
        metodo: 'POST', claveIdempotencia: `${clave}-${excepcion.excepcion_id}`, cuerpo: {},
      })
      if (resp.estado >= 400) {
        alError(mensajeDeError(resp.datos, resp.estado))
        alRechazar(resp.estado, renovar)
      } else {
        renovar()
        alConfirmar(resp.datos)
      }
    } catch {
      alError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  if (!lista.length && !puedeEditar) return null
  return (
    <section className="tipo-excepciones" aria-label={`Excepciones por fecha de ${tipo.nombre}`}>
      <h3>Excepciones por fecha</h3>
      {lista.length === 0 ? (
        <p className="nota-chica">Sin excepciones vigentes ni futuras.</p>
      ) : (
        <ul>
          {lista.map((e) => (
            <li key={e.excepcion_id} className={e.vigente_hoy ? 'vigente' : ''}>
              <span className="excepcion-alcance">{e.alcance === 'tipo' ? 'Todo el tipo' : e.habitacion_id}</span>
              <span className="excepcion-rango">{rangoNoches(e.fecha_desde, e.fecha_hasta)}</span>
              <strong>{e.precio_clp ? clp(e.precio_clp) : 'Sin venta'}</strong>
              {e.precio_clp && <Desglose precio={e.precio_clp} tasa={tasa} compacto />}
              {e.motivo && <span className="excepcion-motivo">{e.motivo}</span>}
              {e.vigente_hoy && <span className="origen origen-excepcion_tipo">hoy</span>}
              {puedeEditar && (
                <button type="button" className="enlace-boton" onClick={() => retirar(e)}>Retirar</button>
              )}
            </li>
          ))}
        </ul>
      )}
      {puedeEditar && (
        <button type="button" className="enlace-boton" onClick={() => setAbierta(!abierta)} aria-expanded={abierta}>
          {abierta ? 'Cerrar' : '+ Nueva excepción (temporada, feriado o cierre)'}
        </button>
      )}
      {puedeEditar && abierta && <NuevaExcepcion tipo={tipo} ctx={ctx} alCerrar={() => setAbierta(false)} />}
    </section>
  )
}

function NuevaExcepcion({ tipo, ctx, alCerrar }) {
  const { tasa, alConfirmar, alError } = ctx
  const [form, setForm] = useState({ alcance: 'tipo', habitacionId: '', desde: '', hasta: '', sinVenta: false, motivo: '' })
  const [precio, setPrecio] = useState({ valor: '', en: 'con_iva' })
  const [clave, renovar] = useClaveOperacion()
  const monto = montoONulo(precio.valor)
  const problema = validarExcepcion({ ...form, precio: monto })

  async function crear(e) {
    e.preventDefault()
    alError('')
    if (problema) return alError(problema)
    const cuerpo = {
      fecha_desde: form.desde,
      fecha_hasta: form.hasta,
      precio_clp: form.sinVenta ? null : monto,
      precio_en: precio.en,
      motivo: form.motivo.trim() || null,
    }
    if (form.alcance === 'tipo') cuerpo.tipo_id = tipo.tipo_id
    else cuerpo.habitacion_id = form.habitacionId
    try {
      const resp = await api('/hotel/precios/excepciones', { metodo: 'POST', claveIdempotencia: clave, cuerpo })
      if (resp.estado >= 400) {
        alError(mensajeDeError(resp.datos, resp.estado))
        alRechazar(resp.estado, renovar)
      } else {
        renovar()
        alCerrar()
        alConfirmar(resp.datos)
      }
    } catch {
      alError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <form className="formulario tipo-edicion" onSubmit={crear}>
      <CampoSelect etiqueta="Aplica a" value={form.alcance} onChange={(e) => setForm({ ...form, alcance: e.target.value })}>
        <option value="tipo">Todas las habitaciones {tipo.nombre}</option>
        <option value="habitacion">Una habitación</option>
      </CampoSelect>
      {form.alcance === 'habitacion' && (
        <CampoSelect etiqueta="Habitación" value={form.habitacionId} onChange={(e) => setForm({ ...form, habitacionId: e.target.value })}>
          <option value="">— elegir —</option>
          {tipo.habitaciones.map((h) => <option key={h.habitacion_id} value={h.habitacion_id}>{h.habitacion_id}</option>)}
        </CampoSelect>
      )}
      <Campo etiqueta="Primera noche (Llegada)" type="date" value={form.desde} onChange={(e) => setForm({ ...form, desde: e.target.value })} />
      <Campo etiqueta="Hasta la Salida del (no incluida)" type="date" value={form.hasta} onChange={(e) => setForm({ ...form, hasta: e.target.value })} />
      <label className="campo campo-casilla">
        <input type="checkbox" checked={form.sinVenta} onChange={(e) => setForm({ ...form, sinVenta: e.target.checked })} />
        <span>Sin venta esas noches (cierre)</span>
      </label>
      {!form.sinVenta && (
        <CampoPrecio id={`exc-${tipo.tipo_id}`} etiqueta="Precio por noche" valor={precio.valor} en={precio.en} tasa={tasa}
          alCambiar={setPrecio} opcional={false} />
      )}
      <Campo etiqueta="Motivo (opcional)" maxLength={120} placeholder="p. ej. Fiestas Patrias" value={form.motivo}
        onChange={(e) => setForm({ ...form, motivo: e.target.value })} />
      {form.desde && form.hasta && form.hasta > form.desde && (
        <p className="nota-chica" role="status">Cubre las {rangoNoches(form.desde, form.hasta)}.</p>
      )}
      <button type="submit" className="boton-primario" disabled={Boolean(problema)}>Crear excepción</button>
    </form>
  )
}

function EdicionTipo({ tipo, ctx }) {
  const { tasa, alConfirmar, alError } = ctx
  const [form, setForm] = useState({ nombre: tipo.nombre, capacidad_base: tipo.capacidad_base, activo: tipo.activo })
  const [precio, setPrecio] = useState({ valor: tipo.precio_base_clp ?? '', en: 'con_iva' })
  const [clave, renovar] = useClaveOperacion()
  const monto = montoONulo(precio.valor)
  const nuevoPrecio = Number.isNaN(monto) ? NaN : aConIva(monto, precio.en, tasa)
  const cambiaPrecio = nuevoPrecio !== (tipo.precio_base_clp ?? null)

  async function guardar(e) {
    e.preventDefault()
    alError('')
    if (Number.isNaN(monto)) return alError('El precio base debe ser un monto entero mayor que cero, o vacío para dejarlo sin precio.')
    if (!form.nombre.trim()) return alError('Falta completar: Nombre.')
    try {
      const resp = await api(`/hotel/tipos/${encodeURIComponent(tipo.tipo_id)}`, {
        metodo: 'PUT',
        claveIdempotencia: clave,
        cuerpo: {
          nombre: form.nombre.trim(),
          capacidad_base: Number(form.capacidad_base),
          precio_base_clp: monto,
          precio_en: precio.en,
          activo: form.activo,
        },
      })
      if (resp.estado >= 400) {
        alError(mensajeDeError(resp.datos, resp.estado))
        alRechazar(resp.estado, renovar)
      } else {
        renovar()
        alConfirmar(resp.datos)
      }
    } catch {
      alError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <form className="formulario tipo-edicion" onSubmit={guardar}>
      <Campo etiqueta="Nombre" value={form.nombre} maxLength={80} onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
      <Campo etiqueta="Capacidad base" type="number" min="1" max="30" value={form.capacidad_base} onChange={(e) => setForm({ ...form, capacidad_base: e.target.value })} />
      <CampoPrecio id={`base-${tipo.tipo_id}`} etiqueta="Precio base por noche" valor={precio.valor} en={precio.en} tasa={tasa} alCambiar={setPrecio} />
      <label className="campo campo-casilla">
        <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
        <span>Tipo activo (admite altas nuevas)</span>
      </label>
      {cambiaPrecio && !Number.isNaN(nuevoPrecio) && <ImpactoPrecio tipo={tipo} nuevoPrecio={nuevoPrecio} />}
      <button type="submit" className="boton-primario">Guardar cambios</button>
    </form>
  )
}

function ImpactoPrecio({ tipo, nuevoPrecio }) {
  const r = tipo.resumen
  const heredan = tipo.habitaciones.filter((h) => !h.precio_propio_clp).length
  let texto
  if (nuevoPrecio && heredan > 0) {
    texto = <><strong>{heredan}</strong> {heredan === 1 ? 'habitación pasa' : 'habitaciones pasan'} a {clp(nuevoPrecio)} por noche.</>
  } else if (!nuevoPrecio && heredan > 0) {
    texto = <>Sin precio base, <strong>{heredan}</strong> {heredan === 1 ? 'habitación quedará' : 'habitaciones quedarán'} sin precio y no se ofrecerán (salvo en sus excepciones).</>
  } else {
    texto = <>Todas las habitaciones de este tipo tienen precio propio: hoy ninguna cambia.</>
  }
  return (
    <p className="tipo-impacto" role="status">
      {texto}
      {r.con_precio_propio > 0 && <> {r.con_precio_propio === 1 ? 'La habitación' : `Las ${r.con_precio_propio} habitaciones`} con precio propio no cambian.</>}
      {(tipo.excepciones || []).length > 0 && <> En las noches con excepción manda la excepción.</>}
      {' '}Las reservas confirmadas conservan su precio.
    </p>
  )
}

function AltaPorLote({ tipos, idsExistentes, alConfirmar, alError }) {
  const activos = tipos.filter((t) => t.activo)
  const [form, setForm] = useState({ tipoId: activos[0]?.tipo_id || '', cantidad: 1, prefijo: 'HAB-', desde: '', digitos: 2, capacidad: '' })
  const [clave, renovar] = useClaveOperacion()
  const sugerido = siguienteNumero(idsExistentes, form.prefijo)
  const desde = form.desde === '' ? sugerido : Number(form.desde)
  const ids = idsDelLote(form.prefijo, desde, form.cantidad, form.digitos)
  const tipo = tipos.find((t) => t.tipo_id === form.tipoId)
  const problema = validarLote({ ...form, desde }, idsExistentes)

  async function crear(e) {
    e.preventDefault()
    alError('')
    if (problema) return alError(problema)
    try {
      const cuerpo = {
        tipo_id: form.tipoId,
        cantidad: Number(form.cantidad),
        prefijo: form.prefijo,
        desde_numero: desde,
        digitos: Number(form.digitos),
      }
      if (form.capacidad !== '') cuerpo.capacidad = Number(form.capacidad)
      const resp = await api('/hotel/habitaciones/lote', { metodo: 'POST', claveIdempotencia: clave, cuerpo })
      if (resp.estado >= 400) {
        const existentes = resp.datos?.existentes
        alError(existentes ? `Ya existen: ${resumenIds(existentes)}. No se creó ninguna.` : mensajeDeError(resp.datos, resp.estado))
        alRechazar(resp.estado, renovar)
      } else {
        renovar()
        setForm({ ...form, desde: '' })
        alConfirmar(resp.datos)
      }
    } catch {
      alError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <section className="tarjeta" aria-labelledby="titulo-lote">
      <h2 id="titulo-lote">Agregar habitaciones</h2>
      <p className="nota-clave">
        Crea de una vez varias habitaciones del mismo tipo (hasta {MAX_LOTE}). Nacen en servicio y limpias, y cotizan con
        el precio base de su tipo. Si alguna ya existe, no se crea ninguna.
      </p>
      <form className="formulario" onSubmit={crear}>
        <CampoSelect etiqueta="Tipo" value={form.tipoId} onChange={(e) => setForm({ ...form, tipoId: e.target.value })}>
          {activos.map((t) => (
            <option key={t.tipo_id} value={t.tipo_id}>{t.nombre}{t.precio_base_clp ? ` · ${clp(t.precio_base_clp)}` : ' · sin precio base'}</option>
          ))}
        </CampoSelect>
        <Campo etiqueta="Cantidad" type="number" min="1" max={MAX_LOTE} value={form.cantidad} onChange={(e) => setForm({ ...form, cantidad: e.target.value })} />
        <Campo etiqueta="Prefijo" value={form.prefijo} maxLength={20} onChange={(e) => setForm({ ...form, prefijo: e.target.value })} />
        <Campo etiqueta="Desde el número" type="number" min="0" placeholder={String(sugerido)} value={form.desde} onChange={(e) => setForm({ ...form, desde: e.target.value })} />
        <Campo etiqueta="Dígitos" type="number" min="1" max="5" value={form.digitos} onChange={(e) => setForm({ ...form, digitos: e.target.value })} />
        <Campo etiqueta="Capacidad" type="number" min="1" max="30" placeholder={tipo ? `${tipo.capacidad_base} (del tipo)` : ''} value={form.capacidad} onChange={(e) => setForm({ ...form, capacidad: e.target.value })} />
        <div className="lote-vista-previa" role="status">
          <span className="campo-etiqueta">Se crearán</span>
          <strong>{ids.length ? resumenIds(ids) : '—'}</strong>
          {tipo && !tipo.precio_base_clp && (
            <span className="lote-aviso">El tipo «{tipo.nombre}» no tiene precio base: las habitaciones quedarán sin precio y no se ofrecerán hasta fijarlo.</span>
          )}
          {problema && ids.length > 0 && <span className="lote-aviso">{problema}</span>}
        </div>
        <button type="submit" className="boton-primario" disabled={Boolean(problema)}>
          Crear {ids.length || ''} {ids.length === 1 ? 'habitación' : 'habitaciones'}
        </button>
      </form>
    </section>
  )
}

function NuevoTipo({ tasa, alConfirmar, alError }) {
  const [form, setForm] = useState({ nombre: '', tipo_id: '', capacidad_base: 2 })
  const [precio, setPrecio] = useState({ valor: '', en: 'con_iva' })
  const [clave, renovar] = useClaveOperacion()
  const codigo = form.tipo_id || codigoDesdeNombre(form.nombre)

  async function crear(e) {
    e.preventDefault()
    alError('')
    const monto = montoONulo(precio.valor)
    if (!form.nombre.trim()) return alError('Falta completar: Nombre.')
    if (!PATRON_ID_TIPO.test(codigo)) return alError('El código usa minúsculas, números y guion bajo (p. ej. suite_jardin).')
    if (Number.isNaN(monto)) return alError('El precio base debe ser un monto entero mayor que cero, o vacío.')
    try {
      const resp = await api('/hotel/tipos', {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: {
          tipo_id: codigo, nombre: form.nombre.trim(), capacidad_base: Number(form.capacidad_base),
          precio_base_clp: monto, precio_en: precio.en,
        },
      })
      if (resp.estado >= 400) {
        alError(mensajeDeError(resp.datos, resp.estado))
        alRechazar(resp.estado, renovar)
      } else {
        renovar()
        setForm({ nombre: '', tipo_id: '', capacidad_base: 2 })
        setPrecio({ valor: '', en: 'con_iva' })
        alConfirmar(resp.datos)
      }
    } catch {
      alError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  return (
    <section className="tarjeta" aria-labelledby="titulo-nuevo-tipo">
      <h2 id="titulo-nuevo-tipo">Nuevo tipo</h2>
      <form className="formulario" onSubmit={crear}>
        <Campo etiqueta="Nombre" placeholder="p. ej. Suite" maxLength={80} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
        <Campo etiqueta="Código" placeholder={codigo || 'suite'} value={form.tipo_id} onChange={(e) => setForm({ ...form, tipo_id: e.target.value })} />
        <Campo etiqueta="Capacidad base" type="number" min="1" max="30" value={form.capacidad_base} onChange={(e) => setForm({ ...form, capacidad_base: e.target.value })} />
        <CampoPrecio id="nuevo-tipo" etiqueta="Precio base por noche" valor={precio.valor} en={precio.en} tasa={tasa} alCambiar={setPrecio} />
        <button type="submit" className="boton-primario">Crear tipo</button>
      </form>
    </section>
  )
}
