# Decisiones pendientes V1 — brief para el propietario

**ACTUALIZACIÓN 2026-11-06 — OLA DE DECISIONES RATIFICADA** («todas las ★», orden
«adelante»). Construidas en esta fecha: §1 (D-ENT-01), §2 (roles), §3 (tarifa
noche a noche), §4 (ingresos para administrador), §5a (personas), §6a+c
(carga idéntica 409 y denominador sin fuera_de_servicio), §7 (mantener
solicitud con aprobación humana). Pendientes: §5b/c (reasignación y catálogo,
a pedido), §6b/d (mantenimiento programado y auditoría por rol, a pedido),
ADR/RevPAR (D-IND-02), §8 D-AGT-02 (proveedor) y D-AGT-03..06 en sus valores
por defecto de la spec salvo ajuste. Los detalles de implementación de cada
una están en `backlog/v1/indice.md` §«Ola de decisiones 2026-11-06».

**2026-11-03.** Compendio de las decisiones de negocio abiertas del backlog V1
(GitHub #296, #304, #305, #297, #298, #299, #308 y #316). Para cada una:
comportamiento actual con evidencia (HECHO), opciones y una recomendación
marcada como PROPUESTA. Nada aquí está decidido: se implementa lo que el
propietario ratifique, en el orden en que lo ratifique.

## 1. D-ENT-01 — regla de fecha/hora y documento en entrada y salida (#296)

> Hechos ejecutables (2026-11-06): `servicio/tests/test_caracterizacion_decisiones.py`
> (6 pruebas que documentan el comportamiento vigente; avisarán en rojo si una
> decisión lo cambia). La salida anticipada no prorratea: la reserva finaliza
> con su fin original y el precio aceptado completo (no hay cargo proporcional).

- **HECHO:** la entrada exige que la reserva haya comenzado (`inicio ≤ hoy`
  del servidor; 409 «aún no llega su día de entrada» — en ratificación,
  commit 34862d7). El documento del huésped es opcional y no se exige en
  ninguna operación. La salida no tiene regla de hora: liquida con saldo 0 en
  cualquier momento. Fuente del dominio: llegada 15:00 del inicio
  (`HORA_LLEGADA`), cancelación gratuita hasta 48 h antes
  (`LIMITE_CANCELACION_GRATUITA`).
- **Opciones:** (a) ratificar solo «inicio ≤ hoy»; (b) además exigir hora de
  llegada ≥ 15:00 en el día de inicio y documento del huésped antes de
  pasar a `en_estadia`; (c) exigirlo también en la salida (documento ya
  registrado).
- **PROPUESTA:** (b) con documento, porque la estadía activa cobra y sin
  identidad no hay forma de asociar la cuenta a una persona (fuente: regla
  `check_in` del dominio). La hora de llegada puede esperar: hoy nadie opera
  fuera de horario.

## 2. Roles del check-in y la salida (#304)

- **HECHO:** cualquier rol autenticado puede ejecutar entrada y salida
  (administrador, recepción **y caja**): las rutas no aplican `_exigir_rol`.
  Caja sí está limitada en caja del día y usuarios.
- **Opciones:** (a) recepción + administrador; (b) recepción sola (admin
  opera con usuario de recepción); (c) mantener como está.
- **PROPUESTA:** (a) — coherente con «caja cobra, recepción opera la
  habitación» ya vigente en limpieza/mantenimiento. Es un cambio de dos
  líneas + pruebas.

## 3. Tarifa de estadías que cruzan dos periodos de tarifa (#305)

- **HECHO:** el total cobrado es **tarifa de la noche de inicio × noches**
  (D-TAR-02, ya registrado en spec-api-v1). RES-TARIFA-NOCHES exige que cada
  noche tenga tarifa vigente, pero el precio no la usa noche a noche.
- **Opciones:** (a) mantener D-TAR-02 (simple, predecible); (b) cobrar noche
  a noche con la tarifa vigente de cada noche (el total ofertado ya podría
  calcularse así en `reservas.oferta`); (c) tarifa de inicio con recargo/
  descuento en el cruce.
- **PROPUESTA:** (b): la oferta ya publica `tarifa_noche_clp` y `total_clp`;
  alinear el cargo con lo ofertado evita la discrepancia «se ofreció X, se
  cargó Y» cuando cambia la tarifa a mitad de estadía. Es el cambio con más
  superficie (oferta, reserva, cargos, cancelación, liquidación).

## 4. Indicadores financieros y rol gerencia (#297)

- **HECHO:** el panel muestra los financieros como no disponibles y no
  expone montos a roles sin permiso (E2E MOV-02); la definición (fórmula,
  unidad, fuente) la sirve la API por indicador.
- **Opciones:** definir ADR (ingreso por habitación ocupada), RevPAR
  (ingreso por habitación disponible) e ingresos del periodo: con fuente en
  `cargos`/`pagos` confirmados; y si «gerencia» es un rol nuevo o
  administrador los ve.
- **PROPUESTA:** empezar por **ingresos del periodo = pagos confirmados**
  (dato ya veraz) para administrador; ADR/RevPAR cuando el punto 3 (tarifa
  noche a noche) esté resuelto, porque su fórmula depende del criterio de
  ingreso.

## 5. Personas en la reserva, reasignación y catálogo de tipos (#298)

- **HECHO:** `personas` filtra la oferta (capacidad ≥ personas) pero **no se
  guarda en la reserva**; no existe operación de reasignación de habitación
  (habría que cancelar y crear); `tipo` de habitación es texto libre.
- **Opciones:** (a) persistir `personas` en `reservas` y validar capacidad en
  la confirmación (no solo en la oferta); (b) operación «mover reserva a otra
  habitación» (misma regla de cupo, trazada en auditoría); (c) catálogo
  cerrado de tipos (single, doble, suite…) con capacidad por tipo.
- **PROPUESTA:** (a) ya — es una columna y una validación; (b) y (c) cuando
  el propietario los pida por nombre (hoy el hotel usa «doble»).

## 6. Tarifas superpuestas, mantenimiento programado, denominador de ocupación y auditoría por rol (#299)

- **HECHO:** tarifas append-only con vigencia desempatada por
  `fecha_desde DESC, creado_en DESC` (la más reciente gana; migración 0009
  fijó `creado_en` — ver runbook H7 «Orden de despliegue»); el mantenimiento
  es un flag manual sin agenda; el panel cuenta `disponibles/ocupadas/
  no_vendibles` por noche sobre las habitaciones dadas de alta (denominador =
  habitaciones activas, sin distinguir fuera_de_servicio); la auditoría
  completa solo la ve el administrador en la ficha.
- **Opciones:** (a) permitir tarifas superpuestas con desempate explícito
  (hoy) o prohibir el solape al cargar (409); (b) mantenimiento programado
  (rango de fechas que bloquea oferta/entrada sin intervención diaria);
  (c) definir el denominador de ocupación (¿las fuera_de_servicio cuentan
  como no vendibles en el %?); (d) qué rol ve la auditoría (¿recepción la de
  sus acciones?).
- **PROPUESTA:** (a) prohibir el solape al cargar — el desempate implícito ya
  mordió una vez (issue #306); (c) excluir `fuera_de_servicio` del
  denominador de ocupación del panel; (b) y (d) a pedido explícito.

## 7. D-PUB-01 — qué reserva puede hacer un visitante desde la landing (#308)

- **HECHO:** el visitante deja una **solicitud** `recibida` y recepción la
  convierte (V1-ISSUE-22/24, en main). No hay confirmación en línea.
- **Opciones:** (a) mantener solicitud con aprobación humana (hoy); (b)
  confirmación en línea para rangos dentro de límites (noches, monto,
  antelación), creando la reserva por la misma operación interna, con carrera
  por la última unidad resuelta por el servidor; (c) mezcla (hasta N noches
  confirma, más grande solicita).
- **PROPUESTA:** (a) al menos durante el primer mes de operación real: sin
  volumen, la aprobación humana es el control de calidad. Reevaluar (b) con
  datos de uso.

## 8. D-AGT-01..06 — agente de reservas (#316)

- **HECHO:** la especificación completa está en `specs/005-hotel-agente-reservas/`
  (spec, plan, tareas, contratos, modelo de datos, aceptación), escrita
  2026-11-03, y dice explícitamente: **REQUISITO PROPUESTO, NO APROBADO** —
  todos sus FR/NFR/SC esperan estas decisiones. Nada del paquete se construye
  antes de la ratificación, por eso los issues #317–#319 siguen abiertos.
- **Decisiones (resumen de la spec §6):** D-AGT-01 nivel inicial (propuesta:
  N0 copiloto; SC-003 como compuerta), D-AGT-02 proveedor del modelo (cuenta,
  región, retención, Ley 21.719), D-AGT-03 canal de respuesta, D-AGT-04
  límites de N2, D-AGT-05 tope de gasto, D-AGT-06 tono e identificación del
  asistente.
- **PROPUESTA:** el plan de tareas de la spec (T001–T070) ya ordena el
  trabajo para cuando se ratifique; empezar por D-AGT-01 + D-AGT-06 (basta
  para construir N0 sin proveedor externo: el modelo falso guionado cubre las
  pruebas).
