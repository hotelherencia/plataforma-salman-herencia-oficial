import Link from 'next/link'
import { ETIQUETA_GRAVEDAD, etiqueta, resumirAtencion } from '../../../lib/operacion-etiquetas'

const GRUPOS = [
  ['llegadas_atrasadas', 'Llegadas atrasadas', (i) => `${i.id} · ${i.habitacion_id} · llegada ${i.fecha}`],
  ['salidas_atrasadas', 'Salidas atrasadas', (i) => `${i.id} · ${i.habitacion_id} · salida ${i.fecha}`],
  ['limpiezas_por_verificar', 'Limpiezas por verificar', (i) => `Habitación ${i.habitacion_id}`],
  ['incidencias_abiertas', 'Incidencias abiertas', (i) => `${i.habitacion_id || 'Área común'} · ${etiqueta(ETIQUETA_GRAVEDAD, i.gravedad)}${i.bloquea ? ' · BLOQUEA LA HABITACIÓN' : ''} · ${i.descripcion}`],
  ['productos_bajo_minimo', 'Productos bajo el mínimo', (i) => `${i.nombre}${i.nivel === 'sin_stock' ? ' · sin stock' : ''}`],
]

/** #417: bloque superior del panel operativo; cada fila enlaza al registro de origen. */
export default function Atencion({ atencion }) {
  if (!atencion) return null
  return (
    <section className="tarjeta atencion" aria-label={`Lo que necesita atención: ${resumirAtencion(atencion)}`} data-atencion>
      <h2>Lo que necesita atención {atencion.total > 0 && <span className="insignia">{atencion.total}</span>}</h2>
      {atencion.total === 0 && <p className="estado" role="status">Todo al día: nada urgente por ahora.</p>}
      {GRUPOS.map(([clave, titulo, texto]) => {
        const items = atencion[clave] || []
        if (items.length === 0) return null
        return (
          <div key={clave} data-grupo={clave}>
            <h3 className="subtitulo">{titulo} ({items.length})</h3>
            <ul className="lista-simple">
              {items.map((i) => (
                <li key={`${clave}-${i.id}`}>
                  <Link href={i.enlace}>{texto(i)}</Link>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </section>
  )
}
