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
  ['/hotel/caja', 'Caja del día'],
  ['/hotel/pago', 'Registrar pago'],
]

export const SECCIONES = [
  {
    id: 'operacion',
    rotulo: 'Hotel · operación diaria',
    items: [
      { href: '/hotel/panel', nombre: 'Panel' },
      { href: '/hotel/ocupacion', nombre: 'Ocupación' },
      { href: '/hotel/habitaciones', nombre: 'Estado de habitaciones' },
      { href: '/hotel/aseo', nombre: 'Aseo', si: 'aseo' },
      { href: '/hotel/reservas', nombre: 'Reservas', tambien: ['/hotel/reserva', '/hotel/oferta'] },
      { href: '/hotel/solicitudes', nombre: 'Solicitudes y leads', tambien: ['/hotel/leads'] },
      { href: '/hotel/agente', nombre: 'Agente', si: 'agente' },
      { href: '/hotel/estadia', nombre: 'Llegada' },
      { href: '/hotel/salida', nombre: 'Salida' },
      { href: '/hotel/caja', nombre: 'Caja y pagos', tambien: ['/hotel/pago'] },
    ],
  },
  {
    id: 'configuracion',
    rotulo: 'Hotel · configuración',
    items: [
      { href: '/hotel/configuracion', nombre: 'Configuración', tambien: ['/hotel/tipos'] },
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

export function seccionesVisibles({ puedeVerAgente, puedeVerUsuarios, puedeVerAseo = true, soloAseo = false }) {
  return SECCIONES.map((seccion) => ({
    ...seccion,
    items: seccion.items.filter((item) => {
      // #362: el rol aseo solo ve su lista.
      if (soloAseo) return item.si === 'aseo'
      if (item.si === 'aseo') return puedeVerAseo
      if (item.si === 'agente') return puedeVerAgente
      if (item.si === 'usuarios') return puedeVerUsuarios
      return true
    }),
  })).filter((seccion) => seccion.items.length > 0)
}

export function hayOperacionActiva(ruta, visibilidad) {
  return seccionesVisibles(visibilidad).some((seccion) => seccion.items.some((item) => itemActivo(ruta, item)))
}
