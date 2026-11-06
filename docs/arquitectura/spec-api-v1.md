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
  `totp_activado`. Migración: la columna nace desactivada, nadie queda fuera.
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
- `PUT /hotel/tarifas`: append-only; vigente en la noche *d* la de mayor
  `fecha_desde` con `fecha_desde ≤ d < fecha_hasta`, a igualdad la registrada
  más recientemente. Deja auditoría.
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
- Respuesta 201 `{lead: {id, estado, creado_en}}` sin datos de terceros ni
  identificadores internos ajenos.
- Gestión interna (recepción o administrador; 401 sin sesión, 403 con otro
  rol): `GET /hotel/leads?estado=` — bandeja por estado (`nuevo|contactado|
  cerrado`; sin filtro, todas) orden `creado_en` DESC, con los datos de
  contacto y el mensaje (la bandeja ES la agenda de seguimiento). Solo leads
  de la empresa de la sesión.
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
  `escalado` con motivo). Sin adaptador del modelo (D-AGT-02 pendiente) → 503
  `{"detail":"modelo no configurado","estado":"pendiente"}` con la consulta
  guardada; recepción la atiende como hoy. El texto se guarda **redactado**
  (NFR-A03: sin RUT, tarjetas, correos ni teléfonos). Misma clave y cuerpo →
  misma consulta sin una segunda llamada al modelo.
- `GET /hotel/agente/consultas?estado=` — lista por estado (`pendiente`,
  `procesada`, `escalada`) sin texto completo.
- `GET /hotel/agente/consultas/{id}` — consulta con sus borradores y traza
  resumida; ajena o inexistente → 403.
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
llega solo en N2 (D-PUB-01 y D-AGT-04). El modelo jamás envía `empresa_id`,
rol, tarifa ni total como argumento.

## Operaciones de esta versión (51)

| Operación | Efecto |
|---|---|
| `GET /salud` | Liveness de despliegue (Railway): 200 sin sesión ni datos. No toca la base de datos. |
| `GET /readiness` | Readiness (OPS-A02, 2026-11-05): consulta real a la base y estado de migraciones; 503 si no responde. Sin sesión. |
| `GET /sesion` | Con cookie `sid`: `{id, usuario, rol, empresa_id, totp_activo}`. Sin sesión → 401. |
| `GET /cuenta/2fa/qr` | Con sesión y alta en curso: devuelve el QR (SVG) del secreto **pendiente**. Sin pendiente → 400. El secreto activo nunca se expone (SEC-A02, 2026-11-05). |
| `POST /sesion` | Abre sesión de la empresa Herencia y fija la cookie `sid`. Con 2FA activo exige además `totp` (ver «Identidad y sesión»). |
| `DELETE /sesion` | Cierra la sesión (la fila de `sesiones` queda revocada). |
| `POST /cuenta/2fa` | Con sesión: genera el secreto TOTP **pendiente** (columna propia: el factor activo queda intacto hasta confirmar) y devuelve `{secreto, uri}`. Con 2FA ya activo exige `clave` en el cuerpo (reautenticación): sin clave o errada → 401 (SEC-A02). |
| `POST /cuenta/2fa/activar` | Con sesión: confirma el alta verificando el código contra el secreto pendiente; al confirmar, el pendiente pasa a ser el activo (reemplaza al previo). Código inválido o sin alta en curso → 400. |
| `DELETE /cuenta/2fa` | Con sesión: desactiva el segundo factor y borra ambos secretos. Exige `clave` en el cuerpo (reautenticación): sin clave o errada → 401 (SEC-A02). |
| `GET /auth/google/estado` | `{configurado: bool}`: true solo con `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` en el entorno. |
| `GET /auth/google` | 302 al consentimiento de Google (scope `openid email profile`, `state` de un solo uso, 10 min); sin configurar → 503 «no configurado». Fija la cookie HttpOnly `oauth_tx` (vida 10 min, path `/auth`) que ata el state al navegador (SEC-A05). |
| `GET /auth/google/callback` | Valida `state` **consumiéndolo en todo intento** y exigiendo que la cookie `oauth_tx` coincida con la que originó el login (state de otro navegador → 400, SEC-A05); intercambia `code`, verifica el ID token y abre la sesión con cookie `sid`, redirigiendo a `FRONT_URL`. Email sin vínculo → `/login?error=cuenta_sin_vinculo`; `access_denied` → `/login?error=acceso_denegado`. |
| `GET /usuarios` | Lista `id`, `nombre`, `rol`, `activo` de la empresa. Solo administrador. |
| `POST /usuarios` | Alta `{nombre, rol, clave}` con hash argon2id. Solo administrador. Nombre repetido → 409. |
| `POST /usuarios/{id}/clave` | Cambia la clave (reemplaza el hash). El propio usuario o un administrador. |
| `POST /usuarios/{id}/revocacion` | Revoca todas las sesiones del usuario. Solo administrador, sobre otro usuario. |
| `POST /usuarios/{id}/baja` | `activo=false` y revoca sesiones. Solo administrador, sobre otro usuario; no al último administrador activo (409). |
| `PUT /hotel/habitaciones/{id}` | Alta o cambio de habitación: tipo, capacidad (con `If-None-Match: *` solo alta). Devuelve `creada` y `cambios`; auditado. Solo administrador. |
| `PUT /hotel/tarifas` | Tarifa por rango y unidad (append-only; regla de vigencia arriba). No cambia el precio de una reserva ya aceptada. Auditado. |
| `GET /hotel/oferta?inicio&fin&personas` | Solo lo disponible, con tarifa vigente **en cada noche** de `[inicio, fin)` (spec-hotel-operacion-v1 §2.8, 2026-11-03) y vencimiento de la oferta. `total_clp` es la suma noche a noche con la tarifa vigente de cada noche (DECISIÓN 2026-11-06, #305); `tarifa_noche_clp` es la tarifa de la primera noche. Incluye unidades ocupadas o sucias si el rango no solapa; excluye mantenimiento, bloqueada y fuera de servicio. |
| `GET /hotel/habitaciones` | Inventario operativo de las unidades (REQUISITO PROPUESTO, 2026-11-03, orden del propietario tras la revisión E2E: la pantalla operaba a ciegas sin lectura del estado). Por unidad: `tipo`, `capacidad`, `estado_operativo`, `estado_preparacion`, `mantenimiento`, `tareas_pendientes`, `limpieza_pendiente` y última tarifa configurada como referencia. Solo lectura, cualquier rol de la sesión; las mutaciones conservan sus reglas de rol (limpieza: recepción o administrador; mantenimiento: solo administrador). |
| `GET /hotel/habitaciones/{id}` | Ficha de la habitación: datos, estados, historial de tarifas (con `vigente_hoy`), reservas en cualquier estado, tareas y —solo administrador— auditoría. Cualquier rol; inexistente → 403. |
| `POST /hotel/habitaciones/{id}/servicio` | Retira de operación (`fuera_de_servicio`, con motivo) o reincorpora. Solo administrador; reservas vigentes → 409. Baja lógica: nada se borra. |
| `GET /hotel/reservas?fecha=&estado=&texto=&desde=&hasta=&habitacion_id=` | Búsqueda de reservas de la empresa, filtros opcionales combinados con AND. Ver «Búsqueda de reservas» y la ampliación 2026-11-03. |
| `GET /hotel/reservas/{id}` | Detalle de una reserva con cargos, pagos, cuenta y liquidación. Cualquier rol; documento según rol; ajena o inexistente → 403. |
| `GET /hotel/ocupacion?desde&hasta` | Estado por habitación y noche (confirmada, en estadía, finalizada, disponible, sin tarifa, no vendible) y reservas canceladas del periodo; resumen nocturno con `disponibles`, `ocupadas_cupo` (cupo comprometido §5) y `no_vendibles` — renombrado 2026-11-04 (#320). Cualquier rol. |
| `GET /hotel/indicadores?desde&hasta&tipo` | Panel operativo: situación de hoy y ocupación del periodo con fórmula, unidad y fuente por indicador; serie diaria con `ocupadas_estadias` (estadías reales §4.3, renombrado 2026-11-04, #320); los financieros figuran como no disponibles. Cualquier rol. |
| `POST /hotel/reservas` | Confirma una sola vez. La última unidad en carrera queda en una sola reserva: la confirmación es transaccional y la base rechaza el solape en (unidad, fechas) para `confirmada` y `en_estadia`. Una unidad fuera del cupo (mantenimiento abierto, `bloqueada` o `fuera_de_servicio`) → 409 y nada cambia: misma regla que la oferta (spec-hotel-operacion-v1 §2.7). Alguna noche del rango sin tarifa vigente → 409 «sin tarifa vigente para `<hab>` la noche `<d>`» y nada cambia (§2.8). El precio se cobra noche a noche con la tarifa vigente de cada noche (DECISIÓN del propietario 2026-11-06, #305 opción b; reemplaza D-TAR-02); `tarifa_noche_aceptada_clp` queda como la tarifa de la primera noche, referencia de la penalidad de cancelación. |
| `POST /hotel/reservas/{id}/pagos` | El núcleo registra el efecto. Si el núcleo rechaza, no hay pago. Cuerpo: `{monto_clp, clave, modo}`. `modo="manual"` (DECISIÓN, 2026-10-28): caja en efectivo o transferencia que recepción registra; solo roles recepción, caja o administrador; no consulta el banco y no queda conciliado. `modo="pasarela"` sin adaptador → 503 y nada marcado como cobrado. |
| `POST /hotel/reservas/{id}/cargos` | Cargo de texto libre (minibar, consumo, extra). Roles recepción, caja o administrador; solo en `confirmada` o `en_estadia`; monto entero > 0 (si no, 422); otro estado → 409. Ver «Cargos de la estadía». |
| `POST /hotel/reservas/{id}/cancelacion` | Cancela desde `confirmada` con reversos y regla de 48 h (ver «Cancelación»). Roles recepción o administrador. |
| `POST /hotel/reservas/{id}/entrada` | Check-in si la habitación está lista (mantenimiento abierto, `bloqueada`/`fuera_de_servicio`, sucia u otra estadía solapada en la unidad bloquean → 409; `ocupada` no bloquea el turnover) y **la reserva ya comenzó** (`inicio ≤ hoy` del servidor; si no → 409 «aún no llega su día de entrada»). Exige el documento del huésped (D-ENT-01, DECISIÓN 2026-11-06): si la reserva no lo trae, el cuerpo `{"documento"}` lo registra; sin documento en ninguno → 409. Roles recepción o administrador (D-ROL-ENT, #304). Al pasar, la reserva queda `en_estadia` y la habitación `ocupada`. |
| `POST /hotel/reservas/{id}/salida` | Liquida la cuenta (saldo neto cargo-menos-reverso en cero) y devuelve la liquidación. Roles recepción o administrador (D-ROL-ENT, DECISIÓN 2026-11-06, #304). Si no queda otra estadía en curso en la unidad, la habitación queda `disponible` y `sucia`, con tarea de limpieza pendiente; si otra estadía sigue en curso (turnover no solapado), la unidad permanece `ocupada` y limpia, sin tarea nueva (V1-ISSUE-15, 2026-11-03). |
| `POST /hotel/habitaciones/{id}/limpieza` | Completa la limpieza pendiente y, si estaba sucia, deja la unidad `limpia`. Roles recepción o administrador. |
| `POST /hotel/habitaciones/{id}/mantenimiento` | Abre o cierra el mantenimiento de la unidad (con su tarea). Solo administrador. Con mantenimiento abierto la oferta no la incluye y la entrada responde 409. |
| `GET /hotel/caja?fecha=YYYY-MM-DD` | Pagos del día ligados a reserva. Sin movimiento bancario en esta versión. |
| `GET /publico/disponibilidad?inicio&fin&personas` | Sin sesión: la oferta vigente con la misma regla de cupo y tarifa que `/hotel/oferta` (ver «Canal público»). |
| `POST /publico/solicitudes` | Sin sesión: persiste una solicitud `recibida` con `Idempotency-Key` propia; sin cupo o sin tarifa → 409 y nada se persiste. Ver «Canal público». |
| `GET /hotel/solicitudes?estado=` | Bandeja de solicitudes públicas (recibida/convertida/rechazada). Roles recepción o administrador. |
| `POST /hotel/solicitudes/{id}/conversion` | Convierte la solicitud en reserva por `reservas.crear_reserva` (misma carrera por la última unidad); marca `convertida` con `reserva_id` y auditoría. Roles recepción o administrador; sin cupo → 409 y queda `recibida`. |
| `POST /hotel/solicitudes/{id}/rechazo` | Marca la solicitud `rechazada` con motivo. Roles recepción o administrador; `recibida` → 409. |
| `POST /publico/leads` | Sin sesión: persiste un lead `nuevo` con `Idempotency-Key` propia (origen landing, tabla y espacio de claves propios). Ver «Contacto y leads de la landing». |
| `GET /hotel/leads?estado=` | Bandeja de leads (nuevo/contactado/cerrado) con datos de contacto y mensaje. Roles recepción o administrador; solo la empresa de la sesión. |
| `POST /hotel/leads/{id}/estado` | Avanza el lead (`contactado`/`cerrado` con nota) con auditoría; transición inválida → 409, ajeno → 403. Roles recepción o administrador. |
| `POST /hotel/agente/consultas` | Registra una consulta para el agente (N0): 201 con borrador `pendiente_aprobacion`/`escalado`; sin adaptador → 503 y la consulta queda `pendiente`. Roles recepción o administrador. Ver «Agente de reservas». |
| `GET /hotel/agente/consultas?estado=` | Bandeja del agente por estado, sin texto completo. Roles recepción o administrador. |
| `GET /hotel/agente/consultas/{id}` | Consulta con borradores y traza resumida; ajena → 403. Roles recepción o administrador. |
| `POST /hotel/agente/borradores/{id}/aprobacion` | Aprueba (o edita) el borrador; oferta vencida con cifra distinta → 409 «la oferta cambió» con borrador nuevo. Roles recepción o administrador. |
| `POST /hotel/agente/borradores/{id}/descarte` | Descarta el borrador con motivo; ya resuelto → 409. Roles recepción o administrador. |
| `GET /hotel/agente/politica` | Política de autonomía de la empresa. Roles recepción o administrador. |
| `PUT /hotel/agente/politica` | Cambia la política; solo administrador (recepción → 403); subir de nivel sin `evaluacion_ref` → 409 (SC-003). |

## Criterio de aceptación

El front de Vercel puede implementarse leyendo solo este contrato. Las
operaciones de la tabla pasan contra PostgreSQL con las reglas de sesión,
idempotencia y errores de arriba; nada fuera de la tabla existe.
