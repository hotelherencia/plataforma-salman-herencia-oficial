// «¿Cómo se calcula?» (UI/UX 2026-11-19): cada indicador que entrega el
// servidor tiene su explicación completa, en castellano de Chile, sin
// identificadores internos ni jerga en inglés.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { AUN_NO_DISPONIBLES, EXPLICACIONES } from '../lib/explicaciones.js'

const raiz = new URL('..', import.meta.url).pathname
const leer = (p) => readFileSync(join(raiz, p), 'utf8')
const CAMPOS = ['mide', 'formula', 'cuenta', 'noCuenta', 'ejemplo']

function indicadoresDelServidor() {
  const py = leer('../servicio/panel.py')
  const claves = [...py.matchAll(/"([a-z_]+)": (?:_indicador|_conteo_reservas|\{\s*\n\s*\*\*)/g)].map((m) => m[1])
  claves.push(...[...py.matchAll(/periodo\["([a-z_]+)"\] = _indicador/g)].map((m) => m[1]))
  return claves
}

test('todo indicador del servidor tiene explicación con los cinco apartados', () => {
  const claves = indicadoresDelServidor()
  assert.ok(claves.length >= 20, `se esperaban ≥ 20 indicadores, hay ${claves.length}`)
  for (const clave of claves) {
    const e = EXPLICACIONES[clave]
    assert.ok(e, `falta la explicación de ${clave}`)
    for (const campo of CAMPOS) assert.ok(e[campo] && e[campo].trim().length > 10, `${clave}.${campo} vacío`)
    assert.match(e.formula, /=/, `${clave}: la fórmula se escribe «X = …»`)
    assert.match(e.ejemplo, /\d/, `${clave}: el ejemplo lleva números`)
  }
})

test('cada tarjeta del panel usa su explicación', () => {
  const panel = leer('app/hotel/panel/page.js')
  const enPantalla = [
    ...[...panel.matchAll(/\['([a-z_]+)', '/g)].map((m) => m[1]),
    ...[...panel.matchAll(/clave="([a-z_]+)"/g)].map((m) => m[1]),
  ]
  assert.ok(enPantalla.length >= 20)
  for (const clave of enPantalla) assert.ok(EXPLICACIONES[clave], `la tarjeta ${clave} no tiene explicación`)
})

const PROHIBIDO = [
  [/\b[a-z]+_[a-z_]+\b/, 'identificador con guion bajo'],
  [/#\d+|\bD-[A-Z]+-\d+|\bV1\b|SUPUESTO|\bnull\b|\bjoin\b/i, 'referencia interna'],
  [/check-?in|check-?out|no-?show|booking|revenue|occupancy|\brate\b|\bunits?\b|\bnights?\b|\brooms?\b/i, 'jerga en inglés'],
  [/\d\.\d+ ?%/, 'porcentaje con punto decimal'],
]

test('explicaciones sin identificadores internos ni jerga en inglés', () => {
  const textos = [
    ...Object.entries(EXPLICACIONES).flatMap(([clave, e]) => CAMPOS.map((c) => [`${clave}.${c}`, e[c]])),
    ...AUN_NO_DISPONIBLES.flatMap((i) => [[i.nombre, i.nombre], [i.nombre, i.texto]]),
  ]
  for (const [donde, texto] of textos) {
    for (const [re, motivo] of PROHIBIDO) assert.doesNotMatch(texto, re, `${donde}: ${motivo}`)
  }
})

test('ADR y RevPAR se nombran una sola vez, entre paréntesis, junto a su nombre en castellano', () => {
  const todo = JSON.stringify(EXPLICACIONES) + JSON.stringify(AUN_NO_DISPONIBLES)
  assert.equal((todo.match(/\(ADR\)/g) || []).length, 1)
  assert.equal((todo.match(/\(RevPAR\)/g) || []).length, 1)
  assert.equal((todo.match(/\bADR\b/g) || []).length, 1)
})

test('la ventana de explicación es accesible: botón con estado, Escape y cierre', () => {
  const c = leer('app/hotel/_componentes/explicacion.js')
  assert.match(c, /aria-expanded={abierta}/)
  assert.match(c, /aria-controls=/)
  assert.match(c, /role="dialog"/)
  assert.match(c, /ev\.key === 'Escape'/)
  assert.match(c, /boton\.current\?\.focus\(\)/)
  assert.match(c, /pointerdown/, 'se cierra al tocar fuera (teléfono)')
  assert.match(c, />\s*Cerrar\s*</)
  assert.match(leer('app/diseno.css'), /@media \(max-width: 600px\) {\s*\.explicacion-panel,/)
})
