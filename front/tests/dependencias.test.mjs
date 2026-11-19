// Auditoría de seguridad 2026-11-17 (SA-DEP-01): Next.js 16.3.0–16.4.4 tiene
// un aviso moderado (Dependabot #1, divulgación entre root params con
// 'use cache' + unstable_cache). El lockfile debe resolver una versión
// corregida (≥ 16.4.5) para que Vercel no instale la vulnerable.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const lock = JSON.parse(readFileSync(new URL('../package-lock.json', import.meta.url), 'utf8'))

function comparar(a, b) {
  const pa = a.split('-')[0].split('.').map(Number)
  const pb = b.split('-')[0].split('.').map(Number)
  for (let i = 0; i < 3; i++) if (pa[i] !== pb[i]) return pa[i] - pb[i]
  return 0
}

test('next resuelto en el lockfile fuera del rango vulnerable 16.3.0–16.4.4', () => {
  const version = lock.packages['node_modules/next'].version
  const vulnerable = comparar(version, '16.3.0') >= 0 && comparar(version, '16.4.4') <= 0
  assert.equal(vulnerable, false, `next ${version} está en el rango vulnerable`)
})

test('package.json no permite volver a una versión vulnerable', () => {
  const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))
  const rango = pkg.dependencies.next.replace(/^[\^~]/, '')
  assert.ok(comparar(rango, '16.4.5') >= 0, `rango mínimo ${rango} < 16.4.5`)
})
