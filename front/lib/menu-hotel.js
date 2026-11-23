// Menú del módulo hotel (entrega 1A.3). Una sola fuente para barra, pruebas y
// redirecciones. Objetivo: pocas secciones claras, sin entradas sueltas que mareen.
//
// Antes (entrega 1A.2, lista plana bajo «Hotel · operación»):
//   Panel, Ocupación, Tipos habitaciones y precios, Estado de habitaciones,
//   Oferta, Nueva reserva, Buscar reservas, Solicitudes, Leads, Pago, Estadía,
//   Salida, Caja, Agente (si corresponde), Usuarios (admin de plataforma).
//
// Después: operación diaria, una sola Configuración con pestañas, y Plataforma.

export const PESTANAS_CONFIGURACION = [
  ['tipos', 'Tipos y habitaciones'],
  ['precios', 'Precios y excepciones'],
  ['politicas', 'Políticas y registro de Llegada/Salida'],
  ['faq', 'Preguntas frecuentes'],
  ['reservas_web', 'Reservas web'],
  ['correo', 'Correo'],
  ['avisos', 'Avisos'],
  ['caja', 'Caja y medios de pago'],
]

// Fase 1 contable (2026-11-19): pestañas dentro de Caja y pagos, sin ítem de menú nuevo.
export const PESTANAS_CAJA = [
  ['dia', 'Caja del día'],
  ['turno', 'Turno'],
  ['movimientos', 'Movimientos'],
  ['cuenta', 'Cargos y pagos'],
  ['depositos', 'Depósitos'],
  ['cierre', 'Cierre diario'],
]

export const SUBNAV_RESERVAS = [
  ['/hotel/oferta', 'Oferta'],
  ['/hotel/reserva', 'Nueva reserva'],
  ['/hotel/reservas', 'Buscar reservas'],
]

export const SUBNAV_BANDEJAS = [
  ['/hotel/solicitudes', 'Solicitudes'],
  ['/hotel/leads', 'Leads'],
]

export const SUBNAV_CAJA = [
  ['/hotel/caja', 'Caja'],
  ['/hotel/pago', 'Registrar pago'],
]

// #455: qué rol ve cada entrada. Espejo de lo que la API deja usar (servicio/roles.py, cobro.py):
// recepción y administración del hotel operan Llegada, Salida, solicitudes y habitaciones; caja solo
// consulta reservas y ocupación y trabaja en Caja y pagos. Sin `roles` la entrada es para todos.
const ADMIN_HOTEL = ['administrador', 'admin_hotel']
const ROLES_RECEPCION = [...ADMIN_HOTEL, 'recepcion']
const ROLES_FRENTE = [...ROLES_RECEPCION, 'caja']

/** Primera pantalla de cada rol (logo y enlace de inicio). */
export function rutaInicio(rol) {
  if (rol === 'aseo') return '/hotel/aseo'
  if (rol === 'caja') return '/hotel/caja'
  return '/hotel/panel'
}

export const SECCIONES = [
  {
    id: 'operacion',
    rotulo: 'Hotel · operación diaria',
    items: [
      { href: '/hotel/panel', nombre: 'Panel' },
      { href: '/hotel/ocupacion', nombre: 'Ocupación', roles: ROLES_FRENTE },
      { href: '/hotel/habitaciones', nombre: 'Estado de habitaciones', roles: ROLES_RECEPCION },
      { href: '/hotel/aseo', nombre: 'Aseo', si: 'aseo' },
      { href: '/hotel/reservas', nombre: 'Reservas', tambien: ['/hotel/reserva', '/hotel/oferta'], roles: ROLES_FRENTE },
      { href: '/hotel/solicitudes', nombre: 'Solicitudes y leads', tambien: ['/hotel/leads'], roles: ROLES_RECEPCION },
      { href: '/hotel/agente', nombre: 'Agente', si: 'agente' },
      { href: '/hotel/clientes', nombre: 'Clientes', si: 'clientes' },
      { href: '/hotel/estadia', nombre: 'Llegada', roles: ROLES_RECEPCION },
      { href: '/hotel/salida', nombre: 'Salida', roles: ROLES_RECEPCION },
      { href: '/hotel/caja', nombre: 'Caja y pagos', tambien: ['/hotel/pago'], roles: ROLES_FRENTE },
    ],
  },
  {
    id: 'configuracion',
    rotulo: 'Hotel · configuración',
    items: [
      { href: '/hotel/configuracion', nombre: 'Configuración', tambien: ['/hotel/tipos'], roles: ROLES_RECEPCION },
      { href: '/hotel/productos', nombre: 'Productos y stock' },
    ],
  },
  {
    id: 'plataforma',
    rotulo: 'Plataforma',
    items: [
      { href: '/hotel/usuarios', nombre: 'Usuarios', si: 'usuarios' },
    ],
  },
]

export function esRutaActiva(ruta, href, tambien = []) {
  if (!ruta || !href) return false
  return [href, ...tambien].some((alt) => ruta === alt || ruta.startsWith(`${alt}/`))
}

export function itemActivo(ruta, item) {
  return esRutaActiva(ruta, item.href, item.tambien || [])
}

export function seccionesVisibles({ puedeVerAgente, puedeVerUsuarios, puedeVerAseo = true, puedeVerClientes = true, soloAseo = false, rol = null }) {
  return SECCIONES.map((seccion) => ({
    ...seccion,
    items: seccion.items.filter((item) => {
      // #362: el rol aseo solo ve su lista.
      if (soloAseo) return item.si === 'aseo'
      if (rol && item.roles && !item.roles.includes(rol)) return false
      if (item.si === 'aseo') return puedeVerAseo
      if (item.si === 'clientes') return puedeVerClientes
      if (item.si === 'agente') return puedeVerAgente
      if (item.si === 'usuarios') return puedeVerUsuarios
      return true
    }),
  })).filter((seccion) => seccion.items.length > 0)
}

export function hayOperacionActiva(ruta, visibilidad) {
  return seccionesVisibles(visibilidad).some((seccion) => seccion.items.some((item) => itemActivo(ruta, item)))
}
