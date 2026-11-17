// Roles y permisos en el front (entrega 1A.2), espejo de servicio/roles.py.
// La API decide: esto solo muestra u oculta acciones.
//
// - admin_hotel: Administrador del hotel (precios, tipos, habitaciones,
//   reservas, cobros, caja, reportes).
// - admin_plataforma: Administrador de plataforma (usuarios, seguridad,
//   ajustes del sistema como la tasa de IVA).
// - administrador: rol histórico = ambas administraciones.

export const ROLES = ['administrador', 'admin_hotel', 'admin_plataforma', 'recepcion', 'caja']

export const ETIQUETAS_ROL = {
  administrador: 'Administrador (hotel y plataforma)',
  admin_hotel: 'Administrador del hotel',
  admin_plataforma: 'Administrador de plataforma',
  recepcion: 'Recepción',
  caja: 'Caja',
}

export function esAdminHotel(rol) {
  return rol === 'administrador' || rol === 'admin_hotel'
}

export function esAdminPlataforma(rol) {
  return rol === 'administrador' || rol === 'admin_plataforma'
}

/** Todo rol administrativo exige doble factor. */
export function exigeDobleFactor(rol) {
  return esAdminHotel(rol) || esAdminPlataforma(rol)
}

/** Recepción o administración del hotel (bandejas, cancelación, limpieza). */
export function gestionaRecepcion(rol) {
  return rol === 'recepcion' || esAdminHotel(rol)
}

export function etiquetaRol(rol) {
  return ETIQUETAS_ROL[rol] || rol
}
