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

/**
 * Clave de idempotencia estable (spec-front-v1 «Idempotencia en el cliente»):
 * nace al montar el formulario, se muestra antes del primer envío, sobrevive
 * errores de red y 4xx/5xx, y solo se reemplaza tras un 2xx (o con
 * «Nueva operación»). Si el usuario cambia el cuerpo y reintenta con la clave
 * vieja, la API responde 409 y la clave se conserva: no se acuña en silencio.
 */
export function useClaveOperacion() {
  const [clave, setClave] = useState(() => crypto.randomUUID())
  const renovar = () => setClave(crypto.randomUUID())
  return [clave, renovar]
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

/** Devuelve un mensaje si falta algún campo obligatorio, o null si está completo.
 *  Evita llamar a la API con identificadores vacíos (404 crudos). */
export function camposFaltantes(pares) {
  const faltan = pares
    .filter(([valor]) => valor === undefined || valor === null || String(valor).trim() === '')
    .map(([, etiqueta]) => etiqueta)
  return faltan.length ? `Falta completar: ${faltan.join(', ')}.` : null
}

/** Interpreta el cuerpo de error de la API en texto legible. Los `detail` de
 *  negocio ya vienen en español; los códigos técnicos se traducen y las
 *  validaciones 422 (detail como arreglo) se listan en línea. */
export function mensajeDeError(datos, estado) {
  if (estado === 404) return 'No existe ese recurso: revisa el identificador ingresado.'
  const detalle = datos && datos.detail
  if (typeof detalle === 'string') {
    const traducciones = {
      codigo_totp_requerido: 'Ingresa el código del autenticador.',
    }
    return traducciones[detalle] || detalle
  }
  if (typeof datos?.error === 'string') return datos.error
  if (Array.isArray(detalle))
    return detalle
      .map((d) => {
        if (!d || typeof d !== 'object') return String(d)
        const campo = Array.isArray(d.loc) && d.loc.length > 1 ? `${d.loc[d.loc.length - 1]}: ` : ''
        return `${campo}${d.msg || JSON.stringify(d)}`
      })
      .join(' · ')
  if (estado === 401) return 'Sesión expirada. Inicia sesión de nuevo.'
  if (estado === 403) return 'Sin permisos para esta operación.'
  if (estado === 429) return 'Demasiados intentos. Espera unos minutos.'
  if (estado === 503) return 'Servicio no configurado en el servidor.'
  if (estado >= 500) return 'Error interno del servidor. Intenta más tarde.'
  return `Error ${estado}`
}

export function SalidaJson({ datos }) {
  if (!datos) return null
  return (
    <div>
      <p className="operacion-confirmada">Operación confirmada por el servidor</p>
      <details className="json-detalle">
        <summary>Ver detalle técnico</summary>
        <pre className="json-panel">{JSON.stringify(datos, null, 2)}</pre>
      </details>
    </div>
  )
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
