'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import BarraNav from './barra.jsx'
import { useSesion } from '../lib/api'
import PantallaAcceso from './login/pantalla.jsx'

/** Rutas públicas: un visitante sin sesión las ve igual (V1-ISSUE-27 y
 *  V1-ISSUE-23: /reservar es la página de la landing y /privacidad es el
 *  aviso de tratamiento, fuera del menú). */
const RUTAS_PUBLICAS = ['/login', '/reservar', '/privacidad']

/** Estructura visual (V1-ISSUE-27): el chrome completo (sidebar + contenido)
 *  solo se pinta con sesión válida. Sin sesión, toda ruta interna muestra solo
 *  la pantalla de acceso — nunca el menú de operación (spec-front-v1 «Sin
 *  sesión: pantalla de login»); la API ya devolvía 401, pero la estructura
 *  interna quedaba expuesta. Al entrar, la sesión compartida actualiza el
 *  Lienzo y la página protegida aparece en la misma ruta (vuelta sin redirect). */
export default function Lienzo({ children }) {
  const ruta = usePathname()
  // UX: en rutas públicas no se consulta /sesion (evita el 401 de cada visita).
  if (RUTAS_PUBLICAS.includes(ruta)) return <>{children}</>
  return <LienzoPrivado>{children}</LienzoPrivado>
}

function LienzoPrivado({ children }) {
  const sesion = useSesion()

  if (sesion.fase === 'cargando')
    return (
      <main className="pagina">
        <p className="estado" role="status" aria-busy="true">Cargando…</p>
      </main>
    )
  if (sesion.fase === 'fuera') return <PantallaAcceso />
  if (sesion.fase === 'caida')
    return (
      <main className="pagina">
        <p role="alert" className="alerta">
          No se pudo conectar con el servidor. Nada se puede leer ni confirmar por el momento.
        </p>
      </main>
    )
  return (
    <div className="aplicacion">
      <BarraNav />
      <div className="contenido">
        {sesion.usuario?.mfa_pendiente && (
          <p role="status" className="alerta aviso-mfa-pendiente">
            Tu cuenta de administrador aún no tiene doble factor. Actívalo ahora con Google
            Authenticator en <Link href="/cuenta">Mi cuenta</Link>: desde entonces se pedirá el
            código en cada acceso.
          </p>
        )}
        {children}
      </div>
    </div>
  )
}
