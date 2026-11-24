// Roles y permisos en el front (entrega 1A.2), espejo de servicio/roles.py.
// La API decide: esto solo muestra u oculta acciones.
//
// - admin_hotel: Administrador del hotel (precios, tipos, habitaciones,
//   reservas, cobros, caja, reportes).
// - admin_plataforma: Administrador de plataforma (usuarios, seguridad,
//   ajustes del sistema como la tasa de IVA).
// - administrador: rol histórico = ambas administraciones.
// - super_admin: la cuenta institucional (una sola). Gobierna las cuentas privilegiadas; nadie la crea por la API.

export const ROLES = ['super_admin', 'dueno', 'administrador', 'admin_hotel', 'admin_plataforma', 'recepcion', 'caja', 'aseo']

export const ETIQUETAS_ROL = {
  super_admin: 'Súper administrador',
  dueno: 'Dueño (lectura global)',
  administrador: 'Administrador (hotel y plataforma)',
  admin_hotel: 'Administrador del hotel',
  admin_plataforma: 'Administrador de plataforma',
  recepcion: 'Recepción',
  caja: 'Caja',
  aseo: 'Aseo',
}

export function esAdminHotel(rol) {
  return rol === 'super_admin' || rol === 'administrador' || rol === 'admin_hotel'
}

export function esAdminPlataforma(rol) {
  return rol === 'super_admin' || rol === 'administrador' || rol === 'admin_plataforma'
}

/** Valida los cambios de rol: la administración del hotel (nunca quien los pidió; la API lo exige). */
export function apruebaCambiosDeRol(rol) {
  return rol === 'administrador' || rol === 'admin_hotel'
}

/** Dueño del grupo: lee todo y deja observaciones a la administración; no cambia datos. */
export function esDueno(rol) {
  return rol === 'dueno'
}

/** Quién ve el Resumen del dueño y las observaciones: el dueño y la administración del hotel. */
export function veDireccion(rol) {
  return esDueno(rol) || esAdminHotel(rol)
}

/** Todo rol administrativo y el dueño exigen doble factor. */
export function exigeDobleFactor(rol) {
  return esAdminHotel(rol) || esAdminPlataforma(rol) || esDueno(rol)
}

/** Recepción o administración del hotel (bandejas, cancelación, limpieza). */
export function gestionaRecepcion(rol) {
  return rol === 'recepcion' || esAdminHotel(rol)
}

/** Clientes (RUT): recepción, caja o administración del hotel. */
export function gestionaClientes(rol) {
  return rol === 'caja' || gestionaRecepcion(rol)
}

/** #362: personal de aseo; solo ve /hotel/aseo. */
export function esAseo(rol) {
  return rol === 'aseo'
}

/** Quién ve la lista de aseo (aseo, recepción o administración del hotel). */
export function veAseo(rol) {
  return esAseo(rol) || gestionaRecepcion(rol)
}

export function etiquetaRol(rol) {
  return ETIQUETAS_ROL[rol] || rol
}
