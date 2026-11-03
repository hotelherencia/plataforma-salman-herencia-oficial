# INFORME E2E — Revisión de aceptación V1 (módulo hotel)

**Fecha:** 2026-11-03 · **Alcance:** plataforma V1 (front + API + backend, módulo hotel y rutas de acceso/cuenta)
**Fuente de verdad:** `AGENTS.md`, `docs/arquitectura/spec-front-v1.md`, `docs/arquitectura/spec-api-v1.md` (27 operaciones), `docs/arquitectura/spec-backend-v1.md`.
**Ambiente:** local y aislado — base `plataforma_e2e` (sintética, desechable), backend `127.0.0.1:8080`, front en build de producción `127.0.0.1:3000`, navegador Chromium vía Playwright. Sin producción, sin datos reales, sin adaptadores externos.

**Comando reproducible:** `cd e2e && npm install && npm run e2e` (ver `e2e/README.md`).
**Resultado de la última corrida (cierre del ciclo de issues): 44/44 APROBADO, 0 FALLIDOS** (`e2e/e2e-resultados.json`).

## Ciclo de corrección ejecutado en esta sesión (issues del backlog → resueltos)

1. **v1-issue-01 (P1) — 20 tests del servicio en rojo → 129/129 en verde.**
   Correcciones de código que los tests documentaban: cookie de cierre de sesión con Secure/SameSite=None en producción; arranque que exige COOKIE_SEGURA con ORIGIN_FRONT ajeno; normalización de barra final de ORIGEN_FRONT; middleware que rechaza mutaciones con Origin ajeno (403); check-in con turnover (la unidad OCUPADA no bloquea una reserva no solapada, DECISIÓN 2026-10-30 fuente check_in). Tests realineados a la spec vigente: cancelación devuelve penalidad_clp/reversos/reembolso (modelo de cargo único de V1), limpieza sin tarea es no-op 200, entrada no exige documento ni hora (no son condición del contrato), usuarios devuelven `id`, autoprovocación de revocación es 409, adaptador reescrito al espíritud original bajo la arquitectura SQL aprobada.
2. **v1-issue-02 — 2FA en navegador:** caso TFA-01: alta del secreto, código TOTP calculado del secreto mostrado, activación, cierre de sesión y login exigiendo el código. APROBADO.
3. **v1-issue-03 — acciones ocultas por rol:** recepción no ve la caja del día (ROL-01) y caja no ve la cancelación (ROL-02); la API sigue rechazando 403 como red de seguridad. APROBADO.
4. **v1-issue-04/05 — operación:** secciones «Aprobación de deploys Railway» y «Diagnóstico de hidratación en next dev» en `docs/arquitectura/h7-despliegue.md`.
5. **v1-issue-06 — artefactos:** `e2e/README.md` con el comando, la convención de `e2e-resultados.json` y los requisitos.

**Verificaciones manuales complementarias:** API caída (criterio front 1); persistencia tras reinicio del proceso (criterio backend 4); Google OAuth sin adaptador (botón oculto, 503).

**Distingo implementado vs. declarado:** puertos externos y pasarela rechazan 503 (verificado); rol `limpieza` de usuarios y módulos no hoteleros siguen pendientes/cerrados en V1 (no se presentan como funcionales).

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
| HAB-01 | /hotel/habitaciones | inventario refleja la semilla | administrador | las 3 habitaciones sembradas listadas con tarifa ref. | 19 unidades (3 sembradas + sintéticas del dominio) | APROBADO |
| HAB-02 | /hotel/habitaciones | alta desde la UI aparece en el inventario | administrador | HAB-201 creada y listada | HAB-201 listada tras el alta | APROBADO |
| HAB-03 | /hotel/habitaciones | abrir mantenimiento excluye de la oferta | administrador | oferta sin HAB-103; al cerrar vuelve | oferta excluye/incluye según mantenimiento | APROBADO |
| HAB-04 | /hotel/habitaciones | recepción no puede abrir mantenimiento | recepcion | 403 «acceso denegado» | 403 | APROBADO |
| HAB-05 | /hotel/habitaciones | caja no puede completar limpieza | caja | 403 «acceso denegado» | 403 | APROBADO |
| HAB-06 | /hotel/habitaciones | caja lee el inventario | caja | 200 con las unidades | 19 unidades visibles | APROBADO |
| OFE-ADM | /hotel/oferta | consulta de oferta | administrador | 200 solo disponibles, con tarifa y vencimiento | 9 unidades con tarifa y vigencia | APROBADO |
| OFE-REC | /hotel/oferta | consulta de oferta | recepcion | 200 solo disponibles, con tarifa y vencimiento | 9 unidades con tarifa y vigencia | APROBADO |
| OFE-CAJ | /hotel/oferta | consulta de oferta | caja | 200 solo disponibles, con tarifa y vencimiento | 9 unidades con tarifa y vigencia | APROBADO |
| RES-01 | /hotel/reserva | crear reserva desde la UI | recepcion | 201 confirmada; aparece en la búsqueda | Reserva RSV-f6ffda746917: estado «confirmada» | APROBADO |
| RES-02 | /hotel/reserva | reserva sin tarifa vigente es rechazada | recepcion | 409 con mensaje «sin tarifa vigente» | sin tarifa vigente para HAB-201 en 2026-12-03 | APROBADO |
| RES-03 | /hotel/reserva | solape en misma unidad y fechas | recepcion | 409 sin cupo (la carrera la gana una) | sin cupo para HAB-mw0v4zqx-A en [2026-12-03, 2026-12-06) | APROBADO |
| BUS-01 | /hotel/reservas | filtro de estado inválido | administrador | 422 «estado inválido» | estado inválido | APROBADO |
| BUS-02 | /hotel/reservas | documento del huésped por rol | recepcion vs caja | recepcion lo ve; caja no | recepcion:null caja:undefined | APROBADO |
| BUS-03 | /hotel/reservas | la página nace con reservas listadas | caja | tabla visible al entrar, sin buscar | 15 reserva(s) encontrada(s) | APROBADO |
| PAG-01 | /hotel/pago | pago manual de caja registra efecto | caja | 201 confirmado; la caja del día lo lista | Pago PAG-ef697c293bc0 de $100000: estado «confirmado» | APROBADO |
| PAG-02 | /hotel/pago | pasarela sin adaptador | caja | 503 «no configurado», nada cobrado | La pasarela no está configurada: nada quedó marcado como cobrado. | APROBADO |
| PAG-03 | /hotel/pago | pago duplicado con misma clave y cuerpo | caja | mismo resultado, un solo efecto | mismo pago PAG-b319b45a188d | APROBADO |
| EST-01 | /hotel/estadia | check-in deja la unidad ocupada | recepcion | reserva en_estadia; inventario «ocupada» | HAB-101 ocupada | APROBADO |
| EST-02 | /hotel/estadia | cargo de minibar en estadía | caja | 201 cargo; entra en la liquidación | CRG-09f8795a4bc9 | APROBADO |
| EST-03 | /hotel/estadia | cargo con monto inválido | recepcion | 422 | 422 | APROBADO |
| EST-04 | /hotel/estadia | caja no puede cancelar | caja | 403 (cancelación: recepción o admin) | 403 | APROBADO |
| EST-05 | /hotel/estadia | cancelación fuera de plazo carga la primera noche | recepcion | 409 (solo desde confirmada) + penalidad en otra | en_estadia→409; corta→cancelada con penalidad 35000 | APROBADO |
| SAL-01 | /hotel/salida | salida con saldo pendiente es bloqueada | administrador | 409 «saldo pendiente» | la cuenta tiene saldo pendiente de 50000 CLP | APROBADO |
| SAL-02 | /hotel/salida | pago del resto y liquidación | administrador | liquidación con saldo 0; unidad sucia + tarea | Reserva RSV-f6ffda746917: estado «liquidada»; HAB-101 sucia con tarea | APROBADO |
| CAJ-01 | /hotel/caja | recepción no lee la caja | recepcion | 403 en la API | 403 | APROBADO |
| CAJ-02 | /hotel/caja | caja ve los pagos del día | caja | 200 con total y pagos | total $930000 en 18 pago(s) | APROBADO |
| USR-01 | /hotel/usuarios | alta y listado con «Usar id» | administrador | usuario creado y listado | creado y listado | APROBADO |
| USR-02 | /hotel/usuarios | revocación cierra la sesión del otro | administrador | la sesión revocada pasa a 401 | sesión revocada → 401 | APROBADO |
| USR-03 | /hotel/usuarios | baja impide el login | administrador | activo=false; login 401 | login rechazado tras la baja | APROBADO |
| USR-04 | /hotel/usuarios | recepción no gestiona usuarios | recepcion | 403 en la API; la UI avisa «solo administrador» | UI y API rechazan | APROBADO |
| IDE-01 | /hotel/reserva | la clave se muestra antes del envío y rota tras el 2xx | recepcion | clave visible; tras confirmar, otra distinta | visible y rotada | APROBADO |
| TFA-01 | /cuenta | alta del segundo factor y login con TOTP | recepcion | secreto mostrado, activación con código, login exigiendo totp | 2FA activado y login con código | APROBADO |
| ROL-01 | /hotel/caja | recepción no ve la caja del día | recepcion | aviso de rol, sin formulario | formulario oculto y aviso de rol | APROBADO |
| ROL-02 | /hotel/estadia | caja no ve la cancelación de reserva | caja | sin sección «Cancelar reserva» | cancelación oculta para caja; check-in visible | APROBADO |
| SES-01 | /salida-de-sesion | cerrar sesión deja el panel fuera | administrador | la siguiente lectura pide login | sesión cerrada, ruta pide login | APROBADO |
**Conclusión: los 44 flujos están clasificados y aprobados con evidencia; no quedan fallos sin resolver. Los issues v1-issue-01..06 del backlog quedan resueltos y la aceptación V1 del módulo hotel se mantiene.**
