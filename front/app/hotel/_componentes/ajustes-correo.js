'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError, Campo, CampoSelect } from '../../../lib/api'
import {
  AUTENTICACIONES, ETIQUETAS_CAMPO, PRESETS, PROPOSITOS, PROVEEDORES, SEGURIDADES,
  aplicarPreset, camposVisibles, cuerpoBuzon, formularioVacio,
} from '../../../lib/correo'
import { plural } from '../../../lib/formato'

const NOMBRE_PROPOSITO = Object.fromEntries(PROPOSITOS)
const NOMBRE_PROVEEDOR = Object.fromEntries([...PROVEEDORES.lectura_enviados, ...PROVEEDORES.envio_avisos])

const AYUDA = {
  imap: 'Gmail y Yahoo piden una clave de aplicación (con verificación en dos pasos). Microsoft 365 suele exigir OAuth2.',
  smtp: 'Para Gmail y Outlook usa una clave de aplicación u OAuth2. En hosting propio, el usuario es la casilla completa.',
  gmail_api: 'Workspace: cuenta de servicio con delegación de dominio y alcance gmail.metadata (lectura) o gmail.send (envío). Gmail personal: OAuth2 con refresh token.',
  microsoft_graph: 'Registra una aplicación en Entra ID con permiso de aplicación Mail.ReadBasic.All (lectura) o Mail.Send (envío) y consentimiento del administrador.',
}

function clave() {
  return `cor-${crypto.randomUUID().slice(0, 12)}`
}

function fecha(iso) {
  return iso ? iso.slice(0, 16).replace('T', ' ') : '—'
}

/**
 * Correo (#355): servidores de correo configurables. Buzones que leen los
 * enviados (para marcar leads contactados) y el buzón que envía los avisos.
 * Las claves se guardan cifradas y nunca se vuelven a mostrar.
 */
export default function AjustesCorreo() {
  const [datos, setDatos] = useState(null)
  const [form, setForm] = useState(null)
  const [revision, setRevision] = useState(null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [ocupado, setOcupado] = useState(false)

  const cargar = useCallback(async () => {
    try {
      const r = await api('/hotel/correo/buzones')
      if (r.estado === 200) {
        setDatos(r.datos)
        setRevision(r.datos.revision)
      } else setError(mensajeDeError(r.datos, r.estado))
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  async function llamar(ruta, metodo, cuerpo, ok, conClave = true) {
    setError('')
    setAviso('')
    setOcupado(true)
    try {
      const r = await api(ruta, { metodo, cuerpo, ...(conClave ? { claveIdempotencia: clave() } : {}) })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        return null
      }
      if (ok) setAviso(typeof ok === 'function' ? ok(r.datos) : ok)
      await cargar()
      return r.datos
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
      return null
    } finally {
      setOcupado(false)
    }
  }

  async function guardarRevision(e) {
    e.preventDefault()
    await llamar('/hotel/ajustes/revision_correo', 'PUT', {
      activo: revision.activo, registrar_buzon: revision.registrar_buzon, intervalo_minutos: Number(revision.intervalo_minutos),
    }, 'Revisión guardada.')
  }

  async function guardarBuzon(e) {
    e.preventDefault()
    if (form.etiqueta.trim().length < 2) {
      setError('Ponle un nombre al buzón (por ejemplo «reservas» o «comercial»).')
      return
    }
    const cuerpo = cuerpoBuzon(form)
    const ok = form.buzon_id
      ? await llamar(`/hotel/correo/buzones/${form.buzon_id}`, 'PUT', cuerpo, `Buzón «${cuerpo.etiqueta}» actualizado.`)
      : await llamar('/hotel/correo/buzones', 'POST', cuerpo, `Buzón «${cuerpo.etiqueta}» creado. Prueba la conexión.`)
    if (ok) setForm(null)
  }

  function editar(b) {
    setForm({
      buzon_id: b.buzon_id, etiqueta: b.etiqueta, proposito: b.proposito, proveedor: b.proveedor, activo: b.activo,
      autenticacion: b.parametros.autenticacion || AUTENTICACIONES[b.proveedor][0][0],
      parametros: { ...b.parametros }, secretos: {}, guardados: b.secretos_guardados,
    })
  }

  const probar = (b) => llamar(`/hotel/correo/buzones/${b.buzon_id}/prueba`, 'POST', {},
    (d) => (d.ok ? `«${b.etiqueta}»: ${d.detalle}` : `«${b.etiqueta}» falló: ${d.detalle}`), false)
  const eliminar = (b) => {
    if (window.confirm(`¿Eliminar el buzón «${b.etiqueta}»? Se borran sus claves guardadas.`)) {
      llamar(`/hotel/correo/buzones/${b.buzon_id}`, 'DELETE', undefined, `Buzón «${b.etiqueta}» eliminado.`)
    }
  }
  const revisarAhora = () => llamar('/hotel/correo/revision', 'POST', {},
    (d) => `Revisión: ${plural(d.buzones, 'buzón', 'buzones')}, ${plural(d.mensajes, 'mensaje enviado', 'mensajes enviados')}, ${plural(d.leads_contactados, 'lead marcado como contactado', 'leads marcados como contactados')}${d.errores ? `, ${d.errores} con error` : ''}.`, false)

  if (!datos) return error ? <p role="alert" className="alerta">{error}</p> : <p className="estado" role="status" aria-busy="true">Cargando…</p>

  const visibles = form ? camposVisibles(form.proposito, form.proveedor, form.autenticacion) : null
  const setParam = (c, v) => setForm({ ...form, parametros: { ...form.parametros, [c]: v } })
  const setSecreto = (s, v) => setForm({ ...form, secretos: { ...form.secretos, [s]: v } })

  return (
    <>
      {!datos.cifrado_disponible && (
        <p role="alert" className="alerta">
          Por ahora no se pueden guardar claves de correo: falta completar la protección de claves en el servidor.
          Pide a soporte técnico que la active (variable <code>CORREO_CLAVE_CIFRADO</code>).
        </p>
      )}
      <section className="tarjeta">
        <h2>Revisión de correos enviados</h2>
        <p className="nota-clave">
          Si el hotel ya le escribió por correo a un lead nuevo, pasa solo a «contactado» con la nota
          «auto: correo enviado desde &lt;buzón&gt; el &lt;fecha&gt;». Solo se leen destinatarios y fecha, nunca el
          contenido. Se puede deshacer desde Leads.
        </p>
        {revision && (
          <form className="formulario" onSubmit={guardarRevision}>
            <label className="campo-check">
              <input type="checkbox" checked={revision.activo} onChange={(e) => setRevision({ ...revision, activo: e.target.checked })} />
              Revisión automática activa
            </label>
            <Campo etiqueta="Cada cuántos minutos" type="number" min="5" max="1440" value={revision.intervalo_minutos}
              onChange={(e) => setRevision({ ...revision, intervalo_minutos: e.target.value })} />
            <label className="campo-check">
              <input type="checkbox" checked={revision.registrar_buzon} onChange={(e) => setRevision({ ...revision, registrar_buzon: e.target.checked })} />
              Registrar en la nota desde qué buzón se respondió
            </label>
            <div className="acciones-fila">
              <button type="submit" className="boton-primario" disabled={ocupado}>Guardar</button>
              <button type="button" className="boton-secundario" disabled={ocupado} onClick={revisarAhora}>Revisar ahora</button>
            </div>
          </form>
        )}
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      <section className="tarjeta">
        <h2>Buzones ({datos.buzones.length})</h2>
        {datos.buzones.length === 0 && <p className="estado estado-vacio">Aún no hay buzones. Agrega el de reservas y el comercial.</p>}
        <ul className="lista-aseo">
          {datos.buzones.map((b) => (
            <li key={b.buzon_id} className="tarjeta" data-buzon={b.buzon_id}>
              <div className="aseo-cabecera">
                <strong>{b.etiqueta}</strong>
                <span>{NOMBRE_PROPOSITO[b.proposito]}</span>
                <span>{NOMBRE_PROVEEDOR[b.proveedor]}</span>
                <span>{b.parametros.usuario || b.parametros.host || ''}</span>
                <span className={`reserva-estado ${b.activo ? 'estado-confirmada' : 'estado-cancelada'}`}>{b.activo ? 'activo' : 'inactivo'}</span>
              </div>
              {b.proposito === 'lectura_enviados' && (
                <p className="nota-clave">
                  Última revisión: {fecha(b.ultima_revision_en)}{b.ultimo_resultado ? ` · ${b.ultimo_resultado}` : ''}
                </p>
              )}
              {b.ultimo_error && <p className="alerta">Error: {b.ultimo_error}</p>}
              <div className="acciones-aseo">
                <button type="button" className="boton-secundario" disabled={ocupado} onClick={() => probar(b)}>Probar conexión</button>
                <button type="button" className="boton-fantasma" onClick={() => editar(b)}>Editar</button>
                <button type="button" className="boton-fantasma" onClick={() => eliminar(b)}>Eliminar</button>
              </div>
            </li>
          ))}
        </ul>
        {!form && (
          <div className="acciones-fila">
            <button type="button" className="boton-primario" onClick={() => setForm(formularioVacio('lectura_enviados'))}>Agregar buzón de lectura</button>
            <button type="button" className="boton-secundario" onClick={() => setForm(formularioVacio('envio_avisos'))}>Configurar envío de avisos</button>
          </div>
        )}
      </section>
      {form && (
        <section className="tarjeta">
          <h2>{form.buzon_id ? `Editar «${form.etiqueta}»` : 'Nuevo buzón'}</h2>
          <form className="formulario" onSubmit={guardarBuzon}>
            <Campo etiqueta="Nombre del buzón" placeholder="reservas, comercial…" value={form.etiqueta}
              onChange={(e) => setForm({ ...form, etiqueta: e.target.value })} />
            <CampoSelect etiqueta="Uso" value={form.proposito} disabled={Boolean(form.buzon_id)}
              onChange={(e) => setForm({ ...formularioVacio(e.target.value), etiqueta: form.etiqueta })}>
              {PROPOSITOS.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
            </CampoSelect>
            <CampoSelect etiqueta="Tipo de servidor" value={form.proveedor}
              onChange={(e) => setForm({ ...form, proveedor: e.target.value, autenticacion: AUTENTICACIONES[e.target.value][0][0], parametros: {}, secretos: {} })}>
              {PROVEEDORES[form.proposito].map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
            </CampoSelect>
            {['imap', 'smtp'].includes(form.proveedor) && (
              <CampoSelect etiqueta="Proveedor conocido (rellena servidor y puerto)" value="" onChange={(e) => setForm(aplicarPreset(form, e.target.value))}>
                <option value="">— elegir para rellenar —</option>
                {PRESETS.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
              </CampoSelect>
            )}
            {AUTENTICACIONES[form.proveedor].length > 1 && (
              <CampoSelect etiqueta="Autenticación" value={form.autenticacion} onChange={(e) => setForm({ ...form, autenticacion: e.target.value })}>
                {AUTENTICACIONES[form.proveedor].map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
              </CampoSelect>
            )}
            <p className="nota-chica">{AYUDA[form.proveedor]}</p>
            {visibles.parametros.map((c) => (c === 'seguridad' ? (
              <CampoSelect key={c} etiqueta={ETIQUETAS_CAMPO[c]} value={form.parametros.seguridad || (form.proveedor === 'imap' ? 'ssl' : 'starttls')}
                onChange={(e) => setParam(c, e.target.value)}>
                {SEGURIDADES.map(([id, nombre]) => <option key={id} value={id}>{nombre}</option>)}
              </CampoSelect>
            ) : (
              <Campo key={c} etiqueta={ETIQUETAS_CAMPO[c]} type={c === 'puerto' ? 'number' : 'text'} autoComplete="off"
                value={form.parametros[c] ?? ''} onChange={(e) => setParam(c, e.target.value)} />
            )))}
            {visibles.secretos.map((s) => {
              const guardado = form.guardados?.includes(s)
              const props = {
                value: form.secretos[s] || '', autoComplete: 'new-password',
                placeholder: guardado ? 'guardado: dejar vacío para mantener' : '',
                onChange: (e) => setSecreto(s, e.target.value),
              }
              return s === 'cuenta_servicio_json' ? (
                <label key={s} className="campo">
                  <span className="campo-etiqueta">{ETIQUETAS_CAMPO[s]}</span>
                  <textarea className="entrada" rows={5} {...props} />
                </label>
              ) : (
                <Campo key={s} etiqueta={ETIQUETAS_CAMPO[s]} type="password" {...props} />
              )
            })}
            <label className="campo-check">
              <input type="checkbox" checked={form.activo} onChange={(e) => setForm({ ...form, activo: e.target.checked })} />
              Activo{form.proposito === 'envio_avisos' ? ' (reemplaza al envío configurado por variables)' : ''}
            </label>
            <div className="acciones-fila">
              <button type="submit" className="boton-primario" disabled={ocupado || !datos.cifrado_disponible}>Guardar</button>
              <button type="button" className="boton-fantasma" onClick={() => setForm(null)}>Cancelar</button>
            </div>
          </form>
        </section>
      )}
    </>
  )
}
