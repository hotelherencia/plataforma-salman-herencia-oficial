// «¿Cómo se calcula?» de cada indicador del panel (UI/UX 2026-11-19).
// Cada texto se contrastó con el cálculo real de servicio/panel.py
// (función `indicadores`): qué reservas, habitaciones o pagos entran, cuáles
// no, y con qué fechas. Si cambia el cálculo en el servidor, cambia aquí.
// Campos: mide (una frase), formula (en palabras), cuenta, noCuenta, ejemplo.

export const EXPLICACIONES = {
  llegadas_hoy: {
    mide: 'Cuántas reservas tienen su Llegada hoy y todavía no se registran en recepción.',
    formula: 'Llegadas de hoy = reservas confirmadas cuya fecha de Llegada es hoy.',
    cuenta: 'Reservas confirmadas (aún sin Llegada registrada).',
    noCuenta: 'Las que ya registraron su Llegada (pasan a «Huéspedes en casa») y las canceladas.',
    ejemplo: 'Si hoy llegan 4 reservas y 1 ya hizo su Llegada, el panel muestra 3.',
  },
  salidas_hoy: {
    mide: 'Cuántas estadías en curso tienen su Salida hoy y aún no se cierran.',
    formula: 'Salidas de hoy = reservas con huésped en casa cuya fecha de Salida es hoy.',
    cuenta: 'Reservas con Llegada registrada y Salida programada para hoy.',
    noCuenta: 'Las estadías que ya registraron su Salida (quedan finalizadas).',
    ejemplo: 'Si 5 habitaciones salen hoy y 2 ya entregaron, el panel muestra 3.',
  },
  en_casa: {
    mide: 'Cuántas reservas tienen hoy a su huésped alojado en el hotel.',
    formula: 'Huéspedes en casa = reservas con Llegada registrada y sin Salida registrada.',
    cuenta: 'Cada reserva una vez, sin importar cuántas personas trae.',
    noCuenta: 'Personas (no es un conteo de pasajeros), reservas confirmadas que aún no llegan y estadías ya cerradas.',
    ejemplo: '6 habitaciones con huésped alojado = 6, aunque sumen 11 personas.',
  },
  llegadas_vencidas: {
    mide: 'Reservas cuya Llegada ya pasó y nadie registró en recepción.',
    formula: 'Llegadas atrasadas = reservas confirmadas con fecha de Llegada anterior a hoy.',
    cuenta: 'Reservas confirmadas con Llegada de ayer o antes, sin registrar.',
    noCuenta: 'Las de hoy (están en «Llegadas de hoy»). La plataforma aún no marca «no se presentó»: hay que registrar la Llegada o cancelar.',
    ejemplo: 'Hoy es 19/11: una reserva con Llegada el 17/11 que sigue sin registrar suma 1.',
  },
  salidas_vencidas: {
    mide: 'Estadías cuya Salida ya pasó y siguen abiertas.',
    formula: 'Salidas atrasadas = reservas con huésped en casa y fecha de Salida anterior a hoy.',
    cuenta: 'Estadías con Salida de ayer o antes que no se han cerrado.',
    noCuenta: 'Las que salen hoy (están en «Salidas de hoy»).',
    ejemplo: 'Hoy es 19/11: una estadía con Salida el 18/11 que sigue abierta suma 1.',
  },
  habitaciones_total: {
    mide: 'Cuántas habitaciones tiene registradas el hotel.',
    formula: 'Habitaciones registradas = todas las habitaciones del mantenedor (o del tipo elegido).',
    cuenta: 'Todas: disponibles, ocupadas, en mantenimiento y fuera de servicio.',
    noCuenta: 'Nada se descuenta en este número.',
    ejemplo: 'Con 17 habitaciones en el mantenedor, el panel muestra 17.',
  },
  habitaciones_vendibles: {
    mide: 'Cuántas habitaciones se pueden vender hoy, estén ocupadas o no.',
    formula: 'Vendibles = habitaciones registradas − en mantenimiento hoy − bloqueadas − fuera de servicio.',
    cuenta: 'Habitaciones habilitadas para la venta, incluidas las que hoy tienen huésped.',
    noCuenta: 'Mantenimiento vigente hoy, bloqueadas y fuera de servicio.',
    ejemplo: '17 registradas − 1 en mantenimiento − 1 fuera de servicio = 15 vendibles.',
  },
  habitaciones_ocupadas: {
    mide: 'Cuántas habitaciones están ocupadas en este momento.',
    formula: 'Ocupadas ahora = habitaciones cuyo estado actual es «ocupada».',
    cuenta: 'Habitaciones con huésped alojado según su estado actual.',
    noCuenta: 'Reservas que aún no llegan.',
    ejemplo: 'Si hay 6 habitaciones con huésped, el panel muestra 6.',
  },
  habitaciones_sucias: {
    mide: 'Cuántas habitaciones esperan limpieza.',
    formula: 'Sucias = habitaciones marcadas como «sucia» en su preparación.',
    cuenta: 'Habitaciones sucias, tengan o no huésped.',
    noCuenta: 'Las limpias o ya revisadas.',
    ejemplo: 'Tras 3 Salidas sin limpiar, el panel muestra 3.',
  },
  habitaciones_en_limpieza: {
    mide: 'Cuántas habitaciones está limpiando el personal de aseo en este momento.',
    formula: 'En limpieza = habitaciones sucias cuya limpieza ya fue iniciada con «Empezar limpieza».',
    cuenta: 'Habitaciones sucias que aseo ya tomó y todavía no marca como limpias.',
    noCuenta: 'Las sucias sin iniciar y las ya limpias o inspeccionadas.',
    ejemplo: 'Si aseo empezó 2 habitaciones recién desocupadas, el panel muestra 2.',
  },
  limpiezas_pendientes: {
    mide: 'Cuántas tareas de limpieza siguen por hacer.',
    formula: 'Limpiezas pendientes = tareas de limpieza en estado pendiente.',
    cuenta: 'Tareas de limpieza abiertas de las habitaciones del filtro.',
    noCuenta: 'Tareas ya cerradas por aseo.',
    ejemplo: '2 tareas creadas por Salidas + 1 por cambio de habitación = 3.',
  },
  en_mantenimiento: {
    mide: 'Cuántas habitaciones están hoy en mantenimiento.',
    formula: 'En mantenimiento = habitaciones con un mantenimiento cuyo rango de fechas incluye hoy.',
    cuenta: 'Mantenimientos vigentes hoy (desde ≤ hoy y antes del «hasta»; sin «hasta», solo hasta hoy).',
    noCuenta: 'Mantenimientos programados para fechas futuras.',
    ejemplo: 'Un mantenimiento del 18 al 20 cuenta el 18 y el 19, no el 20.',
  },
  fuera_de_servicio: {
    mide: 'Cuántas habitaciones están retiradas de la operación.',
    formula: 'Fuera de servicio = habitaciones cuyo estado actual es «fuera de servicio».',
    cuenta: 'Habitaciones fuera de servicio hoy.',
    noCuenta: 'Mantenimientos con fecha (se ven en «En mantenimiento»).',
    ejemplo: 'Si una habitación está fuera de servicio por reparación mayor, el panel muestra 1.',
  },
  unidades_noche: {
    mide: 'Cuántas noches de habitación tuvo el hotel para vender en el periodo.',
    formula: 'Unidades-noche = suma, noche a noche, de las habitaciones existentes esa noche.',
    cuenta: 'Cada habitación ya registrada esa noche, incluidas las en mantenimiento; también cualquier habitación que tenga una reserva esa noche.',
    noCuenta: 'Habitaciones fuera de servicio (según su estado actual) y habitaciones que aún no se registraban esa noche.',
    ejemplo: '16 habitaciones × 7 noches = 112 unidades-noche.',
  },
  noches_ocupadas: {
    mide: 'Cuántas noches de habitación se alojaron realmente, hasta hoy.',
    formula: 'Noches ocupadas = noches con huésped (Llegada registrada) desde el inicio del periodo hasta hoy.',
    cuenta: 'Estadías en curso y finalizadas; una Salida anticipada cuenta solo hasta el día en que se cerró.',
    noCuenta: 'Noches futuras, reservas confirmadas que nunca registraron Llegada y canceladas.',
    ejemplo: '3 habitaciones con huésped durante 2 noches = 6 noches ocupadas.',
  },
  ocupacion: {
    mide: 'Qué parte de lo que se podía vender se alojó de verdad (ocupación real).',
    formula: 'Ocupación = noches ocupadas ÷ unidades-noche, ambas solo de las noches hasta hoy.',
    cuenta: 'Solo estadías reales (con Llegada registrada).',
    noCuenta: 'Noches futuras y reservas sin Llegada. Si todo el periodo es futuro se muestra «sin muestra».',
    ejemplo: '45 noches ocupadas ÷ 112 unidades-noche = 40,2 %.',
  },
  noches_reservadas: {
    mide: 'Cuántas noches de habitación están comprometidas con reservas en el periodo.',
    formula: 'Noches reservadas = noches del periodo con una reserva confirmada, en curso o finalizada.',
    cuenta: 'Pasadas y futuras, incluidas reservas confirmadas cuya Llegada ya pasó sin registrarse.',
    noCuenta: 'Reservas canceladas.',
    ejemplo: 'Una reserva de 3 noches dentro del periodo suma 3.',
  },
  ocupacion_reservada: {
    mide: 'Qué parte del periodo está vendida o comprometida (incluye lo que viene).',
    formula: 'Ocupación reservada = noches reservadas ÷ unidades-noche de todo el periodo.',
    cuenta: 'Reservas confirmadas, en curso y finalizadas.',
    noCuenta: 'Canceladas. No dice si el huésped llegó: para eso está «Ocupación».',
    ejemplo: '60 noches reservadas ÷ 112 unidades-noche = 53,6 %.',
  },
  ingresos_periodo_clp: {
    mide: 'Cuánto dinero se recaudó en caja durante el periodo (base percibida).',
    formula: 'Recaudación del periodo = suma de los cobros confirmados con fecha contable dentro del periodo.',
    cuenta: 'Cobros confirmados, en pesos y con IVA incluido (tal como se recibieron), aunque correspondan a estadías de otras fechas.',
    noCuenta: 'Lo reservado y aún no pagado, cobros no confirmados ni ingresos devengados por noche vendida (eso vive en Cierre diario).',
    ejemplo: 'Un anticipo de $50.000 el día 3 y un cobro de $415.000 el día 9 = $465.000.',
  },
  ingresos_por_canal: {
    mide: 'Cuánto se recaudó en el periodo separado según el canal por donde llegó cada reserva.',
    formula: 'Recaudación por canal = suma de cobros confirmados del periodo agrupados por el origen de la reserva.',
    cuenta: 'Cobros confirmados de reservas creadas en recepción, sitio web, teléfono, WhatsApp, Google o agencias externas.',
    noCuenta: 'Reservas sin cobros en el periodo, cobros anulados ni movimientos directos sin reserva.',
    ejemplo: 'Sitio web $280.000 (2 reservas) + Recepción $185.000 (1 reserva) = $465.000.',
  },
  reservas_canceladas: {
    mide: 'Cuántas reservas canceladas tenían noches dentro del periodo.',
    formula: 'Reservas canceladas = reservas canceladas cuyas fechas de estadía tocan el periodo; debajo, cuántas de sus noches caían en él.',
    cuenta: 'Canceladas según la fecha de la estadía.',
    noCuenta: 'La fecha en que se canceló (no se usa para filtrar).',
    ejemplo: '2 canceladas de 2 y 3 noches dentro del periodo = 2 reservas, 5 noches.',
  },
  reservas_registradas: {
    mide: 'Cuántas reservas se crearon dentro del periodo.',
    formula: 'Reservas registradas = reservas con fecha de creación dentro del periodo, agrupadas por su estado actual.',
    cuenta: 'Todas las creadas en esas fechas, también las que hoy están canceladas.',
    noCuenta: 'Reservas creadas antes, aunque se alojen en el periodo.',
    ejemplo: '39 reservas creadas: 27 confirmadas, 9 canceladas y 3 finalizadas.',
  },
  ingreso_alojamiento_clp: {
    mide: 'Cuánto ingreso de alojamiento se devengó por las noches realmente alojadas del periodo.',
    formula: 'Ingreso de alojamiento = suma de la tarifa congelada de cada noche alojada hasta hoy.',
    cuenta: 'Noches con huésped en casa o finalizadas, con IVA incluido según el precio congelado al confirmar.',
    noCuenta: 'Noches futuras, reservas sin Llegada, canceladas ni consumos extras.',
    ejemplo: '6 noches alojadas a $60.000 por noche = $360.000.',
  },
  adr_clp: {
    mide: 'Tarifa promedio por noche vendida (ADR) sobre las estadías reales del periodo.',
    formula: 'Tarifa promedio diaria = ingreso de alojamiento devengado ÷ noches ocupadas.',
    cuenta: 'Solo noches efectivamente alojadas (estadías en curso o finalizadas) con precio congelado e IVA incluido.',
    noCuenta: 'Noches futuras ni habitaciones vacías. Si no hubo noches ocupadas se muestra «sin muestra».',
    ejemplo: '$360.000 en 6 noches ocupadas = $60.000 por noche.',
  },
  revpar_clp: {
    mide: 'Ingreso de alojamiento por habitación disponible (RevPAR) en las noches del periodo hasta hoy.',
    formula: 'Ingreso por habitación disponible = ingreso de alojamiento devengado ÷ unidades-noche hasta hoy.',
    cuenta: 'El ingreso real de alojamiento repartido entre todas las noches-habitación en servicio del periodo.',
    noCuenta: 'Habitaciones fuera de servicio ni noches futuras. Sin muestra en el periodo se muestra «sin muestra».',
    ejemplo: '$360.000 ÷ 15 unidades-noche = $24.000 por habitación disponible.',
  },
}

/** Indicadores estándar de la industria que el panel todavía no calcula. */
export const AUN_NO_DISPONIBLES = [
  {
    nombre: 'No se presentó',
    texto: 'La plataforma aún no tiene ese estado: esas reservas aparecen en «Llegadas atrasadas sin registrar».',
  },
]
