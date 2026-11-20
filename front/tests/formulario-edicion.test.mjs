import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

// El módulo importa React/api; solo se prueba la función pura de armado del cuerpo.
const fuente = await import('node:fs').then((fs) => fs.readFileSync(new URL('../app/hotel/_componentes/formulario-edicion.js', import.meta.url), 'utf8'))
const bloque = fuente.slice(fuente.indexOf('export function cuerpoPorDefecto'), fuente.indexOf('export default function'))
const { cuerpoPorDefecto } = new Function(`${bloque.replace('export function', 'function')}; return { cuerpoPorDefecto }`)()

describe('cuerpoPorDefecto', () => {
  const campos = [
    { nombre: 'nombre', requerido: true }, { nombre: 'giro' }, { nombre: 'huespedes', tipo: 'number' },
    { nombre: 'activo', tipo: 'checkbox' },
  ]
  it('recorta, manda null en opcionales vacíos, numera y convierte checkbox', () => {
    assert.deepEqual(cuerpoPorDefecto(campos, { nombre: ' Ana ', giro: '  ', huespedes: '3', activo: 1 }),
      { nombre: 'Ana', giro: null, huespedes: 3, activo: true })
    assert.deepEqual(cuerpoPorDefecto(campos, { nombre: 'Ana', giro: 'x', huespedes: '', activo: false }),
      { nombre: 'Ana', giro: 'x', huespedes: null, activo: false })
  })
})
