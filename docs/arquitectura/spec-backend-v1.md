# Especificación backend V1 — el servicio en Railway

**Estado:** REQUISITO PROPUESTO, fechado 2026-10-28. Un solo servicio,
`plataforma-salman-herencia-api`, en Railway. Cumple y sirve
[spec-api-v1.md](spec-api-v1.md). El prototipo `plataforma/servidor.py` queda
obsoleto con esta especificación: se reemplaza por este servicio y sus pruebas
se portan a HTTP contra el contrato.

## Stack (el que el proceso ejecuta)

Python 3 + **FastAPI** + **PostgreSQL 17**. Acceso a datos con SQL
parametrizado (DECISIÓN, 2026-10-28: `psycopg` v3 directo, sin ORM; todo
valor que viene del request entra como parámetro, no interpolado en el SQL;
`specs/*/plan.md` y ADR-001 quedan como histórico no ejecutado). El hash de
claves usa `argon2-cffi` (argon2id). Migraciones
versionadas en `servicio/migraciones/` (SQL numerado, ejecutado por comando de
arranque). Solo biblioteca estándar + estas dependencias declaradas en
`requirements.txt`.

## Arranque y composición

- Al arrancar carga el núcleo (`core/incremento1/nucleo`) y el módulo hotel
  (`verticales/hotel/incremento1/hotel_inventario`) en el **mismo proceso**.
- El hotel se construye con `empresa=nucleo.empresa`; el proceso **rechaza el
  arranque** si el hotel trae otra empresa (regla ya probada en código:
  `construir_hotel`).
- Configuración solo por variables de entorno (`DATABASE_URL`, flags de
  cookie, puerto `SERVICIO_PUERTO` con reserva de `$PORT` para Railway).
  **El repositorio no lleva `.env`**.
- `GET /salud` (sin autenticar) responde 200 con estado y versión;
  `GET /readiness` (OPS-A02) consulta la base y migraciones.

## Flujo real de las reglas (sincronizado 2026-11-05, ARC-A01)

La auditoría de jefatura 2026-11-03 señaló que la decisión documentada («el
dominio decide cada operación HTTP») no describía el flujo real. Flujo
vigente, de afuera hacia adentro:

1. **Límite HTTP** (`servicio/aplicacion.py`): sesión, roles, CORS, frenos de
   abuso, idempotencia; **ninguna regla de negocio** vive aquí.
2. **Persistencia con reglas** (`servicio/reservas.py`, `servicio/cobro.py`):
   las invariantes transaccionales (carrera por la última unidad, estados,
   reversos, liquidación) se ejecutan en SQL dentro de la transacción.
3. **Núcleo puro** (`core/`, `verticales/*/incremento1`): decide los efectos
   de cobro/estadía que el servicio persiste en `efectos_nucleo`; es la
   especificación ejecutable del dominio (181 pruebas, sin red).

Split aplicado el 2026-11-05 (ARC-A01): `aplicacion.py` quedó como fábrica
(arranque, middlewares, salud/readiness, handlers) y las rutas viven en
`servicio/rutas/` (`acceso`, `hotel` —incluye solicitudes/leads— y `agente`)
con las dependencias compartidas en `rutas/comun.py` y los modelos en
`rutas/modelos.py`. Los 277 tests del servicio son la red de seguridad del
movimiento; comportamiento idéntico, verificado por la regresión completa.

## Licencias de las dependencias (revisión ARC-A01, 2026-11-05)

| Paquete (fijado) | Licencia |
|---|---|
| fastapi 0.162.0 | MIT |
| uvicorn 0.54.0 | BSD-3-Clause |
| psycopg[binary] 3.3.6 | LGPL-3.0-only |
| argon2-cffi 25.1.0 | MIT |
| httpx 0.28.1 | BSD-3-Clause |
| qrcode 8.2 | BSD |

Todas OSI y compatibles con uso comercial. Única cautela: psycopg es
LGPL-3.0 — el import dinámico desde CPython sin modificación del paquete es
el modo de uso aceptado (mismo caso histórico de psycopg2); no hay código
propietario derivado ni linking estático. Si el negocio exigiera
alternativa permissiva, el único punto de toque es `servicio/` (el dominio
no importa psycopg).

## Persistencia

PostgreSQL guarda: `usuarios` (con `activo` y `UNIQUE (empresa_id, nombre)`),
`sesiones`, `habitaciones` (con `estado_operativo`, `estado_preparación` y
`mantenimiento`), `tarifas`, `reservas`, `cargos` (con `tipo` `cargo|reverso`
y `referencia` nullable), `pagos`, `efectos_nucleo`, `claves_idempotencia`,
`liquidaciones` y `tareas_operativas` (limpieza y mantenimiento, durable al
reinicio). Reglas:

- Reserva confirmada o en estadía: constraint de **no solape** por (unidad,
  fechas); la confirmación es transaccional (la carrera por la última unidad
  la gana una sola, la otra recibe 409). `cancelada` y `finalizada` sueltan el
  rango.
- HECHO DOCUMENTADO (dominio): los cargos son inmutables; una corrección es un
  asiento `reverso` de monto positivo que referencia al cargo original. La
  salida y cualquier saldo suman cargo menos reverso.
- Tarifa aceptada en reserva queda congelada: cambiar `tarifas` no altera el
  precio de reservas existentes.
- Pago: el efecto lo registra el núcleo; la fila `pagos` es la proyección de
  lectura. El servicio no marca cobrado nada que el núcleo no aceptó.
- `huesped_documento` solo sale en las respuestas para roles `recepcion` o
  `administrador` (HECHO DOCUMENTADO: `ROLES_DOCUMENTO` del dominio).
- Habitaciones: baja lógica (`estado_operativo = fuera_de_servicio`,
  `motivo_fuera_de_servicio`, `fuera_de_servicio_desde`; migración 0009);
  jamás `DELETE` (las FK de reservas, tarifas y tareas ya lo impiden).
  `tarifas.creado_en` desempata la vigencia. Altas, ediciones, tarifas y
  retiros dejan fila en `auditoria` (spec-hotel-operacion-v1 §2).
- Indicadores y ocupación se calculan en SQL en el servidor, sin escribir
  nada; el front no recalcula (spec-hotel-operacion-v1 §4–5).
- **Al reiniciar el servicio, una reserva confirmada y un pago siguen ahí**
  (fila 6 del dictamen); las tareas operativas también.
- Agente de reservas (N0, 2026-11-04, V1-ISSUE-29): tablas propias
  `consultas_agente`, `borradores_agente`, `trazas_agente` y `politica_agente`
  (migración 0011), más el usuario de servicio `agente` (sin clave utilizable
  ni sesión posible). Puerto `ModeloLenguaje`: sin adaptador (D-AGT-02
  pendiente) responde 503 «modelo no configurado» y la consulta queda
  `pendiente`; el modelo guionado solo existe para las pruebas. El orquestador
  corre dentro de la petición (sin cola ni worker), con tope de 3 turnos y
  verificador determinista: ninguna cifra del borrador sale del resultado de
  las herramientas de su turno. Detalle en `specs/005-hotel-agente-reservas/`
  y en la sección «Agente de reservas» de spec-api-v1.

## Puertos y sistemas externos

Webpay, Mercado Pago, SII, Booking, Airbnb y WhatsApp son puertos del
núcleo. En esta versión responden **«no configurado»** y la API traduce eso a
**503** con estado pendiente. No hay adaptador real ni llamadas salientes.

## Criterio de aceptación

1. `GET /salud` responde en el despliegue de Railway.
2. Las **47 operaciones** de spec-api-v1 (contrato ampliado 2026-10-30,
   2026-11-03 y 2026-11-04 con el agente N0) pasan contra PostgreSQL.
3. Una segunda llamada con la misma clave de idempotencia no crea un segundo
   efecto; con otro cuerpo responde 409.
4. Reinicio del proceso: reserva y pago persisten.
5. Sin sesión 401; otra empresa 403 sin revelar existencia; puerto sin
   adaptador 503.
6. El proceso no arranca si el hotel no entra por la empresa del núcleo.
