# Dictamen: ¿plataforma? — 2026-10-28 (leído del código, no del documento viejo)

Criterio: una plataforma es un **sistema** con frente, API y núcleo
compartido. Veredicto a la fecha: **no es una plataforma** — son cinco
bibliotecas de dominio en memoria, cada una con su propia empresa, más un
destino escrito (Vercel/Railway) donde no hay proyecto. Las siete filas del
criterio, cada una con ruta de código o con «no existe»:

1. **Front que una persona abra y que solo hable con la API propia** → *no
   existe*. No hay `package.json` ni aplicación web en el árbol
   (`find . -name package.json` → vacío, 2026-10-28).
2. **API HTTP que autentique la empresa en cada request** → *no existe*.
   `docs/definicion-herencia/contratos/openapi.yaml` se declara «Especificación
   de API, no servicio desplegado» (líneas 4–9), con servidor ficticio
   `herencia-api.example.invalid` y `x-specification-status:
   PROPOSED_NOT_IMPLEMENTED`. Ningún proceso HTTP en el código.
3. **Proceso backend que cargue el núcleo y el hotel en el mismo servicio** →
   *no existe*. Los cinco módulos (`core/incremento1/nucleo`,
   `verticales/{hotel,cafeteria,inmobiliaria,constructora}/incremento1/*`) se
   invocan solo desde sus `tests/`; sin empaquetado ni servicio.
4. **Una sola puerta de empresa (la vertical usa la del núcleo)** → *no existe*.
   Cinco `EMPRESA_FIJA` y cinco `class AccesoDenegado`, una por módulo
   (`core/incremento1/nucleo/empresa.py:11`,
   `verticales/hotel/incremento1/hotel_inventario/empresa.py:9` y equivalentes
   en cafeteria, inmobiliaria y constructora). Ninguna vertical importa
   `nucleo`: búsqueda de imports en `core/` y `verticales/` — el único enlace
   es `verticales/hotel/incremento1/tests/test_cobro_nucleo.py`, una prueba.
5. **Cobro y documento solo por el núcleo; el hotel no guarda un pago que el
   núcleo no aceptó** → *no existe como sistema*. El hotel guarda `pagos` en su
   lista (`hotel_inventario/servicio.py`, `_pagos`); el punto de inyección
   `cobros: RegistroCobro` (`servicio.py:90–93,138`) existe y el servicio no
   guarda el pago si el cobrador rechaza — pero ese cobrador real nunca está
   conectado: solo lo ejercen pruebas. El núcleo no tiene puertos de pago,
   documento ni comunicación (`core/incremento1/nucleo/servicio.py` solo tiene
   `Conector` con `placeholder=True`).
6. **Estado que sobreviva al reinicio (caja y conciliación)** → *no existe*.
   Toda la persistencia es memoria de proceso; terminada la corrida no queda
   caja ni conciliación.
7. **Sistemas externos solo detrás de puertos que respondan «no configurado»**
   → *parcial*. Puertos del hotel (`hotel_inventario/puertos.py`: PMS, canal,
   pago, documento) responden «no configurado» sin simular éxito; el núcleo no
   tiene puertos que cerrar.

**Stack**: tres descripciones, ninguna corriendo — (a) hecho: Python 3 solo
biblioteca estándar; (b) `specs/*/plan.md`: Python/FastAPI/Next.js/PostgreSQL,
propuesta no aprobada; (c)
`docs/definicion-herencia/sdd/ADR-001-stack-propuesto.md`:
TypeScript/Next.js 16/Node 24/PostgreSQL 17, estado PROPUESTA (25-10-2026).

**Hueco frente al manual**: el recorrido mínimo (configurar habitación y
tarifa → consultar y reservar → cobrar y confirmar → estadía → salida → caja
y conciliación) tiene en código consultar, reservar, operar y salir en
memoria; no configura tarifas (son constantes), no cobra por el núcleo y no
hay por dónde entrarle una persona.

*Estas siete filas describen el repositorio antes del corte del proceso. El
estado actual (tras el corte `plataforma/` del mismo día) está en la tabla
«Dictamen de plataforma — 2026-10-28», más abajo en este documento.*

---

# Evaluación de la definición contra el manual — 2026-10-27

Criterio del manual de comprensión (27-10-2026, Mijaíl y Cristóbal): la primera
puesta en marcha es Hotel Herencia bajo Herencia SpA con 17 habitaciones;
Cafetería Fadwa es fase 2; inmobiliaria y constructora vienen después, cada una
con aprobación. El resultado mínimo de la primera versión es un recorrido de
extremo a extremo: configurar habitaciones y tarifas, consultar y reservar,
cobrar y confirmar, operar la estadía, registrar la salida, y dejar caja y
conciliación trazables.

## Hecho (lo que el código hace hoy, con ruta)

1. `core/incremento1/nucleo` — empresa fija al construir el servicio; conector
   con permisos y bloqueo de placeholder; deuda; aprobaciones con
   monto/parámetros/vigencia/uso único; `aplicar_resultado_pago` idempotente.
   Ejercido solo por `core/incremento1/tests/test_AC_US_CORE_ids.py` (9 pruebas
   OK); sin uso desde ninguna vertical.
2. `verticales/hotel/incremento1/hotel_inventario` — inventario local único;
   `consultar_oferta` con `tarifa_noche_clp` y `POLITICA_CANCELACION`
   constantes; confirmación con cerrojo (máxima una confirmación simultánea);
   estadía, check-in, housekeeping; `cuenta`, `pagos` y
   `pedir_a_habitacion` en el mismo módulo; puertos que responden
   «no configurado». Suite de `verticales/hotel/incremento1`: 102 pruebas OK.
3. `verticales/cafeteria/incremento1/cafeteria_mesas_pos` — mesas con QR,
   pedidos con comanda única e imputación sin doble cobro (19 pruebas OK).
4. `verticales/inmobiliaria/incremento1/inmobiliaria_comercial` — leads,
   reserva única de unidad, cotización versionada, promesas y cuotas con
   imputación idempotente (20 pruebas OK).
5. `verticales/constructora/incremento1/constructora_obra` — avance por
   partida, presupuesto versionado, órdenes y recepciones idempotentes,
   inspección sin cierre por el reportante (14 pruebas OK).
6. `verticales/hotel/incremento0` (17 pruebas OK) y
   `verticales/hotel/incremento1/hotel_reservas_incremento1` (copia paralela
   del mismo contrato del hotel) — pruebas y copia fuera de la arquitectura.
7. Sin imports cruzados: ninguna vertical importa `nucleo`; la única
   importación de `nucleo` está en las pruebas del propio núcleo (verificado
   por búsqueda de imports en `core/` y `verticales/`).
8. Empresa y acceso repetidos por módulo: cada uno de los cinco módulos
   (`nucleo`, `hotel_inventario`, `cafeteria_mesas_pos`,
   `inmobiliaria_comercial`, `constructora_obra`) define su propia
   `EMPRESA_FIJA` y su propia `class AccesoDenegado`.
9. El cobro del hotel no pasa por el núcleo: `pagos`, `cuenta` y
   `pedir_a_habitacion` viven en `hotel_inventario/servicio.py`; el
   `aplicar_resultado_pago` del núcleo corre solo en las pruebas del núcleo; el
   núcleo no tiene puertos de pago ni de documento.
10. Solo biblioteca estándar, sin UI ni red: los módulos se invocan únicamente
    desde pruebas; no hay front, ni borde HTTP, ni proceso backend.

## Destino (lo que el manual y plataforma.md prometen y el código no enlaza)

1. Orden de fases del manual: primero Hotel Herencia (Herencia SpA, 17
   habitaciones), Cafetería Fadwa en fase 2, inmobiliaria y constructora
   después con aprobación cada una. El código tiene las cuatro verticales
   construidas en paralelo y con el mismo formato, sin orden de fases y con
   datos sintéticos sin límite de 17 habitaciones.
2. Recorrido mínimo V1 del manual (configurar habitaciones y tarifas →
   consultar y reservar → cobrar y confirmar → operar la estadía → registrar
   la salida → caja y conciliación trazables): hay consultar, reservar, operar
   y salir en `hotel_inventario`; no hay operación de configurar habitaciones y
   tarifas (fixtures sintéticos; tarifa y política como constantes), ni caja ni
   conciliación persistente.
3. Cobrar y confirmar con pasarela y documento tributario (spec 002, FR-004):
   prometido; en código el cobro se detiene en memoria dentro del hotel y los
   puertos responden «no configurado».
4. Core compartido sin duplicarlo (spec 002, FR-015; constitución I;
   plataforma.md): ninguna vertical importa el núcleo y cada una repite su
   `EMPRESA_FIJA` y su `AccesoDenegado` (cinco copias, cinco puertas); el
   enlace vertical → núcleo no está escrito.
5. Un solo login y una sola base de pagos para las cuatro verticales
   (plataforma.md, flujo-04, incluido el hotel): prometido; hoy cada módulo
   fija su propia empresa y ningún vertical usa la del núcleo.
6. Front único con módulos `/hotel`, `/cafeteria`, `/inmobiliaria`,
   `/constructora` (plataforma.md destino): no hay código de front ni de
   login.
7. API única que reconoce la empresa en cada request (plataforma.md destino):
   no hay borde HTTP; la verificación de empresa ocurre solo dentro de las
   pruebas de cada módulo.
8. Servicio único core+verticales donde la vertical llama al núcleo por
   interfaz interna (plataforma.md destino): no hay proceso desplegable ni
   interfaz interna escrita.
9. Puertos del núcleo con adaptadores de pagos, documentos tributarios y
   comunicación (specs/000-core; plataforma.md): el núcleo no tiene puertos;
   los puertos «no configurado» existen en las verticales; no hay adaptadores
   Webpay/Mercado Pago, SII/DTE ni WhatsApp.
10. Sincronización de disponibilidad y reservas con Booking y Airbnb (spec 002,
    FR-003): prometida; el puerto de canal del hotel no se invoca y no hay
    channel manager.

## Hueco de stack

La decisión del 2026-10-28 (`spec-front-vercel.md`, `spec-api.md`, `spec-backend-railway.md`) elige runtime, framework y PostgreSQL 17. Los puntos 1 a 4 de abajo describen el árbol al 2026-10-27 y ya no frenan esa construcción. `plataforma/servidor.py` no los cierra.

1. Front: falta la aplicación web (rutas `/hotel`, `/cafeteria`,
   `/inmobiliaria`, `/constructora`, login y sesión) y todo runtime que la
   sirva; la decisión documentada solo fija dónde viviría en Vercel — no hay
   proyecto creado ni despliegue.
2. API: falta el borde HTTP (framework, rutas, serialización, autenticación de
   sesión); el runtime no está elegido.
3. Servicio: falta el proceso desplegable (runtime/framework, empaquetado y
   configuración por entorno); la decisión documentada solo fija dónde viviría
   en Railway — no hay proyecto creado.
4. Persistencia: falta elegir y montar el motor de datos; los datos viven en
   memoria dentro de cada corrida de pruebas, y sin persistencia no hay caja
   ni conciliación trazables entre corridas.
5. Enlace interno vertical → núcleo: falta la interfaz en proceso; hoy hay
   cinco `EMPRESA_FIJA` y cinco `AccesoDenegado`, uno por módulo.
6. Puertos del núcleo: faltan los puertos de pago, documento tributario y
   comunicación en el núcleo, con sus adaptadores y contratos; hoy el
   «no configurado» solo existe en las verticales.
7. Caja y conciliación: falta lectura bancaria y cierre de caja persistente; el
   ledger del núcleo es en memoria y el hotel no lo usa.

## Dictamen de plataforma — 2026-10-28 (leído del código)

Este dictamen sustituye, para las filas 2, 3 y 4, la evaluación de la sección
«Hueco de stack» del 2026-10-27, que ya no describe el repositorio. Las rutas
son del árbol de trabajo. «Cumplida en código» significa que una prueba lo
ejerce; no significa que esté desplegado ni que exista persistencia.

| # | Criterio | Estado | Ruta y evidencia | Límite |
|---|---|---|---|---|
| 1 | Front que una persona abre y que solo habla con la API propia | **No existe** | `find . -name package.json` devuelve 0; no hay aplicación web | Fila del siguiente corte |
| 2 | API HTTP que autentica la empresa en cada request | **Cumplida en código** | `plataforma/servidor.py` (`Manejador._empresa`, `do_GET`, `do_POST`); 401 sin token o con token desconocido (`plataforma/tests/test_api_hotel.py`) | Token sintético en código; no es la identidad del núcleo (FR-001 de specs/000-core, sin implementar) |
| 3 | Proceso backend que carga núcleo y hotel en el mismo servicio | **Cumplida en código** | `plataforma/servidor.py` (`construir_aplicacion` crea `Nucleo` y `ServicioHotelInventario` en el mismo proceso); arranque `python3 -m plataforma.servidor --puerto 8080` | Un solo módulo de vertical; sin empaquetado ni configuración por entorno |
| 4 | Una sola puerta de empresa: la vertical usa la del núcleo | **Cumplida en el proceso; residual en el código** | `construir_hotel` pasa `empresa=nucleo.empresa` y rechaza establecimientos de otra empresa (prueba `test_establecimiento_de_otra_empresa_no_se_carga`) | `verticales/hotel/incremento1/hotel_inventario/empresa.py` conserva su `EMPRESA_FIJA` como valor por defecto para sus pruebas aisladas; las otras cuatro verticales siguen con su copia |
| 5 | Cobro y documento solo por el núcleo | **Cobro: cumplida en código. Documento: no existe** | `ServicioHotelInventario.registrar_pago` llama a `cobros` (el núcleo) y no guarda si el núcleo rechaza; prueba HTTP `test_si_el_nucleo_rechaza_el_cobro_el_hotel_no_lo_guarda`. El núcleo no tiene puerto de documento | Con `cobros` omitido el hotel sigue cobrando solo (compatibilidad de las pruebas del incremento 1) |
| 6 | Estado que sobrevive al reinicio (caja y conciliación) | **No existe** | Todo vive en memoria; reservas, pagos y efectos se pierden al reiniciar el proceso | Siguiente corte |
| 7 | Sistemas externos solo detrás de puertos «no configurado» | **Cumplida en código** | `hotel_inventario/puertos.py` (`NO_CONFIGURADO`); `test_puertos_no_invocados.py` comprueba que el flujo no los invoca; el proceso no llama a ningún sistema externo | Sin adaptadores; el núcleo no tiene puertos de pago, documento ni comunicación |

**Dictamen:** hay una plataforma mínima ejecutable en un proceso (filas 2, 3 y
una parte de la 4), con un único punto de cobro que es el núcleo. **No hay
plataforma completa:** falta el front (1), falta la persistencia (6) y la
emisión documental no existe (5). La fila 4 queda cumplida en el proceso, no
en el código de cada vertical.

**Stack — decisión del propietario, 2026-10-28.** Esta decisión prevalece sobre
el párrafo anterior y sobre la sección «Hueco de stack». El mínimo es front
Next.js en Vercel, API según `spec-api.md`, backend Python/FastAPI/PostgreSQL 17
en Railway. `plataforma/servidor.py` no cumple esas especificaciones: un token
en código no es la sesión, y la memoria del proceso no es PostgreSQL. ADR-001
sigue en propuesta en lo que junta front y API en un solo Next.js.

**Siguiente corte:** crear los tres artefactos de `spec-front-vercel.md`,
`spec-api.md` y `spec-backend-railway.md`. El hotel es el primer módulo. No
contar `plataforma/servidor.py` como fila cumplida.

**Avance del corte (2026-10-28) — H1 verificado.** El backend real está en
`servicio/` (FastAPI + psycopg v3 + uvicorn; configuración solo por variables
de entorno; migraciones SQL numeradas en `servicio/migraciones/`): arranca con
núcleo y hotel de la misma empresa, rechaza el arranque si el hotel trae otra
(`ErrorArranque` → `SystemExit`) y responde `/salud` 200. Evidencia: 6 pruebas
OK en `servicio/tests/test_h1.py`, humo real del proceso y las 181 pruebas del
dominio sin roturas; arranque con `.venv/bin/python -m servicio`. Gobiernan
las specs V1 (`spec-api-v1.md`, `spec-backend-v1.md`, `spec-front-v1.md`) y el
backlog de construcción vive en `backlog/v1/`.

**H2 de sesión (2026-10-28, verificado).** `POST/DELETE/GET /sesion` sobre
PostgreSQL local (16; el 17 llega con Railway): clave solo como hash argon2id,
administrador inicial desde variables de entorno al arrancar (ningún SQL con
credenciales), cookie `sid` HttpOnly/SameSite=None (Secure solo si
`COOKIE_SEGURA=1`), sesión server-side revocable; 401 sin sesión o con clave
mala; la regla 403 de empresa ajena se resuelve antes que cualquier consulta
de existencia. Evidencia: 7 pruebas en `servicio/tests/test_h2.py`, humo real
contra la base y 181 del dominio sin roturas.

**H3 de reserva persistente (2026-10-28, verificado).** Habitaciones, tarifas
y reservas viven en PostgreSQL: `PUT /hotel/habitaciones/{id}` y
`PUT /hotel/tarifas` solo administrador; `GET /hotel/oferta` con vigencia de
15 minutos; `POST /hotel/reservas` transaccional con constraint de exclusión
`reservas_sin_solape` (btree_gist) — la carrera de 100 requests sobre la
última unidad dejó 1 reserva y 99 con 409, sin sobreventa en la base; la
tarifa aceptada queda congelada en la reserva; la idempotencia por clave
repite respuesta con el mismo cuerpo y responde 409 con cuerpo distinto.
Evidencia: 7 pruebas en `servicio/tests/test_h3.py`, humo real y 181 del
dominio sin roturas.

**H4 de cobro y estadía (2026-10-28, verificado).** `POST
/hotel/reservas/{id}/pagos`: el efecto lo registra el núcleo (si rechaza, no
hay pago) y queda durable en `efectos_nucleo`; `modo="manual"` es caja en
efectivo/transferencia (sin banco ni conciliación) y `modo="pasarela"` sin
adaptador responde 503 con estado pendiente. `POST .../entrada` exige
habitación lista; `POST .../salida` liquida con saldo 0 y registra la
liquidación; `GET /hotel/caja?fecha` lista los pagos del día ligados a
reserva (rol caja/administrador). La idempotencia por clave ahora cubre toda
mutación (PUT incluidos): mismo cuerpo repite, otro cuerpo 409. Una reserva
ajena o inexistente responde 403 sin revelar cuál es el caso. Evidencia: 10
pruebas en `servicio/tests/test_h4.py`, humo real del flujo completo y 181
del dominio sin roturas.

**H6 del front (2026-10-28, verificado con navegador).** `front/`
(Next.js, mínimo funcional — no hay diseño visual definido): login contra
`POST /sesion` (cookie HttpOnly puesta por la API), las siete pantallas del
hotel leyendo y escribiendo solo por `API_BASE_URL`, rutas de cafetería,
inmobiliaria y constructora vacías, y la regla dura cumplida: con la API
apagada el front muestra «La API no está disponible: nada se puede leer ni
confirmar» y no confirma operación alguna. CORS restringido a
`ORIGEN_FRONT`; cookie `Secure` activa (Chrome exige `Secure` con
`SameSite=None`). Verificado con Playwright/Chrome contra el servicio real.

**Maduración y H5 (2026-10-28, verificado).** Validación de los datos que se
consumen (límites pydantic: montos, capacidades, claves, modos → 422;
errores de integridad → 409, sin 500). Diseño seguro: sesiones con
expiración (`SESSION_HORAS`, por defecto 12), freno de fuerza bruta en login
(5 fallos en 5 minutos → 429, por IP y usuario), CORS restringido a
`ORIGEN_FRONT`, cabeceras `X-Content-Type-Options`/`X-Frame-Options`/
`Referrer-Policy`. Contrato: `/openapi.json` (OpenAPI 3.1 servido por el
backend) verificado contra las 10 operaciones. Imputación: tabla `auditoria`
con actor, acción, recurso y resultado en reserva, pago, entrada, salida y
login. H5: prueba de reinicio real — el proceso A registra reserva y pago,
se termina, el proceso B (misma base) lee la caja del día y la ocupación.
Backend maduro: 39 pruebas del servicio y 181 del dominio en verde.
