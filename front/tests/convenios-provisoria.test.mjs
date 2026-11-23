import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..')

test('SPEC-CONV-01 y SPEC-PROV-01: panel de convenios, reserva provisoria y cierre de caja cumplen invariantes UI', () => {
  const conveniosSrc = fs.readFileSync(path.join(ROOT, 'app/hotel/_componentes/convenios-panel.js'), 'utf8')
  const reservaSrc = fs.readFileSync(path.join(ROOT, 'app/hotel/reserva/page.js'), 'utf8')
  const clientesSrc = fs.readFileSync(path.join(ROOT, 'app/hotel/clientes/page.js'), 'utf8')
  const cajaSrc = fs.readFileSync(path.join(ROOT, 'app/hotel/_componentes/caja-contable.js'), 'utf8')

  assert.match(conveniosSrc, /BarraContextual/)
  assert.match(conveniosSrc, /SelectorFila/)
  assert.match(conveniosSrc, /tabIndex=\{0\}\s+role="region"/)
  assert.match(reservaSrc, /convenio_id/)
  assert.match(reservaSrc, /es_huesped_provisorio/)
  assert.match(clientesSrc, /ConveniosPanel/)
  assert.match(cajaSrc, /convenios_aplicados/)

  for (const [nombre, src] of [
    ['convenios-panel.js', conveniosSrc],
    ['reserva/page.js', reservaSrc],
    ['caja-contable.js', cajaSrc],
  ]) {
    assert.doesNotMatch(src, /check-?in|check-?out/i, `${nombre} no debe usar check-in/check-out`)
    assert.doesNotMatch(src, /\w\(e?s\)/, `${nombre} no debe usar (s)/(es)`)
  }
})
