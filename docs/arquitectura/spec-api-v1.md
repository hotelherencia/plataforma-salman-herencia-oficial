# Especificación API V1 — contrato entre el front y el backend

**Estado:** REQUISITO PROPUESTO, fechado 2026-10-28; ampliado 2026-10-30
(búsqueda de reservas, gestión de usuarios, operación de la habitación,
cancelación y cargos — secciones etiquetadas) y 2026-11-03 (lectura del
inventario de habitaciones, `GET /hotel/habitaciones`, orden del propietario
tras la revisión E2E) y, el mismo 2026-11-03, mantenedor de habitaciones,
consulta de reservas por periodo, ocupación e indicadores operativos (flujos,
métricas y criterios en [spec-hotel-operacion-v1.md](spec-hotel-operacion-v1.md)).
Es el contrato que el
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
  `totp_activado` y `mfa_pendiente` (administrador sin 2FA activo: el front
  muestra un aviso persistente). Migración: la columna nace desactivada, nadie queda fuera.
  **Política 2FA (2026-11-17, reemplaza C-03 basado en `amr`):** la decisión
  depende solo del TOTP de la plataforma, igual para Google y usuario/clave.
  Con TOTP activo (cualquier rol) siempre se pide el código, aunque Google
  envíe `amr`. Un administrador sin TOTP entra para poder enrolarse: queda
  `mfa_pendiente=true`, auditoría `ok sin 2fa (mfa_excepcion_enrolamiento)` y
  evento de seguridad `mfa_excepcion_enrolamiento`. Modo estricto opcional:
  `GOOGLE_ADMIN_EXIGE_MFA=1` rechaza por Google al administrador sin TOTP
  (`/login?error=mfa_requerido`); el enrolamiento sigue por usuario/clave.
  **SEC-A02 (2026-11-05):** el secreto pendiente vive en su propia columna
  (`totp_secreto_pendiente`, migración 0013): iniciar un reenrolamiento jamás
  desprotege la cuenta, y reemplazar o desactivar el factor exige la clave
  actual (reautenticación → 401 sin ella). El QR solo expone el pendiente.
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
`limpieza` queda DECISIÓN PENDIENTE, no se inventa). **1A.2 (2026-11-17,
`servicio/roles.py`)**: se separan dos administraciones —`admin_hotel`
(Administrador del hotel: precios, tipos, habitaciones, reservas, cobros,
caja, reportes) y `admin_plataforma` (Administrador de plataforma: usuarios,
seguridad, ajustes del sistema como la tasa de IVA)—; `administrador` sigue
existiendo y equivale a ambas (los usuarios existentes no pierden acceso).
Los tres roles administrativos exigen doble factor (aviso de enrolamiento y
regla de Google). En esta sección «solo `administrador`» se lee «solo
administración de plataforma»; en las de operación del hotel, «solo
administración del hotel». HECHO DOCUMENTADO:
`usuarios.activo boolean NOT NULL DEFAULT true` y `UNIQUE (empresa_id,
nombre)`; la clave solo se guarda como hash argon2id
(`seguridad.hashear_clave`); `cobro.ROLES_PAGO_MANUAL` ya exige `recepcion`,
`caja` o `administrador` para el cobro manual.

- `GET /usuarios`: solo `administrador`. Lista `id`, `nombre`, `rol`, `activo`.
  Jamás devuelve `clave_hash`.
- `POST /usuarios {nombre, rol, clave}`: solo `administrador`. Crea con hash
  argon2id. Nombre repetido en la empresa → **409**.
- `POST /usuarios/{id}/clave {clave, clave_actual?}`: el propio usuario o un
  `administrador`. Quien cambia su propia clave envía `clave_actual`; si no
  coincide, **401** y el hash no cambia. Un administrador que cambia la clave
  de otro usuario no la envía. La clave nueva reemplaza el hash y revoca las
  demás sesiones de ese usuario (#322): la sesión que ejecuta el cambio sigue
  viva si es de él.
  Respuesta `{"id","estado":"clave actualizada","sesiones_revocadas"}`.
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
  `estado_operativo` es `bloqueada` o `fuera_de_servicio`, su
  `estado_preparacion` no es `limpia` ni `inspeccionada`, u otra reserva
  `en_estadia` de esa habitación solapa su rango → **409** y nada cambia. Si
  pasa: la reserva queda `en_estadia` y `estado_operativo` pasa a `ocupada`.
  - HECHO DOCUMENTADO (corregido 2026-11-03, V1-ISSUE-14; antes decía «no es
    `disponible`»): `ocupada` no bloquea la entrada de una reserva no
    solapada (turnover). Fuente: dominio `check_in` (solo `BLOQUEADA`/
    `FUERA_DE_SERVICIO`), `cobro.entrada` y
    `test_turnover_solape_sucia_limpieza_y_siguiente_checkin`. Efecto abierto
    sobre la salida: V1-ISSUE-15.
  - DECISIÓN D-ENT-01 **RATIFICADA 2026-11-06** (#296, opción b, orden del
    propietario): la entrada **exige el documento del huésped** antes de
    `en_estadia` — si la reserva aún no lo trae (p. ej. conversión de
    solicitud pública), el cuerpo de la entrada lo captura
    (`{"documento": ...}`); si falta en ambos → 409 «registra el documento
    del huésped». La hora de llegada (15:00 del dominio) queda fuera por
    ahora: nadie opera fuera de horario. La entrada sigue sin asentar cargo:
    el alojamiento completo nace al confirmar la reserva.
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

## Mantenedor, consulta, ocupación e indicadores (2026-11-03)

REQUISITO PROPUESTO. Las reglas completas (flujos por rol, campos editables,
regla de vigencia de tarifas, definición de cada indicador y estados por noche)
viven en [spec-hotel-operacion-v1.md](spec-hotel-operacion-v1.md); aquí solo
el contrato:

- `PUT /hotel/habitaciones/{id}`: `id` con patrón
  `^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$` (si no, 422); con `If-None-Match: *` solo
  crea (existe → 409). Responde `creada` y `cambios {campo: [antes, después]}`
  y deja auditoría. No toca reservas, tarifas ni estados.
- **Precio de una noche: UNA sola fuente (entregas 1A y 1A.2,
  `servicio/precios.py`, migración 0022)**. Todo precio se define en el
  mantenedor «Tipos, habitaciones y precios» (`/hotel/tipos`). De mayor a
  menor prioridad: excepción por fecha de la habitación → excepción por fecha
  del tipo → precio propio de la habitación (`habitaciones.precio_propio_clp`)
  → precio base del tipo (`tipos_habitacion.precio_base_clp`). Entre
  excepciones del mismo nivel gana la de mayor `fecha_desde` con
  `fecha_desde ≤ d < fecha_hasta`; a igualdad, la registrada más
  recientemente (la regla de vigencia de siempre). Excepción con
  `precio_clp: null` = sin venta. Sin ningún precio la noche queda sin tarifa
  y no se vende. Resolvedor único para oferta, reserva, ocupación, listado y
  canal público. La reserva guarda el precio de cada noche y su origen en
  `reserva_noches` y el total en `reservas.total_aceptado_clp`.
- **El editor heredado `PUT /hotel/tarifas` ya no existe** (1A.2): duplicaba
  el mantenedor. La migración 0022 convirtió las tarifas por habitación en
  precio base del tipo, precio propio y excepciones por fecha con precios
  idénticos noche a noche, y las dejó archivadas (`tarifas.archivada_en`,
  visibles en la ficha como historial).
- **IVA (1A.2, `servicio/iva.py`)**: todos los precios son **con IVA
  incluido** y ese monto es la fuente de verdad. Con la tasa vigente *t*
  (`ajustes_plataforma.iva_porcentaje`, 19 por defecto): neto =
  redondeo medio-arriba(precio × 100 / (100 + t)); IVA = precio − neto. Un
  monto ingresado como neto (`precio_en: "neto"`) se guarda como
  redondeo medio-arriba(neto × (100 + t) / 100). Cambiar la tasa no cambia
  los precios guardados, solo su desglose.
- `POST /hotel/habitaciones/{id}/servicio {en_servicio, motivo?}`: baja
  lógica (`fuera_de_servicio`) y reincorporación. Solo administrador; con
  `Idempotency-Key`; retirar exige `motivo` (422) y ninguna reserva
  `confirmada`/`en_estadia` (si no, 409 con `reservas_vigentes`). **No existe
  `DELETE` de habitaciones.**
- `GET /hotel/reservas` suma `desde`, `hasta` (la reserva toca el periodo:
  `inicio < hasta` y `fin > desde`; `hasta ≤ desde` → 422) y `habitacion_id`.
- `GET /hotel/reservas/{id}`: detalle con cargos, pagos y cuenta (saldo con la
  misma fórmula de la salida). Documento solo para `ROLES_DOCUMENTO`.
- `GET /hotel/ocupacion?desde&hasta` (≤ 62 noches) y `GET
  /hotel/indicadores?desde&hasta&tipo` (≤ 92 noches): lectura para cualquier
  rol, sin dinero ni documento; fecha de corte = fecha del servidor.

## Canal público (2026-11-03, V1-ISSUE-21; implementado en V1-ISSUE-22/24)

Superficie sin sesión para la landing https://hotelherencia.cl/. Prefijo
propio `/publico/`; sin cookie ni credenciales (el navegador del visitante
jamás recibe `sid`). La empresa es la del núcleo del proceso (regla de
arranque), **nunca un parámetro**: una sola empresa en V1 (SUPUESTO
Q-CORE-01). Las respuestas no llevan datos de huéspedes ni identificadores
internos ajenos a la operación (la oferta cita `habitacion_id` porque la
solicitud lo necesita).

- `GET /publico/disponibilidad?inicio&fin&personas` — misma regla que
  `GET /hotel/oferta` (cupo, tarifa vigente en cada noche §2.8, RES-VENDIBLE,
  vencimiento): la decide `reservas.oferta`; esta ruta solo la expone sin
  sesión. Validación: 400 `fin <= inicio`; 422 personas fuera de 1..30,
  `inicio` en el pasado o más de 30 noches.
- `POST /publico/solicitudes` — persiste una **solicitud** (no una reserva:
  D-PUB-01 sigue pendiente) en tabla propia con `estado='recibida'`,
  `origen='landing'` y fila de auditoría (`actor='publico:<solicitud_id>'`).
  Cuerpo mínimo: `{habitacion_id, inicio, fin, personas, huesped_nombre,
  huesped_contacto}`; cabecera `Idempotency-Key` obligatoria. Sin cupo o con
  alguna noche sin tarifa → 409 legible y **nada se persiste** (CA-PUB-05).
  Misma clave + mismo cuerpo → misma solicitud (200, `reintento:true`);
  misma clave + otro cuerpo → 409 (espacio de claves separado del interno,
  `solicitudes(empresa_id, idempotency_key)` único). Espacio de claves y tabla
  son propios: la clave del visitante nunca toca `claves_idempotencia`.
- Freno de abuso en memoria por IP: máximo 6 solicitudes por minuto → 429;
  cuerpo mayor a 8 KB → 413.
- CORS: con `ORIGEN_LANDING` configurado, ese origen accede **solo** a
  `/publico/*`, con `Access-Control-Allow-Origin` sin credenciales (preflight
  incluido); el resto de la API sigue exigiendo `ORIGEN_FRONT` con
  credenciales y `origin_de_mutaciones` devuelve 403 a orígenes ajenos en
  mutaciones internas (CA-PUB-03). Sin `ORIGEN_LANDING`, las rutas públicas
  responden same-origin (útiles para el front y para pruebas).
- Conversión interna (recepción, V1-ISSUE-24): `GET /hotel/solicitudes`,
  `POST /hotel/solicitudes/{id}/conversion` (crea la reserva por
  `reservas.crear_reserva` — la misma operación y la misma carrera por la
  última unidad; sin cupo → 409 y la solicitud queda `recibida`) y
  `POST /hotel/solicitudes/{id}/rechazo` (estado `rechazada` + motivo). La
  trazabilidad es solicitud → `reserva_id` + auditoría. Dos solicitudes
  idénticas concurrentes son dos solicitudes; la conversión de cada una la
  decide el servidor de a una (CA-PUB-06: como máximo una confirmación por
  carrera, la misma regla transaccional de la reserva).
- CA-PUB-01: sin sesión, la disponibilidad responde 200 sin datos personales.
  CA-PUB-02: las rutas internas siguen 401 sin sesión. CA-PUB-04: misma clave
  y cuerpo no crean dos solicitudes.

## Contacto y leads de la landing (2026-11-04, V1-ISSUE-20 punto 8 resuelto)

DECISIÓN 2026-11-04 (orden del propietario): el formulario de contacto de
https://hotelherencia.cl/ se integra a la plataforma con **formulario
propio**; Formspree se retira (independencia y sin costo adicional). La
landing postea a `{API_URL}/publico/leads`, con `API_URL` por defecto el
front Vercel en `/api/*` (reenvío al backend según `front/vercel.json`, sin
CORS extra); en pruebas y E2E, `window.LANDING_API_URL` apunta al servicio
directo. Mismas reglas generales del canal público: prefijo `/publico/`, sin
cookie ni credenciales, empresa = la del núcleo del proceso (nunca un
parámetro).

- `POST /publico/leads` — sin sesión: persiste un **lead** (prospección:
  consulta general del visitante) en tabla propia con `estado='nuevo'`,
  `origen='landing'` y fila de auditoría (`actor='publico:<lead_id>'`).
  Cuerpo mínimo: `{nombre, correo, telefono}`; opcionales `{huespedes,
  check_in, check_out, mensaje}` (el formulario de la landing envía los
  siete). Cabecera `Idempotency-Key` obligatoria. Espacio de claves propio
  (`leads(empresa_id, idempotency_key)` único): la clave del visitante nunca
  toca `claves_idempotencia`. Misma clave + mismo cuerpo → 200 `reintento:true`;
  misma clave + otro cuerpo → 409. Freno por IP: máximo 6 por minuto → 429;
  cuerpo mayor a 8 KB → 413.
- Validación: `nombre` no vacío (≤ 200); `correo` con formato (≤ 320);
  `telefono` no vacío (≤ 40); `huespedes` 1..30 si viene; si vienen fechas,
  vienen ambas y `check_out > check_in` (422); `mensaje` ≤ 2000. Los datos de
  contacto se guardan **tal cual**: son el objeto de la gestión comercial
  (igual que `solicitudes.huesped_contacto`); la redacción NFR-A03 aplica solo
  si el texto se envía a un modelo externo, que este canal no hace.
- Respuesta 201 `{lead: {id, estado, creado_en}, referencia}` sin datos de
  terceros ni identificadores internos ajenos. `referencia` es opaca. La
  landing, al confirmar, ofrece continuar en `/reservar` con las fechas y
  `ref`: el nombre, el correo y el teléfono no viajan en la URL. La
  Idempotency-Key se conserva si la red no confirma el resultado y se renueva
  en 2xx o 4xx, para no crear otro lead al reintentar.
- Gestión interna (recepción o administrador; 401 sin sesión, 403 con otro
  rol): `GET /hotel/leads?estado=` — bandeja por estado (`nuevo|contactado|
  cerrado`; sin filtro, todas) orden `creado_en` DESC, con los datos de
  contacto y el mensaje (la bandeja ES la agenda de seguimiento). Solo leads
  de la empresa de la sesión.
- `PUT /hotel/leads/{id}` — corrige los datos del lead en cualquier estado (2026-11-20; ver la tabla de operaciones).
- `POST /hotel/leads/{id}/estado` — `{estado: contactado|cerrado, nota?}`.
  Transiciones válidas: `nuevo→contactado`, `nuevo→cerrado`,
  `contactado→cerrado`; cualquier otra → 409. Ajeno o inexistente → 403
  «acceso denegado» (sin revelar cuál es el caso, igual que las solicitudes).
  `Idempotency-Key` interna obligatoria (la compuerta de mutaciones). Guarda
  `gestion_en`/`gestion_por`/nota con fila de auditoría (`actor=<nombre de
  sesión>`). La gestión nunca borra: el lead queda en su estado final.
- CA-LEAD-01: sin sesión, crear un lead responde 201 sin datos personales de
  terceros. CA-LEAD-02: reintento con misma clave y cuerpo no crea dos leads.
  CA-LEAD-03: la bandeja exige rol de gestión y nunca muestra leads de otra
  empresa. CA-LEAD-04: la gestión es idempotente por clave interna: repetir
  la misma operación con la misma clave devuelve el mismo resultado sin
  reescribir `gestion_en`.

## Agente de reservas (2026-11-04, V1-ISSUE-28/29; D-AGT-01 ratificada 2026-11-04)

Copiloto de recepción (nivel **N0**, DECISIÓN 2026-11-04: orden del propietario
de proceder con N0; D-AGT-02..06 siguen pendientes y nada de este paquete se
despliega sin autorización). Detalle de historias, herramientas y datos en
`specs/005-hotel-agente-reservas/`; aquí va el contrato. **El agente no es
autoridad**: cupo, tarifa, total, política y estado los produce el servidor
(`reservas.oferta`, mismas reglas de `/hotel/oferta`); el modelo solo elige
una plantilla y un saludo libre, y un verificador determinista rechaza todo
borrador cuyas cifras no vengan del turno que las originó.

Todas las rutas exigen sesión de recepción o administrador (401 sin sesión,
403 con otro rol o con otra empresa). Las mutaciones llevan
`Idempotency-Key`. La identidad de servicio `agente` se crea por migración,
sin clave utilizable: ninguna sesión web puede emitirse para ella (FR-A06) y
su barrera es la lista cerrada de herramientas, no los roles de sesión.

- `POST /hotel/agente/consultas` — `{canal_origen: manual|landing|correo|whatsapp, texto: 1..4000}`.
  201 `{consulta, borrador?}`: el borrador queda `pendiente_aprobacion` (o
  `escalado` con motivo). Con política N1 y borrador solo informativo, el
  puerto del canal intenta el envío; sin adaptador (D-AGT-03 sin canal
  nombrado) → 503 `{"detail":"canal no configurado","estado":"pendiente_envio"}`
  y el borrador queda `pendiente_envio` (T060). Datos sensibles, plantilla
  `escalar` u horario definido caen a N0 (`pendiente_aprobacion`). Sin
  adaptador del modelo (D-AGT-02 pendiente) → 503
  `{"detail":"modelo no configurado","estado":"pendiente"}` con la consulta
  guardada; recepción la atiende como hoy. El texto se guarda **redactado**
  (NFR-A03: sin RUT, tarjetas, correos ni teléfonos). Misma clave y cuerpo →
  misma consulta sin una segunda llamada al modelo.
- `GET /hotel/agente/consultas?estado=` — lista por estado (`pendiente`,
  `procesada`, `escalada`) sin texto completo.
- `GET /hotel/agente/consultas/{id}` — consulta con sus borradores y traza
  resumida; ajena o inexistente → 403. Si un turno creó una solicitud, la
  traza incluye solo `solicitud_id` (sin nombre ni contacto).
- `POST /hotel/agente/borradores/{id}/aprobacion` — `{texto_editado?}`.
  Si la oferta del borrador venció (> 15 min), el servidor **recotiza**:
  cifra distinta → 409 «la oferta cambió» con borrador nuevo; igual → 200
  `aprobado` (o `editado` con `texto_editado`). Ya resuelto → 409. Dos
  aprobaciones concurrentes: una 200 y otra 409.
- `POST /hotel/agente/borradores/{id}/descarte` — `{motivo}`; 200; ya
  resuelto → 409.
- `GET /hotel/agente/politica` / `PUT /hotel/agente/politica` — política de
  autonomía por empresa (`nivel` N0|N1|N2, horario, `max_noches`,
  `max_personas`, `tope_mensual_clp`). GET: recepción o administrador. PUT:
  solo administrador; subir de nivel sin `evaluacion_ref` → 409 (compuerta
  SC-003); recepción → 403.

Herramientas internas (no son HTTP; el modelo solo las nombra con
argumentos validados): `consultar_disponibilidad` (envuelve `reservas.oferta`)
y `proponer_borrador` (plantilla ∈ {cotizacion, sin_disponibilidad,
pedir_dato, escalar} con referencias a ítems del turno y saludo ≤ 280 sin
dígitos). En N0 son exactamente estas dos: una decisión que nombra
`crear_reserva`, pagos, caja, usuarios, cancelación, entrada, salida o
habitaciones se rechaza sin ejecutar y la consulta escala. `crear_solicitud`
llega solo en N2: crea una solicitud `recibida` con origen `agente` por la
misma operación del canal público (no cobra ni confirma la reserva; una sola
por consulta). Sin cupo o sobre `max_noches`/`max_personas`, escala y no
persiste. El modelo jamás envía `empresa_id`,
rol, tarifa ni total como argumento.

## Canal WhatsApp (2026-11-09, spec 006, #324)

Puerto de mensajería del servicio, no del front. El hotel lo consume: un
mensaje de texto válido se guarda como consulta del agente con
`canal_origen = whatsapp` y el texto ya redactado. El identificador externo
del mensaje y el de la conversación viven en `mensajes_whatsapp` para no
duplicar un reintento de Meta; un mensaje posterior de la misma conversación
incluye el texto redactado del anterior. Adjuntos y avisos de entrega no
crean consulta. La salida hacia el hilo sigue en el puerto vacío
(`canal no configurado`) hasta que el canal de N1 y la cuenta de Meta estén
autorizados (D-AGT-03, D-WSP-01). Sin las tres variables
`WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN` y `WHATSAPP_PHONE_NUMBER_ID`
el puerto responde 503 «no configurado» y no persiste nada. Ninguna prueba
llama a Meta.


## Políticas del hotel (2026-11-17, Entrega 1A.3)

Única fuente editable de los datos operativos que el agente y la cotización
necesitan: horarios de llegada y salida, recargos de llegada anticipada y
salida tardía, cancelación, no-show, depósito, mínimo de noches, niños y cama
adicional, mascotas, desayuno, estacionamiento, medios de pago, el proceso de
registro de llegada/salida y las preguntas frecuentes. Las edita la
**administración del hotel** (`PUT /hotel/politicas`). La tasa de IVA sigue en
`PUT /plataforma/ajustes/iva` (administración de plataforma).

Los valores iniciales salen de lo ya publicado en la landing o de lo que
estaba en el código. Lo no ratificado (en particular la cancelación de 48 h y
la hora de llegada 14:00 frente a un comentario interno de 15:00) se marca
`pendiente_confirmar` y la UI lo resalta. El servicio no inventa datos.

`GET /publico/disponibilidad` y `GET /hotel/oferta` aceptan de forma opcional
`hora_llegada`, `hora_salida`, `cama_adicional`, `ninos` y `mascotas`. El
total incluye los recargos de la política vigente (IVA incluido) y devuelve
desglose neto/IVA más el texto de cancelación. Al confirmar una reserva se
congela un `politica_snapshot` (y los recargos) en la fila: un cambio
posterior del mantenedor no altera reservas ya hechas.

El agente suma la herramienta `consultar_politicas` (tema opcional: horarios,
cancelacion, faq, etc.). El verificador acepta cifras que salgan de esa
herramienta o de la oferta del mismo turno. El modelo no redacta los montos:
los compone el servidor.

## Operaciones de esta versión

| Operación | Efecto |
|---|---|
| `GET /salud` | Liveness: 200 sin sesión ni datos. No toca la base de datos. |
| `GET /readiness` | Readiness (OPS-A02, 2026-11-05): consulta real a la base y estado de migraciones; 503 si no responde. Sin sesión. Es el healthcheck de despliegue de Railway desde 2026-11-16 (OBS-02). |
| `GET /sesion` | Con cookie `sid`: `{id, usuario, rol, empresa_id, totp_activo}`. Sin cookie → 401 `sin sesión`; sid vencido → 401 `sesión inválida o vencida`; sid de otra empresa que el núcleo (titular↔sintético) → 401 `sesion_empresa_ajena` (borra cookie, audita y deja traza en logs). |
| `GET /cuenta/2fa/qr` | Con sesión y alta en curso: devuelve el QR (SVG) del secreto **pendiente**. Sin pendiente → 400. El secreto activo nunca se expone (SEC-A02, 2026-11-05). |
| `POST /sesion` | Abre sesión de la empresa Herencia y fija la cookie `sid`. Con 2FA activo exige además `totp` (ver «Identidad y sesión»). |
| `DELETE /sesion` | Cierra la sesión (la fila de `sesiones` queda revocada). |
| `POST /cuenta/2fa` | Con sesión: genera el secreto TOTP **pendiente** (columna propia: el factor activo queda intacto hasta confirmar) y devuelve `{secreto, uri}`. Con 2FA ya activo exige `clave` en el cuerpo (reautenticación): sin clave o errada → 401 (SEC-A02). |
| `POST /cuenta/2fa/activar` | Con sesión: confirma el alta verificando el código contra el secreto pendiente; al confirmar, el pendiente pasa a ser el activo (reemplaza al previo). Código inválido o sin alta en curso → 400. |
| `DELETE /cuenta/2fa` | Con sesión: desactiva el segundo factor y borra ambos secretos. Exige `clave` en el cuerpo (reautenticación): sin clave o errada → 401 (SEC-A02). |
| `GET /auth/google/estado` | `{configurado: bool}`: true solo con `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` en el entorno. |
| `GET /auth/google` | 302 al consentimiento de Google (scope `openid email profile`, `state` de un solo uso, 10 min); sin configurar → 503 «no configurado». Fija la cookie HttpOnly `oauth_tx` (vida 10 min, path `/`) que ata el state al navegador (SEC-A05; path `/` para que sobreviva el proxy same-origin `/api/auth/...`). |
| `GET /auth/google/callback` | Valida `state` **consumiéndolo en todo intento** y exigiendo que la cookie `oauth_tx` coincida con la que originó el login (state de otro navegador → 400, SEC-A05); intercambia `code`, verifica el ID token y abre la sesión con cookie `sid`, redirigiendo a `FRONT_URL`. Email sin vínculo → `/login?error=cuenta_sin_vinculo`; `access_denied` → `/login?error=acceso_denegado`. |
| `POST /auth/google/totp` | Segundo paso del login Google de un administrador con TOTP activo: valida el código contra la transacción MFA pendiente (cookie propia, un solo uso) y abre la sesión con cookie `sid`. Sin transacción → 400; código errado → 401; freno de intentos → 429. Sin sesión previa. |
| `GET /usuarios` | Lista `id`, `nombre`, `rol`, `activo` de la empresa. Solo administrador. |
| `POST /usuarios` | Alta `{nombre, rol, clave, email?}` con hash argon2id. (#352) `email` opcional: correo de Google con que entra (minúsculas; ya vinculado a otro → 409). Solo administrador. Nombre repetido → 409. |
| `GET /hotel/ajustes` | (#348, 2026-11-18) Ajustes operativos editables desde Configuración; hoy `tope_solicitudes_cliente {activo, max_solicitudes, dias}` (inicial 3 en 7 días). Solo administración del hotel. |
| `PUT /hotel/ajustes/{clave}` | (#348) Guarda un ajuste validado (422 si no cumple) y lo audita. Idempotente. Solo administración del hotel. |
| `GET /hotel/correo/buzones` | (#355, 2026-11-18) Buzones de correo configurados (lectura de enviados o envío de avisos), sin secretos: solo `secretos_guardados`. Incluye `cifrado_disponible`, el ajuste `revision_correo` y el catálogo de proveedores (IMAP/SMTP con clave u OAuth2, API de Gmail, Microsoft Graph). Solo administración del hotel. |
| `POST /hotel/correo/buzones` | (#355) Alta `{etiqueta, proposito, proveedor, parametros, secretos, activo}`; secretos cifrados con `CORREO_CLAVE_CIFRADO` (sin ella → 409). Validación → 422. Idempotente; la huella guarda el hash de los secretos, no los secretos. |
| `PUT /hotel/correo/buzones/{id}` | (#355) Edita un buzón; un secreto omitido o vacío conserva el guardado, `null` lo borra. Un solo buzón de envío activo por empresa. |
| `DELETE /hotel/correo/buzones/{id}` | (#355) Elimina el buzón (auditado). |
| `POST /hotel/correo/buzones/{id}/prueba` | (#355) Prueba la conexión: lectura → cuenta enviados de 7 días (solo metadatos); envío → correo de prueba al destino. Responde `{ok, detalle}`. |
| `POST /hotel/correo/revision` | (#355) «Revisar ahora»: revisa los enviados y pasa a `contactado` los leads `nuevo` a cuyo correo el hotel escribió después de su creación (nota «auto: correo enviado desde <buzón> el <fecha>», autor `auto:correo`, reversible). El ciclo automático corre cada `revision_correo.intervalo_minutos` (inicial 15). |
| `POST /usuarios/{id}/email` | (#352, 2026-11-18) Vincula `{email}` (o desvincula con `null`) el correo de Google con que entra el usuario; un correo pertenece a un solo usuario (409). La auditoría registra el vínculo sin copiar el correo. Solo administración de plataforma. |
| `POST /usuarios/{id}/clave` | Cambia la clave (reemplaza el hash) y revoca las demás sesiones de ese usuario. La sesión propia exige `clave_actual` (401 si no coincide). La sesión que ejecuta el cambio sigue viva si es de él. El propio usuario o un administrador. |
| `POST /usuarios/{id}/revocacion` | Revoca todas las sesiones del usuario. Solo administrador, sobre otro usuario. |
| `POST /usuarios/{id}/baja` | `activo=false` y revoca sesiones. Solo administrador, sobre otro usuario; no al último administrador activo (409). |
| `PUT /hotel/habitaciones/{id}` | Alta o cambio de habitación: tipo, capacidad (con `If-None-Match: *` solo alta). Devuelve `creada` y `cambios`; auditado. Solo administrador. |
| `GET /hotel/tipos` | Mantenedor único de precios: tipos con sus habitaciones, excepciones por fecha activas (del tipo y de sus habitaciones), el precio de hoy de cada habitación y su origen (`tipo`, `habitacion`, `excepcion_tipo`, `excepcion_habitacion`), resumen por tipo e `iva {porcentaje, regla}`. Cualquier rol; `puede_editar` para administración del hotel, `puede_editar_iva` para administración de plataforma. En titular, solo el inventario operativo (HAB-01..17 y altas por lote). |
| `POST /hotel/tipos` | Alta de un tipo (`tipo_id` `^[a-z0-9][a-z0-9_]{0,49}$`, nombre, capacidad base, precio base opcional con IVA o `precio_en: "neto"`). Ya existe → 409. Auditado. Solo administración del hotel. |
| `PUT /hotel/tipos/{id}` | Edición parcial del tipo (nombre, capacidad base, `precio_base_clp` —`null` lo quita; `precio_en` con_iva/neto—, orden, activo). El precio base lo heredan las habitaciones del tipo sin precio propio ni excepción en esa noche; las reservas aceptadas no cambian (precio congelado por noche). Devuelve `cambios`; auditado. Solo administración del hotel. |
| `POST /hotel/habitaciones/lote` | Alta de N habitaciones (1–100) de un tipo con numeración `prefijo + número` con `digitos` (p. ej. `HAB-` desde 18 → HAB-18…). Todo o nada: alguna ya existe → 409 con `existentes`; tipo inexistente → 422; tipo inactivo → 409. Nacen en servicio, limpias y `en_inventario`. Auditado por habitación y por lote. Solo administración del hotel. |
| `PUT /hotel/habitaciones/{id}/precio` | Precio propio de la habitación `{precio_clp, precio_en?}` (gana al base del tipo); `precio_clp: null` lo quita y vuelve a heredar. Inexistente → 404. Auditado. Solo administración del hotel. |
| `POST /hotel/precios/excepciones` | Excepción por fecha `[fecha_desde, fecha_hasta)` de un tipo (`tipo_id`) o de una habitación (`habitacion_id`), uno de los dos (si no, 422); `precio_clp` con IVA (o `precio_en: "neto"`) o `null` = sin venta; `motivo` opcional. Idéntica a una activa → 409. Auditada. Solo administración del hotel. |
| `POST /hotel/precios/excepciones/{id}/retiro` | Retiro lógico de una excepción (deja de aplicar; queda en el historial). No activa → 404. Auditado. Solo administración del hotel. |
| `GET /plataforma/ajustes` | Ajustes del sistema visibles para cualquier sesión: `iva {porcentaje, regla}` y `puede_editar`. |
| `PUT /plataforma/ajustes/iva` | Tasa de IVA `{iva_porcentaje}` (0–100, hasta 3 decimales). No cambia precios guardados (son con IVA), solo el desglose. Auditado. Solo administración de plataforma. |
| `GET /hotel/oferta?inicio&fin&personas` | Solo lo disponible, con tarifa vigente **en cada noche** de `[inicio, fin)` (spec-hotel-operacion-v1 §2.8, 2026-11-03) y vencimiento de la oferta. `total_clp` es la suma noche a noche con la tarifa vigente de cada noche (DECISIÓN 2026-11-06, #305); `tarifa_noche_clp` es la tarifa de la primera noche. Incluye unidades ocupadas o sucias si el rango no solapa; excluye mantenimiento, bloqueada y fuera de servicio. |
| `GET /hotel/habitaciones` | Inventario operativo de las unidades (REQUISITO PROPUESTO, 2026-11-03, orden del propietario tras la revisión E2E: la pantalla operaba a ciegas sin lectura del estado). Por unidad: `tipo`, `capacidad`, `estado_operativo`, `estado_preparacion`, `mantenimiento`, `tareas_pendientes`, `limpieza_pendiente` y última tarifa configurada como referencia. Solo lectura, cualquier rol de la sesión; las mutaciones conservan sus reglas de rol (limpieza: recepción o administrador; mantenimiento: solo administrador). |
| `GET /hotel/habitaciones/{id}` | Ficha de la habitación: datos, estados, precio de hoy y su origen, excepciones por fecha que la alcanzan (con `aplicada_hoy`), tarifas heredadas archivadas por 0022 (solo lectura), reservas en cualquier estado, tareas y —solo administrador— auditoría. Cualquier rol; inexistente → 403. |
| `POST /hotel/habitaciones/{id}/servicio` | Retira de operación (`fuera_de_servicio`, con motivo) o reincorpora. Solo administrador; reservas vigentes → 409. Baja lógica: nada se borra. |
| `GET /hotel/reservas?fecha=&estado=&texto=&desde=&hasta=&habitacion_id=` | Búsqueda de reservas de la empresa, filtros opcionales combinados con AND. Ver «Búsqueda de reservas» y la ampliación 2026-11-03. |
| `GET /hotel/reservas/{id}` | Detalle de una reserva con cargos, pagos, cuenta, liquidación y `personas` (#298). Cualquier rol; documento según rol; ajena o inexistente → 403. |
| `GET /hotel/reservas/{id}/mensajes` | (#452, #454) Mensajes preformateados para el huésped (confirmación, recordatorio, pedir datos, cancelación, gracias) con texto, asunto, enlace `wa.me` si hay teléfono y `puede_correo`; contacto del titular, `datos_faltantes`, `alerta` si no hay forma de contactarlo e historial de envíos (destino enmascarado). Recepción y administración del hotel; ajena → 403. |
| `POST /hotel/reservas/{id}/mensajes` | (#452) `{plantilla, canal: correo \| whatsapp}` con `Idempotency-Key`: `correo` envía por el buzón de envío activo (409 sin buzón o sin correo válido; fallo de envío queda `fallido`); `whatsapp` registra que se abrió el enlace (409 sin teléfono). Registra plantilla, canal, estado y actor, nunca el cuerpo. Recepción y administración del hotel. |
| `GET /hotel/ocupacion?desde&hasta` | Estado por habitación y noche (confirmada, en estadía, finalizada, disponible, sin tarifa, no vendible) y reservas canceladas del periodo; resumen nocturno con `disponibles`, `ocupadas_cupo` (cupo comprometido §5) y `no_vendibles` — renombrado 2026-11-04 (#320). Cualquier rol. |
| `GET /hotel/indicadores?desde&hasta&tipo` | Panel operativo: situación de hoy y ocupación del periodo con fórmula, unidad y fuente por indicador; serie diaria con `ocupadas_estadias` (estadías reales §4.3; denominador sin `fuera_de_servicio`, #299); `ingresos_periodo_clp` (pagos confirmados del periodo) solo para administrador (D-ROL-01 RATIFICADA 2026-11-06, #297); ADR/RevPAR siguen como no disponibles (D-IND-02). Cualquier rol. |
| `GET /hotel/documental/resumen` | Paquete documental cargado (levantamiento 2026-11-11): conteos y estado de carga. Solo lectura; no es oferta ni cobro. Con sesión. |
| `GET /hotel/documental/habitaciones` | Habitaciones del levantamiento documental (`doc_habitacion`). Solo lectura. Con sesión. |
| `GET /hotel/documental/tarifas` | Tarifas documentales (`doc_tarifa`) con `publicar_activas: false`. Solo lectura. Con sesión. |
| `GET /hotel/documental/ocupacion?periodo&habitacion_id` | Histórico de ocupación reportado (`doc_ocupacion_reportada`), `es_kpi: false`. Solo lectura. Con sesión. |
| `GET /hotel/documental/control-ocupacion` | Control de ocupación documental, `es_kpi: false`. Solo lectura. Con sesión. |
| `GET /hotel/documental/ocupacion/serie` | Serie mensual del histórico documental (no es KPI operativo). Solo lectura. Con sesión. |
| `GET /hotel/documental/tablas/{tabla}?limite` | Filas de una tabla `doc_*` permitida (máx. 2000); tabla desconocida → 404. Solo lectura. Con sesión. |
| `POST /hotel/reservas` | Confirma una sola vez. La última unidad en carrera queda en una sola reserva: la confirmación es transaccional y la base rechaza el solape en (unidad, fechas) para `confirmada` y `en_estadia`. Una unidad fuera del cupo (mantenimiento abierto, `bloqueada` o `fuera_de_servicio`) → 409 y nada cambia: misma regla que la oferta (spec-hotel-operacion-v1 §2.7). Alguna noche del rango sin tarifa vigente → 409 «sin tarifa vigente para `<hab>` la noche `<d>`» y nada cambia (§2.8). El precio se cobra noche a noche con la tarifa vigente de cada noche (DECISIÓN del propietario 2026-11-06, #305 opción b; reemplaza D-TAR-02); `tarifa_noche_aceptada_clp` queda como la tarifa de la primera noche, referencia de la penalidad de cancelación. `personas` (opcional) se persiste en la reserva y se valida contra la capacidad al confirmar (#298, DECISIÓN 2026-11-06): si excede la capacidad de la unidad → 409 y nada cambia. |
| `POST /hotel/reservas/{id}/pagos` | El núcleo registra el efecto. Si el núcleo rechaza, no hay pago. Cuerpo: `{monto_clp, clave, modo}`. `modo="manual"` (DECISIÓN, 2026-10-28): caja en efectivo o transferencia que recepción registra; solo roles recepción, caja o administrador; no consulta el banco y no queda conciliado. `modo="pasarela"` sin adaptador → 503 y nada marcado como cobrado. (#364/#365, 2026-11-18) La respuesta trae `huesped_nombre`, `habitacion_id`, `saldo_antes_clp`, `saldo_despues_clp` y `tipo` (`parcial`, `total` o `exceso`). Un monto mayor que el saldo sin `confirmar_exceso: true` → 409 con `saldo_clp` y `exceso_clp`; un monto menor se acepta como pago parcial. (Fase 1 contable / #401) `medio` es **obligatorio** para pagos manuales nuevos (`efectivo`, `debito`, `credito`, `transferencia`; omitirlo → **422**; filas históricas con `no_informado` siguen siendo legibles en reportes y cierres). Opcionales: `documento_tipo` (`boleta`, `factura`, `sin_documento`; por defecto el del mantenedor), `receptor` `{rut, razon_social, giro, direccion, comuna, correo?}` obligatorio con factura, `documento_folio`, `tarjeta_marca`, `tarjeta_ultimos4`, `codigo_autorizacion` (obligatorio con débito/crédito) y `comprobante`. Campos desconocidos → 422 (PCI: jamás número completo ni CVV; un texto con 12+ dígitos → 422). Efectivo sin turno abierto → 409 si el mantenedor lo exige. El pago lleva `fecha_contable` (Chile; un día cerrado pasa al siguiente), `turno_id` y `es_anticipo` (cobrado antes de la Llegada). |
| `POST /hotel/reservas/{id}/cargos` | (#357, 2026-11-18) `{producto_id, cantidad}`: concepto y precio salen del catálogo (precio copiado × cantidad); si el producto controla stock lo descuenta y sin stock → 409. Concepto libre `{concepto, monto_clp}` solo para la administración del hotel (recepción y caja → 403). Roles recepción, caja o administrador; solo en `confirmada` o `en_estadia`; otro estado → 409. Ver «Cargos de la estadía». |
| `POST /hotel/reservas/{id}/cargos/{cargo_id}/reverso` | (#359, 2026-11-18) Reverso contable de un cargo: asienta el movimiento contrario con `referencia` al original; nunca borra. Solo administración del hotel; motivo obligatorio (3–150); cuenta abierta (`confirmada` o `en_estadia`); cargo inexistente, ya reversado o que ya es reverso → 409. Idempotente. |
| `POST /hotel/reservas/{id}/habitacion` | (#361, 2026-11-18) Cambia la habitación de una reserva `confirmada` o `en_estadia` con `{habitacion_id, motivo}`; conserva la tarifa pactada. Recepción o administración del hotel. Destino fuera del cupo, sin capacidad, no preparada (en estadía) u ocupada en el rango → 409. En estadía la habitación de origen queda sucia con tarea de limpieza. Queda en `reasignaciones` y en la auditoría. La entrada (`/entrada`) acepta además `habitacion_id` para confirmar la unidad al llegar (#360) y `documento_tipo` (`rut` o `pasaporte`, validado; #367). |
| `GET /hotel/aseo` | (#362, 2026-11-18) Lista para aseo: habitaciones con limpieza pendiente primero; situación (`ocupada`, `sale_hoy`, `llega_hoy`, `libre`), observaciones pendientes y última limpieza (quién, verificación). Sin datos del huésped ni precios. Roles aseo, recepción o administración del hotel. |
| `POST /hotel/limpiezas/{tarea_id}/verificacion` | (#363) `{aprobada, observacion}`. Verificada → la unidad `limpia` pasa a `inspeccionada`. Rechazada (observación obligatoria) → vuelve a `sucia` con tarea nueva y la observación queda para aseo. Solo administración del hotel; ya verificada o no completada → 409. |
| `GET /hotel/incidencias` | (#415) Incidencias por habitación o área, abiertas primero y las que bloquean la unidad antes. Filtros `estado` (`abiertas`, `abierta`, `en_curso`, `resuelta`, `cerrada`) y `habitacion_id`. Roles aseo, recepción o administración del hotel. |
| `POST /hotel/incidencias` | (#415) `{habitacion_id? o area, descripcion, gravedad, responsable?, plazo?, costo_clp?, bloquea_disponibilidad}`. Con `bloquea_disponibilidad` la unidad sale del cupo (mantenimiento desde hoy hasta `plazo`) salvo que ya estuviera en mantenimiento. Idempotente; auditada sin datos personales. |
| `GET /hotel/incidencias/{incidencia_id}` | (#415) Detalle con bitácora append-only (creación, estados, bloqueo, evidencias, cierre) y número de fotos. |
| `POST /hotel/incidencias/{incidencia_id}/actualizacion` | (#415) `{estado: abierta\|en_curso\|resuelta, gravedad, responsable, plazo, costo_clp}`. `resuelta` libera la unidad si esta incidencia la había bloqueado y no queda otra que la bloquee. Cerrada → 409. |
| `POST /hotel/incidencias/{incidencia_id}/cierre` | (#415) `{costo_clp?, nota?}`. Cierra y libera el bloqueo que aplicó. Recepción o administración; ya cerrada → 409. |
| `POST /hotel/incidencias/{incidencia_id}/evidencias` | (#415) `{mime: image/jpeg\|png\|webp, contenido_base64}`: foto ligera desde el móvil (hasta 180 KB y 6 por incidencia; el front la reduce antes de enviar). |
| `GET /hotel/incidencias/{incidencia_id}/evidencias/{evidencia_id}` | (#415) Devuelve la imagen (privada, sin caché compartida). |
| `GET /hotel/tareas` | (#416) Tareas generales con subtareas y progreso, urgentes y próximas a vencer primero. Filtros `estado`, `habitacion_id`. |
| `POST /hotel/tareas` | (#416) `{titulo, area, habitacion_id?, prioridad, vence?, responsable?, observaciones?, plantilla_id?, subtareas[{texto, obligatoria}]}`. Recepción o administración. |
| `POST /hotel/tareas/{tarea_id}/actualizacion` | (#426) `{titulo?, prioridad?, vence?, responsable?, observaciones?}`. Recepción o administración; tarea completada o sin cambios → 409. |
| `POST /hotel/tareas/{tarea_id}/subtareas` | (#426) `{texto, obligatoria}`: agrega una subtarea a una tarea pendiente (máximo 40). Recepción o administración. |
| `POST /hotel/tareas/{tarea_id}/subtareas/{subtarea_id}/marcado` | (#416) `{hecha}`: marca o desmarca una subtarea (queda quién). |
| `POST /hotel/tareas/{tarea_id}/cierre` | (#416) Cierra la tarea; con subtareas obligatorias pendientes → 409. |
| `GET /hotel/checklists/plantillas` | (#416) Plantillas de checklist configuradas. |
| `POST /hotel/checklists/plantillas` | (#416) `{nombre, area, items[{texto, obligatoria}]}`. Solo administración del hotel; nombre repetido → 409. |
| `POST /hotel/habitaciones/{habitacion_id}/en-limpieza` | (#416) Aseo toma una habitación `sucia`: figura «En limpieza» hasta que se marque limpia (no cambia `estado_preparacion`). |
| `POST /hotel/habitaciones/{id}/observaciones` | (#363) Nota `{texto}` para aseo en una habitación. Recepción o administración del hotel. |
| `POST /hotel/habitaciones/{id}/observaciones/{obs_id}/atendida` | (#363) Aseo (o recepción/administración) marca la observación como atendida; ya atendida → 409. |
| `GET /hotel/avisos` | (#353, 2026-11-18) `{solicitudes_recibidas, canales_activos}`: contador para la insignia del menú y del panel (el front sondea cada 60 s) y canales de aviso encendidos (`correo`, `whatsapp`). Roles de gestión de solicitudes. |
| `GET /hotel/avisos/configuracion` | (2026-11-19) Configuración → Avisos: `preferencias` por tipo de evento (`solicitud_recibida`, `consulta_recibida`, `reserva_confirmada`, `pago_registrado`, `resumen_diario`) con `activo` y `destinatarios`; `destinatarios_defecto` (destino del buzón de envío, `AVISO_CORREO_DESTINO` o `ADMIN_EMAIL`); `canal` desde el que sale el correo, sin secretos; `envios`: los 20 últimos con estado `enviado`/`fallido`/`reintentando`/`omitido` y detalle legible. Solo administración del hotel. |
| `PUT /hotel/avisos/preferencias` | (2026-11-19) `{preferencias: [{tipo, activo, destinatarios}]}`: guarda qué eventos avisan y a quién (máximo 10 correos por aviso; lista vacía = correo por defecto). Validación → 422. Idempotente y auditado. Solo administración del hotel. |
| `POST /hotel/avisos/prueba` | (2026-11-19) Envía ahora un correo de prueba a todos quienes reciben algún aviso encendido (su lista o el correo por defecto) por el buzón de envío vigente; queda en «últimos envíos». Responde `{ok, detalle, destinatarios}`. Solo administración del hotel. |
| `GET /hotel/productos` | (#357, 2026-11-18) Catálogo para cargos: `texto` (todas las palabras, en nombre o categoría), `categoria` (`minibar`, `cafeteria`, `servicio`, `extra`), `inactivos` (solo administración). Recepción, caja o administración del hotel. |
| `POST /hotel/productos` | (#357) Alta `{nombre, categoria, precio_clp (IVA incluido), controla_stock, stock}`; nombre único sin distinguir mayúsculas → 409. Solo administración del hotel. |
| `PUT /hotel/productos/{id}` | (#357) Cambia nombre, categoría, precio, `activo` o `controla_stock`. Los cargos asentados conservan su precio. Solo administración del hotel. |
| `POST /hotel/productos/{id}/stock` | (#357) Ajuste `{delta, motivo}` (reposición o merma); nunca deja stock negativo (409). Solo administración del hotel. |
| `GET /hotel/productos/{id}/movimientos` | (#357) Últimos movimientos de stock (stock inicial, ajustes, cargos y reversos). Solo administración del hotel. |
| `POST /hotel/productos/importacion/vista-previa` | (2026-11-19) Revisa sin escribir las líneas de una factura electrónica XML (DTE 33/34, sin DOCTYPE/ENTITY, máx. 1,5 MB), de una planilla pegada o del lector de códigos: devuelve cada línea con su producto coincidente (`codigo`, `nombre` o `parecido`) o nueva, y si la factura ya fue cargada. Solo administración del hotel. |
| `POST /hotel/productos/importacion` | (2026-11-19) Confirma la carga en una sola transacción con `Idempotency-Key`: suma stock a los existentes (movimiento con `importacion_id`), crea los nuevos (precio de venta obligatorio, lo fija la administración) y registra costo neto. Una factura (emisor, tipo, folio) solo se carga una vez → 409. Solo administración del hotel. |
| `GET /hotel/productos/importaciones` | (2026-11-19) Últimas cargas (origen, documento, líneas, unidades, quién y cuándo). Solo administración del hotel. |
| `GET /hotel/productos/documentos?estado` | (2026-11-19) Bandeja de facturas de proveedores: `abiertos` (pendientes y pedidos en borrador), `cargada` o `todos`; informa si la lectura automática (IA) está activa y si hay buzón de recepción. Solo administración del hotel. |
| `POST /hotel/productos/documentos/archivo` | (2026-11-19) Cuerpo binario: foto (JPG/PNG/WebP) o PDF de una factura o pedido, máx. 10 MB, tipo verificado por contenido. Lee el timbre del SII (PDF417) y, con `GEMINI_API_KEY`, transcribe las líneas; queda **pendiente** (pedido: borrador), sin tocar stock. Misma foto o mismo proveedor+tipo+folio → 200 con el existente. Solo administración del hotel. |
| `POST /hotel/productos/documentos/xml` | (2026-11-19) XML del SII (DTE o EnvioDTE con facturas 33/34 y notas de crédito 61) → documentos pendientes; repetidos no se duplican; acuses/respuestas se ignoran. Solo administración del hotel. |
| `GET /hotel/productos/documentos/{id}` | (2026-11-19) Documento con líneas emparejadas al catálogo, equivalencias recordadas del proveedor, unidades por envase sugeridas, diferencias para revisar, pedido sugerido y si ya se cargó. Solo administración del hotel. |
| `GET /hotel/productos/documentos/{id}/archivo` | (2026-11-19) Foto/PDF/XML original (`nosniff`, CSP `sandbox`, sin caché). Solo administración del hotel. |
| `PUT /hotel/productos/documentos/{id}` | (2026-11-19) Corrige clase, encabezado o líneas (p. ej. escritas a mano sin IA) de un documento abierto; RUT/tipo/folio del timbre o del XML no se cambian. Recalcula diferencias. Solo administración del hotel. |
| `POST /hotel/productos/documentos/{id}/confirmacion` | (2026-11-19) `Idempotency-Key`. Carga la factura al inventario una sola vez: cantidad × `unidades_por_paquete`, costo por unidad; recuerda proveedor+ítem → producto y envase; marca el pedido como facturado. Nota de crédito o pedido → 409. Solo administración del hotel. |
| `POST /hotel/productos/documentos/{id}/descarte` | (2026-11-19) Saca el documento de la bandeja (nota de crédito: queda archivada). Solo administración del hotel. |
| `POST /hotel/productos/recepcion-correo` | (2026-11-19) Revisa ahora los buzones `recepcion_dte` (casilla de intercambio del SII) sin esperar la revisión periódica. Solo administración del hotel. |
| `GET /hotel/productos/equivalencias` | (2026-11-19) Equivalencias recordadas por proveedor: ítem del proveedor → producto y unidades por envase. Solo administración del hotel. |
| `PUT /hotel/productos/equivalencias/{id}` | (2026-11-19) Cambia producto, unidades por envase o nota de una equivalencia. Solo administración del hotel. |
| `DELETE /hotel/productos/equivalencias/{id}` | (2026-11-19) Olvida una equivalencia. Solo administración del hotel. |
| `POST /hotel/reservas/{id}/cancelacion` | Cancela desde `confirmada` con la regla de 48 h que decide `cancelar` del dominio (ver «Cancelación»); la cuenta nace vacía (ENMIENDA ADP-4/7, 2026-11-19), así que solo se revierten los cargos sueltos que hubiera (recargos, consumos) y no hay reverso de alojamiento. Roles recepción o administrador. |
| `POST /hotel/reservas/{id}/entrada` | Check-in si la habitación está lista (mantenimiento abierto, `bloqueada`/`fuera_de_servicio`, sucia u otra estadía solapada en la unidad bloquean → 409; `ocupada` no bloquea el turnover) y **ya llegó la hora de entrada** (15:00 del día de inicio según el reloj del servidor; antes → 409 «aún no es hora de llegada»; ENMIENDA ADP-5, 2026-11-19: lo decide `check_in` del dominio). Al pasar asienta la cuenta del alojamiento, una noche por cargo, con el precio de cada noche (#305). Exige el documento del huésped (D-ENT-01, DECISIÓN 2026-11-06): si la reserva no lo trae, el cuerpo `{"documento"}` lo registra; sin documento en ninguno → 409. Roles recepción o administrador (D-ROL-ENT, #304). Al pasar, la reserva queda `en_estadia` y la habitación `ocupada`. |
| `POST /hotel/reservas/{id}/salida` | Liquida la cuenta (saldo neto cargo-menos-reverso en cero) y devuelve la liquidación. Roles recepción o administrador (D-ROL-ENT, DECISIÓN 2026-11-06, #304). La habitación queda `disponible` y `sucia`, con tarea de limpieza pendiente, aunque otra estadía contigua siga en curso (ENMIENDA ADP-6, 2026-11-19: lo decide `check_out` del dominio; reemplaza la excepción de V1-ISSUE-15). |
| `POST /hotel/habitaciones/{id}/limpieza` | Completa la limpieza pendiente y, si estaba sucia, deja la unidad `limpia`. Sin limpieza pendiente → 409 (ENMIENDA ADP-8, 2026-11-19: no hay tarea que completar). Roles recepción o administrador. |
| `POST /hotel/habitaciones/{id}/mantenimiento` | Abre o cierra el mantenimiento de la unidad (con su tarea). Solo administrador. Con mantenimiento abierto la oferta no la incluye y la entrada responde 409. |
| `GET /hotel/caja?fecha=YYYY-MM-DD` | Pagos del día contable en hora de Chile (antes por fecha UTC), con `medio`, `documento_tipo` y `por_medio`; los reversos restan. Sin movimiento bancario en esta versión. |
| `GET /hotel/reservas/{id}/saldo` | (Contabilidad 2.1) Total, abonado (recibido sin aplicar), pagado (aplicado) y pendiente de la reserva, con el detalle por noche (`precio`, `pagado`, `pendiente`, `asentada`). El total incluye las noches aún no asentadas; un pago reversado deja de contar. Ajena o inexistente → 403. |
| `GET /hotel/contabilidad/movimientos?desde&hasta` | (Contabilidad 2.1) Cargos, reversos de cargo, pagos y reversos de pago del rango (días en hora de Chile) con quién los hizo, huésped, habitación, medio y documento. No depende de que haya un turno abierto: un cargo con la caja cerrada queda aquí. Roles caja o administración del hotel. |
| `GET /hotel/caja/estado` | (Fase 1 contable) Turno abierto con totales en vivo por medio, efectivo por recibir del turno anterior, fecha contable y parámetros de la caja. Roles caja, recepción o administración del hotel. |
| `POST /hotel/caja/turnos` | Abre el turno de caja: `{fondo_inicial_clp, nota?}`. Una sola caja abierta a la vez (409). Si el turno anterior entregó efectivo y el fondo difiere, exige nota de 10+ caracteres (422). Idempotente y auditado. |
| `GET /hotel/caja/turnos?desde&hasta` | Turnos del rango (máx. 92 días) con totales por medio, esperado, contado y diferencia. |
| `GET /hotel/caja/turnos/{id}` | Detalle de un turno con sus movimientos. 404 si no existe en la empresa. |
| `POST /hotel/caja/turnos/{id}/retiros` | Retiro de efectivo para depósito en el banco: `{monto_clp, comprobante, banco?, nota?}`. No puede superar el efectivo esperado (409). Movimiento inmutable. |
| `POST /hotel/caja/turnos/{id}/cierre` | Cierre con arqueo `{arqueo: {denominación: cantidad}, declarado?: {debito, credito, transferencia}, justificacion?, deposito?: {monto_clp, comprobante, banco?}}`. Cuadratura por medio; cualquier diferencia exige justificación (422). Solo quien abrió o la administración. Lo contado menos el depósito pasa al turno siguiente. |
| `GET /hotel/caja/movimientos?desde&hasta&medio` | Diario de caja (cobros, reversos y retiros) por fecha contable. |
| `POST /hotel/reservas/{id}/pagos/{pago_id}/reverso` | Solo administración del hotel: `{motivo}` (10+ caracteres). Registra un pago `reverso` por el mismo monto y medio en el día abierto; el original no se edita (la base lo impide). 409 si ya fue reversado. |
| `GET /hotel/caja/conciliacion?fecha` | Conciliación diaria: habitaciones ocupadas contra cargos, pagado, anticipos y saldo; ocupación, ADR y RevPAR; cobros por medio, depósitos, anticipos, documentos, turnos y alertas. Un día cerrado devuelve la conciliación congelada. Roles caja o administración. |
| `GET /hotel/caja/cierres?desde&hasta` | Cierres diarios del rango y fecha contable actual. |
| `POST /hotel/caja/cierres` | Cierre diario `{fecha, nota?, confirmar_alertas}`: exige turnos cerrados; con alertas exige confirmarlas (409). Congela la conciliación; los movimientos nuevos caen en el siguiente día abierto. |
| `POST /hotel/caja/cierres/{fecha}/reapertura` | Solo administración del hotel: `{motivo}` (10+ caracteres), auditado. |
| `GET /hotel/estadias/busqueda?q&alcance` | (2026-11-19) Busca reservas por nombre del huésped (sin distinguir tildes), número de habitación, código de reserva o documento. `alcance`: `salida` (en estadía; recepción/administración), `llegada` (confirmadas; recepción/administración), `pago` (confirmadas o en estadía; también caja). Sin texto devuelve la lista del día. Máx. 12 resultados con `hay_mas`, saldo de la cuenta incluido. Caja solo encuentra por documento completo y nunca lo recibe. |
| `GET /publico/disponibilidad?inicio&fin&personas` | Sin sesión: la oferta vigente con la misma regla de cupo y tarifa que `/hotel/oferta` (ver «Canal público»). (#346, 2026-11-18) Sin `habitacion_id`: el visitante ve una línea por unidad libre con su tipo y precio, nunca el número; el hotel asigna la unidad al convertir. |
| `POST /publico/solicitudes` | Sin sesión: persiste una solicitud `recibida` por **tipo** de habitación (#346: cuerpo con `tipo`; `habitacion_id` solo por compatibilidad, se traduce a su tipo; la respuesta nunca trae número) con `Idempotency-Key` propia; sin cupo o sin tarifa → 409 y nada se persiste. Ver «Canal público». |
| `GET /hotel/solicitudes?estado=` | Bandeja de solicitudes públicas (recibida/convertida/rechazada). Roles recepción o administrador. |
| `POST /hotel/solicitudes/{id}/conversion` | Convierte la solicitud en reserva por `reservas.crear_reserva` (misma carrera por la última unidad) y propaga `personas` de la solicitud (#298). Marca `convertida` con `reserva_id` y auditoría. Roles recepción o administrador; sin cupo o capacidad excedida → 409 y queda `recibida`. |
| `POST /hotel/solicitudes/{id}/rechazo` | Marca la solicitud `rechazada` con motivo. Roles recepción o administrador; `recibida` → 409. |
| `POST /publico/leads` | Sin sesión: persiste un lead `nuevo` con `Idempotency-Key` propia (origen landing, tabla y espacio de claves propios). Ver «Contacto y leads de la landing». |
| `GET /publico/referencia?token=` | Sin sesión: con la referencia opaca del lead devuelve solo `{nombre, correo}` para precargar `/reservar` (nunca teléfono ni mensaje). La referencia caduca a las 72 h (`LEAD_REFERENCIA_HORAS`, 1 h a 30 días) y se revoca al cerrar el lead (SOC-016, 2026-11-16); vencida, revocada o inexistente → 404; formato inválido o parámetros extra → 422; freno por IP → 429. |
| `GET /hotel/metricas-publicas` | Solo `administrador`: contadores en memoria de esta instancia del canal público por ruta y clase de resultado (`ok`, `entrada_rechazada`, `freno`, `recaptcha_rechazado`, `no_encontrado`, `conflicto`, `no_disponible`, `error`). Sin datos personales ni tokens; la vista agregada son los logs JSON `evento=publico` (2026-11-16). |
| `GET /hotel/leads?estado=` | Bandeja de leads (nuevo/contactado/cerrado) con datos de contacto y mensaje. (#354, 2026-11-18) Por defecto solo la ventana vigente (`LEADS_VENTANA_NUEVO_DIAS`, 30 por defecto) con `corte` visible; `desde`, `hasta`, `contacto_id` y `todos` la cambian. Cada lead trae `contacto_id`, `leads_del_contacto` y `situacion` (`nuevo` dentro de la ventana, `sin_gestionar_antiguo` fuera); `sin_gestionar_antiguos` cuenta los que quedaron fuera. Roles recepción o administrador; solo la empresa de la sesión. |
| `GET /hotel/leads/contactos` | (#354) Contactos deduplicados (correo en minúsculas o teléfono normalizado) con cantidad de leads y último contacto: base para fidelización, un envío por persona y nunca por lead. Roles recepción o administrador. (2026-11-19) `?desde&hasta` (fecha de Chile, inclusive) acota la exportación a contactos con algún lead en ese rango. |
| `POST /hotel/leads/{id}/estado` | Avanza el lead (`contactado`/`cerrado` con nota) con auditoría; transición inválida → 409, ajeno → 403. Roles recepción o administrador. |
| `PUT /hotel/leads/{id}` | (2026-11-20) Corrige los datos del lead en cualquier estado (también cerrado): `{nombre, correo, telefono, huespedes?, check_in?, check_out?, mensaje?, nota?}`. No cambia estado ni gestión. La llegada pasada solo se rechaza si la edición toca las fechas. Si cambian correo o teléfono, el lead pasa a la ficha de contacto que corresponda (#354). Auditoría `lead_edicion` con los nombres de campo. Ajeno o inexistente → 403; datos inválidos → 422. Roles recepción o administrador. |
| `GET /hotel/leads/{id}/historial` | (2026-11-20) Historial auditable del lead desde `auditoria` (`lead_edicion`, `lead_gestion`, `lead_vinculo`): actor, acción, campos modificados o transición y marca de tiempo, nunca valores personales. Ajeno o inexistente → 403. Roles recepción o administrador. |
| `PUT /hotel/leads/{id}/vinculo` | (2026-11-20) Vincula (o desvincula con `null`) el lead con `{cliente_id?, solicitud_id?}` verificando existencia y pertenencia a la empresa. Auditoría `lead_vinculo` solo con nombres de campo. Ajeno o inexistente → 403; vínculo inválido → 422. Roles recepción o administrador. |
| `PUT /hotel/solicitudes/{id}` | (2026-11-20) Corrige `{huesped_nombre, huesped_contacto, personas}` de la solicitud. Nombre y contacto en cualquier estado; las personas solo mientras `recibida` (otro estado con personas distintas → 409). Tipo, unidad y fechas no se editan. Auditoría `solicitud_edicion`. Roles recepción o administrador. |
| `PUT /hotel/reservas/{id}/huesped` | (2026-11-20) Corrige `{nombre, documento?, documento_tipo?}` del huésped en cualquier estado de la reserva. El documento exige tipo (`rut`/`pasaporte`), se normaliza como en la entrada y no se borra (sin documento = no cambia). Un RUT de otro cliente registrado con otro nombre → 409. No toca fechas, unidad ni cuenta. Auditoría `reserva_edicion_huesped` sin el documento. Recepción o administración del hotel. |
| `GET /hotel/clientes?q` | (2026-11-20) Clientes por nombre, RUT, correo o teléfono (máx. 200, `truncado`). Recepción, caja o administración del hotel. |
| `POST /hotel/clientes` | (2026-11-20) Alta manual de cliente `{rut, nombre, tipo?, giro?, direccion?, comuna?, correo?, telefono?, activo?}` con `Idempotency-Key`. Mismas validaciones de RUT, correo y teléfono; RUT duplicado → 409. Auditoría `cliente_alta` sin valores personales. Recepción, caja o administración del hotel. |
| `PUT /hotel/clientes/{id}` | (2026-11-20) Corrige la ficha `{rut, nombre, tipo, giro?, direccion?, comuna?, correo?, telefono?, activo}`. El RUT se valida y no puede ser de otro cliente (409); las imputaciones y movimientos asentados apuntan por id y no cambian. Nada se borra: se desactiva. Auditoría `cliente_edicion`. Recepción, caja o administración del hotel. |
| `GET /hotel/huespedes/busqueda` | Busca huéspedes registrados de la empresa por documento (solo recepción y administración del hotel). |
| `GET /hotel/reservas/{id}/huespedes` | Lista los huéspedes vinculados a la reserva y el estado de ocupación (`adultos`, `ninos`, `faltantes`). |
| `PUT /hotel/reservas/{id}/ocupacion` | Actualiza ocupación real (`adultos`, `ninos`) validando capacidad y asentando ajuste append-only si aplica. |
| `POST /hotel/reservas/{id}/huespedes` | Registra o vincula un huésped a la reserva (`titular` o `acompanante`). |
| `PUT /hotel/reservas/{id}/huespedes/{huesped_id}` | Edita datos de un huésped vinculado a la reserva (sincroniza el titular). |
| `DELETE /hotel/reservas/{id}/huespedes/{huesped_id}` | Desvincula un acompañante de la reserva (no permite quitar al titular). |
| `POST /hotel/agente/consultas` | Registra una consulta para el agente (N0): 201 con borrador `pendiente_aprobacion`/`escalado`; sin adaptador → 503 y la consulta queda `pendiente`. Roles recepción o administrador. Ver «Agente de reservas». |
| `GET /hotel/agente/consultas?estado=` | Bandeja del agente por estado, sin texto completo. Roles recepción o administrador. |
| `GET /hotel/agente/consultas/{id}` | Consulta con borradores y traza resumida; ajena → 403. Roles recepción o administrador. |
| `POST /hotel/agente/borradores/{id}/aprobacion` | Aprueba (o edita) el borrador; oferta vencida con cifra distinta → 409 «la oferta cambió» con borrador nuevo. Roles recepción o administrador. |
| `POST /hotel/agente/borradores/{id}/descarte` | Descarta el borrador con motivo; ya resuelto → 409. Roles recepción o administrador. |
| `GET /hotel/agente/politica` | Política de autonomía de la empresa. Roles recepción o administrador. |
| `PUT /hotel/agente/politica` | Cambia la política; solo administrador (recepción → 403); subir de nivel sin `evaluacion_ref` → 409 (SC-003). |
| `GET /mensajeria/whatsapp/webhook` | Verificación del puerto. Sin las tres variables → 503 «no configurado». Con el puerto, el token correcto devuelve `hub.challenge` en texto plano; otro token → 403. Sin sesión. |
| `POST /mensajeria/whatsapp/webhook` | Entrada firmada (`X-Hub-Signature-256`). Firma inválida o `phone_number_id` distinto del autorizado → 403 y nada se persiste. Texto válido → consulta `whatsapp`, id externo guardado, 200. El mismo id no crea otra consulta. Sin modelo, la consulta queda `pendiente` y la respuesta sigue en 200. Por remitente aplica el freno del canal público (429). |
| `GET /publico/politicas` | Sin sesión: políticas públicas del hotel (horarios de llegada/salida, cancelación, depósito, desayuno, estacionamiento, medios de pago, FAQ públicas y datos de llegada que el huésped debe conocer). Los bloques no ratificados van con `confirmacion: pendiente_confirmar` o `no_definido`; no se afirman como hechos. Freno por IP → 429. Ver «Políticas del hotel». |
| `GET /hotel/politicas` | Políticas completas (incluye registro de llegada/salida y FAQ internas), lista de pendientes y `puede_editar`. Cualquier rol de la sesión. |
| `PUT /hotel/politicas` | Reemplaza el cuerpo de las políticas (`{cuerpo}`). Solo administración del hotel. Validación 400; auditado; `Idempotency-Key`. |
| `POST /hotel/politicas/simulacion` | Calculadora: fechas, horas de llegada/salida y recargos opcionales → total con desglose neto/IVA. Con `habitacion_id` usa el precio real; si no, un `precio_noche_clp` de ejemplo. Cualquier rol de la sesión. |
| `GET /roles` | (#323) Catálogo transversal de roles desde el core filtrado por los módulos activos de la empresa. Cualquier sesión activa. |
| `POST /hotel/contabilidad/movimientos-directos` | Registra un ingreso o egreso directo sin habitación ni reserva (funciona con caja abierta o cerrada, devengando de inmediato en contabilidad). Roles caja, recepción o administración del hotel; `Idempotency-Key`. |
| `POST /hotel/contabilidad/movimientos-directos/{movimiento_id}/cobrar` | Cobra un movimiento directo pendiente (efectivo con turno abierto o tarjeta/transferencia). Roles caja o administración del hotel; `Idempotency-Key`. |
| `POST /hotel/contabilidad/movimientos-directos/{movimiento_id}/reverso` | Asienta el reverso inmutable de un movimiento directo (y devuelve stock si corresponde). Solo administración del hotel; `Idempotency-Key`. |
| `GET /core/stock/bodegas` | (#358) Lista bodegas compartidas del core (`bodega_principal`, `minibar`, `cafeteria`). Roles de lectura de productos. |
| `GET /hotel/productos/bodegas` | Alias hotel de `GET /core/stock/bodegas`. |
| `GET /core/stock/reposicion` | (#358) Reporte transversal de stock por bodega, alertas de bajo mínimo/sin stock y sugerido a reponer. Solo administración del hotel. |
| `GET /hotel/productos/reposicion` | Alias hotel de `GET /core/stock/reposicion`. |
| `POST /core/stock/transferencias` | (#358) Transfiere stock entre bodegas del core sin alterar el total. Solo administración del hotel; `Idempotency-Key`. |
| `POST /hotel/productos/{producto_id}/transferencia` | Alias hotel de transferencia entre bodegas para un producto específico. Solo administración del hotel; `Idempotency-Key`. |
| `POST /hotel/reservas/{reserva_id}/devolucion` | (#91 / Q-HOT-04) Registra la devolución formal (efectivo con turno abierto o transferencia) de saldo a favor del huésped (`saldo_clp < 0`) hasta dejar la cuenta en $0. Solo administración del hotel; `Idempotency-Key`. |
| `POST /hotel/productos/documentos/{documento_id}/aplicar-nota-credito` | (#402 / `PUR-004`) Vincula una nota de crédito de proveedor (`nota_credito`, DTE 61) a su factura cargada (`factura_id`), rebajando stock en bodegas (`0055`, movimiento `reverso`) y saldo en cuenta por pagar (`cxp_movimientos` append-only e idempotente). Solo administración del hotel; `Idempotency-Key`. |
| `GET /hotel/productos/cuentas-por-pagar?estado&emisor_rut` | (#402 / `PUR-004`) Lista cuentas por pagar de facturas de proveedor con notas de crédito, pagos, saldo pendiente y movimientos append-only. Solo administración del hotel. |
| `POST /hotel/productos/cuentas-por-pagar/{cxp_id}/pagos` | (#402 / `PUR-004`) Registra abono o pago total a proveedor sobre una cuenta por pagar de forma append-only e idempotente (sin superar el saldo). Solo administración del hotel; `Idempotency-Key`. |
| `GET /hotel/contabilidad/comisiones-medios` | (Contable 2.6 / `#396`) Comisiones (%) y días hábiles de abono configurados por medio de pago. Roles caja o administración del hotel. |
| `PUT /hotel/contabilidad/comisiones-medios` | (Contable 2.6 / `#396`) Configura comisiones, IVA sobre comisión, días hábiles de abono y mapeo de columnas por medio/proveedor (sin hardcoding). Solo administración del hotel; `Idempotency-Key`. |
| `POST /hotel/contabilidad/cartolas/vista-previa` | (Contable 2.6 / `#396` / `FIN-003`) Vista previa de cartola CSV con mapeo de columnas, hash anti-duplicado y filas rechazadas sin escribir en BD. Roles caja o administración del hotel. |
| `POST /hotel/contabilidad/cartolas` | (Contable 2.6 / `#396` / `FIN-003`) Importa cartola bancaria (idempotente por SHA-256) y cruza automáticamente retiros, transferencias y liquidaciones de tarjetas según comisiones y desfase. Roles caja o administración del hotel; `Idempotency-Key`. |
| `GET /hotel/contabilidad/cartolas?periodo` | (Contable 2.6 / `#396` / `FIN-006`) Cartolas importadas, movimientos (`conciliado`, `parcial`, `pendiente`), bandeja de pendientes y ventas «en tránsito» hacia el mes siguiente. Roles caja o administración del hotel. |
| `POST /hotel/contabilidad/conciliacion-bancaria/emparejar` | (Contable 2.6 / `#396` / `FIN-004`) Conciliación manual muchos-a-muchos append-only con justificación obligatoria (10+ caracteres), sin superar importes disponibles. Roles caja o administración del hotel; `Idempotency-Key`. |
| `GET /hotel/contabilidad/tributario?anio&mes` | (Contable 2.7 / `#397` / `TAX-002`) Resumen tributario mensual (borrador F29): boletas, facturas y notas de crédito con neto, IVA vigente y total, crédito fiscal de compras y ventas con tarjeta en tránsito. Sin envío al SII. Roles caja o administración del hotel. |
| `GET /hotel/contabilidad/tributario/exportar.csv?anio&mes` | (Contable 2.7 / `#397`) Exportación CSV UTF-8 del borrador tributario F29 del mes calendario. Roles caja o administración del hotel. |
| `POST /hotel/grupos` | (PR B / `RES-007`) Crea un grupo bajo un titular con 1 o más habitaciones (`reservas_grupo` + reservas individuales 1:1) en una transacción atómica (sin cupo/tarifa/capacidad en cualquier habitación → 409 con rollback total). Soporta `titular_aloja` por habitación. Recepción o administración del hotel; `Idempotency-Key`. |
| `GET /hotel/grupos/{grupo_id}` | (PR B / `RES-007`) Cabecera del grupo, lista de habitaciones con estado de huéspedes y cuentas individuales, más resumen consolidado sin duplicación. Documento solo para `ROLES_DOCUMENTO`. Ajeno o inexistente → 403. |
| `POST /hotel/grupos/{grupo_id}/reservas` | (PR B / `RES-007`) Agrega una nueva habitación al grupo (o vincula una reserva existente de la empresa) en transacción atómica. Recepción o administración del hotel; `Idempotency-Key`. |
| `POST /hotel/grupos/{grupo_id}/entrada` | (PR B / `RES-007`) Llegada en lote atómica de las habitaciones confirmadas del grupo, exigiendo huéspedes completos en cada habitación; si falla cualquier habitación → 409 con rollback total. Recepción o administración del hotel; `Idempotency-Key`. |
| `GET /hotel/contabilidad/cuadratura-diaria?fecha` | (Contable 2.3 / `#393`) Cuadratura diaria de ocupación física, noches devengadas, imputaciones, abonos (anticipos) y cruce libro vs caja con lista de diferencias. Roles caja o administración del hotel. |
| `GET /hotel/contabilidad/cierre-mensual?anio&mes` | (Contable 2.4 / `#394`) Cierre mensual (congelado si está cerrado; en vivo si está abierto) con matriz habitaciones × días (equivalente a `Ocupación 2026`), totales y alertas. Roles caja o administración del hotel. |
| `GET /hotel/contabilidad/cierre-mensual/exportar.csv?anio&mes` | (Contable 2.4 / `#394`) Descarga CSV UTF-8 (compatible con Excel) de la matriz habitaciones × días del mes. Roles caja o administración del hotel. |
| `POST /hotel/contabilidad/cierre-mensual` | (Contable 2.4 / `#394`) Congela el cierre mensual `{anio, mes, nota?, confirmar_alertas}` en `cierres_mensuales`. Roles caja o administración del hotel; `Idempotency-Key`. |
| `POST /hotel/contabilidad/cierre-mensual/{anio}/{mes}/reapertura` | (Contable 2.4 / `#394`) Reabre un mes cerrado con `{motivo}` (mín. 10 caracteres), auditado. Solo administración del hotel; `Idempotency-Key`. |
| `GET /hotel/contabilidad/indicadores-ejecutivos?desde&hasta&tipo` | (Contable 2.5 / `#395` / `KPI-002`) Indicadores ejecutivos reales calculados en el servidor (ocupación, ADR, RevPAR con IVA y neto; `null` = sin muestra, nunca cero inventado). Solo administración del hotel. |
| `GET /hotel/comunicados?archivados` | (#418) Comunicados dirigidos al rol de la sesión (o a todos), con `leido` por usuario y `sin_leer`. `archivados` solo lo respeta la administración. Todos los roles, incluido aseo. |
| `POST /hotel/comunicados` | (#418) `{titulo, cuerpo, roles[]}` (roles vacío = todo el personal). Solo administración del hotel; `Idempotency-Key`. |
| `POST /hotel/comunicados/{id}/lectura` | (#418) Confirma la lectura del usuario de la sesión; una sola vez (solo se agrega, repetir no cambia nada). Comunicado ajeno al rol → 404. `Idempotency-Key`. |
| `POST /hotel/comunicados/{id}/archivo` | (#418) Archiva el comunicado (deja de mostrarse). Solo administración del hotel; `Idempotency-Key`. |
| `GET /hotel/comunicados/{id}/lecturas` | (#418) Quién leyó (con hora) y quién falta entre los destinatarios. Solo administración del hotel. |
| `GET /hotel/clientes/{cliente_id}/credito` | (Contable 2.2 / `#392`) Política de crédito vigente del cliente/empresa, cupo, plazo, deuda abierta, cupo disponible y alertas de límite o vencimiento. Roles recepción, caja o administración del hotel. |
| `PUT /hotel/clientes/{cliente_id}/credito` | (Contable 2.2 / `#392`) Configura política de crédito (`pago_al_registrarse`, `credito_autorizado`, `garantia_salida`), límite, plazo en días y marca/últimos 4 dígitos (PCI: jamás número completo ni CVV). Solo administración del hotel; `Idempotency-Key`. |
| `POST /hotel/reservas/{reserva_id}/salida-credito` | (Contable 2.2 / `#392` / `REC-003`) Registra Salida física dejando cuenta por cobrar trazable si el cliente tiene política de crédito/garantía habilitada; exceso de cupo → 409 salvo confirmación de administración. Recepción o administración del hotel; `Idempotency-Key`. |
| `GET /hotel/contabilidad/cuentas-por-cobrar?estado&cliente_id` | (Contable 2.2 / `#392` / `FIN-002`) Listado de cuentas por cobrar agrupado por tramos de antigüedad (`0-30`, `31-60`, `61-90`, `mas_90` días) con totales y alertas de vencimiento. Roles caja o administración del hotel. |
| `POST /hotel/contabilidad/cuentas-por-cobrar/{cxc_id}/abonos` | (Contable 2.2 / `#392`) Registra abono append-only e idempotente sobre una cuenta por cobrar (sin superar saldo pendiente). Roles caja o administración del hotel; `Idempotency-Key`. |
| `GET /hotel/turnos?desde&hasta&area&solo_mios` | (#418) Rol de turnos por día (por defecto 7 días desde hoy, máximo 31) con área, persona y horario. Todos los roles, incluido aseo. |
| `POST /hotel/turnos` | (#418) `{fecha, area, usuario, hora_inicio, hora_fin, nota?}`; la persona debe existir y no repetir el mismo bloque el mismo día (409). Solo administración del hotel; `Idempotency-Key`. |
| `POST /hotel/turnos/{id}/cambio` | (#418) `{propuesto, motivo}`: quien tiene el turno (o la administración) pide que lo cubra otra persona; un solo cambio pendiente por turno y no sobre turnos pasados (409). `Idempotency-Key`. |
| `GET /hotel/turnos/cambios?estado` | (#418) Solicitudes de cambio con su turno. Solo administración del hotel. |
| `POST /hotel/turnos/cambios/{id}/resolucion` | (#418) `{aprobar}`: al aprobar, el turno pasa a la persona propuesta; la solicitud queda como historia y no se resuelve dos veces (409). Solo administración del hotel; `Idempotency-Key`. |
| `GET /hotel/biblioteca?categoria&archivados` | (#418) Documentos (manuales, instructivos, políticas) dirigidos al rol de la sesión o a todos. `archivados` solo lo respeta la administración. Todos los roles, incluido aseo. |
| `POST /hotel/biblioteca` | (#418) `{titulo, categoria, contenido?, enlace? (https), roles[]}`; exige contenido o enlace. Solo administración del hotel; `Idempotency-Key`. |
| `POST /hotel/biblioteca/{id}/archivo` | (#418) Archiva el documento. Solo administración del hotel; `Idempotency-Key`. |
| `POST /hotel/sugerencias` | (#418) `{texto}`: buzón de sugerencias del personal; queda con su autor. Todos los roles; `Idempotency-Key`. |
| `GET /hotel/sugerencias?estado` | (#418) Sugerencias recibidas. Solo administración del hotel. |
| `POST /hotel/sugerencias/{id}/atencion` | (#418) `{respuesta?}`: marca la sugerencia como atendida; no se atiende dos veces (409). Solo administración del hotel; `Idempotency-Key`. |
| `GET /hotel/activos?habitacion_id&estado` | (#418) Inventario de activos por habitación o área común. Recepción, aseo y administración del hotel. |
| `POST /hotel/activos` | (#418) `{habitacion_id? o area, nombre, categoria, notas?}`; la habitación debe existir. Recepción o administración del hotel; `Idempotency-Key`. |
| `POST /hotel/activos/{id}/actualizacion` | (#418) `{estado?: operativo\|en_reparacion\|de_baja, notas?}`; al dar de baja se desactivan sus planes de mantención. Recepción o administración del hotel; `Idempotency-Key`. |
| `POST /hotel/activos/{id}/plan` | (#418) `{descripcion, cada_dias, proxima?}`: mantención preventiva periódica (por defecto la primera es hoy + `cada_dias`); no sobre activos de baja (409). Recepción o administración del hotel; `Idempotency-Key`. |
| `GET /hotel/mantenciones?dentro_de_dias` | (#418) Mantenciones vencidas y las que vencen en los próximos N días (14 por defecto), con `vencida`. Recepción, aseo y administración del hotel. |
| `POST /hotel/mantenciones/{plan_id}/realizada` | (#418) `{fecha?, nota?}`: registra la mantención hecha en el historial (solo se agrega) y corre la próxima a `fecha + cada_dias`. Fecha futura o ya registrada → 409. Recepción, aseo o administración; `Idempotency-Key`. |

## Criterio de aceptación

El front de Vercel puede implementarse leyendo solo este contrato. Las
operaciones de la tabla pasan contra PostgreSQL con las reglas de sesión,
idempotencia y errores de arriba; nada fuera de la tabla existe.
