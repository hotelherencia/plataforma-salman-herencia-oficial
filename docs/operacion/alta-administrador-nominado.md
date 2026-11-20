# Procedimiento operativo: alta de cuenta administradora nominada (`#338` y `#352`)

- **Fecha:** 2026-11-20
- **Aplica a:** `V1-ISSUE-43` (`#338`) y `V1-ISSUE-51` (`#352`, único ítem pendiente de la épica `#368`).
- **Regla de privacidad y seguridad (Ley 21.719 / `AGENTS.md`):** este procedimiento **no** crea cuentas reales automáticamente ni registra correos personales, contraseñas o secretos TOTP en el repositorio ni en issues públicos. La creación real solo se ejecuta con autorización explícita del propietario.

---

## 1. Estado del código (verificado en `main`)

No falta código ni rol nuevo: todo el soporte backend y front ya está desplegado en `main` (PR `#372`, `#379` y catálogo de roles `#323`):

- **Alta de usuario con correo de Google opcional:** `POST /usuarios` (`servicio/rutas/acceso.py`), requiere rol `administrador` o `admin_plataforma` y cabecera `Idempotency-Key`.
- **Vinculación/cambio de correo Google en usuario existente:** `POST /usuarios/{usuario_id}/email`.
- **Pantalla web:** `/hotel/usuarios` (`front/app/hotel/usuarios/page.js`) — incluye formulario «Alta de usuario» con campo «Correo de Google (opcional)» y selector de rol (`administrador` = acceso total; `admin_hotel` = gestión del hotel sin gestión de usuarios).
- **Primer ingreso con Google y 2FA:** `GET /auth/google` → `/auth/google/callback` valida el correo contra `usuarios.email` (cuentas activas), permite el primer ingreso del administrador sin TOTP dejando traza `mfa_excepcion_enrolamiento` y muestra aviso persistente en `/cuenta` para activar TOTP (`POST /cuenta/2fa` + `POST /cuenta/2fa/activar`). Si el intento falla con otra cuenta Google, `#351` redirige a `/login` con opción de reintentar.
- **Auditoría sin PII:** `seguridad.auditar` registra `accion='usuario'`, `resultado='creado con Google'` (jamás guarda el correo en `auditoria` ni en `GET /usuarios`, que solo devuelve `google_vinculado: true`).

---

## 2. Pasos de ejecución (solo tras autorización explícita del propietario)

### Vía recomendada: pantalla `/hotel/usuarios` en producción (`https://plataforma.hotelherencia.cl/hotel/usuarios`)

1. Iniciar sesión en `https://plataforma.hotelherencia.cl/login` con la cuenta administradora inicial (`admin`).
2. Ir a **Usuarios** (`/hotel/usuarios`) → sección **Alta de usuario**.
3. Completar:
   - **Nombre:** nombre nominado acordado con el propietario (distinto de `admin`, p. ej. sin espacios ni tildes).
   - **Rol:** `administrador` (cubre `#338` y `#352`; conserva administración de hotel y plataforma sin crear un rol nuevo).
   - **Clave:** clave temporal robusta (≥ 12 caracteres, entregada por canal privado fuera del repo/chat público).
   - **Correo de Google:** correo Google entregado por el propietario por canal privado (vincula `usuarios.email` en el mismo acto).
4. Presionar **Crear usuario** y confirmar en la tabla «Usuarios de la empresa» que aparece con `activo: sí` y Google vinculado.

### Vía alternativa: API (si se ejecuta desde consola autorizada)

```bash
# 1) Abrir sesión como admin (guardar cookie en archivo temporal, nunca en el repo)
curl -fsS -c /tmp/sid.cookie -H "Content-Type: application/json" \
  -d '{"usuario":"<ADMIN_USUARIO>","clave":"<ADMIN_CLAVE>"}' \
  https://servicio-production-a2d7.up.railway.app/sesion

# 2) Crear cuenta nominada con Idempotency-Key única
curl -fsS -b /tmp/sid.cookie \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: alta-admin-nominado-2026-11-20" \
  -d '{"nombre":"<NOMBRE_NOMINADO>","rol":"administrador","clave":"<CLAVE_TEMPORAL>","email":"<CORREO_GOOGLE_PRIVADO>"}' \
  https://servicio-production-a2d7.up.railway.app/usuarios

# 3) Eliminar cookie temporal
rm -f /tmp/sid.cookie
```

---

## 3. Prueba de humo y cierre de `#338`, `#352` y `#368`

1. La persona nominada ingresa en `https://plataforma.hotelherencia.cl/login` usando **Continuar con Google** con su cuenta vinculada.
2. Verifica que llega al panel (`/hotel/panel`) y ve el aviso de enrolamiento de doble factor.
3. En `/cuenta`:
   - Cambia su clave temporal por una personal (requiere clave actual).
   - Activa el segundo factor TOTP escaneando el QR y validando el código de 6 dígitos (requerido por `#352`).
4. Verifica acceso operativo: `/hotel/habitaciones`, `/hotel/tipos`, `/hotel/reservas`, `/hotel/leads`, `/hotel/solicitudes`, `/hotel/caja` y `/hotel/usuarios`.
5. **Evidencia de cierre (sin PII ni secretos):**
   - Comentar en `#338` y `#352` únicamente el **nombre de usuario nominado** (no el correo personal, no la clave, no el TOTP) y la **fecha de alta + confirmación de prueba de humo**.
   - El acta con detalle operativo queda en el tablero/canal privado del propietario.
   - Cerrar `#338`, `#352` y, al quedar 23/23 ítems completados, cerrar la épica `#368`.
