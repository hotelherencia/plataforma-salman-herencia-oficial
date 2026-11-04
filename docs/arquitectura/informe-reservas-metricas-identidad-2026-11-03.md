# Informe: reservas vs reservas, métricas «no disponibles» e identidad transversal

**Fecha:** 2026-11-03 · **Alcance:** rutas `/hotel/reserva` y `/hotel/reservas`, declaraciones `no_disponibles` del panel, gestión de usuarios y cambio de clave.
**Verificación:** base 56/56 (incluye CLV-01 nuevo), operación 20/20, vendible 3/3, tarifa-noches 3/3, reserva-pública 6/6, servicio 206/206.

## 1. Dictamen: «Reserva» y «Reservas» no están duplicadas — son complementarias

**HECHO DOCUMENTADO** (mapa UI → endpoint → persistencia):

| Ruta | Actor | Endpoint | Efecto |
|---|---|---|---|
| `/hotel/reserva` (crear) | interno autenticado (recepción/admin) | `POST /hotel/reservas` (`aplicacion.py:728`) → dominio `core/incremento1` + persistencia `reservas`, `cargos_netos_clp` | crea reserva `confirmada` si hay cupo y noches con tarifa |
| `/hotel/reservas` (buscar) | interno autenticado | `GET /hotel/reservas` (`aplicacion.py:869`) | lista/filtra reservas persistidas, sin mutar |
| `/reservar` (canal público) | visitante de la landing, sin sesión | superficie pública (V1-ISSUE-21/23) | solicitud de reserva, no confirmación directa |

Ambas rutas internas comparten modelo pero no operación ni parámetros: una muta con `Idempotency-Key`, la otra solo consulta. El nombre duplicado («Reserva» / «Reservas») sí era un defecto real de claridad de menú: ambas apuntaban a capacidades distintas con etiquetas casi iguales. Corrección aplicada: el menú las distingue como **«Nueva reserva»** y **«Buscar reservas»** (`front/app/barra.jsx`, también en el panel móvil), y `spec-front-v1.md` renombra las rutas 3/4 en consecuencia. No se consolidaron endpoints: no había duplicación que justifique romper clientes.

## 2. Verificación de las afirmaciones «no disponibles»

| Afirmación | Dictamen | Evidencia |
|---|---|---|
| ADR, RevPAR e ingresos de hospedaje requieren cargos netos **por noche** y un rol `gerencia`; V1 registra alojamiento como cargo único y sin ese rol | **HECHO DOCUMENTADO — la afirmación es correcta.** No calculables fielmente con los datos actuales; el panel los declara en `no_disponibles` con motivo | dominio (`hotel_inventario/servicio.py`, cálculo de cargos por estadía como cargo único), spec §4.4, issue #297 |
| Ingresos por canal: no se persiste el canal de origen | **HECHO DOCUMENTADO** con matiz: el canal público (V1-ISSUE-21/23) deja solicitudes cuyo origen es identificable, pero no hay campo de canal en reservas confirmadas. Hoy no es una métrica fiel | `servicio/canal_publico.py`, modelo `reservas`. Habilitación propuesta en #324 |
| Pagos del periodo: decisión pendiente; Caja muestra pagos diarios sin conciliación | **DECISIÓN PENDIENTE** (brief `decisiones-pendientes-v1.md` §6); lo que Caja muestra hoy es HECHO DOCUMENTADO y correcto según contrato: pagos por día, sin conciliación de periodo | `front/app/hotel/caja`, spec de caja |
| No-show: no existe ese estado; se informa `llegadas_vencidas` | **HECHO DOCUMENTADO.** V1 no modela no-show; el panel lo declara en `no_disponibles` («V1 no tiene ese estado; ver `llegadas_vencidas`», `servicio/panel.py:192`) y expone `llegadas_vencidas` como sustituto operativo | `servicio/panel.py:192,225` |

Ninguna métrica sin datos se presenta como cero: todas van a `no_disponibles` con motivo explícito.

## 3. Identidad transversal: qué es de core y qué es del hotel

**HECHO DOCUMENTADO:**

- Gestión de usuarios vive en el servicio como identidad transversal: `servicio/seguridad.py` (alta, clave con hash, activación, TOTP, auditoría) y endpoints `GET/POST /usuarios`, `POST /usuarios/{id}/clave` (`aplicacion.py:908,947`). Aislamiento por empresa en todas las consultas (`empresa_id`).
- Los **roles vigentes son los del hotel** (`administrador`, `recepcion`, `caja` — `seguridad.py:70` y permisos por ruta). No hay catálogo de roles fuera del módulo: cafetería y demás módulos cerrados no tienen identidad propia en V1.
- Políticas de permisos por ruta se declaran en el servicio (hotel), no en un módulo transversal de autorización.

**Brechas (propuestas, no construidas):** catálogo de roles transversal para futuros módulos → #323; revocación de las demás sesiones al cambiar la clave → #322 (hoy el contrato conserva las sesiones activas: no es bug, es comportamiento vigente).

## 4. Cambio de contraseña del administrador: estado comprobado

**FUNCIONAL** (antes: implementado en API pero inaccesible — sin ruta visible en la UI).

- Ruta visible: `/cuenta` → sección «Cambiar clave» (título de página actualizado a «Mi cuenta: clave y doble factor»).
- Endpoint: `POST /usuarios/{propio_id}/clave` con `Idempotency-Key`; cualquier rol autenticado puede cambiar su propia clave (admin también la de otros).
- Validación: mínimo 6 caracteres (front y servicio); almacenamiento con hash (sin texto plano); auditoría de la operación.
- Efecto: la clave vieja deja de abrir sesión; la nueva funciona. Las sesiones existentes **siguen activas** (contrato vigente; mejora propuesta en #322).
- Prueba: **CLV-01** (E2E base) — admin cambia su clave desde la interfaz, reautentica con la nueva y la vieja es rechazada. Incluido en la corrida 56/56.

Fix adicional en esta ronda: `.barra { overflow-y: auto }` (`front/app/globals.css`) — en páginas largas el botón «Cerrar sesión» del pie quedaba fuera de alcance; ahora la barra lateral desplaza.

## 5. Issues registrados en esta evaluación

| Issue | Tipo | Contenido |
|---|---|---|
| #320 | Propuesta | Unificar el nombre `ocupadas` (resumen de ocupación vs serie del panel) en revisión de contrato |
| #322 | Propuesta | Revocar las demás sesiones al cambiar la clave |
| #323 | Propuesta | Catálogo de roles transversal, fuera del módulo hotel |
| #324 | Propuesta | Ingresos por canal: traza parcial desde la solicitud pública |

Todos quedan agregados al tablero «Plataforma Hotel Herencia» junto a las decisiones abiertas previas (#296–#299, #304–#306, #308, #313–#319).

## 6. Límites y no verificado

- La no-revocación de sesiones se validó como comportamiento de contrato; la mejora (#322) requiere decisión por impacto en sesiones móviles/tabletas en uso.
- El alcance de recepción/caja en estas pantallas se cubre con las suites por rol; no se repitió exploración manual por rol en esta ronda.
- Nada de esta ronda tocó producción: sin despliegue, sin datos reales.
