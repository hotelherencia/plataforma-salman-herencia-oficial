import test from 'node:test'
import assert from 'node:assert/strict'
import { ROLES, esAdminHotel, esAdminPlataforma, exigeDobleFactor, gestionaRecepcion, etiquetaRol } from '../lib/roles.js'

test('roles: administrador histórico conserva ambas administraciones', () => {
  assert.ok(esAdminHotel('administrador'))
  assert.ok(esAdminPlataforma('administrador'))
})

test('roles: hotel y plataforma separados; recepción y caja sin administración', () => {
  assert.ok(esAdminHotel('admin_hotel'))
  assert.ok(!esAdminPlataforma('admin_hotel'))
  assert.ok(esAdminPlataforma('admin_plataforma'))
  assert.ok(!esAdminHotel('admin_plataforma'))
  for (const rol of ['recepcion', 'caja', null, undefined]) {
    assert.ok(!esAdminHotel(rol))
    assert.ok(!esAdminPlataforma(rol))
    assert.ok(!exigeDobleFactor(rol))
  }
})

test('roles: doble factor para todo rol administrativo; bandejas para recepción y admin del hotel', () => {
  for (const rol of ['administrador', 'admin_hotel', 'admin_plataforma']) assert.ok(exigeDobleFactor(rol))
  assert.ok(gestionaRecepcion('recepcion'))
  assert.ok(gestionaRecepcion('admin_hotel'))
  assert.ok(!gestionaRecepcion('admin_plataforma'))
  assert.ok(!gestionaRecepcion('caja'))
  assert.equal(ROLES.length, 5)
  assert.equal(etiquetaRol('admin_hotel'), 'Administrador del hotel')
  assert.equal(etiquetaRol('desconocido'), 'desconocido')
})
