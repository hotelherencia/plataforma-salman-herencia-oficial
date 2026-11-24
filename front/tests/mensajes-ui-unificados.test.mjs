import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..')

function listarJs(dir) {
  const salida = []
  for (const entrada of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entrada.name.startsWith('.') || entrada.name === 'node_modules') continue
    const ruta = path.join(dir, entrada.name)
    if (entrada.isDirectory()) salida.push(...listarJs(ruta))
    else if (/\.(js|jsx|mjs)$/.test(entrada.name)) salida.push(ruta)
  }
  return salida
}

test('Unificación de mensajes y diálogos: cero window.alert/confirm/prompt nativos en front', () => {
  const archivos = [...listarJs(path.join(ROOT, 'app')), ...listarJs(path.join(ROOT, 'lib'))]
  const hallazgos = []
  for (const archivo of archivos) {
    const src = fs.readFileSync(archivo, 'utf8')
    if (/\bwindow\.(alert|confirm|prompt)\s*\(/.test(src)) {
      hallazgos.push(path.relative(ROOT, archivo))
    }
  }
  assert.deepEqual(hallazgos, [], `Quedan diálogos nativos del navegador en: ${hallazgos.join(', ')}`)
})

test('Centro de mensajes accesible montado en layout global y estilos unificados en diseno.css', () => {
  const layout = fs.readFileSync(path.join(ROOT, 'app/layout.js'), 'utf8')
  const centro = fs.readFileSync(path.join(ROOT, 'app/_componentes/centro-mensajes.js'), 'utf8')
  const css = fs.readFileSync(path.join(ROOT, 'app/diseno.css'), 'utf8')

  assert.match(layout, /ProveedorMensajes/)
  assert.match(centro, /role="alertdialog"/)
  assert.match(centro, /aria-modal="true"/)
  assert.match(centro, /Escape/)
  assert.match(centro, /toast-pila/)
  assert.match(centro, /export function AvisoLinea/)
  assert.doesNotMatch(centro, /\w\(e?s\)/)
  assert.doesNotMatch(centro, /check-?in|check-?out/i)

  for (const selector of [
    '.alerta',
    '.aviso-ok',
    '.aviso-ok::before',
    '.aviso',
    '.aviso::before',
    '.aviso-info',
    '.dialogo-fondo',
    '.dialogo-modal',
    '.toast-pila',
    '.toast-exito',
    '.toast-error',
  ]) {
    assert.ok(css.includes(selector), `Falta el estilo unificado ${selector} en app/diseno.css`)
  }
})
