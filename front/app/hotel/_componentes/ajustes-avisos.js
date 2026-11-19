'use client'

import { useCallback, useEffect, useState } from 'react'
import { api, mensajeDeError } from '../../../lib/api'
import {
  MAX_DESTINATARIOS, aQuienLlega, cuerpoPreferencias, estadoEnvio, filasDesdeApi, nombreCanal, textoCanal,
} from '../../../lib/avisos'
import { fechaHora, plural } from '../../../lib/formato'

function clave() {
  return `avi-${crypto.randomUUID().slice(0, 12)}`
}

const SIN_CONEXION = 'No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.'

/**
 * Avisos (2026-11-19): qué eventos llegan por correo a la administración de
 * Hotel Herencia y a quién, últimos envíos y correo de prueba. El buzón desde
 * el que salen se configura en la pestaña Correo.
 */
export default function AjustesAvisos() {
  const [datos, setDatos] = useState(null)
  const [filas, setFilas] = useState([])
  const [cambios, setCambios] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [ocupado, setOcupado] = useState(false)

  const cargar = useCallback(async (conFilas = true) => {
    try {
      const r = await api('/hotel/avisos/configuracion')
      if (r.estado === 200) {
        setDatos(r.datos)
        if (conFilas) {
          setFilas(filasDesdeApi(r.datos.preferencias))
          setCambios(false)
        }
      } else setError(mensajeDeError(r.datos, r.estado))
    } catch {
      setError(SIN_CONEXION)
    }
  }, [])

  useEffect(() => { cargar() }, [cargar])

  function cambiar(tipo, campo, valor) {
    setFilas((fs) => fs.map((f) => (f.tipo === tipo ? { ...f, [campo]: valor } : f)))
    setCambios(true)
    setAviso('')
  }

  async function guardar(e) {
    e.preventDefault()
    setError('')
    setAviso('')
    const { cuerpo, error: invalido } = cuerpoPreferencias(filas, datos?.max_destinatarios || MAX_DESTINATARIOS)
    if (invalido) {
      setError(invalido)
      return
    }
    setOcupado(true)
    try {
      const r = await api('/hotel/avisos/preferencias', { metodo: 'PUT', cuerpo, claveIdempotencia: clave() })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setAviso('Avisos guardados.')
        await cargar()
      }
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setOcupado(false)
    }
  }

  async function probar() {
    setError('')
    setAviso('')
    setOcupado(true)
    try {
      const r = await api('/hotel/avisos/prueba', { metodo: 'POST', cuerpo: {} })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else if (r.datos.ok) setAviso(r.datos.detalle)
      else setError(`No se envió el correo de prueba: ${r.datos.detalle}`)
      await cargar(false)
    } catch {
      setError(SIN_CONEXION)
    } finally {
      setOcupado(false)
    }
  }

  if (!datos) return error ? <p role="alert" className="alerta">{error}</p> : <p className="estado" role="status" aria-busy="true">Cargando…</p>

  const defecto = datos.destinatarios_defecto || []
  const sinCanal = !datos.canal || datos.canal.origen === 'ninguno'

  return (
    <>
      <section className="tarjeta">
        <h2>Avisos por correo</h2>
        <p className="nota-clave">
          La plataforma avisa por correo cuando pasa algo importante en Hotel Herencia. Los correos traen solo lo
          necesario (tipo, fechas de Llegada y Salida, personas y montos) y un enlace directo a la pantalla; los datos
          del huésped quedan en la plataforma.
        </p>
        <p className={sinCanal ? 'alerta' : 'nota-clave'} role={sinCanal ? 'alert' : undefined}>{textoCanal(datos.canal)}</p>
        <p className="nota-chica">
          Correo por defecto: {defecto.length ? defecto.join(', ') : 'ninguno'}. Se usa cuando un aviso no tiene lista propia.
        </p>
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      <section className="tarjeta">
        <h2>Qué avisa y a quién</h2>
        <form className="formulario" onSubmit={guardar}>
          <ul className="lista-aseo">
            {filas.map((f) => (
              <li key={f.tipo} className="tarjeta" data-aviso={f.tipo}>
                <label className="campo-check">
                  <input type="checkbox" checked={f.activo} onChange={(e) => cambiar(f.tipo, 'activo', e.target.checked)} />
                  <strong>{f.nombre}</strong>
                </label>
                <p className="nota-chica">
                  {f.tipo === 'resumen_diario'
                    ? `Cada mañana a las ${datos.hora_resumen || '08:00'} (hora de Chile): Llegadas y Salidas de hoy y solicitudes por responder.`
                    : f.descripcion}
                </p>
                <label className="campo">
                  <span className="campo-etiqueta">Destinatarios (separados por coma; vacío = correo por defecto)</span>
                  <textarea className="entrada" rows={2} value={f.texto} disabled={!f.activo} autoComplete="off"
                    placeholder={defecto.join(', ') || 'reservas@hotelherencia.cl'}
                    onChange={(e) => cambiar(f.tipo, 'texto', e.target.value)} />
                </label>
                <p className="nota-chica">{aQuienLlega(f, defecto)}</p>
              </li>
            ))}
          </ul>
          <div className="acciones-fila">
            <button type="submit" className="boton-primario" disabled={ocupado || !cambios}>Guardar avisos</button>
            <button type="button" className="boton-secundario" disabled={ocupado || sinCanal} onClick={probar}>
              Enviar correo de prueba
            </button>
          </div>
          {cambios && <p className="nota-chica">Hay cambios sin guardar. El correo de prueba usa lo guardado.</p>}
        </form>
      </section>

      <section className="tarjeta">
        <div className="aseo-cabecera">
          <h2>Últimos envíos</h2>
          <button type="button" className="boton-fantasma" disabled={ocupado} onClick={() => cargar(false)}>Actualizar</button>
        </div>
        {datos.envios.length === 0 ? (
          <p className="estado estado-vacio">Aún no se ha enviado ningún aviso.</p>
        ) : (
          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Últimos avisos enviados">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Aviso</th>
                  <th>Canal</th>
                  <th>Estado</th>
                  <th>Destinatarios</th>
                  <th>Detalle</th>
                </tr>
              </thead>
              <tbody>
                {datos.envios.map((v) => {
                  const [texto, clase] = estadoEnvio(v.estado)
                  return (
                    <tr key={`${v.evento_id}-${v.canal}`}>
                      <td className="celda-fecha">{fechaHora(v.actualizado_en)}</td>
                      <td>{v.nombre}</td>
                      <td>{nombreCanal(v.canal)}</td>
                      <td>
                        <span className={`reserva-estado ${clase}`}>{texto}</span>
                        {v.intentos > 1 && <span className="nota-chica"> {plural(v.intentos, 'intento')}</span>}
                      </td>
                      <td>{v.destinatarios.length ? v.destinatarios.join(', ') : '—'}</td>
                      <td>{v.detalle || '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="nota-chica">
          «Reintentando»: se vuelve a intentar solo, hasta 5 veces. «No enviado»: el aviso estaba apagado, no tenía
          destinatarios o era un resumen de otro día.
        </p>
      </section>
    </>
  )
}
