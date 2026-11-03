# Especificación de la operación del hotel V1 — mantenedor, consulta, ocupación e indicadores

**Estado:** REQUISITO PROPUESTO, fechado 2026-11-03 (orden del propietario:
«completar el flujo operativo del hotel para que los usuarios entiendan el
negocio y gestionen habitaciones sin ambigüedades»). Complementa y no
reemplaza a [spec-api-v1.md](spec-api-v1.md) (contrato),
[spec-backend-v1.md](spec-backend-v1.md) y [spec-front-v1.md](spec-front-v1.md):
aquí viven los flujos por rol, las definiciones de métricas y los criterios de
aceptación; el contrato publica las operaciones. Informe de diagnóstico y
evidencia: [`capturas/e2e-2026-11-03/INFORME-operacion.md`](../../capturas/e2e-2026-11-03/INFORME-operacion.md).

Etiquetas: **HECHO DOCUMENTADO** (con fuente en código o documento), **REQUISITO
PROPUESTO** (esta especificación lo define), **DECISIÓN PENDIENTE** (del
propietario; no se inventa), **SUPUESTO** (se asume y se declara).

## 0. Cambio de alcance

- HECHO DOCUMENTADO: `backlog/v1/indice.md` («Limpieza del tablero»,
  2026-10-28) dejó los indicadores HU-HOT-03 **fuera de V1**.
- REQUISITO PROPUESTO (orden del 2026-11-03): entra a V1 un **panel operativo**
  con métricas que se calculan con los datos que V1 ya guarda. Los indicadores
  financieros de HU-HOT-03 (ADR, RevPAR, ingresos por canal) **siguen fuera**
  (ver §4.4, DECISIÓN PENDIENTE D-IND-01/02).

## 1. Roles vigentes y matriz de permisos

HECHO DOCUMENTADO: roles creables en V1 `administrador`, `recepcion`, `caja`
(spec-api-v1 «Gestión de usuarios»); `ROLES_DOCUMENTO = {recepcion,
administrador}` (dominio); configuración de habitaciones y tarifas solo
`administrador` (dominio `ROLES_CONFIGURACION`; spec-api-v1).
DECISIÓN PENDIENTE (D-ROL-01): el dominio reserva los indicadores a
`gerencia`, rol que V1 no crea. Mientras no se decida, nada financiero se
publica (§4.4).

| Capacidad | administrador | recepcion | caja |
|---|---|---|---|
| Ver inventario y ficha de habitación | sí | sí | sí |
| Ver historial de auditoría de la habitación | sí | no (no se envía) | no (no se envía) |
| Alta y edición de habitación (tipo, capacidad) | sí | 403 | 403 |
| Registrar tarifa | sí | 403 | 403 |
| Retirar / reincorporar a operación | sí | 403 | 403 |
| Completar limpieza | sí | sí | 403 |
| Abrir / cerrar mantenimiento | sí | 403 | 403 |
| Buscar reservas por periodo, estado, habitación, texto | sí | sí | sí |
| Detalle de reserva con cuenta (cargos, pagos, saldo) | sí | sí | sí |
| Documento del huésped en búsquedas y detalles | sí | sí | no (no se envía) |
| Ocupación y disponibilidad por periodo | sí | sí | sí |
| Panel de indicadores operativos | sí | sí | sí |
| Caja del día (pagos) | sí | 403 | sí |

Fuente de las filas nuevas: REQUISITO PROPUESTO. Ninguna lectura nueva expone
dinero que el rol no vea ya, ni el documento a `caja`: el detalle de reserva
muestra cargos y pagos de **una** reserva a los tres roles porque los tres ya
pueden asentar cargos y registrar pagos sobre ella (HECHO: `ROLES_PAGO_MANUAL`,
`ROLES_CARGO`). La auditoría se reserva a administrador porque contiene
nombres de operadores (SUPUESTO de mínimo privilegio; DECISIÓN PENDIENTE
D-AUD-01 si otro rol debe verla).

## 2. Mantenedor de habitaciones

### 2.1 Modelo y reglas de integridad

- HECHO DOCUMENTADO: `habitaciones` (`id` PK, `tipo`, `capacidad`,
  `estado_operativo`, `estado_preparacion`, `mantenimiento`, `creado_en`);
  `reservas`, `tarifas` y `tareas_operativas` la referencian por FK sin
  `ON DELETE`, así que la base ya **impide borrar** una habitación con
  registros. La API no publica `DELETE` de habitaciones (y no lo publicará).
- HECHO DOCUMENTADO: la reserva guarda `tarifa_noche_aceptada_clp` y su cargo
  de alojamiento al confirmar; cambiar `tarifas` no altera reservas existentes.
- REQUISITO PROPUESTO: **retiro de operación = baja lógica** con el estado del
  dominio `fuera_de_servicio` (`EstadoUnidad.FUERA_DE_SERVICIO`: «no entra al
  cupo para ninguna fecha»), reversible, con `motivo` y fecha. Nada se borra:
  reservas, cargos, pagos, tarifas y tareas quedan intactos y consultables.
- Campos editables después de existir reservas:

| Campo | ¿Editable? | Efecto en reservas existentes |
|---|---|---|
| `id` | **no** (clave primaria; la referencian reservas, tarifas y tareas) | — |
| `tipo` | sí | ninguno: la reserva no copia el tipo; el histórico muestra el tipo actual (limitación L-HAB-01) |
| `capacidad` | sí | ninguno: la reserva **no guarda cantidad de personas**, así que no se puede validar contra reservas futuras (DECISIÓN PENDIENTE D-HAB-01) |
| tarifa | se **agrega** una tarifa nueva; las existentes no se modifican ni se borran | ninguno: la tarifa aceptada queda congelada |
| servicio (retiro) | sí, con precondición (§2.4) | ninguno sobre el pasado; impide nuevas ventas |
| `estado_operativo`/`estado_preparacion`/`mantenimiento` | solo por sus operaciones (entrada, salida, limpieza, mantenimiento, servicio) | — |

### 2.2 Flujo HAB-ALTA — ingresar una habitación

- **Actor:** administrador. **Precondición:** sesión vigente; el `id` no existe.
- **Datos:** `id` (patrón `^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$`), `tipo` (texto
  1–50, sin espacios a los lados), `capacidad` (entero 1–30).
- **Acción:** `PUT /hotel/habitaciones/{id}` con cabecera `If-None-Match: *`
  (semántica HTTP «crear solo si no existe») e `Idempotency-Key`.
- **Resultado observable:** 200 `{habitacion_id, tipo, capacidad, creada:
  true, cambios: {...}}`; aparece en el inventario como `disponible`/`limpia`,
  sin tarifa (no se ofrece hasta tener una). Fila de auditoría `habitacion`
  · `creada tipo=… capacidad=…`.
- **Errores:** `id` ya existe con `If-None-Match: *` → **409** «la habitación
  ya existe» (nada cambia); id con caracteres no admitidos, tipo vacío o
  capacidad fuera de rango → **422**; sin `Idempotency-Key` → 400; rol
  distinto de administrador → 403; sin sesión → 401.

### 2.3 Flujo HAB-EDICION — editar datos de una habitación existente

- **Actor:** administrador. **Precondición:** la habitación existe (también
  si tiene reservas previas o está fuera de servicio).
- **Acción:** `PUT /hotel/habitaciones/{id}` **sin** `If-None-Match`.
- **Resultado:** 200 con `creada: false` y `cambios` `{campo: [antes,
  después]}` (vacío si no cambió nada). Reservas, tarifas, estados y tareas no
  se tocan. Auditoría `habitacion` · `editada tipo: a→b; capacidad: x→y` o
  `sin cambios`.
- **Compatibilidad:** sin `If-None-Match` el PUT sigue siendo alta-o-cambio
  como en el contrato 2026-10-28 (los clientes existentes no se rompen).

### 2.4 Flujo HAB-SERVICIO — retirar de operación y reincorporar

- **Actor:** administrador. **Acción:** `POST
  /hotel/habitaciones/{id}/servicio {en_servicio: bool, motivo?: str}` con
  `Idempotency-Key`.
- **Retirar (`en_servicio=false`):** precondición: la habitación **no** tiene
  reservas en `confirmada` ni `en_estadia` (de cualquier fecha: una confirmada
  pasada sin check-in también debe resolverse antes). `motivo` obligatorio
  (3–200 caracteres). Efecto en una transacción: `estado_operativo =
  fuera_de_servicio`, guarda `motivo` y fecha (`fuera_de_servicio_desde`);
  `estado_preparacion` y `mantenimiento` se conservan. La oferta la excluye
  (HECHO: `oferta` ya excluye `fuera_de_servicio`) y la entrada la rechaza
  (HECHO: `cobro.entrada`).
- **Errores:** reservas vigentes → **409** con `reservas_vigentes: [ids]` y
  nada cambia (la reasignación de una reserva a otra unidad no existe en V1:
  DECISIÓN PENDIENTE D-HAB-02; hoy se cancela y se vuelve a reservar); sin
  motivo → 422; no administrador → 403; habitación inexistente → 403 (mismo
  criterio que limpieza/mantenimiento: no revela existencia).
- **Reincorporar (`en_servicio=true`):** si estaba `fuera_de_servicio` vuelve
  a `disponible` y se limpia el motivo; si ya estaba en servicio, no cambia
  nada.
- **Respuesta:** 200 `{habitacion_id, en_servicio, estado_operativo, motivo,
  cambio: bool}`. Auditoría `habitacion-servicio` · `retirada: <motivo>` /
  `reincorporada` / `sin cambios`.
- **Distinción operativa:** *mantenimiento* = arreglo temporal con tarea
  (HECHO, spec-api-v1); *fuera de servicio* = retiro de la operación (baja
  lógica), sin tarea. Ambos sacan la unidad del cupo.

### 2.5 Flujo HAB-TARIFA — cambiar la tarifa

- **Actor:** administrador. **Acción:** `PUT /hotel/tarifas` (sin cambio de
  contrato de entrada). Las tarifas son **append-only**: registrar una tarifa
  nueva es la única forma de cambiar el precio; ninguna fila se edita ni borra.
- **Regla de vigencia** (HECHO: `reservas.tarifa_vigente` usa la de mayor
  `fecha_desde`; REQUISITO PROPUESTO: desempate determinista): la tarifa de la
  noche *d* es la fila con `fecha_desde ≤ d < fecha_hasta` de **mayor
  `fecha_desde`**; a igual `fecha_desde`, gana la **registrada más
  recientemente** (`tarifas.creado_en`). Una tarifa nueva sobre un rango ya
  cubierto **reemplaza** el precio de esas noches desde su `fecha_desde`.
- **Efecto en reservas:** ninguno. HECHO: la reserva guarda su tarifa
  aceptada y su cargo; la regla aplica solo a ventas nuevas.
- **Resultado:** 201 con la tarifa; auditoría `tarifa` · `<hab> <desde>→<hasta>
  $<monto>`. La ficha de la habitación lista el historial completo con
  `vigente_hoy` marcado.
- **Errores:** habitación inexistente → 409 (HECHO: FK, test
  `test_integridad_de_base_responde_409_y_no_500`); `fecha_hasta ≤
  fecha_desde` → 400; monto ≤ 0 → 422.
- HECHO DOCUMENTADO de divergencia: el dominio en memoria
  (`configurar_tarifa`) **rechaza** una tarifa superpuesta para la misma
  unidad y fecha; el servicio V1 la acepta y aplica la regla de arriba.
  DECISIÓN PENDIENTE D-TAR-01: si el propietario prefiere la regla del dominio,
  cambiar tarifa exigirá otra operación (cierre de vigencia).

### 2.6 Flujo HAB-FICHA — consultar el inventario y una habitación

- `GET /hotel/habitaciones` (HECHO, 2026-11-03) suma `en_servicio`,
  `motivo_fuera_de_servicio` y `tarifa_vigente_hoy_clp` (null si hoy no hay
  tarifa; `tarifa_noche_clp` se conserva como «última configurada» por
  compatibilidad).
- `GET /hotel/habitaciones/{id}` (nueva), cualquier rol: datos y estados;
  `tarifas` (todas, orden `fecha_desde` desc, `creado_en` desc, cada una con
  `vigente_hoy`); `reservas` de la unidad en cualquier estado (orden `inicio`
  desc; documento solo para `ROLES_DOCUMENTO`); `tareas` (historial);
  `auditoria` solo para administrador (las filas cuyo recurso es la
  habitación). Inexistente → 403.

## 3. Consulta y análisis de reservas

### 3.1 Búsqueda (ampliación de `GET /hotel/reservas`)

HECHO: filtros `fecha`, `estado`, `texto` (spec-api-v1). REQUISITO PROPUESTO:
se agregan, combinables con AND:

- `desde`, `hasta` (periodo, `hasta` exclusivo): la reserva **toca** el periodo
  si `inicio < hasta` y `fin > desde`. Solo uno → cota abierta. `hasta ≤
  desde` → 422.
- `habitacion_id`: igualdad exacta.
- Cada ítem suma `noches`. Sin cambios en permisos ni orden.

### 3.2 Detalle `GET /hotel/reservas/{id}` (nueva)

- **Actor:** cualquier rol. **Resultado:** la reserva (con `documento` según
  rol), `noches`, `tipo` de la habitación, `cargos` (cargo y reverso con
  concepto, monto, referencia y fecha), `pagos` (monto, modo, estado, fecha),
  `cuenta {cargos_netos_clp, pagado_clp, saldo_clp}` con la **misma fórmula
  que la salida** (HECHO: `cobro.salida`, cargo menos reverso menos pagos
  confirmados; se calcula en el servidor, en una sola función) y `liquidacion`
  si existe.
- **Errores:** reserva de otra empresa o inexistente → 403 (HECHO:
  `_reserva_de_la_empresa`).

### 3.3 Qué necesita observar cada rol

| Rol | Pregunta operativa | Dónde |
|---|---|---|
| recepción | ¿Quién llega y sale hoy? ¿Qué llegadas quedaron sin check-in? | Panel (§4) → enlaces a reservas |
| recepción | ¿Qué unidad está libre para estas noches? | Ocupación (§5) y Oferta |
| recepción / caja | ¿Cuánto debe esta reserva antes de la salida? | Detalle de reserva (§3.2) |
| caja | ¿Qué se cobró hoy? | Caja (HECHO) |
| administrador | ¿Qué pasó con esta habitación (reservas, tarifas, cambios)? | Ficha (§2.6) |

## 4. Panel de indicadores operativos — `GET /hotel/indicadores`

### 4.1 Contrato

- **Parámetros:** `desde`, `hasta` (periodo de noches, `hasta` exclusivo;
  por defecto la noche de hoy: `[hoy, hoy+1)`; máximo **92 noches**, si no
  422; `hasta ≤ desde` → 422); `tipo` opcional (tipo de habitación: filtra
  unidades y reservas de ese tipo).
- **Fecha de corte (`hoy`):** fecha del reloj del servidor, igual que la
  cancelación (HECHO: `cobro.cancelar` usa `datetime.now()`). Se devuelve en
  la respuesta como `fecha_corte`.
- **Roles:** cualquiera (no contiene dinero ni documentos).
- **Respuesta:** `{fecha_corte, periodo: {desde, hasta, noches}, filtros,
  hoy: {...}, periodo_indicadores: {...}, no_disponibles: [...]}`; **cada
  indicador** es `{valor, unidad, formula, fuente, limitaciones}`. Un
  indicador sin muestra (denominador 0) vale `null`, nunca 0 (HECHO: regla
  del dominio `IndicadoresDiarios`, «un indicador sin muestra es None»).

### 4.2 Situación de hoy (no depende del periodo)

| Nombre | Fórmula | Unidad | Fuente |
|---|---|---|---|
| `llegadas_hoy` | reservas `confirmada` con `inicio = hoy` | reservas | `reservas` |
| `llegadas_vencidas` | reservas `confirmada` con `inicio < hoy` (no hicieron check-in; V1 no tiene estado *no-show*) | reservas | `reservas` |
| `salidas_hoy` | reservas `en_estadia` con `fin = hoy` | reservas | `reservas` |
| `salidas_vencidas` | reservas `en_estadia` con `fin < hoy` | reservas | `reservas` |
| `en_casa` | reservas `en_estadia` | reservas | `reservas` |
| `habitaciones_total` | habitaciones registradas | unidades | `habitaciones` |
| `habitaciones_ocupadas` | `estado_operativo = ocupada` | unidades | `habitaciones` |
| `habitaciones_vendibles` | sin mantenimiento y fuera de `bloqueada`/`fuera_de_servicio` | unidades | `habitaciones` (regla HECHA de la oferta) |
| `habitaciones_sucias` | `estado_preparacion = sucia` | unidades | `habitaciones` |
| `limpiezas_pendientes` | tareas `limpieza` `pendiente` | tareas | `tareas_operativas` |
| `en_mantenimiento` | `mantenimiento = true` | unidades | `habitaciones` |
| `fuera_de_servicio` | `estado_operativo = fuera_de_servicio` | unidades | `habitaciones` |

Cada conteo de reservas lleva además la lista de `reserva_id` para navegar.

### 4.3 Indicadores del periodo

Definiciones comunes: una **noche** *d* pertenece a la reserva si `inicio ≤ d <
fin_efectivo`; `fin_efectivo = fin`, salvo `finalizada` con liquidación
anterior a `fin` (salida anticipada): `fin_efectivo = fecha de la
liquidación` (HECHO: `liquidaciones.creado_en` es el instante de la salida).
**Unidades-noche** = Σ sobre las noches del periodo de las habitaciones con
`creado_en::date ≤ d` (del tipo filtrado). HECHO: el dominio cuenta todas las
unidades del establecimiento, incluidas fuera de servicio y mantenimiento
(`indicadores_diarios`: «noches vendidas / unidades del establecimiento»).

| Nombre | Fórmula | Unidad | Fuente | Limitaciones |
|---|---|---|---|---|
| `unidades_noche` | ver arriba | unidades-noche | `habitaciones.creado_en` | una habitación retirada sigue contando (fórmula del dominio; D-IND-03) |
| `noches_ocupadas` | noches del periodo con `d ≤ hoy` de reservas `en_estadia` o `finalizada` | noches | `reservas`, `liquidaciones` | refleja estadías reales; noches futuras no cuentan |
| `ocupacion` | `noches_ocupadas / unidades_noche` restringido a noches `d ≤ hoy` | proporción 0–1 | ídem | `null` si el periodo es todo futuro. Equivale a «noches vendidas» del dominio con la diferencia de que V1 no asienta cargos por noche (SUPUESTO: noche de estadía = noche vendida) |
| `noches_reservadas` | noches del periodo de reservas `confirmada`, `en_estadia` o `finalizada` | noches | `reservas`, `liquidaciones` | incluye confirmadas pasadas sin check-in |
| `ocupacion_reservada` | `noches_reservadas / unidades_noche` | proporción 0–1 | ídem | es ocupación **comprometida** (prospectiva), no realizada |
| `reservas_canceladas` | reservas `cancelada` cuyo rango toca el periodo, y sus noches | reservas, noches | `reservas` | la fecha de cancelación no está en `reservas` (solo en `auditoria`); el periodo se mide por fecha de estadía |
| `reservas_registradas` | reservas creadas (`creado_en::date`) dentro del periodo, por estado actual | reservas | `reservas.creado_en` | — |

Serie diaria: por noche, `unidades`, `ocupadas` (si `d ≤ hoy`), `reservadas`.

### 4.4 Fuera del panel (no se calcula; se declara en `no_disponibles`)

| Indicador | Motivo |
|---|---|
| ADR, RevPAR, ingresos de hospedaje | DECISIÓN PENDIENTE D-IND-01: el dominio los calcula con cargos de noche netos y los reserva a `gerencia` (D-ROL-01); V1 asienta un cargo único de alojamiento al reservar (HECHO: `reservas.crear_reserva`), cuyo reconocimiento por noche no está definido. Presentarlo sería inventar la fórmula. |
| Ingresos por canal | HECHO: «el modelo no registra canal de origen» (dominio). |
| Pagos y caja del periodo | ya cubierto por `GET /hotel/caja` por día (caja/administrador). Un acumulado por periodo es DECISIÓN PENDIENTE D-IND-02 (rol y conciliación: los pagos manuales no están conciliados). |
| No-show | V1 no tiene ese estado; se informa `llegadas_vencidas`. |
| Objetivos/metas | HECHO (HU-HOT-03): «los objetivos numéricos se ratifican con la gerencia y no se inventan». |

## 5. Ocupación y disponibilidad — `GET /hotel/ocupacion`

- **Parámetros:** `desde`, `hasta` (noches, `hasta` exclusivo; por defecto las
  14 noches desde hoy; máximo **62**; `hasta ≤ desde` → 422). **Roles:** cualquiera. **Fecha de corte:** `hoy` del
  servidor.
- **Respuesta:** `{fecha_corte, noches: [fechas], habitaciones: [{habitacion_id,
  tipo, capacidad, estado_operativo, estado_preparacion, mantenimiento,
  en_servicio, noches: [{fecha, estado, reserva_id?, tarifa_noche_clp?,
  motivo?}], reservas: [{reserva_id, inicio, fin, estado, huesped_nombre}]}],
  resumen: [{fecha, disponibles, ocupadas, no_vendibles}]}`.
- **Estado de cada noche** (en el servidor; el front solo pinta):
  1. hay reserva `confirmada` o `en_estadia` que la contiene → ese estado y su
     `reserva_id` (es lo que protege el constraint `reservas_sin_solape`);
  2. si no, y `d < hoy`: `finalizada` (con su reserva, rango efectivo) o
     `sin_ocupar`;
  3. si no (`d ≥ hoy`): unidad no vendible hoy (mantenimiento, `bloqueada`,
     `fuera_de_servicio`) → `no_vendible` con `motivo`; sin tarifa vigente esa
     noche → `sin_tarifa`; si no → `disponible` con `tarifa_noche_clp`.
- Las reservas `cancelada` del periodo vienen en `reservas` y **no pintan
  noches** (HECHO: sueltan el cupo).
- **Consistencia con la oferta** (criterio de aceptación): una noche
  `disponible` de una unidad con capacidad ≥ *p* aparece en `GET
  /hotel/oferta?inicio=d&fin=d+1&personas=p`, y una noche `confirmada`/
  `en_estadia`/`no_vendible`/`sin_tarifa` no.
- **Limitación L-OCU-01:** el mantenimiento y el fuera de servicio son estados
  actuales sin rango de fechas (HECHO: columna booleana / estado); se
  proyectan a todas las noches futuras, igual que la oferta. Programar
  mantenimiento por fechas es DECISIÓN PENDIENTE D-OCU-01.

## 6. Criterios de aceptación (verificables)

| Id | Criterio | Prueba |
|---|---|---|
| CA-HAB-01 | Alta con `If-None-Match: *` crea; repetirla con otra clave → 409 sin cambios | unittest + E2E |
| CA-HAB-02 | Edición de tipo/capacidad de una habitación con reserva previa no altera la reserva (tarifa, estado, rango) y deja auditoría con antes→después | unittest + E2E |
| CA-HAB-03 | Tarifa nueva sobre rango cubierto cambia la oferta y no la reserva existente; desempate por registro más reciente | unittest + E2E |
| CA-HAB-04 | Retiro con reserva vigente → 409 con ids; sin reservas vigentes → `fuera_de_servicio`, fuera de la oferta, historial intacto; reincorporar la devuelve | unittest + E2E |
| CA-HAB-05 | No existe `DELETE` de habitaciones; la base impide borrar una con reservas | unittest |
| CA-HAB-06 | Recepción y caja reciben 403 en alta, edición, tarifa y servicio; leen inventario y ficha sin auditoría | unittest + E2E |
| CA-RES-01 | Búsqueda por periodo y habitación combina con AND; `hasta ≤ desde` → 422 | unittest + E2E |
| CA-RES-02 | Detalle de reserva devuelve cuenta con el mismo saldo que exige la salida; caja no ve el documento | unittest + E2E |
| CA-OCU-01 | Estados por noche según §5, canceladas listadas sin pintar, consistentes con la oferta | unittest + E2E |
| CA-IND-01 | Indicadores con fórmula/fuente/unidad; `null` sin muestra; valores iguales a un conteo independiente sobre datos sintéticos | unittest + E2E |
| CA-IND-02 | ADR/RevPAR/ingresos no se publican; figuran en `no_disponibles` con motivo | unittest |
| CA-NAV-01 | Desde el menú: Panel, Ocupación, Habitaciones (ficha, edición, tarifa, retiro), Reservas (periodo, detalle) operables según rol | E2E (navegador) |

## 7. Decisiones pendientes (no se inventan)

| Id | Pregunta | Mientras tanto |
|---|---|---|
| D-ROL-01 | ¿Se crea el rol `gerencia` de HU-HOT-03, o los indicadores financieros los ve `administrador`? | sin indicadores financieros |
| D-IND-01 | ¿Cómo se reconoce el ingreso de hospedaje por noche (cargo único al reservar vs. noche asentada)? | sin ADR/RevPAR |
| D-IND-02 | ¿Pagos acumulados por periodo, para qué rol, y con qué advertencia de no conciliación? | caja por día |
| D-IND-03 | ¿Una habitación retirada sale del denominador de ocupación desde su retiro? | fórmula del dominio (cuenta) |
| D-HAB-01 | ¿Se registra la cantidad de personas en la reserva para validar cambios de capacidad? | capacidad editable sin validar contra reservas |
| D-HAB-02 | ¿Se habilita reasignar una reserva a otra habitación (para retirar una unidad con reservas)? | cancelar y volver a reservar |
| D-HAB-03 | ¿Catálogo cerrado de tipos de habitación? | texto libre 1–50 |
| D-TAR-01 | ¿Tarifas superpuestas: reemplazo (V1) o rechazo (dominio)? | reemplazo con regla §2.5 |
| D-OCU-01 | ¿Mantenimiento programado por fechas? | estado actual proyectado |
| D-AUD-01 | ¿Otros roles ven la auditoría de la habitación? | solo administrador |
