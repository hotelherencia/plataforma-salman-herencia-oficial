# Estado vigente de la construcción V1

**Ficha viva (DOC-A01, #335).** Sustituye a los conteos dispersos del README;
si un número de aquí se usa en otra parte, citar esta ficha en vez de copiarlo.
Última actualización: 2026-11-18 (hallazgos de operación del propietario, épica #368; registro en `backlog/hallazgos-2026-11-18.md`).

## Qué es operable hoy

- **Módulo hotel completo de V1** (empresa fija): habitaciones/tarifas,
  oferta, reserva transaccional, cobro por el núcleo, estadía (entrada/salida
  con turnover), caja, cancelación con reversos, mantenedor auditado,
  búsqueda, ocupación e indicadores operativos, canal público (disponibilidad,
  solicitudes, landing con CTA y leads),   agente N0 copiloto con compuerta
  SC-003 (modelo guionado; el adaptador HTTP espera D-AGT-02). Con la política
  en N1 el borrador informativo queda `pendiente_envio` si no hay canal; en N2
  puede crear una solicitud de origen `agente` sin reserva ni cobro. El nivel
  por defecto sigue N0. Cambiar la clave revoca las demás sesiones (#322).
- **Ronda del 2026-11-18 (épica #368):**
  - reserva pública por tipo, con preselección desde la landing;
  - recepción con documento validado y habitación seleccionable;
  - mover a un huésped de habitación;
  - caja con huésped visible, pago parcial o en exceso y reverso de cargo;
  - rol **aseo** con verificación y observaciones;
  - mantenimiento por rango de fechas;
  - **productos** con stock de minibar;
  - **avisos** de solicitudes y leads deduplicados por contacto;
  - **tope de solicitudes por cliente**;
  - **servidores de correo** configurables, con lead «contactado» automático;
  - alta de usuarios con correo de Google.
- **Front** en Vercel (login con 2FA TOTP y Google opcional, las pantallas del
  hotel, bandejas de solicitudes/leads/agente, /reservar pública) y **API +
  backend** desplegados (API en Vercel `/api/*`, backend Railway restaurado el
  2026-11-02).

## Números vigentes (2026-11-18)

| Magnitud | Valor | Fuente |
|---|---|---|
| Operaciones del contrato | 97 | spec-api-v1 (2026-11-18: 97 tras la ronda de hallazgos; migraciones del servicio: 31) (la tabla manda; la validan `scripts/validar_estado_v1.py` y `servicio/tests/test_contrato_rutas.py`, que la compara con las rutas reales). El 2026-11-16 se sumaron a la tabla las 9 que ya existían en el código: `POST /auth/google/totp`, `GET /publico/referencia` y las 7 de `/hotel/documental/*`. |
| Pruebas del servicio | 566 (pytest, 2026-11-18) | `pytest servicio/tests` contra PostgreSQL 16 local, base dedicada; la diferencia son 4 funciones estilo pytest que `unittest` no recoge. Antes de esta ronda: 413 / 409. |
| Pruebas del dominio | 5 raíces en verde (180) | core 9 · hotel 118 · cafetería 19 · inmobiliaria 20 · constructora 14 (`unittest discover`) |
| Unitarios de la landing | 18 | `node --test landing/test/*.test.mjs` |
| E2E con navegador | base 56 · operación 20 · tarifa-noches 3 · público 6 · landing 3 · leads 5 · agente 4 | `e2e/` (corridas fechadas en `capturas/`; la última guardada tiene 7 fallos, W16-A03) |
| Tablero V1 | 92 ítems (87 hechos) | `backlog/v1/construccion-v1.json` (conteo de `validar_estado_v1.py`) |

Verificación local: `python3 scripts/verificar_local.py` (instala con
`uv sync --frozen` y corre la suite del servicio con pytest).

## Fuera de V1 (nombrado, no operable)

Financieros (tarifa promedio e ingreso por habitación disponible: pendientes de decisión del propietario; el panel deja de mostrarlos como «no disponibles» con #381), verticales cafetería/
inmobiliaria/constructora (rutas vacías con guardia), puertos externos reales
(Webpay, Mercado Pago, SII, Booking, Airbnb, WhatsApp/Meta: sin adaptador →
503 «no configurado», regla AGENTS.md).

## Decisiones resueltas en la ola del 2026-11-06

Ratificadas y construidas: precio noche a noche (#305), documento en entrada
(#296), roles de entrada/salida (#304), ingresos para administrador (#297),
personas en la reserva (#298), guarda de tarifa idéntica y denominador del
panel (#299), solicitud con aprobación humana (#308). Pendientes: D-AGT-02
(proveedor del modelo — el adaptador HTTP ya existe), D-IND-02 (ADR/RevPAR),
items «a pedido» del brief. Detalle: `docs/arquitectura/decisiones-pendientes-v1.md`.

## Seguridad (post-auditoría 2026-11-03)

Resueltas el 2026-11-05: SEC-A01..A05 y OPS-A02 (issues #326–#330, #333) más
ARC-A01 (split y dependencias) y DOC-A01 (validador y ficha) el 2026-11-05/06 —
todas las issues de la auditoría están cerradas salvo OPS-A01 (#332, ensayo de
restauración) y REL-A01 (#331, verificación local por orden del propietario). Pendientes:
rotación periódica de secretos (proceso; última rotación 2026-11-05, #275),
ensayo de restauración PITR (OPS-A01, #332), ruleset de protección de rama
(REL-A01, #331 — el CI ya corre; falta exigir el check).
