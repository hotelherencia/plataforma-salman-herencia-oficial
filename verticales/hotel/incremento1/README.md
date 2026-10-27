# Incremento 1 — inventario local, estados de unidad y cuenta

Fecha: 2026-10-27. **PROPUESTA TÉCNICA**: los ocho defaults de esta sección se toman
para construir, no están ratificados. La firma del propietario en
`backlog/hotel/acta-para-firmar.md` sigue en blanco y corrige después; no detiene este
módulo. Este incremento no firma ninguna Q, no marca Hecha ninguna T003 ni T104/T105/T204,
y no cambia la constitución ni los ADR.

Módulo en memoria y sin red. Hay **dos implementaciones paralelas del mismo alcance**,
cada una con sus pruebas, sin acoplar entre sí:

- `hotel_inventario/` — implementación base de este incremento.
- `hotel_reservas_incremento1/` — segunda implementación del mismo contrato (mismos
  ocho defaults), añadida el 2026-10-27; su empresa fija repite el mismo id
  (`EMP-SINTETICA-001`) para no acoplar las pruebas con el incremento 0.

## Defaults (una sola vez)

1. **Inventario.** La fuente de disponibilidad es el inventario local del servicio. El PMS
   externo es un puerto que devuelve «no configurado»; no se espera a elegir Cloudbeds ni
   Opera.
2. **Dueño.** Una empresa fija (`EMPRESA_FIJA`, id `EMP-SINTETICA-001`). Debajo, un
   establecimiento que le pertenece. El servicio rechaza un establecimiento de otra empresa
   y deniega cualquier llamada con otra empresa (`AccesoDenegado`). `company_id` y
   `establishment_id` del diccionario V1.0 no se fusionan con esta spec.
3. **Estados de unidad.** Limpia, sucia, inspeccionada, bloqueada y fuera de servicio. Se
   venden: limpia, sucia e inspeccionada. No entran al cupo: bloqueada y fuera de servicio.
4. **Reserva.** Disponibilidad y reserva de la última unidad vendible bajo el mismo cerrojo
   del incremento 0: dos reservas simultáneas confirman como máximo una. La empresa que se
   guarda en la reserva es `self._empresa.id`, no el parámetro del llamador.
5. **Cancelación.** Gratuita si se cancela con al menos 48 horas de antelación respecto de la
   llegada. La llegada se toma a las 15:00 del día de inicio (convención técnica, `HORA_LLEGADA`).
   Dentro de esas 48 horas (incluida la no presentación), la cuenta recibe un cargo en
   memoria por la primera noche. No es un cobro.
6. **Cuenta.** La estadía tiene cargos (`asentar_cargo`). Un asiento no se edita: es
   inmutable. Una corrección es un cargo de reverso que referencia al original. Un cargo se
   revierte una sola vez y un reverso no se revierte. No se elige proveedor de boleta y no
   se emite documento tributario.
7. **Canal, pago y documento.** Los cuatro puertos (PMS, canal, pago y documento tributario) devuelven «no configurado». El
   servicio los guarda y no los invoca: la prueba de flujo completo usa un puerto que falla
   si alguien lo llama. El agente no cobra; no hay código de agente. El límite de 0 CLP sigue
   sin ratificar y este módulo no ejecuta autonomía.
8. **Huésped.** Nombre y documento sintéticos, marcados con `sintetico=True`. La ficha oficial
   chilena no bloquea este módulo.

## Flujo de la estadía (diagrama, definición del módulo)

Texto diff-eable. Cada flecha tiene prueba. `[3]` = flecha nueva del bucle 3.

```
consultar_disponibilidad(inicio, fin, personas)
  → reservar → CONFIRMADA (ocupa el rango; rechaza solapes y no vendibles)
  → cancelar(ahora) ── ≥48 h antes de la llegada → CANCELADA, sin cargo
                    └── <48 h → CANCELADA + cargo «primera noche»
check_in(ahora ≥ 15:00 del día de inicio; unidad LIMPIA o INSPECCIONADA) [3]
  → HOSPEDADA + unidad OCUPADA + cargo «Noche» (noche del inicio)
  └── unidad SUCIA → rechazo «unidad no preparada» [3]
asentar_noche(noche, ahora)  (inicio < noche < fin; una sola vez por noche)
  → + cargo «Noche»
check_out(ahora)
  → SALIDA + unidad SUCIA (vendible para reservas futuras)
  → crea TAREA de limpieza PENDIENTE para la unidad [3]
completar_tarea(tarea_id)  (solo tarea PENDIENTE)
  → tarea COMPLETADA + unidad SUCIA → LIMPIA [3]
cargos: asentar_cargo → inmutable; reversar_cargo → reverso (no se edita nada)
puertos PMS / canal / pago / documento: «no configurado», el servicio no los invoca
```

Error encontrado al comparar código y diagrama: el código del bucle 2 permitía
check-in de una unidad SUCIA (porque «sucia se vende» como inventario futuro), sin
tarea de limpieza ni preparación: la especificación (AC-US-HOT-002) no deja
entrar al huésped hasta completar la limpieza. Corrección de este bucle: sucia se
sigue vendiendo para fechas futuras, pero el check-in exige unidad LIMPIA o
INSPECCIONADA, y el check-out crea la tarea de limpieza que la devuelve a LIMPIA.

## Estadía (bucle 2, 2026-10-27)

**PROPUESTA TÉCNICA — 2026-10-27**: reglas de operación hotelera de décadas; se adoptan
para construir, no están ratificadas. Construido en `hotel_inventario`:

1. La reserva confirmada pasa a hospedada y desde ahí a salida; cancelada y rechazada no entran a la estadía.
2. Check-in solo de reserva CONFIRMADA, el día de inicio a las 15:00 o después (`HORA_LLEGADA`); antes se rechaza con «aún no es hora de llegada». El instante llega en el argumento `ahora`; no se usa el reloj del sistema.
3. Al hacer check-in la unidad pasa a OCUPADA: su rango deja de venderse por solape
   (otra reserva solapada no confirma); para fechas futuras libres sigue vendible.
4. El check-in asienta un solo cargo «Noche» por la noche del día de inicio, monto = `tarifa_noche_clp`; un segundo check-in de la misma reserva falla.
5. `asentar_noche(empresa_id, reserva_id, noche, ahora)`: solo con reserva HOSPEDADA, con `inicio < noche < fin` (fin exclusivo) y sin cargo previo de esa noche; la repetición falla con «noche ya asentada».
6. Check-out solo desde HOSPEDADA: la reserva pasa a SALIDA, la unidad a sucia (vendible) y el rango queda libre. El saldo no se borra ni se cobra: con saldo positivo la salida se completa igual, sin llamar al puerto de pago ni al de documento.
7. No hay check-in de unidad bloqueada o fuera de servicio, de reserva cancelada, ni con otra empresa (`AccesoDenegado` igual que antes).
8. Huésped sintético; sin agente, WhatsApp, emisión ni red.

## Qué construye

- `hotel_inventario/dominio.py`: estados, establecimiento, unidad, huésped, reserva, cargo.
- `hotel_inventario/servicio.py`: `ServicioHotelInventario`, con `consultar_disponibilidad`,
  `reservar`, `cambiar_estado_unidad`, `cancelar`, `asentar_cargo`, `reversar_cargo`,
  `cuenta`, `saldo_clp`. Fábricas sintéticas: `hotel_sintetico()` y `servicio_con_una_unidad()`.
- `hotel_inventario/puertos.py`: puertos vacíos que devuelven «no configurado».
- `hotel_reservas_incremento1/` (`dominio.py`, `empresa.py`, `puertos.py`,
  `servicio.py`): misma regla de negocio con la API de empresa + establecimiento
  explícita; `revertir_cargo` deja el saldo en cero sin editar el asiento original
  (el asiento es inmutable; el reverso es un cargo negativo que lo referencia).
- `tests/`: estados, concurrencia de la última unidad, cancelación antes y después de 48 horas,
  cuenta con reverso, acceso de otra empresa denegado, puertos no invocados.

## Cuenta y servicio a habitación (2026-10-27, código completo)

**AT-009 (FR-009)** — la cuenta acumula cargos y anticipos, liquida al salir y no duplica:

```
registrar_pago(monto, clave) → abono inmutable (anticipo o pago); idempotente por clave  [AT-009]
asentar_cargo(concepto, monto, clave) → cargo inmutable; la misma clave no duplica      [AT-009]
saldo_clp = cargos − reversos − pagos                                                    [AT-009]
check_out → SALIDA + liquidación (total cargos, total pagos, saldo) almacenada;
   el saldo no se cobra ni se borra; pago y documento no se invocan                      [AT-009]
recuperación: reversar_cargo → la liquidación refleja el neto                            [AT-009]
```

**AT-007 (FR-007)** — servicio a habitación sobre la interfaz opcional de cafetería:

```
pedir_a_habitacion(items, clave) con reserva HOSPEDADA                                   [AT-007]
  → interfaz no habilitada → «servicio no disponible», sin comanda, sin cargo,
     y sin bloquear reservas                                                             [AT-007]
  → interfaz habilitada (puerto inyectable) → comanda + cargo con referencia
     «pedido:<comanda>» e idempotencia por clave                                         [AT-007]
```

Corrección de semántica incluida: `OCUPADA` ya no quita la unidad de todas las fechas;
el rango ocupado se protege por solape y la unidad sigue vendible para fechas futuras
libres (AC-US-HOT-001-02). Bloqueada, fuera de servicio y mantenimiento sí excluyen
de todo el cupo.

## Devoluciones, extras y cambios (2026-10-27, código completo)

**AC-US-HOT-001-03 (FR-018)** — el dinero de una reserva pagada no se devuelve solo:

```
cancelar(reserva pagada) → CANCELADA; el saldo sigue a favor del huésped,
   sin devolución automática                                            [AC-US-HOT-001-03]
solicitar_devolucion(monto) → PENDIENTE (no mueve dinero; valida contra
   lo pagado sin devolver)                                              [AC-US-HOT-001-03]
autorizar_devolucion(aprobador) → AUTORIZADA (aprobación humana registrada;
   tampoco mueve dinero)                                                [AC-US-HOT-001-03]
ejecutar_devolucion(operacion_confirmada=False) → sigue AUTORIZADA      [AC-US-HOT-001-03]
ejecutar_devolucion(operacion_confirmada=True) → EFECTUADA; el saldo
   refleja la devolución; repetir falla                                 [AC-US-HOT-001-03]
```

**AC-US-HOT-002-03 (FR-019)** — extras con reglas de cantidad visibles:

```
agregar_extra(extra_id, personas, noches) con reserva en cuenta abierta  [AC-US-HOT-002-03]
  → POR_PERSONA_NOCHE: cantidad = personas × noches
    («Desayuno: 2 personas × 3 noches = 6»)                              [AC-US-HOT-002-03]
  → POR_ESTADIA: cantidad = 1 («Botella de bienvenida: 1 por estadía»)   [AC-US-HOT-002-03]
  → cargo «Extra: <nombre>» = cantidad × precio                          [AC-US-HOT-002-03]
```

**AC-US-HOT-001-04 (FR-018)** — previsualizar el cambio de tarifa, no aplicar sin aceptación:

```
previsualizar_cambio(reserva, tarifa_nueva) → PropuestaCambio con tarifa actual,
   noches y diferencia total; NO muta nada                                [AC-US-HOT-001-04]
aplicar_cambio(propuesta, aceptacion=False) → rechazo; sin cargos        [AC-US-HOT-001-04]
aplicar_cambio(propuesta, aceptacion=True) → cargo «Ajuste de tarifa»
   = diferencia total; la tarifa aceptada queda registrada y las noches
   posteriores la usan; repetir o usar propuesta obsoleta falla          [AC-US-HOT-001-04]
```

## Cola local drenada (2026-10-27)

Ids de `specs/002-hotel-reservas-concierge/acceptance.md` cerrados en memoria, cada uno con
prueba que lleva su id en el nombre. Diagrama de flechas:

```
consultar_oferta(fechas, personas, ahora) → OfertaVigente con tarifa,
   política y vigencia; mantenimiento no se oferta                    [AT-001]
cien intentos simultáneos sobre la última unidad → una sola confirmación
                                                                      [AT-005, ADV-001, AC-US-HOT-001-01]
sucia hoy sigue vendible para fechas futuras libres                   [AC-US-HOT-001-02]
mantenimiento abierto impide check-in aunque la limpieza termine;
el cierre autorizado habilita el estado operativo                     [AT-008, AC-US-HOT-002-01]
al terminar la limpieza solo cambia la preparación; las reservas de
otras fechas permanecen intactas                                      [AC-US-HOT-002-02]
el huésped autenticado consulta su reserva; la consulta ajena se
deniega con evidencia; su pedido de cambio queda borrador y escala    [AT-010]
acción con monto > 0 sin aprobación → denegada (política 0 CLP);
aprobación ligada a parámetros exactos, vigencia y uso único          [AT-011]
upsell: propuesta con link a flujo de pago controlado y tarifa del
catálogo; la conversión solo cuenta con pago confirmado               [AT-012]
cada acción registra fuente, regla, actor y resultado; el documento
completo del huésped nunca entra al registro                          [AT-013]
proyección pública de solo lectura (sin datos de huésped); la
escritura desde ella se deniega                                       [AT-014]
el flujo hotelero no importa otras verticales (guarda arquitectónica) [AT-015]
oferta vencida → reserva PENDIENTE sin prometer cupo + transferencia
humana registrada (recepción), sin marcar resuelto                    [AT-017]
cancelar reserva pagada → el dinero queda retenido (sin devolución
automática); otro tenant no cancela                                    [AT-018]
extras: desayuno = personas × noches; botella = 1 por estadía;
otro tenant denegado                                                  [AT-019]
reintento del cambio de tarifa → consulta estado, sin segundo cargo   [AC-US-HOT-001-05]
pedido con cargo asentado pero sin entregar → la cuenta no informa
el servicio como entregado hasta marcarlo                             [AC-US-HOT-002-04]
mismo pedido reintentado → una sola comanda y un solo cargo aunque
el conector responda dos veces (idempotencia por clave)               [AC-US-HOT-002-05]
abrir mantenimiento genera tarea de mantención; el cierre autorizado
la completa (housekeeping + mantención, FR-008 completo)              [AT-008]
concierge local (no envía mensajes; WhatsApp sigue siendo puerto):
  cancelar → deriva a recepción con resumen mínimo y referencia;
     no cancela ni marca resuelto                                     [AC-US-HOT-003-01]
  cancelar y devolver → prepara contexto y escala; no ejecuta ninguna [AC-US-HOT-003-03]
  en atención humana → mensaje adicional no dispara acción autónoma
     ni segunda respuesta de compromiso                               [AC-US-HOT-003-02]
  mismo hecho notificado tres veces → una sola notificación/link      [AC-US-HOT-003-04]
  respuesta con link → no figura como reserva pagada hasta
     evidencia de pago                                                [AC-US-HOT-003-05]
```

## Ejecutar las pruebas

Desde esta carpeta:

```bash
python -m unittest discover -s tests -t . -v
```

Resultado real del 2026-10-27 (cola drenada + H3 + FR-006): `Ran 102 tests`, `OK`, exit 0 (94 previos
+ 20 con id de acceptance, 6 del concierge/H3 y 1 de FR-006).

## Incremento 0 (no roto)

Desde `verticales/hotel/incremento0`, `python -m unittest discover -s tests -t .`
da `Ran 17 tests`, `OK`, exit 0. La instrucción hablaba de 11 pruebas; el conteo real del
directorio es 17 (el archivo `test_estados_unidad.py` añadido después cuenta 6). No se
modificó el incremento 0.

## Issue y Project (GitHub)

Issue creado y vinculado el 2026-10-27 con la cuenta `hotelherencia` (token de `.env`):

- Issue: https://github.com/hotelherencia/plataforma-salman-herencia-oficial/issues/151
  «Incremento 1 — inventario local, estados de unidad y cuenta».
- Project n.º 2 «Project Plataforma Hotel Herencia»: ítem vinculado, estado **Done**
  (pasó por «In Progress»; las 32 pruebas ya estaban en verde al crearse).

Nota: el repo es **privado**; un observador sin acceso a la cuenta `hotelherencia`
no ve ni el repo ni los ítems del tablero. No se cambió el estado de las cinco T003
ni de las tareas de decisión humana.

## Fuera de este incremento

Canal, PMS, pago, documento tributario, adaptadores, migraciones, red, UI, y cualquier paso a
base de datos (bloqueados por Q-CORE-01/02/03 y Q-HOT-01/02/03 sin firma).
