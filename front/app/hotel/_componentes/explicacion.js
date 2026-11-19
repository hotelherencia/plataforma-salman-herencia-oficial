'use client'

import { useEffect, useId, useRef, useState } from 'react'
import { EXPLICACIONES } from '../../../lib/explicaciones'

/**
 * «¿Cómo se calcula?» como ventana emergente accesible: se abre con clic,
 * toque o teclado (Enter/Espacio), se cierra con Escape, con «Cerrar» o
 * tocando fuera, y devuelve el foco al botón. En el teléfono aparece como
 * panel inferior para que se lea completo. Solo una abierta a la vez.
 */
const EVENTO = 'herencia:explicacion-abierta'

export function Explicacion({ clave, titulo }) {
  const e = EXPLICACIONES[clave]
  const [abierta, setAbierta] = useState(false)
  const [derecha, setDerecha] = useState(false)
  const id = useId()
  const boton = useRef(null)
  const panel = useRef(null)

  useEffect(() => {
    if (!abierta) return undefined
    const otra = (ev) => { if (ev.detail !== id) setAbierta(false) }
    const tecla = (ev) => { if (ev.key === 'Escape') { setAbierta(false); boton.current?.focus() } }
    const fuera = (ev) => {
      if (!panel.current?.contains(ev.target) && !boton.current?.contains(ev.target)) setAbierta(false)
    }
    window.addEventListener(EVENTO, otra)
    document.addEventListener('keydown', tecla)
    document.addEventListener('pointerdown', fuera)
    const r = panel.current?.getBoundingClientRect()
    if (r && r.right > window.innerWidth - 8) setDerecha(true)
    panel.current?.focus()
    return () => {
      window.removeEventListener(EVENTO, otra)
      document.removeEventListener('keydown', tecla)
      document.removeEventListener('pointerdown', fuera)
    }
  }, [abierta, id])

  if (!e) return null
  function alternar() {
    if (!abierta) { setDerecha(false); window.dispatchEvent(new CustomEvent(EVENTO, { detail: id })) }
    setAbierta((v) => !v)
  }
  return (
    <div className="explicacion">
      <button
        ref={boton}
        type="button"
        className="explicacion-boton"
        aria-expanded={abierta}
        aria-controls={`${id}-panel`}
        onClick={alternar}
      >
        <span className="explicacion-i" aria-hidden="true">i</span>
        ¿Cómo se calcula?
      </button>
      <div
        ref={panel}
        id={`${id}-panel`}
        role="dialog"
        aria-modal="false"
        aria-labelledby={`${id}-titulo`}
        tabIndex={-1}
        hidden={!abierta}
        className={`explicacion-panel${derecha ? ' a-la-derecha' : ''}`}
      >
        <p className="explicacion-titulo" id={`${id}-titulo`}>{titulo}</p>
        <p className="explicacion-mide">{e.mide}</p>
        <dl>
          <dt>Fórmula</dt>
          <dd>{e.formula}</dd>
          <dt>Qué cuenta</dt>
          <dd>{e.cuenta}</dd>
          <dt>Qué no cuenta</dt>
          <dd>{e.noCuenta}</dd>
          <dt>Ejemplo</dt>
          <dd>{e.ejemplo}</dd>
        </dl>
        <p className="explicacion-nota">Si eliges un tipo de habitación, se calcula solo con ese tipo.</p>
        <button type="button" className="explicacion-cerrar" onClick={() => { setAbierta(false); boton.current?.focus() }}>
          Cerrar
        </button>
      </div>
    </div>
  )
}
