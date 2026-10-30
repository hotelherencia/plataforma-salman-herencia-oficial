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
- `GET /salud` (sin autenticar) responde 200 con estado y versión.

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
- **Al reiniciar el servicio, una reserva confirmada y un pago siguen ahí**
  (fila 6 del dictamen); las tareas operativas también.

## Puertos y sistemas externos

Webpay, Mercado Pago, SII, Booking, Airbnb y WhatsApp son puertos del
núcleo. En esta versión responden **«no configurado»** y la API traduce eso a
**503** con estado pendiente. No hay adaptador real ni llamadas salientes.

## Criterio de aceptación

1. `GET /salud` responde en el despliegue de Railway.
2. Las **26 operaciones** de spec-api-v1 (contrato ampliado 2026-10-30) pasan
   contra PostgreSQL.
3. Una segunda llamada con la misma clave de idempotencia no crea un segundo
   efecto; con otro cuerpo responde 409.
4. Reinicio del proceso: reserva y pago persisten.
5. Sin sesión 401; otra empresa 403 sin revelar existencia; puerto sin
   adaptador 503.
6. El proceso no arranca si el hotel no entra por la empresa del núcleo.
