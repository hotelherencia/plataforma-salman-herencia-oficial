# Especificación API V1 — contrato entre el front y el backend

**Estado:** REQUISITO PROPUESTO, fechado 2026-10-28; ampliado 2026-10-30
(búsqueda de reservas, gestión de usuarios, operación de la habitación,
cancelación y cargos — secciones etiquetadas) y 2026-11-03 (lectura del
inventario de habitaciones, `GET /hotel/habitaciones`, orden del propietario
tras la revisión E2E). Es el contrato que el
front (Vercel) y el backend (Railway) cumplen juntos; sustituye como contrato
vigente al catálogo heredado `docs/definicion-herencia/contratos/openapi.yaml`
(que queda como referencia histórica, no como contrato). Lo sirve el backend;
una operación que no está en la tabla no se publica.

## Identidad y sesión

- La empresa sale **solo** de la sesión. Un `company_id` enviado por el
  cliente no autoriza nada.
- `POST /sesion` abre la sesión con **usuario y clave** (DECISIÓN, 2026-10-28:
  tabla `usuarios` en PostgreSQL; la clave se guarda solo como hash argon2id;
  el usuario pertenece a una empresa; V1 crea el administrador inicial al
  arrancar, leyendo usuario y clave de variables de entorno, nunca de un SQL
  commiteado ni del repositorio).
- **Segundo factor TOTP** (DECISIÓN, 2026-10-29, orden del propietario: «el
  login no puede ser acceso normal»): estándar RFC 6238 implementado en el
  servicio, compatible con Google Authenticator; **no usa servicio externo ni
  clave de API** — el secreto base32 lo genera el propio backend. `POST
  /sesion` acepta `totp` opcional (6 dígitos). Con 2FA activo y sin código →
  **401** con `detail="codigo_totp_requerido"`; código incorrecto → **401**
  `detail="código 2FA inválido"`. La alta se confirma con un código válido
  (`POST /cuenta/2fa` + `POST /cuenta/2fa/activar`); `GET /sesion` declara
  `totp_activado`. Migración: la columna nace desactivada, nadie queda fuera.
- La sesión vive en el servidor (tabla `sesiones`, revocable). El front solo
  recibe la cookie.
- **Login con Google (OAuth 2.0 / OIDC)** (DECISIÓN, 2026-10-29, orden del
  propietario; reemplazable por orden suya): adaptador de identidad externo,
  **opcional** — solo existe con `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`
  en el entorno; sin ellas los endpoints responden **503**
  `detail="no configurado"`, igual que los demás puertos. HECHO DOCUMENTADO:
  la columna `usuarios.email` (TEXT, nullable, única por índice parcial)
  vincula la identidad; el email del administrador inicial se toma de
  `ADMIN_EMAIL` al arrancar y, si no se define, ese usuario queda sin vínculo
  y Google login deshabilitado para él. `GET /auth/google` redirige (302) al
  consentimiento de Google con scope `openid email profile` y `state` aleatorio
  de un solo uso (10 minutos, guardado server-side). El callback valida el
  `state`, intercambia el `code`, verifica el ID token (firma RS256 contra el
  JWKS de Google, caché por `kid`; `iss` de Google, `aud ==
  GOOGLE_CLIENT_ID`, `exp` vigente, email verificado) y abre la **misma
  sesión** que `POST /sesion` (tabla `sesiones`, cookie `sid`, misma
  vigencia, fila de auditoría), redirigiendo a `FRONT_URL`. DECISIÓN V1: este
  flujo **sustituye al par usuario/clave + TOTP** para la identidad vinculada
  (Google ya autenticó): no aplica el freno de fuerza bruta. Sin
  aprovisionamiento: solo entra un email ya presente en `usuarios.email`;
  email desconocido → redirección a `/login?error=cuenta_sin_vinculo`;
  `error=access_denied` → `/login?error=acceso_denegado`.
- Cookie de sesión: nombre `sid`, **HttpOnly**, **Secure** en producción,
  **SameSite=None** (front y API son orígenes distintos: Vercel ↔ Railway).
  En local, sobre `http://127.0.0.1`, la cookie usa **SameSite=Lax** y no
  pide `Secure`: el navegador rechaza `SameSite=None` sin `Secure`, y los
  dos puertos de `127.0.0.1` son el mismo sitio.
- Sin sesión válida → **401**. Sesión de otra empresa sobre un recurso →
  **403**, sin revelar si el recurso existe.

## Idempotencia

- Toda mutación (POST/PUT) lleva cabecera `Idempotency-Key`.
- Misma clave + mismo cuerpo → mismo resultado (la respuesta original se
  repite).
- Misma clave + otro cuerpo → **409**.
- La clave es por empresa y por operación; se guarda en PostgreSQL
  (`claves_idempotencia`: clave, hash del cuerpo, respuesta, código).

## Estados de la reserva

- Publicados en V1: **confirmada**, **en_estadia**, **finalizada** y, con esta
  ampliación, **cancelada** (REQUISITO PROPUESTO: la columna `reservas.estado`
  ya existe y el CHECK `reservas_estado_valido` se amplía; no se renombra
  nada). HECHO DOCUMENTADO: el dominio (`hotel_inventario/dominio.py`,
  `EstadoReserva`) llama **hospedada** y **salida** a lo que en la API V1 sigue
  siendo `en_estadia` y `finalizada`.
- HECHO DOCUMENTADO: el constraint de no solape `reservas_sin_solape` protege
  el rango para `confirmada` y `en_estadia`; `cancelada` y `finalizada` sueltan
  el cupo.

## Búsqueda de reservas

REQUISITO PROPUESTO (2026-10-30): `GET /hotel/reservas?fecha=&estado=&texto=`.
Los tres filtros son opcionales y se combinan con **AND**, acotados a la
empresa de la sesión, ordenados por `inicio`, `id`.

- `fecha`: la noche de hotel contiene ese día — `inicio <= fecha < fin`.
- `estado`: igualdad exacta con un estado válido; si no lo es, **422**.
- `texto`: coincidencia sin distinguir mayúsculas (`ILIKE`) sobre `id`,
  `huesped_nombre`, `huesped_documento` o `habitacion_id`.
- Cada ítem devuelve `reserva_id`, `habitacion_id`, `inicio`, `fin`,
  `huesped_nombre`, `estado`, `tarifa_noche_aceptada_clp`.
- `huesped_documento` solo se incluye si el rol de la sesión es `recepcion` o
  `administrador` (HECHO DOCUMENTADO: `ROLES_DOCUMENTO` del dominio,
  `hotel_inventario/servicio.py`); `caja` ve la reserva y no el documento.
- Cero resultados → **200** con lista vacía.

## Gestión de usuarios

REQUISITO PROPUESTO (2026-10-30). Roles creables en V1: `administrador`,
`recepcion`, `caja` (DECISIÓN, 2026-10-30, orden del propietario; un rol
`limpieza` queda DECISIÓN PENDIENTE, no se inventa). HECHO DOCUMENTADO:
`usuarios.activo boolean NOT NULL DEFAULT true` y `UNIQUE (empresa_id,
nombre)`; la clave solo se guarda como hash argon2id
(`seguridad.hashear_clave`); `cobro.ROLES_PAGO_MANUAL` ya exige `recepcion`,
`caja` o `administrador` para el cobro manual.

- `GET /usuarios`: solo `administrador`. Lista `id`, `nombre`, `rol`, `activo`.
  Jamás devuelve `clave_hash`.
- `POST /usuarios {nombre, rol, clave}`: solo `administrador`. Crea con hash
  argon2id. Nombre repetido en la empresa → **409**.
- `POST /usuarios/{id}/clave {clave}`: el propio usuario o un `administrador`.
  La clave nueva reemplaza el hash.
- `POST /usuarios/{id}/revocacion`: solo `administrador`, sobre **otro**
  usuario: pone `revocada_en` en todas sus sesiones. La sesión propia se
  sigue cerrando con `DELETE /sesion`.
- `POST /usuarios/{id}/baja`: solo `administrador`, sobre **otro** usuario de
  su empresa: `activo = false` y revoca sus sesiones. `autenticar` rechaza al
  usuario inactivo igual que una clave mala (HECHO DOCUMENTADO: regla de
  `seguridad.autenticar`). No se puede dar de baja al último administrador
  activo → **409**.

## Operación de la habitación

HECHO DOCUMENTADO (fuente: dominio `hotel_inventario`): `ocupada` y `sucia` se
siguen vendiendo en otras fechas (ESTADOS_VENDIBLES); el solape protege el
rango; el **mantenimiento**, distinto de la limpieza, saca la unidad del cupo;
el check-in con mantenimiento abierto o unidad sucia se niega; el check-out
deja la unidad sucia y abre una tarea de limpieza; completar esa tarea la deja
limpia. DECISIÓN (2026-10-30, orden del propietario): el servicio lo traduce a
columnas y tabla — `habitaciones.mantenimiento boolean`, `tareas_operativas`
(`id`, `habitacion_id`, `tipo` `limpieza|mantenimiento`, `estado`
`pendiente|completada`), durable al reinicio.

- `POST /hotel/reservas/{id}/entrada` (ya publicada) queda así: en la misma
  transacción, si la habitación tiene mantenimiento abierto, su
  `estado_operativo` no es `disponible`, su `estado_preparacion` no es
  `limpia` ni `inspeccionada`, u otra reserva `en_estadia` ocupa esa
  habitación → **409** y nada cambia. Si pasa: la reserva queda `en_estadia` y
  `estado_operativo` pasa a `ocupada`.
- `POST /hotel/reservas/{id}/salida` (ya publicada): con el saldo neto
  (cargo menos reverso) ya en cero, en la misma transacción: la reserva queda
  `finalizada`, `estado_operativo` vuelve a `disponible`,
  `estado_preparacion` pasa a `sucia` y nace una tarea de limpieza `pendiente`.
- `POST /hotel/habitaciones/{id}/limpieza` (REQUISITO PROPUESTO): rol
  `recepcion` o `administrador`; con `Idempotency-Key`. Completa la tarea de
  limpieza pendiente y, si `estado_preparacion` es `sucia`, la deja `limpia`.
- `POST /hotel/habitaciones/{id}/mantenimiento {abierto: bool}`
  (REQUISITO PROPUESTO): solo `administrador`; con `Idempotency-Key`.
  `abierto=true` marca mantenimiento y abre tarea de mantenimiento pendiente;
  `abierto=false` lo cierra y completa esa tarea. Con mantenimiento abierto la
  entrada responde **409** aunque la preparación sea limpia, y la oferta no
  incluye la habitación.
- HECHO DOCUMENTADO: la oferta incluye una habitación `ocupada` o `sucia`
  cuando el rango pedido no solapa (AC-US-HOT-001-02); excluye mantenimiento,
  `bloqueada` y `fuera_de_servicio`. El test
  `test_oferta_excluye_la_unidad_ocupada` sigue significando «hay una reserva
  confirmada en esas fechas».

## Cancelación

DECISIÓN (2026-10-30, fuente: dominio `hotel_inventario/servicio.py`,
`cancelar`, `LIMITE_CANCELACION_GRATUITA = 48 h`, `HORA_LLEGADA = 15:00`,
`solo desde CONFIRMADA`): `POST /hotel/reservas/{id}/cancelacion`, rol
`recepcion` o `administrador`; con `Idempotency-Key`. Solo desde `confirmada`:
`en_estadia`, `finalizada` o `cancelada` → **409**. La hora de corte es el
inicio de la reserva a las 15:00 en el reloj del servidor.

- Si llegada menos ahora es al menos 48 horas: sin cargo. Si no: se asienta el
  concepto del dominio «Cancelación fuera de plazo: primera noche» por la
  tarifa de esa reserva.
- V1 ya inserta en crear la reserva el cargo del alojamiento completo:
  cancelar **no** suma la penalización encima de ese cargo. HECHO DOCUMENTADO:
  los cargos del dominio son inmutables; una corrección es otro asiento,
  `TipoCargo.REVERSO`, monto positivo. Migración: `cargos.tipo`
  (`cargo|reverso`, default `cargo`) y `cargos.referencia` nullable; el reverso
  guarda monto positivo y referencia al cargo original.
- La cancelación, en una transacción: estado `cancelada`; un reverso por cada
  cargo aún no reversado; si es fuera de plazo, un cargo nuevo por
  `tarifa_noche_aceptada_clp`. Ningún `UPDATE` ni `DELETE` de cargos. La
  salida y cualquier saldo suman **cargo menos reverso**.
- Si ya había pagos y el neto queda a favor del huésped, la cancelación igual
  se confirma. No hay reembolso ni llamada a pasarela: la devolución sigue
  siendo puerto sin adaptador (503). El rango cancelado deja de ocupar cupo.

## Cargos de la estadía

REQUISITO PROPUESTO (2026-10-30): `POST /hotel/reservas/{id}/cargos
{concepto, monto_clp}`; con `Idempotency-Key`. Rol `recepcion`, `caja` o
`administrador` (HECHO DOCUMENTADO: `cobro.ROLES_PAGO_MANUAL`). HECHO
DOCUMENTADO: `ESTADOS_CON_CUENTA_ABIERTA` del dominio — solo con la reserva en
`confirmada` o `en_estadia`; otro estado → **409**. `monto_clp` entero mayor
que cero; si no → **422**. Inserta un cargo de tipo `cargo`. No hay catálogo de
minibar ni inventario de productos: el concepto es texto libre (minibar,
consumo, extra). La liquidación de salida ya suma los cargos; con el neto
cargo-menos-reverso, ese consumo entra en el total y un saldo distinto de cero
sigue impidiendo la salida.

## Errores y puertos

- Puerto externo sin adaptador (pasarela, DTE, PMS, canal, mensajería) →
  **503** y el estado queda **pendiente**; nada se marca como cobrado,
  emitido ni enviado. El cuerpo declara qué puerto falta.

## Operaciones de esta versión (27)

| Operación | Efecto |
|---|---|
| `POST /sesion` | Abre sesión de la empresa Herencia y fija la cookie `sid`. Con 2FA activo exige además `totp` (ver «Identidad y sesión»). |
| `DELETE /sesion` | Cierra la sesión (la fila de `sesiones` queda revocada). |
| `POST /cuenta/2fa` | Con sesión: genera el secreto TOTP pendiente y devuelve `{secreto, uri}` (otpauth://). No activa nada. |
| `POST /cuenta/2fa/activar` | Con sesión: confirma el alta verificando el código recibido contra el secreto pendiente; código inválido → 400. |
| `DELETE /cuenta/2fa` | Con sesión: desactiva el segundo factor y borra el secreto. |
| `GET /auth/google/estado` | `{configurado: bool}`: true solo con `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` en el entorno. |
| `GET /auth/google` | 302 al consentimiento de Google (scope `openid email profile`, `state` de un solo uso, 10 min); sin configurar → 503 «no configurado». |
| `GET /auth/google/callback` | Valida `state`, intercambia `code`, verifica el ID token y abre la sesión con cookie `sid`, redirigiendo a `FRONT_URL`. Email sin vínculo → `/login?error=cuenta_sin_vinculo`; `access_denied` → `/login?error=acceso_denegado`. |
| `GET /usuarios` | Lista `id`, `nombre`, `rol`, `activo` de la empresa. Solo administrador. |
| `POST /usuarios` | Alta `{nombre, rol, clave}` con hash argon2id. Solo administrador. Nombre repetido → 409. |
| `POST /usuarios/{id}/clave` | Cambia la clave (reemplaza el hash). El propio usuario o un administrador. |
| `POST /usuarios/{id}/revocacion` | Revoca todas las sesiones del usuario. Solo administrador, sobre otro usuario. |
| `POST /usuarios/{id}/baja` | `activo=false` y revoca sesiones. Solo administrador, sobre otro usuario; no al último administrador activo (409). |
| `PUT /hotel/habitaciones/{id}` | Alta o cambio de habitación: tipo, capacidad. Solo administrador. |
| `PUT /hotel/tarifas` | Tarifa por fecha y unidad. No cambia el precio de una reserva ya aceptada. |
| `GET /hotel/oferta?inicio&fin&personas` | Solo lo disponible, con tarifa vigente y vencimiento de la oferta. Incluye unidades ocupadas o sucias si el rango no solapa; excluye mantenimiento, bloqueada y fuera de servicio. |
| `GET /hotel/habitaciones` | Inventario operativo de las unidades (REQUISITO PROPUESTO, 2026-11-03, orden del propietario tras la revisión E2E: la pantalla operaba a ciegas sin lectura del estado). Por unidad: `tipo`, `capacidad`, `estado_operativo`, `estado_preparacion`, `mantenimiento`, `tareas_pendientes`, `limpieza_pendiente` y última tarifa configurada como referencia. Solo lectura, cualquier rol de la sesión; las mutaciones conservan sus reglas de rol (limpieza: recepción o administrador; mantenimiento: solo administrador). |
| `GET /hotel/reservas?fecha=&estado=&texto=` | Búsqueda de reservas de la empresa, filtros opcionales combinados con AND. Ver «Búsqueda de reservas». |
| `POST /hotel/reservas` | Confirma una sola vez. La última unidad en carrera queda en una sola reserva: la confirmación es transaccional y la base rechaza el solape en (unidad, fechas) para `confirmada` y `en_estadia`. |
| `POST /hotel/reservas/{id}/pagos` | El núcleo registra el efecto. Si el núcleo rechaza, no hay pago. Cuerpo: `{monto_clp, clave, modo}`. `modo="manual"` (DECISIÓN, 2026-10-28): caja en efectivo o transferencia que recepción registra; solo roles recepción, caja o administrador; no consulta el banco y no queda conciliado. `modo="pasarela"` sin adaptador → 503 y nada marcado como cobrado. |
| `POST /hotel/reservas/{id}/cargos` | Cargo de texto libre (minibar, consumo, extra). Roles recepción, caja o administrador; solo en `confirmada` o `en_estadia`; monto entero > 0 (si no, 422); otro estado → 409. Ver «Cargos de la estadía». |
| `POST /hotel/reservas/{id}/cancelacion` | Cancela desde `confirmada` con reversos y regla de 48 h (ver «Cancelación»). Roles recepción o administrador. |
| `POST /hotel/reservas/{id}/entrada` | Check-in si la habitación está lista (mantenimiento abierto, no disponible, sucia u otra estadía en la unidad bloquean → 409). Al pasar, la reserva queda `en_estadia` y la habitación `ocupada`. |
| `POST /hotel/reservas/{id}/salida` | Liquida la cuenta (saldo neto cargo-menos-reverso en cero) y devuelve la liquidación. La habitación queda `disponible` y `sucia`, con tarea de limpieza pendiente. |
| `POST /hotel/habitaciones/{id}/limpieza` | Completa la limpieza pendiente y, si estaba sucia, deja la unidad `limpia`. Roles recepción o administrador. |
| `POST /hotel/habitaciones/{id}/mantenimiento` | Abre o cierra el mantenimiento de la unidad (con su tarea). Solo administrador. Con mantenimiento abierto la oferta no la incluye y la entrada responde 409. |
| `GET /hotel/caja?fecha=YYYY-MM-DD` | Pagos del día ligados a reserva. Sin movimiento bancario en esta versión. |

## Criterio de aceptación

El front de Vercel puede implementarse leyendo solo este contrato. Las
operaciones de la tabla pasan contra PostgreSQL con las reglas de sesión,
idempotencia y errores de arriba; nada fuera de la tabla existe.
