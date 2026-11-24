'use client'

import { useEffect, useState } from 'react'
import { api, alRechazar, mensajeDeError } from '../../../lib/api'
import { fechaHora } from '../../../lib/formato'
import { ETIQUETAS_ROL, apruebaCambiosDeRol } from '../../../lib/roles'

/* Cambios de rol pendientes. Un rol privilegiado en un alta y todo cambio de rol quedan pendientes
   hasta que los valida la administración del hotel; quien los pidió no los aprueba (la API lo exige). */

export default function CambiosDeRol({ rol }) {
  const [lista, setLista] = useState(null)
  const [error, setError] = useState('')
  const [version, setVersion] = useState(0)
  const puedeResolver = apruebaCambiosDeRol(rol)

  useEffect(() => {
    let vivo = true
    api('/usuarios/cambios-rol?estado=pendiente').then((r) => { if (vivo && r.estado === 200) setLista(r.datos.cambios) }).catch(() => {})
    return () => { vivo = false }
  }, [version])

  async function resolver(id, accion) {
    setError('')
    const r = await api(`/usuarios/cambios-rol/${id}/${accion}`, { metodo: 'POST' })
    if (r.estado >= 400) { setError(mensajeDeError(r.datos, r.estado)); alRechazar(r.estado, () => {}); return }
    setVersion((v) => v + 1)
  }

  if (!lista || lista.length === 0) return null
  const etiqueta = (c) => ETIQUETAS_ROL[c] || c
  return (
    <section className="tarjeta" aria-label="Cambios de rol pendientes">
      <h2>Cambios de rol pendientes de validación · {lista.length}</h2>
      {error && <p role="alert" className="alerta">{error}</p>}
      <ul className="lista-simple">
        {lista.map((c) => (
          <li key={c.id}>
            <strong>{c.usuario}</strong>: {c.rol_anterior ? `${etiqueta(c.rol_anterior)} → ` : 'alta como '}{etiqueta(c.rol_nuevo)}
            <div className="nota-clave">Pedido por {c.solicitado_por} · {fechaHora(c.solicitado_en)}{c.motivo ? ` · ${c.motivo}` : ''}</div>
            {puedeResolver ? (
              <div className="acciones-fila">
                <button type="button" className="boton-primario" onClick={() => resolver(c.id, 'aprobacion')}>Aprobar</button>
                <button type="button" className="boton-secundario" onClick={() => resolver(c.id, 'rechazo')}>Rechazar</button>
              </div>
            ) : (
              <p className="nota-chica">Lo valida la administración del hotel.</p>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
