'use client'

import { useEffect, useState } from 'react'

const BASE = process.env.API_BASE_URL

export class ApiCaida extends Error {}

/** URL absoluta de la API para recursos binarios (imágenes, descargas). */
export function urlApi(ruta) {
  return BASE + ruta
}

/** Cliente HTTP del front: solo habla con API_BASE_URL y jamás calcula negocio. */
export async function api(ruta, { metodo = 'GET', cuerpo, claveIdempotencia } = {}) {
  const cabeceras = {}
  let cuerpoSerializado
  if (cuerpo !== undefined) {
    cabeceras['Content-Type'] = 'application/json'
    cuerpoSerializado = JSON.stringify(cuerpo)
  }
  if (claveIdempotencia) cabeceras['Idempotency-Key'] = claveIdempotencia
  let respuesta
  try {
    respuesta = await fetch(BASE + ruta, {
      method: metodo,
      headers: cabeceras,
      body: cuerpoSerializado,
      credentials: 'include',
    })
  } catch (error) {
    throw new ApiCaida('la API no responde')
  }
  const texto = await respuesta.text()
  let datos = {}
  try {
    datos = texto ? JSON.parse(texto) : {}
  } catch {
    datos = { detalle: texto }
  }
  return { estado: respuesta.status, datos }
}

export function useSesion() {
  const [sesion, setSesion] = useState({ fase: 'cargando', usuario: null })
  useEffect(() => {
    api('/sesion')
      .then((r) =>
        setSesion(r.estado === 200 ? { fase: 'ok', usuario: r.datos } : { fase: 'fuera', usuario: null })
      )
      .catch(() => setSesion({ fase: 'caida', usuario: null }))
  }, [])
  return sesion
}

/** Marco común: con API caída muestra error y ninguna operación se confirma. */
export function MarcoHotel({ children, titulo }) {
  const sesion = useSesion()
  if (sesion.fase === 'cargando')
    return (
      <main className="pagina">
        <p className="estado">Cargando…</p>
      </main>
    )
  if (sesion.fase === 'caida')
    return (
      <main className="pagina">
        <h1>{titulo}</h1>
        <p role="alert" className="alerta">
          La API no está disponible: nada se puede leer ni confirmar.
        </p>
      </main>
    )
  if (sesion.fase === 'fuera')
    return (
      <main className="pagina">
        <h1>{titulo}</h1>
        <p>
          Sesión cerrada. <a href="/login">Inicia sesión</a>.
        </p>
      </main>
    )
  return (
    <main className="pagina">
      <header className="pagina-cabecera">
        <h1>{titulo}</h1>
        <p className="operador">
          Operando como {sesion.usuario.usuario} · {sesion.usuario.rol}
        </p>
      </header>
      {children}
    </main>
  )
}

export function SalidaJson({ datos }) {
  if (!datos) return null
  return <pre className="json-panel">{JSON.stringify(datos, null, 2)}</pre>
}

export function Campo({ etiqueta, ...props }) {
  return (
    <label className="campo">
      <span className="campo-etiqueta">{etiqueta}</span>
      <input className="entrada" {...props} />
    </label>
  )
}

export function CampoSelect({ etiqueta, children, ...props }) {
  return (
    <label className="campo">
      <span className="campo-etiqueta">{etiqueta}</span>
      <select className="entrada" {...props}>
        {children}
      </select>
    </label>
  )
}
