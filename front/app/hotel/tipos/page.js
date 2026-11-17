'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  api, alRechazar, clp, mensajeDeError, MarcoHotel, SalidaJson, Campo, CampoSelect, useClaveOperacion, useSesion,
} from '../../../lib/api'
import {
  codigoDesdeNombre, etiquetaOrigen, idsDelLote, MAX_LOTE, montoONulo, PATRON_ID_TIPO, resumenIds,
  siguienteNumero, validarLote,
} from '../../../lib/tipos'

/**
 * Tipos y habitaciones (entrega 1A, plan modulo-hotel §5). Cada tipo tiene un
 * precio base que heredan todas sus habitaciones; una tarifa por fechas en la
 * ficha de una habitación manda sobre la base en esas fechas. Con 100
 * habitaciones no hay que cambiar precios uno a uno: se edita el tipo.
 * Administración edita y da de alta por lote; recepción y caja solo leen.
 * El precio de hoy y su origen los calcula la API (resolvedor único).
 */
export default function TiposYHabitaciones() {
  const sesion = useSesion()
  const [tipos, setTipos] = useState(null)
  const [puedeEditar, setPuedeEditar] = useState(false)
  const [idsExistentes, setIdsExistentes] = useState([])
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)
  const [editando, setEditando] = useState(null)

  const cargar = useCallback(async () => {
    try {
      const [rt, rh] = await Promise.all([api('/hotel/tipos'), api('/hotel/habitaciones')])
      if (rt.estado === 200) {
        setTipos(rt.datos.tipos)
        setPuedeEditar(Boolean(rt.datos.puede_editar))
      } else {
        setTipos([])
        setError(mensajeDeError(rt.datos, rt.estado))
      }
      if (rh.estado === 200) setIdsExistentes(rh.datos.habitaciones.map((h) => h.habitacion_id))
    } catch {
      setTipos([])
      setError('La API no está disponible')
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
    }
  }, [tipos])

  return (
    <MarcoHotel titulo="Tipos y habitaciones">
      <section className="tarjeta">
        <p className="nota-clave">
          Cada habitación pertenece a un <strong>tipo</strong>. El <strong>precio base</strong> del tipo lo heredan
          todas sus habitaciones: para cambiar el precio de 10 o 100 habitaciones basta con editar el tipo. Una
          tarifa por fechas cargada en la <Link href="/hotel/habitaciones">ficha de una habitación</Link> manda sobre
          la base en esas fechas, y las reservas ya confirmadas conservan su precio noche a noche.
        </p>
        {!puedeEditar && sesion.fase === 'ok' && (
          <p className="tipos-solo-lectura" role="note">Solo lectura: los tipos, precios y altas los edita Administración.</p>
        )}
        <dl className="tipos-totales">
          <div><dt>Tipos activos</dt><dd>{tipos ? totales.tipos : '—'}</dd></div>
          <div><dt>Habitaciones</dt><dd>{tipos ? totales.habitaciones : '—'}</dd></div>
          <div><dt>En servicio</dt><dd>{tipos ? totales.enServicio : '—'}</dd></div>
          <div className={totales.sinPrecio ? 'tipos-total-alerta' : ''}>
            <dt>Sin precio hoy</dt><dd>{tipos ? totales.sinPrecio : '—'}</dd>
          </div>
        </dl>
      </section>

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
              puedeEditar={puedeEditar}
              editando={editando === tipo.tipo_id}
              alEditar={() => { setSalida(null); setEditando(editando === tipo.tipo_id ? null : tipo.tipo_id) }}
              alConfirmar={alConfirmar}
              alError={setError}
            />
          ))}
        </div>
      )}

      {puedeEditar && tipos && (
        <div className="tipos-formularios">
          <AltaPorLote tipos={tipos} idsExistentes={idsExistentes} alConfirmar={alConfirmar} alError={setError} />
          <NuevoTipo alConfirmar={alConfirmar} alError={setError} />
        </div>
      )}
    </MarcoHotel>
  )
}

function TarjetaTipo({ tipo, puedeEditar, editando, alEditar, alConfirmar, alError }) {
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
          <strong>{tipo.precio_base_clp ? `${clp(tipo.precio_base_clp)}` : 'Sin precio base'}</strong>
          {tipo.precio_base_clp && <span className="tipo-precio-etiqueta">por noche</span>}
        </div>
      </header>

      <ul className="tipo-cifras">
        <li><strong>{r.habitaciones}</strong> {r.habitaciones === 1 ? 'habitación' : 'habitaciones'} · {r.en_servicio} en servicio</li>
        <li>
          Precio hoy: <strong>{r.precio_hoy_min_clp ? rango : '—'}</strong>
        </li>
        <li className="tipo-origenes">
          {r.heredan_precio_base > 0 && <span className="origen origen-tipo">{r.heredan_precio_base} heredan la base</span>}
          {r.con_tarifa_por_fechas > 0 && <span className="origen origen-tarifa">{r.con_tarifa_por_fechas} con tarifa por fechas</span>}
          {r.con_precio_propio > 0 && <span className="origen origen-habitacion">{r.con_precio_propio} con precio propio</span>}
          {r.sin_precio_hoy > 0 && <span className="origen origen-ninguno">{r.sin_precio_hoy} sin precio hoy</span>}
        </li>
      </ul>

      {tipo.habitaciones.length > 0 && (
        <details className="tipo-habitaciones">
          <summary>Ver habitaciones</summary>
          <ul>
            {tipo.habitaciones.map((h) => (
              <li key={h.habitacion_id} className={h.en_servicio ? '' : 'fuera'}>
                <Link href={`/hotel/habitaciones/${h.habitacion_id}`} title="Abrir ficha de la habitación">{h.habitacion_id}</Link>
                <span>{h.precio_hoy_clp ? clp(h.precio_hoy_clp) : '—'}</span>
                <span className={`origen origen-${h.origen_precio_hoy || 'ninguno'}`}>{etiquetaOrigen(h.origen_precio_hoy)}</span>
                {!h.en_servicio && <span className="tipo-fuera">fuera de servicio</span>}
              </li>
            ))}
          </ul>
        </details>
      )}

      {puedeEditar && (
        <button type="button" className="boton-secundario" onClick={alEditar} aria-expanded={editando}>
          {editando ? 'Cerrar edición' : 'Editar tipo y precio'}
        </button>
      )}
      {puedeEditar && editando && <EdicionTipo tipo={tipo} alConfirmar={alConfirmar} alError={alError} />}
    </article>
  )
}

function EdicionTipo({ tipo, alConfirmar, alError }) {
  const [form, setForm] = useState({
    nombre: tipo.nombre,
    capacidad_base: tipo.capacidad_base,
    precio_base_clp: tipo.precio_base_clp ?? '',
    activo: tipo.activo,
  })
  const [clave, renovar] = useClaveOperacion()
  const r = tipo.resumen
  const nuevoPrecio = montoONulo(form.precio_base_clp)
  const cambiaPrecio = nuevoPrecio !== (tipo.precio_base_clp ?? null)

  async function guardar(e) {
    e.preventDefault()
    alError('')
    if (Number.isNaN(nuevoPrecio)) return alError('El precio base debe ser un monto entero mayor que cero, o vacío para dejarlo sin precio.')
    if (!form.nombre.trim()) return alError('Falta completar: Nombre.')
    try {
      const resp = await api(`/hotel/tipos/${encodeURIComponent(tipo.tipo_id)}`, {
        metodo: 'PUT',
        claveIdempotencia: clave,
        cuerpo: {
          nombre: form.nombre.trim(),
          capacidad_base: Number(form.capacidad_base),
          precio_base_clp: nuevoPrecio,
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
      alError('La API no está disponible')
    }
  }

  return (
    <form className="formulario tipo-edicion" onSubmit={guardar}>
      <Campo etiqueta="Nombre" value={form.nombre} maxLength={80} onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
      <Campo etiqueta="Capacidad base" type="number" min="1" max="30" value={form.capacidad_base} onChange={(e) => setForm({ ...form, capacidad_base: e.target.value })} />
      <Campo etiqueta="Precio base por noche (CLP)" inputMode="numeric" placeholder="vacío = sin precio" value={form.precio_base_clp} onChange={(e) => setForm({ ...form, precio_base_clp: e.target.value })} />
      <label className="campo campo-casilla">
        <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
        <span>Tipo activo (admite altas nuevas)</span>
      </label>
      {cambiaPrecio && <ImpactoPrecio resumen={r} nuevoPrecio={nuevoPrecio} />}
      <button type="submit" className="boton-primario">Guardar cambios</button>
    </form>
  )
}

function ImpactoPrecio({ resumen: r, nuevoPrecio }) {
  const afectadas = nuevoPrecio ? r.heredan_precio_base + r.sin_precio_hoy : r.heredan_precio_base
  let texto
  if (nuevoPrecio && afectadas > 0) {
    texto = <>Desde ahora, <strong>{afectadas}</strong> {afectadas === 1 ? 'habitación cotizará' : 'habitaciones cotizarán'} {clp(nuevoPrecio)} por noche.</>
  } else if (!nuevoPrecio && afectadas > 0) {
    texto = <>Sin precio base, <strong>{afectadas}</strong> {afectadas === 1 ? 'habitación quedará' : 'habitaciones quedarán'} sin tarifa y no se ofrecerán.</>
  } else {
    texto = <>Hoy ninguna habitación de este tipo cambia de precio.</>
  }
  return (
    <p className="tipo-impacto" role="status">
      {texto}
      {r.con_tarifa_por_fechas > 0 && (
        <> {r.con_tarifa_por_fechas === 1 ? 'La habitación' : `Las ${r.con_tarifa_por_fechas} habitaciones`} con tarifa por fechas mantienen esa tarifa mientras esté vigente.</>
      )}
      {' '}El precio base se usa en las habitaciones nuevas del tipo y en las fechas sin tarifa. Las reservas confirmadas conservan su precio.
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
      alError('La API no está disponible')
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
            <span className="lote-aviso">El tipo «{tipo.nombre}» no tiene precio base: las habitaciones quedarán sin tarifa y no se ofrecerán hasta fijarlo.</span>
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

function NuevoTipo({ alConfirmar, alError }) {
  const [form, setForm] = useState({ nombre: '', tipo_id: '', capacidad_base: 2, precio_base_clp: '' })
  const [clave, renovar] = useClaveOperacion()
  const codigo = form.tipo_id || codigoDesdeNombre(form.nombre)

  async function crear(e) {
    e.preventDefault()
    alError('')
    const precio = montoONulo(form.precio_base_clp)
    if (!form.nombre.trim()) return alError('Falta completar: Nombre.')
    if (!PATRON_ID_TIPO.test(codigo)) return alError('El código usa minúsculas, números y guion bajo (p. ej. suite_jardin).')
    if (Number.isNaN(precio)) return alError('El precio base debe ser un monto entero mayor que cero, o vacío.')
    try {
      const resp = await api('/hotel/tipos', {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: { tipo_id: codigo, nombre: form.nombre.trim(), capacidad_base: Number(form.capacidad_base), precio_base_clp: precio },
      })
      if (resp.estado >= 400) {
        alError(mensajeDeError(resp.datos, resp.estado))
        alRechazar(resp.estado, renovar)
      } else {
        renovar()
        setForm({ nombre: '', tipo_id: '', capacidad_base: 2, precio_base_clp: '' })
        alConfirmar(resp.datos)
      }
    } catch {
      alError('La API no está disponible')
    }
  }

  return (
    <section className="tarjeta" aria-labelledby="titulo-nuevo-tipo">
      <h2 id="titulo-nuevo-tipo">Nuevo tipo</h2>
      <form className="formulario" onSubmit={crear}>
        <Campo etiqueta="Nombre" placeholder="p. ej. Suite" maxLength={80} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} />
        <Campo etiqueta="Código" placeholder={codigo || 'suite'} value={form.tipo_id} onChange={(e) => setForm({ ...form, tipo_id: e.target.value })} />
        <Campo etiqueta="Capacidad base" type="number" min="1" max="30" value={form.capacidad_base} onChange={(e) => setForm({ ...form, capacidad_base: e.target.value })} />
        <Campo etiqueta="Precio base por noche (CLP)" inputMode="numeric" placeholder="vacío = sin precio" value={form.precio_base_clp} onChange={(e) => setForm({ ...form, precio_base_clp: e.target.value })} />
        <button type="submit" className="boton-primario">Crear tipo</button>
      </form>
    </section>
  )
}
