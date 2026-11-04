# Arquitectura funcional y stack de la plataforma — Grupo Salman / Herencia

**PROPUESTA TÉCNICA — 2026-10-27** (no ratificada; el acta sigue sin firma y
corrige después). Corrección del mismo día tras contraste con el código: dos
bloques separados, **hecho de código** (verificado, con pruebas) y **destino**
(propuesta). Las specs y la constitución no se editan. No despliega nada: no
hay proyectos en Vercel ni en Railway todavía, ni cobros, ni emisiones, ni
llamadas a sistemas externos.

**Actualización 2026-10-28:** el «destino» de esta sección queda sustituido
como especificación gobernante por las tres specs V1:
[spec-front-v1.md](spec-front-v1.md), [spec-api-v1.md](spec-api-v1.md) y
[spec-backend-v1.md](spec-backend-v1.md) (front Vercel, contrato API, backend
Railway con FastAPI y PostgreSQL 17). Lo que sigue se conserva como histórico
del contraste; el estado por filas está en
[evaluacion-bases.md](evaluacion-bases.md).

## 1. Hecho de código (verificado el 2026-10-27)

Cinco módulos Python en memoria, solo biblioteca estándar, sin UI ni red:

- `core/incremento1/nucleo` — conector con permisos, deuda, aprobaciones con
  monto/parámetros/vigencia/uso único y `aplicar_resultado_pago`
  idempotente; ejercido solo por sus pruebas (9 OK).
- `verticales/hotel/incremento1/hotel_inventario` — reserva, estadía, cuenta,
  pagos, pedir a habitación y sus puertos, dentro del mismo módulo (la suite
  de `verticales/hotel/incremento1` corre 102 pruebas OK).
- `verticales/cafeteria/incremento1/cafeteria_mesas_pos` — mesas, pedidos y
  operación (19 pruebas OK).
- `verticales/inmobiliaria/incremento1/inmobiliaria_comercial` (20 pruebas OK)
  y `verticales/constructora/incremento1/constructora_obra` (14 pruebas OK).

Propiedades comprobadas del código:

- **Sin imports cruzados.** Ninguna vertical importa `nucleo`; cada módulo se
  construye y se prueba solo. El «llama al core por interfaz interna» que
  describía la versión anterior de este documento todavía no existe en código.
- **Cinco puertas de empresa, no una.** Cada módulo trae su propia
  `EMPRESA_FIJA` y su propia copia de `AccesoDenegado` (una definición por
  `servicio.py`). La excepción repetida evidencia una copia, no una puerta
  única.
- **El cobro del hotel no pasa por el núcleo.** `pagos`, `pedir_a_habitacion`
  y `cuenta` viven en `hotel_inventario/servicio.py`; el
  `aplicar_resultado_pago` del núcleo (`core/incremento1/nucleo/servicio.py`)
  corre solo en las pruebas del núcleo. Son dos islas sin enlace.
- **El núcleo no tiene puertos de pago ni de documento.** Su salvaguarda de
  hoy es el conector con `placeholder=True`, que bloquea con `AccesoDenegado`
  (efectos desconocidos); los puertos «no configurado» existen en las
  verticales (`hotel_inventario/puertos.py`), no en el núcleo.
- **`hotel_reservas_incremento1/` no forma parte de la arquitectura.** Es una
  segunda implementación del mismo contrato del hotel (consta en su README),
  copia paralela con su propia empresa fija. Tampoco lo forma
  `verticales/hotel/incremento0`, la prueba aislada anterior (17 pruebas OK).

Consecuencia (2026-10-27): hoy **no hay front, no hay API (borde HTTP) y no hay proceso
backend**. Esas palabras nombran el destino, no un artefacto existente.

**Actualización 2026-10-28 (decisión del propietario).** El mínimo a construir es
el front en Vercel, la API y el backend en Railway:
`spec-front-vercel.md`, `spec-api.md`, `spec-backend-railway.md`.
`plataforma/servidor.py` es un proceso de biblioteca estándar en memoria; no es
la API ni el servicio de Railway, y no cumple esas tres especificaciones.

## 2. Destino (propuesta)

### Front — una sola aplicación para la empresa base Herencia

Una única aplicación web en **Vercel**. Cada vertical es un **módulo** de esa
aplicación (`/hotel`, `/cafeteria`, `/inmobiliaria`, `/constructora`), no un
sitio distinto. Un solo login, una sola sesión, la empresa derivada de la
identidad autenticada. El front no habla con sistemas externos: solo con la
API propia.

### API — un solo borde HTTP

Un solo borde, el del mismo servicio. El **core** expone identidad, empresa,
autorización, pagos, documentos tributarios y auditoría (specs/000-core:
FR-001..FR-012, NFR-001..006). Cada vertical expone **solo su operación** —
hotel: disponibilidad, reserva, estadía, cuenta; cafetería: mesas, pedidos,
POS; inmobiliaria: lead a promesa; constructora: avance, presupuesto, obra —
y **no duplica identidad ni cobro**: esos efectos pasan por el core, que es
la única puerta que autentica la empresa en cada request y registra pago o
documento en el ledger (principio IV de la constitución).

### Backend — un servicio con módulos de dominio

Un **solo proceso** en **Railway**. El core es la parte transversal
(identidad, autorización, pagos/documentos/comunicación por adaptadores,
auditoría/ledger). Cada vertical es un **módulo del mismo servicio** con su
dominio propio y llama al core por **interfaz interna** (llamada en proceso,
no red). Los sistemas externos — PMS, channel manager, pasarela
(Webpay/Mercado Pago), SII/DTE, WhatsApp — entran **solo por puertos**. Un
puerto vacío responde «no configurado» y no simula éxito
(`hotel_inventario/puertos.py` es la prueba vigente).

## 3. Integración — cuatro flujos (diagramas Mermaid)

*2026-11-03 (V1-ISSUE-19): estos cuatro diagramas describen el destino que
AGENTS.md sustituyó por las specs V1; se archivan en
`docs/archivo-no-construccion/diagramas-destino-anterior/`.*

Convención en los cuatro diagramas: **línea continua** = lo que el código hace
hoy; **línea punteada** = enlace que falta o destino propuesto.

1. [flujo-01-acceso-empresa.mmd](../archivo-no-construccion/diagramas-destino-anterior/flujo-01-acceso-empresa.mmd) — hoy: cada
   módulo fija su empresa y niega otra con su propia excepción. Falta: front,
   API y una única puerta de empresa en el núcleo.
2. [flujo-02-reserva-sin-canal.mmd](../archivo-no-construccion/diagramas-destino-anterior/flujo-02-reserva-sin-canal.mmd) — hoy: el
   hotel confirma reserva con cerrojo y sin invocar el puerto de canal. Falta:
   el borde HTTP delante del módulo.
3. [flujo-03-cobro-detenido-en-puerto.mmd](../archivo-no-construccion/diagramas-destino-anterior/flujo-03-cobro-detenido-en-puerto.mmd)
   — hoy: pago en memoria dentro del hotel y `aplicar_resultado_pago` solo en
   las pruebas del núcleo. Falta: el enlace vertical → núcleo y los puertos de
   pago/documento en el núcleo.
4. [flujo-04-core-compartido.mmd](../archivo-no-construccion/diagramas-destino-anterior/flujo-04-core-compartido.mmd) — hoy: cuatro
   verticales (incluido el hotel) con empresa fija copiada, sin compartir
   código. Destino: un solo login y una sola base de pagos por el núcleo.

## 4. Stack — decisión tomada (solo alojamiento por artefacto)

| Capa | Opción | Decisión | Motivo (del repositorio) | Límite de esta elección |
|---|---|---|---|---|
| Front | **Vercel** | **se construye** | Una sola aplicación para Herencia. En esta versión la pantalla es `/hotel`; las otras tres rutas quedan vacías. | Next.js. Spec: `spec-front-vercel.md`. Sin despliegue a producción en este corte. |
| API | contrato | **se construye** | Diez operaciones del hotel, sesión por cookie, idempotencia. | Spec: `spec-api.md`. No es el OpenAPI heredado ni `plataforma/servidor.py`. |
| Backend | **Railway** | **se construye** | Un proceso con núcleo y hotel. | Python, FastAPI, PostgreSQL 17. Spec: `spec-backend-railway.md`. Sin pasarela ni OTA. |

**Artefactos**: el front es `plataforma-salman-herencia-front` en Vercel. El
servicio es `plataforma-salman-herencia-api` en Railway. La decisión del
2026-10-28 fija runtime, framework y base de datos de ese mínimo. Ninguno de
los dos proyectos está creado todavía.

## 5. Lo que sigue sin elegir

- **Adaptadores reales** de pasarela, DTE, Booking, Airbnb y WhatsApp: siguen
  en «no configurado». Elegirlos no es parte de este mínimo.
- **Redis, worker y colas**: fuera de este mínimo.
- **Q-CORE-03** sigue pendiente para retención, recuperación (RPO/RTO), presupuesto y autonomía. No anula PostgreSQL 17, ya elegido para el servicio de Railway.
- **Adaptadores de puertos**: PMS (Q-HOT-01 evalúa exportación), channel
  manager (Q-HOT-02), pasarela de pago y proveedor DTE (Q-CORE-02),
  SII/DTE y WhatsApp Business. Todos siguen como puertos «no configurado».
