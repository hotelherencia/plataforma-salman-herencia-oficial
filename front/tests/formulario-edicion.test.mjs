import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

// El módulo importa React/api; solo se prueban las funciones puras y las garantías de accesibilidad.
const fuente = await import('node:fs').then((fs) => fs.readFileSync(new URL('../app/hotel/_componentes/formulario-edicion.js', import.meta.url), 'utf8'))
const inicio = fuente.indexOf('const PATRON_CORREO')
const fin = fuente.indexOf('export default function')
const bloque = fuente.slice(inicio, fin).replace(/export function/g, 'function')
const { cuerpoPorDefecto, validarCampos } = new Function(`${bloque}; return { cuerpoPorDefecto, validarCampos }`)()

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

describe('validarCampos y accesibilidad de FormularioEdicion', () => {
  it('detecta obligatorios, correos inválidos, números inválidos y validadores propios', () => {
    const campos = [
      { nombre: 'nombre', etiqueta: 'Nombre', requerido: true },
      { nombre: 'correo', etiqueta: 'Correo', tipo: 'email' },
      { nombre: 'personas', etiqueta: 'Personas', tipo: 'number' },
      { nombre: 'rut', etiqueta: 'RUT', validar: (v) => (v === 'mal' ? 'RUT inválido.' : undefined) },
    ]
    const err = validarCampos(campos, { nombre: '  ', correo: 'sin-arroba', personas: 'abc', rut: 'mal' })
    assert.equal(err.nombre, 'Nombre es obligatorio.')
    assert.match(err.correo, /correo válido/)
    assert.match(err.personas, /número válido/)
    assert.equal(err.rut, 'RUT inválido.')
    assert.deepEqual(validarCampos(campos, { nombre: 'Ana', correo: 'ana@ejemplo.cl', personas: '2', rut: 'ok' }), {})
  })

  it('expone aria-invalid, aria-describedby, noValidate y foco al primer error', () => {
    assert.match(fuente, /noValidate/)
    assert.match(fuente, /'aria-invalid': msgError \? 'true' : undefined/)
    assert.match(fuente, /'aria-describedby': msgError \? idError : undefined/)
    assert.match(fuente, /enfocarElemento\(refs\.current\[primeroConError\.nombre\]\)/)
    assert.match(fuente, /role="alert"[^>]*ref=\{refAlerta\}/)
  })
})
