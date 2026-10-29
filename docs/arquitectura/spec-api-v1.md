# Especificación API V1 — contrato entre el front y el backend

**Estado:** REQUISITO PROPUESTO, fechado 2026-10-28. Es el contrato que el
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

## Errores y puertos

- Puerto externo sin adaptador (pasarela, DTE, PMS, canal, mensajería) →
  **503** y el estado queda **pendiente**; nada se marca como cobrado,
  emitido ni enviado. El cuerpo declara qué puerto falta.

## Operaciones de esta versión (16)

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
| `PUT /hotel/habitaciones/{id}` | Alta o cambio de habitación: tipo, capacidad. Solo administrador. |
| `PUT /hotel/tarifas` | Tarifa por fecha y unidad. No cambia el precio de una reserva ya aceptada. |
| `GET /hotel/oferta?inicio&fin&personas` | Solo lo disponible, con tarifa vigente y vencimiento de la oferta. |
| `POST /hotel/reservas` | Confirma una sola vez. La última unidad en carrera queda en una sola reserva: la confirmación es transaccional y la base rechaza el solape en (unidad, fechas). |
| `POST /hotel/reservas/{id}/pagos` | El núcleo registra el efecto. Si el núcleo rechaza, no hay pago. Cuerpo: `{monto_clp, clave, modo}`. `modo="manual"` (DECISIÓN, 2026-10-28): caja en efectivo o transferencia que recepción registra; solo roles recepción, caja o administrador; no consulta el banco y no queda conciliado. `modo="pasarela"` sin adaptador → 503 y nada marcado como cobrado. |
| `POST /hotel/reservas/{id}/entrada` | Check-in si la habitación está lista (mantenimiento abierto bloquea). |
| `POST /hotel/reservas/{id}/salida` | Liquida la cuenta y devuelve la liquidación. |
| `GET /hotel/caja?fecha=YYYY-MM-DD` | Pagos del día ligados a reserva. Sin movimiento bancario en esta versión. |

## Criterio de aceptación

El front de Vercel puede implementarse leyendo solo este contrato. Las
operaciones de la tabla pasan contra PostgreSQL con las reglas de sesión,
idempotencia y errores de arriba; nada fuera de la tabla existe.
