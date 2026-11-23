'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError, useClaveOperacion } from '../../../lib/api'
import { fechaHora } from '../../../lib/formato'

/* #452 / #454: mensajes preformateados para el huésped y datos que faltan.
   Un solo selector de plantilla y una sola fila de acciones (sin botones por plantilla). */

const ESTADO = { enviado: 'enviado', fallido: 'falló el envío', abierto: 'WhatsApp abierto' }
const CANAL = { correo: 'correo', whatsapp_manual: 'WhatsApp' }

export default function MensajesHuesped({ reservaId }) {
  const [datos, setDatos] = useState(null)
  const [plantilla, setPlantilla] = useState('confirmacion')
  const [aviso, setAviso] = useState('')
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  const [clave, renovarClave] = useClaveOperacion()

  useEffect(() => {
    let vivo = true
    api(`/hotel/reservas/${encodeURIComponent(reservaId)}/mensajes`)
      .then((r) => { if (vivo && r.estado === 200) setDatos(r.datos) })
      .catch(() => {})
    return () => { vivo = false }
  }, [reservaId, version])

  if (!datos) return null
  const actual = datos.mensajes.find((m) => m.plantilla === plantilla) || datos.mensajes[0]

  async function registrar(canal) {
    setError('')
    setAviso('')
    const r = await api(`/hotel/reservas/${encodeURIComponent(reservaId)}/mensajes`, {
      metodo: 'POST', claveIdempotencia: clave, cuerpo: { plantilla: actual.plantilla, canal },
    })
    if (r.estado >= 400) {
      setError(mensajeDeError(r.datos, r.estado))
      alRechazar(r.estado, renovarClave)
      return false
    }
    renovarClave()
    setVersion((v) => v + 1)
    if (r.datos.estado === 'fallido') { setError('No se pudo enviar el correo. Revisa Configuración → Correo.'); return false }
    return true
  }

  async function copiar() {
    try { await navigator.clipboard.writeText(`${actual.asunto}\n\n${actual.texto}`); setAviso('Texto copiado.') }
    catch { setError('No se pudo copiar. Selecciona el texto y cópialo a mano.') }
  }

  async function abrirWhatsapp() {
    if (await registrar('whatsapp')) window.open(actual.whatsapp, '_blank', 'noopener')
  }

  async function enviarCorreo() {
    if (await registrar('correo')) setAviso(`Correo enviado a ${datos.contacto.correo}.`)
  }

  return (
    <section className="tarjeta" aria-label="Mensajes al huésped">
      <h2>Mensajes al huésped</h2>
      {datos.alerta && <p role="alert" className="alerta">{datos.alerta}</p>}
      {datos.datos_faltantes.length > 0 ? (
        <p className="nota-clave">Faltan: {datos.datos_faltantes.join('; ')}. Se completan en la pestaña Huéspedes.</p>
      ) : (
        <p className="nota-clave">Datos de contacto y documento completos.</p>
      )}
      <dl className="ficha-datos">
        <dt>Correo</dt><dd>{datos.contacto.correo || '—'}</dd>
        <dt>Teléfono</dt><dd>{datos.contacto.telefono || '—'}</dd>
      </dl>
      <div className="formulario">
        <label className="campo">
          <span className="campo-etiqueta">Mensaje</span>
          <select className="entrada" value={plantilla} onChange={(e) => setPlantilla(e.target.value)}>
            {datos.mensajes.map((m) => <option key={m.plantilla} value={m.plantilla}>{m.nombre}</option>)}
          </select>
        </label>
      </div>
      <p className="nota-clave"><strong>Asunto:</strong> {actual.asunto}</p>
      <pre className="mensaje-previa" tabIndex={0} aria-label="Texto del mensaje">{actual.texto}</pre>
      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}
      <div className="acciones-fila">
        <button type="button" className="boton-secundario" onClick={copiar}>Copiar texto</button>
        <button type="button" className="boton-secundario" onClick={abrirWhatsapp} disabled={!actual.whatsapp}
          title={actual.whatsapp ? undefined : 'La reserva no tiene teléfono'}>Abrir WhatsApp</button>
        <button type="button" className="boton-primario" onClick={enviarCorreo} disabled={!actual.puede_correo}
          title={actual.puede_correo ? undefined : 'La reserva no tiene correo'}>Enviar por correo</button>
      </div>
      {datos.historial.length > 0 && (
        <>
          <h3>Enviados</h3>
          <ul className="lista-simple">
            {datos.historial.map((h, i) => (
              <li key={i}>{fechaHora(h.creado_en)} · {h.plantilla} · {CANAL[h.canal] || h.canal} a {h.destino} · {ESTADO[h.estado] || h.estado} · {h.actor}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
