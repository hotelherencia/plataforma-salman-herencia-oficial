# Especificación front V1 — la aplicación en Vercel

**Estado:** REQUISITO PROPUESTO, fechado 2026-10-28; ampliado 2026-10-30
(rutas `/hotel/reservas` y `/hotel/usuarios`, operaciones de habitación y
estadía, idempotencia de cliente). Un solo proyecto,
`plataforma-salman-herencia-front`, **Next.js**, desplegado en **Vercel**.
Consume y solo consume [spec-api-v1.md](spec-api-v1.md) en el origen
`API_BASE_URL` (el servicio de Railway). El hotel es el primer módulo;
`/cafeteria`, `/inmobiliaria` y `/constructora` existen como rutas vacías.

## Reglas duras

- **Una sesión, una empresa.** La sesión viaja en la cookie `sid`
  (HttpOnly, Secure, SameSite=None) que pone la API. El front **no guarda
  token en localStorage ni en el código**.
- El front **no calcula tarifa, no confirma cupo y no registra un pago**.
  Cada acción es una llamada a la API con `Idempotency-Key` en mutaciones.
- El front no llama a Webpay, Booking, Airbnb, SII ni WhatsApp. No existe
  otra URL que `API_BASE_URL`.
- Sin sesión: pantalla de login contra `POST /sesion`. V1-ISSUE-27
  (2026-11-03): la guardia vive en el `Lienzo` (layout raíz) — sin sesión,
  toda ruta interna muestra solo ese formulario y jamás el menú de operación;
  las rutas públicas sin sesión son `/login`, `/reservar` y `/privacidad`
  (lista `RUTAS_PUBLICAS`). Al
  entrar, la sesión compartida actualiza el Lienzo y la página protegida
  aparece en la misma ruta, sin redirección.

## Rutas de esta versión (hotel)

1. `/hotel/habitaciones` — inventario, alta de habitación (admin, solo crear
   desde 2026-11-03); completar limpieza y abrir o cerrar mantenimiento, cada
   acción con su clave de idempotencia (2026-10-30). Desde 2026-11-03 la
   edición, la tarifa y el retiro viven en la ficha (ruta 12).
2. `/hotel/oferta` — consulta de disponibilidad con tarifa y vencimiento.
3. `/hotel/reserva` («Nueva reserva» en el menú) — confirmación con clave de
   idempotencia estable (ver «Idempotencia en el cliente»).
4. `/hotel/reservas` («Buscar reservas» en el menú) — búsqueda con filtros
   por periodo, fecha, estado, texto y habitación; enlaza al detalle
   (2026-10-30).
5. `/hotel/pago` — registro de pago (modo manual de caja; pasarela muestra
   «no disponible» ante 503).
6. `/hotel/estadia` — check-in y operación de la estadía: cancelar y asentar
   un cargo (2026-10-30).
7. `/hotel/salida` — liquidación de la cuenta.
8. `/hotel/caja` — pagos del día ligados a reserva.
9. `/hotel/usuarios` — alta, cambio de clave, revocación y baja de usuarios;
   visible para administrador (2026-10-30).
10. `/hotel/panel` — panel operativo: situación de hoy e indicadores del
    periodo con su fórmula y fuente, tal como los envía `GET
    /hotel/indicadores` (2026-11-03). Es la entrada del módulo Hotel.
11. `/hotel/ocupacion` — rejilla habitación × noche de `GET /hotel/ocupacion`
    con leyenda de estados; cada celda con reserva enlaza a su detalle
    (2026-11-03).
12. `/hotel/habitaciones/[id]` — ficha de la habitación: edición de tipo y
    capacidad, tarifa nueva, retiro/reincorporación (administrador),
    historial de tarifas, reservas, tareas y auditoría (2026-11-03). El alta en
    `/hotel/habitaciones` envía `If-None-Match: *`.
13. `/hotel/reservas/[id]` — detalle de la reserva con su cuenta; la búsqueda
    de `/hotel/reservas` suma periodo y habitación (2026-11-03).
14. `/hotel/solicitudes` — bandeja de solicitudes públicas con conversión a
    reserva y rechazo (recepción o administrador, 2026-11-03, v1-issue-24).
    La columna Origen distingue `landing` de `agente`.
15. `/hotel/agente` — bandeja del agente de reservas (N0, 2026-11-04,
    V1-ISSUE-30): recepción pega la consulta entrante, ve el borrador con las
    cifras releídas por API, aprueba (con «Copiar respuesta»), edita o
    descarta; «modelo no configurado» cuando el puerto no tiene adaptador.
    Si un turno creó una solicitud, la traza muestra su `solicitud_id` y
    enlaza a la bandeja. Recepción o administrador; el ítem del menú no se
    muestra a otros roles.

Reglas de las rutas 10–13 (spec-hotel-operacion-v1): el front pinta lo que
la API decide —estado de cada noche, saldo, valor de cada indicador— y no
recalcula ninguno; las acciones que el rol no puede ejecutar no se muestran.

## Rutas públicas (2026-11-03, v1-issue-23; contrato «Canal público»)

1. `/reservar` — página del visitante, **fuera de `MarcoHotel`** (sin menú
   interno) y dentro de `RUTAS_PUBLICAS` del Lienzo (con `/login`). Lee
   `inicio`, `fin` y `personas` de la query y los valida antes de usarlos (no
   confía en ellos); consulta `GET /publico/disponibilidad` y muestra lo que
   el servidor responde —no calcula totales—; recoge huésped y contacto con
   el aviso de tratamiento versión 2026-11-10-aviso-02, enlazado a
   `/privacidad` antes de «Enviar solicitud», y envía `POST /publico/solicitudes` con
   `Idempotency-Key` estable que sobrevive errores y se renueva tras 2xx;
   muestra el número de solicitud devuelto. Parámetros inválidos → mensaje,
   sin llamada de mutación; API caída → aviso y nada confirmable. Enviar no
   confirma la estadía.
2. `/privacidad` — política de tratamiento, pública y sin sesión. El
   responsable es Herencia SpA, RUT 76.707.504-9, domicilio 5 de Abril 441,
   oficina 3, Chillán, Región de Ñuble. Los derechos se piden en ese domicilio
   o al +56 9 5649 1501. La conservación dura la respuesta de la consulta y,
   si recepción confirma, la estadía hasta el cierre de esa cuenta.
3. El CTA «Consultar reserva» de la landing apunta a
   `/reservar?inicio=…&fin=…&personas=…` (deep link precargado).

## Idempotencia en el cliente

DECISIÓN (2026-10-30, orden del propietario): en `reserva`, `pago`,
`habitaciones`, `estadia` y `salida` la clave de idempotencia nace al montar
el formulario (`useState` con inicializador perezoso, `crypto.randomUUID()`)
y es la que se envía en cada submit: «reintenta con la misma para no
duplicar» es literalmente cierto. Se muestra antes del primer envío. Un error
de red **no** la cambia; una respuesta 2xx la reemplaza por una clave nueva;
y un rechazo definitivo 4xx también la renueva (REQUISITO PROPUESTO
2026-11-03, V1-ISSUE-13: corregir la causa y reintentar no debe devolver la
respuesta guardada bajo la clave quemada). `habitaciones` tiene dos formularios
(alta y tarifa): cada uno lleva su clave. El otro modo de acuñar una clave es
un botón «Nueva operación», presente en toda pantalla con mutación. Si el
usuario cambia el cuerpo y reintenta con la clave vieja, la API responde 409 y
la pantalla lo muestra; con la renovación automática del 4xx el reintento
corregido ejecuta con clave nueva. El front no calcula tarifa, cupo ni saldo.

## Rutas de cuenta

- `/login` — con la cuenta en doble factor, el flujo pide después el código
  del autenticador (DECISIÓN, 2026-10-29: ver spec-api-v1, «Segundo factor
  TOTP»). Debajo del formulario (que no se toca), botón **«Entrar con
  Google»** que navega a `GET /auth/google` (redirección, no `fetch`) y se
  muestra solo si `GET /auth/google/estado` responde `configurado: true`
  (DECISIÓN, 2026-10-29, ver spec-api-v1, «Login con Google»); la misma
  pantalla anuncia `?error=cuenta_sin_vinculo` y `?error=acceso_denegado`.
- `/cuenta` — cambio de la propia clave (pide la clave actual) y alta y baja
  del segundo factor (Google Authenticator): genera el secreto, muestra la
  clave de configuración y confirma con un código.

## Criterio de aceptación

1. **Con la API apagada, el front muestra error y no confirma una reserva.**
2. Con la API encendida, las **catorce** pantallas hoteleras leen y escriben solo
   por `API_BASE_URL`.
3. No hay secretos ni tokens en el repositorio del front; la única variable
   de entorno es `API_BASE_URL`.
4. Ninguna pantalla replica lógica del contrato (precios, cupos, efectos).
