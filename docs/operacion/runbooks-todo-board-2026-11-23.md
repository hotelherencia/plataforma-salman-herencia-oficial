# Runbooks y Checklists de Decisión — Ítems `Todo` del Board (2026-11-23)

Documento operativo sin secretos ni datos personales reales para destrabar los 8 ítems del tablero **Project Plataforma Hotel Herencia** que dependen de aprobación del propietario, configuración DNS/externa o verificación en producción (`#399`, `#403`, `#404`, `#408`, `#409`, `#410`, `#423`, `#424`).

---

## 1. `#399` — Políticas operativas del módulo contable (Decisión del propietario)

Todo el código de Contable Fase 2 (2.1 a 2.7) ya está en `main` con valores parametrizables en el mantenedor (nunca hardcodeados). El propietario debe confirmar los valores definitivos para cargarlos en **Configuración → Caja** y **Caja y pagos → Libro contable → Comisiones**:

| Parámetro | Valor sugerido / actual de ejemplo | Decisión definitiva del propietario | Dónde se carga |
|---|---|---|---|
| Comisión Débito (%) + IVA sobre comisión + días hábiles de abono | `1,0 %` · IVA sí · `1` día hábil | `____ %` · IVA `Sí/No` · `__` días | `PUT /hotel/contabilidad/comisiones-medios` |
| Comisión Crédito (%) + IVA sobre comisión + días hábiles de abono | `2,0 %` · IVA sí · `2` días hábiles | `____ %` · IVA `Sí/No` · `__` días | `PUT /hotel/contabilidad/comisiones-medios` |
| Fondo de caja (float inicial por turno) | `$50.000` | `$________` | Configuración → Caja |
| Tolerancia máxima de diferencia en arqueo de turno | `$1.000` | `$________` | Configuración → Caja |
| Banco / cuenta destino de retiros de efectivo (alias sin credenciales) | Cuenta corriente hotel | `____________` | Configuración → Caja |
| Documento tributario por defecto al cobrar (`boleta` / `factura` / `pendiente`) | `boleta` | `____________` | Configuración → Caja |
| ¿Recepción puede operar caja o solo rol `caja` + administración? | Recepción opera turno; reversos solo admin | `Sí / Solo caja` | Roles de usuarios |
| ¿Anticipos previos a Llegada omiten confirmación de pago en exceso? | Sí (ya implementado en 2.1) | `Ratificado / Ajustar` | Ya activo en `main` |

---

## 2. `#403` — Buzón de avisos en producción: SPF, DKIM y DMARC

1. **Definir buzón de envío** (por canal privado, nunca en Git): ej. `avisos@hotelherencia.cl` o cuenta SMTP/API autorizada.
2. **Cargar en Configuración → Correo / Avisos** con `CORREO_CLAVE_CIFRADO` configurada en Railway.
3. **Publicar registros DNS en Cloudflare** para `hotelherencia.cl`:
   - **SPF (TXT en `@`):** incluir el mecanismo del proveedor de correo autorizado (ej. `v=spf1 include:<proveedor> ~all`), verificando que exista un único registro SPF.
   - **DKIM (TXT o CNAME del selector del proveedor):** activar firma DKIM desde el panel del proveedor de correo.
   - **DMARC (TXT en `_dmarc`):** iniciar en modo observación `v=DMARC1; p=none; rua=mailto:postmaster@hotelherencia.cl; adkim=r; aspf=r`.
4. **Verificación de solo lectura (sin secretos):**
   ```bash
   dig +short TXT hotelherencia.cl | grep -i spf
   dig +short TXT _dmarc.hotelherencia.cl
   ```
5. **Prueba de humo:** ejecutar «Enviar correo de prueba» en **Configuración → Avisos**, confirmar llegada a bandeja principal (no spam), asunto de **Hotel Herencia**, sin PII de huéspedes y estado `Enviado` en el historial.

---

## 3. `#404` — Agente IA etapa 1 (copiloto de recepción con modelo real)

1. El adaptador real (`ModeloHttp` / Gemini OpenAI-compatible) y las salvaguardas (redacción PII, verificador de cifras contra herramientas del servidor, nivel N0/N1 sin confirmar pagos automáticamente) ya existen en `main`.
2. **Para encender en producción (Railway):**
   - Cargar en variables secretas de Railway: `MODELO_PROVEEDOR=gemini` (o `MODELO_BASE_URL` + `MODELO_API_KEY`) y `MODELO_NOMBRE` según modelo aprobado.
   - Mantener política inicial del agente en **copiloto (propone borrador, recepción aprueba y envía)**.
3. **Prueba de humo:** crear una consulta sintética en `/hotel/agente` («¿Cuánto cuesta una habitación doble para 2 personas del 10 al 12 de diciembre?»), verificar que el borrador cite tarifa exacta del mantenedor sin alucinar y quede en estado `pendiente` de aprobación humana.

---

## 4. `#408` — Cloudflare con proxy naranja, WAF y HSTS

1. **Pre-check obligatorio antes de activar proxy naranja:**
   - Inventariar todos los subdominios de `hotelherencia.cl` (`www`, `plataforma`, `api`, correo) y confirmar HTTPS válido en origen (Vercel y Railway).
   - Modo SSL/TLS en Cloudflare: **Full (strict)** (nunca *Flexible*).
   - Verificar que las reglas de Vercel (`CNAME`/`A`) no pierdan renovación automática de certificado.
2. **Reglas mínimas WAF / Rate Limiting:**
   - Limitar tasa en `POST /publico/solicitudes`, `POST /publico/leads` y `POST /sesion`.
   - Bloquear métodos/rutas de escaneo común (`/.env`, `/wp-login.php`).
3. **HSTS:** activar primero `max-age=31536000` en los hosts verificados; añadir `includeSubDomains; preload` solo tras confirmar 100 % de subdominios con HTTPS.
4. **Verificación de solo lectura post-cambio:**
   ```bash
   curl -sI https://www.hotelherencia.cl | grep -iE 'strict-transport-security|cf-ray|http/'
   curl -sI https://plataforma.hotelherencia.cl/api/readiness | grep -iE 'http/|strict-transport-security'
   ```

---

## 5. `#409` — Decisión de pasar a privados los repositorios

1. **Repositorios involucrados:** `hotelherencia/plataforma-salman-herencia-oficial` y `hotelherencia/landinpage`.
2. **Inventario de integraciones a verificar antes de cambiar visibilidad:**
   - GitHub App de **Vercel** (acceso a repos privados en la cuenta de propietario).
   - GitHub App de **Railway** (acceso al repo de backend).
   - **GitHub Projects #2** (permisos de colaboradores vigentes).
   - Clones locales WSL (`git remote -v` usando HTTPS con token o SSH autenticado).
3. **Si el propietario aprueba pasar a privado:** cambiar visibilidad en *Settings → Danger Zone*, disparar un deploy de prueba en Vercel/Railway y confirmar que ambos despliegues y el tablero siguen operativos.
4. **Si se mantiene público:** dejar constancia en `#409` y re-ejecutar barrido de secretos en el historial.

---

## 6. `#410` — Canal WhatsApp / Meta en producción

1. El webhook verificado con firma `X-Hub-Signature-256` y comparación en tiempo constante ya está en `main` (`GET/POST /mensajeria/whatsapp/webhook`); sin credenciales responde `503` sin filtrar secretos.
2. **Alta operativa (Meta Business):**
   - Crear/vincular app Meta Business + número oficial del hotel.
   - Configurar Webhook URL: `https://<backend-railway>/mensajeria/whatsapp/webhook` con `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` y `WHATSAPP_PHONE_NUMBER_ID` solo en secretos de Railway.
   - Activar avisos deseados en **Configuración → Avisos** (sin incluir datos personales de huéspedes).
3. **Prueba controlada:** enviar mensaje de prueba desde número de control y confirmar recepción en `/hotel/agente` + aviso sin PII.

---

## 7. `#423` — Publicar la barra de reserva en `hotelherencia.cl` y resolver la landing duplicada

1. Confirmar qué repositorio/proyecto de Vercel sirve actualmente el dominio `www.hotelherencia.cl` y retirar/archivar el despliegue duplicado.
2. Verificar que la barra de reserva de 3 campos (`Llegada`, `Salida`, `Huéspedes`) navegue directo a:
   `https://plataforma.hotelherencia.cl/reservar?llegada=AAAA-MM-DD&salida=AAAA-MM-DD&personas=N`
3. Validar E2E en navegador real (móvil y escritorio): barra landing → `/reservar` (RUT opcional) → envío de solicitud de prueba → aparición en `/hotel/solicitudes`.

---

## 8. `#424` — Validar en producción las migraciones `0058` y `0059` y el Corte 1 (`#415`–`#417`)

1. **Verificación de salud y migraciones (solo lectura):**
   ```bash
   curl -s https://plataforma.hotelherencia.cl/api/readiness
   ```
   Confirmar `"estado": "listo"` y conteo de migraciones aplicadas >= 59 (actualmente `main` llega hasta `0072`).
2. **Checklist autenticado en producción (con cuenta nominada del hotel, sin datos reales de huéspedes):**
   - [ ] `/hotel/panel`: bloque superior **«Lo que necesita atención»** visible y enlazando a registros reales.
   - [ ] `/hotel/aseo`: transición de habitación de prueba a **«En limpieza»**, marcado de subtareas de checklist y reporte de incidencia con evidencia móvil.
   - [ ] `/hotel/habitaciones/[id]`: bloqueo automático de disponibilidad al abrir incidencia con `bloquea_disponibilidad = true` y liberación al cerrarla.
   - [ ] Dejar constancia de fecha/hora y resultado en `#424` para cerrarlo.
