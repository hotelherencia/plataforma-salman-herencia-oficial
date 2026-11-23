'use client'

/**
 * Barra contextual única para tablas y listados (auditoría UI/UX 2026-11-23).
 * Evita repetir los mismos botones de acción en cada una de las 10–30 filas:
 * el operador elige un registro activo (clic en fila o radio accesible de 44×44 px)
 * y opera desde esta barra única.
 */
export function BarraContextual({
  titulo = 'Acciones del registro',
  seleccionado = false,
  resumen = '',
  detalle = '',
  placeholder = 'Selecciona una fila de la tabla para ver sus acciones.',
  alLimpiar,
  children,
}) {
  return (
    <section
      className="barra-contextual"
      data-activa={seleccionado ? 'true' : 'false'}
      aria-label={titulo}
    >
      <div className="barra-contextual-info">
        <p className="barra-contextual-titulo">
          {seleccionado ? resumen : titulo}
        </p>
        <p className="barra-contextual-detalle">
          {seleccionado ? (detalle || 'Registro activo') : placeholder}
        </p>
      </div>
      {seleccionado && (
        <div className="barra-contextual-acciones">
          {children}
          {typeof alLimpiar === 'function' && (
            <button type="button" className="boton-fantasma" onClick={alLimpiar}>
              Quitar selección
            </button>
          )}
        </div>
      )}
    </section>
  )
}

/** Selector radio accesible con área táctil mínima 44×44 px (WCAG 2.5.8). */
export function SelectorFila({ nombreGrupo, elegido, etiqueta, alElegir }) {
  return (
    <label
      className="selector-fila"
      onClick={(e) => e.stopPropagation()}
    >
      <input
        type="radio"
        name={nombreGrupo}
        checked={Boolean(elegido)}
        onChange={alElegir}
        aria-label={etiqueta}
      />
    </label>
  )
}
