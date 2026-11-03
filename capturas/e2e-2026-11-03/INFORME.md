# INFORME E2E — Revisión de aceptación V1 (módulo hotel)

**Fecha:** 2026-11-03 · **Alcance:** plataforma V1 (front + API + backend, módulo hotel y rutas de acceso/cuenta)
**Fuente de verdad:** `AGENTS.md`, `docs/arquitectura/spec-front-v1.md`, `docs/arquitectura/spec-api-v1.md` (27 operaciones tras la ampliación 2026-11-03), `docs/arquitectura/spec-backend-v1.md`.
**Ambiente:** local y aislado — base `plataforma_e2e` (sintética, desechable, recreada de cero antes de la corrida), backend `127.0.0.1:8080` (migraciones + admin desde variables de entorno), front en build de producción en `127.0.0.1:3000` (`API_BASE_URL=http://127.0.0.1:8080`, `ORIGEN_FRONT` configurado). Navegador Chromium real vía Playwright. Sin producción, sin datos reales, sin adaptadores externos, sin pagos.

**Comando reproducible:** con backend y front corriendo como arriba,

```bash
cd e2e && npm install && npm run e2e
```

Semilla sintética: usuarios `admin_e2e` (administrador, del arranque), `recepcion_e2e` y `caja_e2e` (altos por API); habitaciones `HAB-101/102/103` con tarifas; más las 3 unidades sintéticas del dominio (`HAB-SINT-*`). Claves de idempotencia únicas por corrida. Resultado de la última corrida: **41/41 APROBADO, 0 FALLIDOS** (`e2e/e2e-resultados.json`); evidencia visual numerada en esta misma carpeta.

**Defectos encontrados en la revisión y corregidos (todos reprobados en verde):**

1. **Regresión real (crítica):** el alta y la tarifa de habitación enviaban `POST` a endpoints `PUT` → «Method Not Allowed»; el alta quedaba silenciosamente rota. Detectado por HAB-02. Corregido en `front/app/hotel/habitaciones/page.js` (método por operación).
2. `/hotel/reservas` nacía vacía (solo formulario) → «el buscador no retorna nada». Corregido: carga automática al entrar (BUS-03).
3. No existía lectura del estado de habitaciones (la pantalla operaba a ciegas). Corregido: `GET /hotel/habitaciones` en contrato, backend y front (tabla de inventario con acciones por rol).
4. `/hotel/usuarios` exigía «Usuario (id)» sin lista para descubrirlo. Corregido: tabla con «Usar id» (USR-01).
5. Resumen de confirmación confundía el estado del pago con el de la reserva; login precargaba «admin»; claves de idempotencia muy ruidosas. Corregidos (IDE-01, ACC-01/02).

**Verificaciones manuales complementarias (fuera de la suite automatizada):**

- **API caída** (criterio de aceptación 1 de spec-front-v1): con el backend detenido, las pantallas hoteleras muestran «La API no está disponible: nada se puede leer ni confirmar.» — APROBADO (observado en esta sesión, front `MarcoHotel`).
- **Persistencia tras reinicio** (criterio 4 de spec-backend-v1): tras reiniciar el proceso, las 3 reservas y los 3 pagos ($155.000) de la corrida siguen en la base — APROBADO.
- **2FA TOTP**: la UI de `/cuenta` muestra el estado y genera el secreto + URI de alta (ACC-04); la verificación del código y el efecto en el login se ejercen en `servicio/tests/test_2fa.py` — IMPLEMENTADO (cobertura de unidad para el código TOTP; la activación completa desde la UI queda como mejora de cobertura E2E futura).
- **Google OAuth**: sin `GOOGLE_CLIENT_ID/SECRET` el botón no se renderiza (ACC-05); el contrato lo declara opcional con 503 «no configurado» — DECLARADO/OPCIONAL, comportamiento verificado.

**Distingo implementado vs. declarado:**

- **Implementado y aprobado:** toda la matriz inferior (41 casos) — acceso, sesión, cuenta, los 9 flujos hoteleros con sus reglas de rol, validaciones, errores del contrato e idempotencia; módulos cerrados sin operación (CER-*).
- **Declarado, operación prohibida por contrato (verificado el rechazo):** pagos por pasarela (503, PAG-02), puertos externos sin adaptador en general.
- **Pendiente/no integrado (no se presenta como funcional):** rol `limpieza` de usuarios (spec-api-v1: DECISIÓN PENDIENTE, no existe); módulos cafetería/inmobiliaria/constructora (cerrados en V1); catálogo de minibar (el concepto es texto libre por contrato).
- **Bloqueos:** ninguno en local. (Independiente de esta revisión: el despliegue del backend a Railway quedó pendiente de aprobación en el dashboard por la política post-incidente — no afecta esta aceptación local.)

## Matriz de resultados

| ID | Ruta/Opción | Flujo | Rol | Esperado | Observado | Estado |
|---|---|---|---|---|---|---|
| ACC-01 | /login | login admin redirige a la plataforma | administrador | 200 y home con empresa y módulos | home con sesión admin | APROBADO |
| ACC-02 | /login | clave inválida no abre sesión y avisa | anónimo | 401 y mensaje de credenciales inválidas | Credenciales inválidas o sesión no disponible. | APROBADO |
| ACC-03 | /hotel/oferta | ruta hotel sin sesión pide login | anónimo | mensaje «Sesión cerrada», sin datos | pide inicio de sesión | APROBADO |
| ACC-04 | /cuenta | estado 2FA visible | administrador | muestra «Estado: desactivado» y alta disponible | estado 2FA desactivado visible | APROBADO |
| ACC-05 | /login | botón Google oculto sin adaptador | anónimo | sin botón «Entrar con Google» (configurado:false) | sin botón Google | APROBADO |
| CER-CAF | /cafeteria | módulo cerrado no operable | administrador | aviso de fuera de la versión, sin formularios ni fetch | presentado como fuera de la versión, sin operación | APROBADO |
| CER-INM | /inmobiliaria | módulo cerrado no operable | administrador | aviso de fuera de la versión, sin formularios ni fetch | presentado como fuera de la versión, sin operación | APROBADO |
| CER-CON | /constructora | módulo cerrado no operable | administrador | aviso de fuera de la versión, sin formularios ni fetch | presentado como fuera de la versión, sin operación | APROBADO |
| HAB-01 | /hotel/habitaciones | inventario refleja la semilla | administrador | las 3 habitaciones sembradas listadas con tarifa ref. | 6 unidades (3 sembradas + sintéticas del dominio) | APROBADO |
| HAB-02 | /hotel/habitaciones | alta desde la UI aparece en el inventario | administrador | HAB-201 creada y listada | HAB-201 listada tras el alta | APROBADO |
| HAB-03 | /hotel/habitaciones | abrir mantenimiento excluye de la oferta | administrador | oferta sin HAB-103; al cerrar vuelve | oferta excluye/incluye según mantenimiento | APROBADO |
| HAB-04 | /hotel/habitaciones | recepción no puede abrir mantenimiento | recepcion | 403 «acceso denegado» | 403 | APROBADO |
| HAB-05 | /hotel/habitaciones | caja no puede completar limpieza | caja | 403 «acceso denegado» | 403 | APROBADO |
| HAB-06 | /hotel/habitaciones | caja lee el inventario | caja | 200 con las unidades | 7 unidades visibles | APROBADO |
| OFE-ADM | /hotel/oferta | consulta de oferta | administrador | 200 solo disponibles, con tarifa y vencimiento | 2 unidades con tarifa y vigencia | APROBADO |
| OFE-REC | /hotel/oferta | consulta de oferta | recepcion | 200 solo disponibles, con tarifa y vencimiento | 2 unidades con tarifa y vigencia | APROBADO |
| OFE-CAJ | /hotel/oferta | consulta de oferta | caja | 200 solo disponibles, con tarifa y vencimiento | 2 unidades con tarifa y vigencia | APROBADO |
| RES-01 | /hotel/reserva | crear reserva desde la UI | recepcion | 201 confirmada; aparece en la búsqueda | Reserva RSV-af8094e3611e: estado «confirmada» | APROBADO |
| RES-02 | /hotel/reserva | reserva sin tarifa vigente es rechazada | recepcion | 409 con mensaje «sin tarifa vigente» | sin tarifa vigente para HAB-201 en 2026-12-03 | APROBADO |
| RES-03 | /hotel/reserva | solape en misma unidad y fechas | recepcion | 409 sin cupo (la carrera la gana una) | sin cupo para HAB-101 en [2026-12-03, 2026-12-06) | APROBADO |
| BUS-01 | /hotel/reservas | filtro de estado inválido | administrador | 422 «estado inválido» | estado inválido | APROBADO |
| BUS-02 | /hotel/reservas | documento del huésped por rol | recepcion vs caja | recepcion lo ve; caja no | recepcion:null caja:undefined | APROBADO |
| BUS-03 | /hotel/reservas | la página nace con reservas listadas | caja | tabla visible al entrar, sin buscar | 1 reserva(s) encontrada(s) | APROBADO |
| PAG-01 | /hotel/pago | pago manual de caja registra efecto | caja | 201 confirmado; la caja del día lo lista | Pago PAG-3f1c59f0a847 de $100000: estado «confirmado» | APROBADO |
| PAG-02 | /hotel/pago | pasarela sin adaptador | caja | 503 «no configurado», nada cobrado | La pasarela no está configurada: nada quedó marcado como cobrado. | APROBADO |
| PAG-03 | /hotel/pago | pago duplicado con misma clave y cuerpo | caja | mismo resultado, un solo efecto | mismo pago PAG-057fe50b8e82 | APROBADO |
| EST-01 | /hotel/estadia | check-in deja la unidad ocupada | recepcion | reserva en_estadia; inventario «ocupada» | HAB-101 ocupada | APROBADO |
| EST-02 | /hotel/estadia | cargo de minibar en estadía | caja | 201 cargo; entra en la liquidación | CRG-4a160ebcfbf4 | APROBADO |
| EST-03 | /hotel/estadia | cargo con monto inválido | recepcion | 422 | 422 | APROBADO |
| EST-04 | /hotel/estadia | caja no puede cancelar | caja | 403 (cancelación: recepción o admin) | 403 | APROBADO |
| EST-05 | /hotel/estadia | cancelación fuera de plazo carga la primera noche | recepcion | 409 (solo desde confirmada) + penalidad en otra | en_estadia→409; corta→cancelada con penalidad 35000 | APROBADO |
| SAL-01 | /hotel/salida | salida con saldo pendiente es bloqueada | administrador | 409 «saldo pendiente» | la cuenta tiene saldo pendiente de 50000 CLP | APROBADO |
| SAL-02 | /hotel/salida | pago del resto y liquidación | administrador | liquidación con saldo 0; unidad sucia + tarea | Reserva RSV-af8094e3611e: estado «liquidada»; HAB-101 sucia con tarea | APROBADO |
| CAJ-01 | /hotel/caja | recepción no lee la caja | recepcion | 403 en la API | 403 | APROBADO |
| CAJ-02 | /hotel/caja | caja ve los pagos del día | caja | 200 con total y pagos | total $155000 en 3 pago(s) | APROBADO |
| USR-01 | /hotel/usuarios | alta y listado con «Usar id» | administrador | usuario creado y listado | creado y listado | APROBADO |
| USR-02 | /hotel/usuarios | revocación cierra la sesión del otro | administrador | la sesión revocada pasa a 401 | sesión revocada → 401 | APROBADO |
| USR-03 | /hotel/usuarios | baja impide el login | administrador | activo=false; login 401 | login rechazado tras la baja | APROBADO |
| USR-04 | /hotel/usuarios | recepción no gestiona usuarios | recepcion | 403 en la API; la UI avisa «solo administrador» | UI y API rechazan | APROBADO |
| IDE-01 | /hotel/reserva | la clave se muestra antes del envío y rota tras el 2xx | recepcion | clave visible; tras confirmar, otra distinta | visible y rotada | APROBADO |
| SES-01 | /salida-de-sesion | cerrar sesión deja el panel fuera | administrador | la siguiente lectura pide login | sesión cerrada, ruta pide login | APROBADO |
**Conclusión: los 41 flujos automatizados están clasificados y aprobados con evidencia; no quedan fallos sin resolver. La aceptación V1 del módulo hotel queda aprobada en local.**
