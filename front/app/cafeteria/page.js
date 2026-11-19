'use client'

import { MarcoHotel } from '../../lib/api'

// Ruta nombrada y vacía en V1 (spec-front-v1). MarcoHotel aplica la misma
// guardia de sesión que el resto de la plataforma (V1-ISSUE-38): sin sesión
// pide login, con API caída lo anuncia, y el contenido vive en .pagina.
export default function Modulo() {
  return (
    <MarcoHotel titulo="Cafetería">
      <p className="estado">Módulo de cafetería en preparación. Estará disponible en una próxima versión.</p>
    </MarcoHotel>
  )
}
