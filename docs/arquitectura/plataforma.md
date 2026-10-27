# Arquitectura funcional y stack de la plataforma — Grupo Salman / Herencia

**PROPUESTA TÉCNICA — 2026-10-27** (no ratificada; el acta sigue sin firma y
corrige después). Corrección del mismo día tras contraste con el código: dos
bloques separados, **hecho de código** (verificado, con pruebas) y **destino**
(propuesta). Las specs y la constitución no se editan. No despliega nada: no
hay proyectos en Vercel ni en Railway todavía, ni cobros, ni emisiones, ni
llamadas a sistemas externos.

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

Consecuencia: hoy **no hay front, no hay API (borde HTTP) y no hay proceso
backend**. Esas palabras nombran el destino, no un artefacto existente.

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

Convención en los cuatro diagramas: **línea continua** = lo que el código hace
hoy; **línea punteada** = enlace que falta o destino propuesto.

1. [flujo-01-acceso-empresa.mmd](flujo-01-acceso-empresa.mmd) — hoy: cada
   módulo fija su empresa y niega otra con su propia excepción. Falta: front,
   API y una única puerta de empresa en el núcleo.
2. [flujo-02-reserva-sin-canal.mmd](flujo-02-reserva-sin-canal.mmd) — hoy: el
   hotel confirma reserva con cerrojo y sin invocar el puerto de canal. Falta:
   el borde HTTP delante del módulo.
3. [flujo-03-cobro-detenido-en-puerto.mmd](flujo-03-cobro-detenido-en-puerto.mmd)
   — hoy: pago en memoria dentro del hotel y `aplicar_resultado_pago` solo en
   las pruebas del núcleo. Falta: el enlace vertical → núcleo y los puertos de
   pago/documento en el núcleo.
4. [flujo-04-core-compartido.mmd](flujo-04-core-compartido.mmd) — hoy: cuatro
   verticales (incluido el hotel) con empresa fija copiada, sin compartir
   código. Destino: un solo login y una sola base de pagos por el núcleo.

## 4. Stack — decisión tomada (solo alojamiento por artefacto)

| Capa | Opción | Decisión | Motivo (del repositorio) | Límite de esta elección |
|---|---|---|---|---|
| Front | **Vercel** | **se usa (destino)** | Una sola aplicación para Herencia con cuatro módulos de vertical: el front es un artefacto desplegable único y sin estado de negocio; encaja con «un solo front, cuatro verticales». | Solo fija dónde vivirá el artefacto. No elige runtime ni framework, no crea el proyecto, no despliega nada. |
| API + Backend | **Railway** | **se usa (destino)** | Un solo servicio core+verticales con puertos vacíos: Railway alojaría el proceso único y sus variables de entorno; no se inventa un segundo backend por vertical. | Solo fija dónde vivirá el artefacto. Sin runtime, sin persistencia, sin proyecto creado. |

**Artefactos**: el **front** viviría en Vercel
(`plataforma-salman-herencia-front`). El **servicio único core+verticales**
viviría en Railway (`plataforma-salman-herencia-api`). Ninguno existe en
ninguna de las dos plataformas: esta decisión solo fija dónde viviría cada
artefacto. Un alojamiento sin runtime ni base de datos no alcanza para
crearlos.

## 5. Lo que sigue sin elegir

- **Runtime y framework** del servicio y del front: se fijan al iniciar el
  primer T-IMP; los módulos en memoria de hoy son la especificación ejecutable
  del dominio.
- **Motor de base de datos**: decisión aparte; no es sinónimo de Q-CORE-03.
  Hoy no hay persistencia seleccionada.
- **Q-CORE-03** (specs/000-core/spec.md): solo responsables de datos,
  retención, recuperación (RPO/RTO), presupuesto y autonomía. No elige motor
  de base de datos.
- **Adaptadores de puertos**: PMS (Q-HOT-01 evalúa exportación), channel
  manager (Q-HOT-02), pasarela de pago y proveedor DTE (Q-CORE-02),
  SII/DTE y WhatsApp Business. Todos siguen como puertos «no configurado».
