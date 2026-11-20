'use client'

import { exportarFormatoUnico } from '../../../lib/exportacion'

/** Botón único de exportación para todas las tablas/datos visibles (SPEC-02). */
export function BotonExportar({
  titulo,
  filtros = '',
  columnas = [],
  filas = [],
  nombreArchivo,
  etiqueta = 'Exportar datos (formato único)',
  disabled = false,
}) {
  return (
    <button
      type="button"
      className="boton-secundario"
      disabled={disabled || !filas || filas.length === 0}
      onClick={() => exportarFormatoUnico({ titulo, filtros, columnas, filas, nombreArchivo })}
    >
      {etiqueta}
    </button>
  )
}
