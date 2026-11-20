// Exportación unificada de datos visibles (SPEC-02, 2026-11-20). Puro, sin JSX.

/** CSV con comillas dobles escapadas y BOM para que Excel lea tildes. */
export function aCsv(filas) {
  const celda = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`
  return '\uFEFF' + filas.map((f) => f.map(celda).join(',')).join('\n')
}

/** Formatea fecha/hora local DD/MM/YYYY HH:mm para el encabezado único. */
export function fechaEmisionLocal(fecha = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(fecha.getDate())}/${pad(fecha.getMonth() + 1)}/${fecha.getFullYear()} ${pad(fecha.getHours())}:${pad(fecha.getMinutes())}`
}

/** Construye la matriz con 1 formato único estándar (encabezado institucional,
 *  emisión, filtros, fila separadora, columnas ordenadas y filas limpias). */
export function construirTablaUnica({ titulo, filtros = '', columnas, filas, emitidoEn }) {
  const emision = emitidoEn || fechaEmisionLocal()
  const cabecera = [
    ['Hotel Herencia', titulo || 'Reporte'],
    ['Emitido el', emision],
  ]
  if (filtros && String(filtros).trim()) {
    cabecera.push(['Filtros aplicados', String(filtros).trim()])
  }
  cabecera.push([])
  cabecera.push(columnas)
  const cuerpo = (filas || []).map((fila) =>
    columnas.map((_, idx) => {
      const val = fila[idx]
      if (val === null || val === undefined) return ''
      if (typeof val === 'boolean') return val ? 'Sí' : 'No'
      return String(val)
    })
  )
  return cabecera.concat(cuerpo)
}

/** Genera y descarga el archivo CSV con el formato único institucional. */
export function exportarFormatoUnico({ titulo, filtros = '', columnas, filas, nombreArchivo }) {
  const tabla = construirTablaUnica({ titulo, filtros, columnas, filas })
  const contenido = aCsv(tabla)
  const enlace = document.createElement('a')
  enlace.href = URL.createObjectURL(new Blob([contenido], { type: 'text/csv;charset=utf-8' }))
  enlace.download = nombreArchivo || 'herencia-reporte.csv'
  enlace.click()
  URL.revokeObjectURL(enlace.href)
}

/** Valida el rango «desde/hasta» (aaaa-mm-dd, ambos opcionales). */
export function errorRango(desde, hasta) {
  if (desde && hasta && desde > hasta) return 'La fecha «desde» debe ser anterior o igual a «hasta».'
  return null
}

/** Parámetros de consulta del rango; sin «desde» pide todos (sin el corte de la bandeja). */
export function parametrosRango(desde, hasta) {
  const q = new URLSearchParams()
  if (desde) q.set('desde', desde)
  if (hasta) q.set('hasta', hasta)
  if (!desde) q.set('todos', 'true')
  return q
}

/** Sufijo del nombre de archivo: «2026-11-01_a_2026-11-19», «desde-…», «hasta-…» o «todo». */
export function sufijoRango(desde, hasta) {
  if (desde && hasta) return `${desde}_a_${hasta}`
  if (desde) return `desde-${desde}`
  if (hasta) return `hasta-${hasta}`
  return 'todo'
}
