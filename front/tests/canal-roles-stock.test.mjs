import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const raiz = new URL('..', import.meta.url).pathname
const leer = (p) => readFileSync(join(raiz, p), 'utf8')

test('#324: panel muestra recaudación por canal y nueva reserva permite elegir canal', () => {
  const panel = leer('app/hotel/panel/page.js')
  assert.match(panel, /data-ingresos-por-canal/)
  assert.match(panel, /Recaudación por canal/)
  assert.match(panel, /clave="ingresos_por_canal"/)

  const reserva = leer('app/hotel/reserva/page.js')
  assert.match(reserva, /etiqueta="Canal de origen"/)
  assert.match(reserva, /canal: campos\.canal/)
})

test('#323: gestión de usuarios consulta el catálogo transversal /roles', () => {
  const usuarios = leer('app/hotel/usuarios/page.js')
  assert.match(usuarios, /api\('\/roles'\)/)
  assert.match(usuarios, /catalogoRoles/)
})

test('#358: productos incluye pestaña Stock y reposición conectada al core compartido', () => {
  const productos = leer('app/hotel/productos/page.js')
  assert.match(productos, /\['reposicion', 'Stock y reposición'\]/)
  assert.match(productos, /stock_minimo/)
  assert.match(productos, /<ReposicionStock/)

  const repo = leer('app/hotel/_componentes/reposicion-stock.js')
  assert.match(repo, /\/core\/stock\/reposicion/)
  assert.match(repo, /\/core\/stock\/transferencias/)
})

test('BarraNav usa visibilidad.soloAseo (sin ReferenceError al autenticar) y PantallaAcceso redirige si ya hay sesión', () => {
  const barra = leer('app/barra.jsx')
  assert.doesNotMatch(barra, /href=\{soloAseo\s*\?/)
  assert.match(barra, /href=\{visibilidad\.soloAseo\s*\?/)

  const pantalla = leer('app/login/pantalla.jsx')
  assert.match(pantalla, /if \(sesion\.fase === 'ok' && despues\) despues\(\)/)
})
