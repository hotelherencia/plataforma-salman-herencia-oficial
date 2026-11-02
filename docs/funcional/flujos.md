# Flujos funcionales (2026-11-02)

HECHO DOCUMENTADO. Secuencias de lo que el usuario vive y qué decide el
backend en cada paso.

## 1. Acceso con usuario y clave

```mermaid
sequenceDiagram
    participant U as Usuario
    participant F as Front
    participant S as Servicio
    U->>F: usuario + clave (+ código TOTP si lo tiene activado)
    F->>S: POST /sesion
    S->>S: freno por usuario: 5 fallos en 5 min → 429
    S->>S: argon2id + TOTP si aplica
    alt credenciales OK
        S-->>F: 200 + cookie sid (12 h, HttpOnly, Secure)
        F-->>U: entra a las pantallas del hotel
    else fallo
        S-->>F: 401 «credenciales inválidas»
        F-->>U: mensaje legible (sin JSON crudo)
    end
```

- El freno cuenta por **usuario** (no por IP): los proxies de borde rotan la
  IP y el contador clásico por (ip, usuario) nunca se activaba (bug real
  corregido el 2026-11-02, commit `8780cc0`).
- Roles: `administrador`, `recepcion`, `caja`; varias operaciones exigen rol
  (pago manual, caja, limpieza, mantenimiento, gestión de usuarios).

## 2. Acceso con Google

```mermaid
sequenceDiagram
    U->>F: «Entrar con Google»
    F->>S: GET /auth/google/estado (¿configurado?)
    S-->>F: configurado:true
    F-->>U: redirige a Google (client_id + redirect_uri /api/auth/google/callback)
    U->>G: elige cuenta y consiente
    G-->>F: vuelve con ?code=…
    F->>S: GET /auth/google/callback?code=…
    S->>S: canjea code, busca usuario por email (ADMIN_EMAIL u otro dado de alta)
    alt email vinculado
        S-->>F: cookie sid → sesión normal
    else sin vínculo
        S-->>F: /login?error=cuenta_sin_vinculo
    end
```

## 3. Ciclo de venta (el corazón del hotel)

```mermaid
sequenceDiagram
    U->>F: Oferta: fechas + personas
    F->>S: GET /hotel/oferta?inicio&fin&personas
    S-->>F: unidades libres con tarifa vigente y política de cancelación
    U->>F: confirmar reserva (huésped, fechas)
    F->>S: POST /hotel/reservas + Idempotency-Key
    S->>S: transacción: última unidad con cupo (carrera por la última habitación)
    alt éxito
        S-->>F: 201 reserva «confirmada»
    else sin tarifa / sin cupo
        S-->>F: 409 «sin tarifa vigente…» / «sin cupo» (la clave se conserva)
    end
    U->>F: registrar pago (monto, modo)
    F->>S: POST /hotel/reservas/{id}/pagos
    U->>F: entrada: documento + hora de llegada
    F->>S: POST /hotel/reservas/{id}/entrada
    S->>S: exige habitación lista (limpia, sin mantenimiento abierto)
    U->>F: cargos en estadía (minibar, etc.)
    F->>S: POST /hotel/reservas/{id}/cargos
    U->>F: salida
    F->>S: POST /hotel/reservas/{id}/salida
    S-->>F: liquidación de la estadía
    U->>F: caja del día
    F->>S: GET /hotel/caja?fecha=…
```

- **Idempotencia**: la clave nace en el formulario, se muestra antes de enviar y
  sobrevive errores; tras un 2xx se renueva. Reintentar con la misma clave y
  distinto cuerpo → 409 (no se acuña en silencio).
- **Pagos**: pasarela externa existe solo como puerto — sin configurar responde
  503 «pasarela no configurada» (estado «pendiente»), nunca cobra de verdad.
- **Cancelación** (desde Estadía): dentro de plazo sin cargos; fuera de plazo
  carga la primera noche; el saldo a favor queda sin reembolso automático.

## 4. Housekeeping (habitaciones)

```mermaid
sequenceDiagram
    U->>F: marcar limpieza (HAB-…)
    F->>S: POST /hotel/habitaciones/{id}/limpieza
    S->>S: cierra tareas de limpieza pendientes; sucia → limpia
    S-->>F: habitacion_id + estado_preparacion + tareas_completadas
    U->>F: abrir mantenimiento
    F->>S: POST /hotel/habitaciones/{id}/mantenimiento
    S-->>F: habitación bloqueada para check-in hasta el cierre autorizado
```

## 5. Gestión de usuarios (solo administrador)

Alta (nombre, usuario único por empresa, rol, clave), cambio de clave,
revocación de sesiones y baja. El **último administrador activo no se puede
dar de baja** (409). La revocación echa a ese usuario de todas sus sesiones.

## Reglas duras transversales

- **API caída → error y nada confirmable**: si el front no alcanza al backend,
  muestra aviso y ninguna operación se confirma (spec-front-v1).
- **La verdad la tiene el backend**: el front jamás calcula negocio (totales,
  estados, vigencias); solo pinta lo que el servidor responde.
- **Auditoría**: cada mutación queda registrada (actor, acción, recurso,
  resultado) para trazabilidad operativa.
