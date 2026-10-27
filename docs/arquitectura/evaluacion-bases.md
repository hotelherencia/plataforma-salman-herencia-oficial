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

## Hueco de stack (qué falta para tener un front, una API y un servicio)

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
