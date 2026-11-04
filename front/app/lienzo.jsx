'use client'

import { usePathname } from 'next/navigation'
import BarraNav from './barra.jsx'
import { useSesion } from '../lib/api'
import PantallaAcceso from './login/pantalla.jsx'

/** Rutas públicas: un visitante sin sesión las ve igual (V1-ISSUE-27). */
const RUTAS_PUBLICAS = ['/login']

/** Estructura visual (V1-ISSUE-27): el chrome completo (sidebar + contenido)
 *  solo se pinta con sesión válida. Sin sesión, toda ruta interna muestra solo
 *  la pantalla de acceso — nunca el menú de operación (spec-front-v1 «Sin
 *  sesión: pantalla de login»); la API ya devolvía 401, pero la estructura
 *  interna quedaba expuesta. Al entrar, la sesión compartida actualiza el
 *  Lienzo y la página protegida aparece en la misma ruta (vuelta sin redirect). */
export default function Lienzo({ children }) {
  const ruta = usePathname()
  const sesion = useSesion()

  if (RUTAS_PUBLICAS.includes(ruta)) return <>{children}</>
  if (sesion.fase === 'cargando')
    return (
      <main className="pagina">
        <p className="estado">Cargando…</p>
      </main>
    )
  if (sesion.fase === 'fuera') return <PantallaAcceso />
  if (sesion.fase === 'caida')
    return (
      <main className="pagina">
        <p role="alert" className="alerta">
          La API no está disponible: nada se puede leer ni confirmar.
        </p>
      </main>
    )
  return (
    <div className="aplicacion">
      <BarraNav />
      <div className="contenido">{children}</div>
    </div>
  )
}
