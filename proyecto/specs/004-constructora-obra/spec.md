# Especificación — Constructora y control de obra

Feature: `004-constructora-obra`. Fecha: 2026-10-16. Estado: **BLOCKED** para implementación.
Fuente: INM §2 H3, §3 FR-010–012, SC-008 y encargo de separación 004. Todos los FR y SC son **REQUISITOS PROPUESTOS**, pendientes de ratificación. Los resultados numéricos son objetivos; no se han medido.

## Problema, actores y límites

V2; FR-010 a FR-012 y H3 heredados. Inspección, materiales, presupuesto y compras son requisitos propuestos nuevos; el supuesto módulo existente no fue entregado.

Actores: jefe de obra, inspector, encargado de materiales y administrador aprobador. Las responsabilidades de aprobación no se transfieren al modelo.

## Escenarios de usuario y pruebas

### H3 (P1) — Reportar avance y preparar compras

Valor: control verificable de la operación. Prueba independiente: ejecutar el escenario sin otra vertical, con adaptadores de prueba explícitos.

Dado un reporte con retroceso, cuando se recibe, entonces se preservan versiones y se exige revisión; una compra queda como propuesta.

### H4 (P2) — Controlar presupuesto, inspección y materiales

Valor: control verificable de la operación. Prueba independiente: ejecutar el escenario sin otra vertical, con adaptadores de prueba explícitos.

Dada recepción de materiales, cuando el responsable la valida, entonces se actualiza la partida y su evidencia sin alterar el avance físico.

## Requisitos funcionales

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-010 | Registrar avance por partida desde texto, voz y foto con fecha, ubicación cuando proceda y evidencia | H3 |
| FR-011 | Comparar avance real con programado y presupuesto bajo unidad y umbral aprobados | H3 |
| FR-012 | Preparar solicitudes de compra con cantidad, proveedor y precio de referencia para aprobación humana | H3 |
| FR-015 | Mantener versiones de presupuesto y programación por partida sin confundir costo y avance físico | H4 |
| FR-016 | Registrar inspecciones, observaciones y cierre humano con evidencia | H4 |
| FR-017 | Registrar recepción, consumo y conciliación de materiales por obra | H4 |
| FR-018 | Aplicar permisos de obra, auditoría y acceso a evidencias por empresa | H4 |

## Criterios de éxito

| ID | Objetivo propuesto |
|---|---|
| SC-008 | Avance por partida disponible el día del reporte; objetivo heredado, condicionado a revisión |
| SC-010 | Cero compras ejecutadas sin aprobación válida en pruebas adversariales |
| SC-011 | 100 % de rectificaciones conserva evidencia y autor en la batería de aceptación |

## Supuestos y decisiones pendientes

Q-OBR-01: obras propias o terceros, presupuesto y módulo previo no entregado; Q-OBR-02: unidad del avance, calendario y umbral; Q-OBR-03: aprobadores, compras, seguridad e inspecciones.

## Reglas normativas y de aceptación añadidas

- NFR-001: toda lectura, escritura, trabajo en cola y evidencia queda limitada por empresa y permiso; probar denegación entre empresas y roles.
- NFR-002: ningún agente ejecuta una acción financiera, tributaria o contractual sin control determinista y autorización vigente; escritura MCP deshabilitada inicialmente.
- NFR-003: reintentos conservan un solo efecto; estados desconocidos no se muestran como éxitos.
- NFR-004: retención, restauración y objetivos de recuperación requieren aprobación en Q-CORE-03; ninguna cifra de disponibilidad se asume acordada.
- NFR-005: medir latencia desde recepción hasta resultado confirmado, incluyendo errores, reintentos y desconexión. No declarar cumplimiento en muestras vacías.

Q-OBR-01: obras propias o terceros, presupuesto y módulo previo no entregado; Q-OBR-02: unidad del avance, calendario y umbral; Q-OBR-03: aprobadores, compras, seguridad e inspecciones.

Las obligaciones fiscales y de recuperación se aplican solo a los efectos pertinentes del dominio; no se atribuyen reservas OTA ni latencias SII al control de obra.

Ver `acceptance.md` para pruebas por requisito; `../../docs/auditorias/trazabilidad.md` para origen y equivalencias. La investigación transversal está en `../../docs/investigacion/estado-del-arte.md`.


## Refinamiento competitivo de historias — 2026-10-16

Estado **PROPUESTO**, sin ratificación del cliente. Las siguientes definiciones amplían las historias originales con alias US, sin eliminarlas. Ante un caso específico se aplica la regla más explícita de esta sección; ninguna cambia los bloqueos comerciales. Evidencia por ID en `../../docs/investigacion-competitiva/matriz-evidencias.md`.

### Historia US-OBR-003 — enriquecimiento de H3 (P1)

Como jefe de obra y administrador de compras, quiero convertir reportes y necesidades en borradores revisables por partida, para hacer visibles desvíos y solicitudes sin inventar avance ni comprar automáticamente.

**Identidad y estado:** alias de `004-constructora-obra/H3`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Convertir reportes y necesidades en borradores revisables por partida. Responde a hacer visibles desvíos y solicitudes sin inventar avance ni comprar automáticamente; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** O03, O05, O07, O08 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-010,FR-011,FR-012,FR-015,FR-020 y NFR-001/002/003/006.

**Disparador:** el jefe envía reporte de avance o necesidad de materiales por texto, voz, foto o entrada manual.

**Precondiciones:** presupuesto/programación versionados, partidas/unidades y aprobadores; catálogo proveedor vigente si existe.

**Flujo principal:** Capturar texto/foto/voz → conservar fuente → extraer partida/cantidad/unidad → marcar inciertos → revisar → consolidar reporte aprobado → calcular desvío → preparar solicitud con precio/convenio como evidencia.

**Flujos alternativos y casos borde:** IA no disponible o deshabilitada: entrada manual equivalente. Unidad/proveedor ambiguo: revisión; convenio vencido no autoriza precio. Retroceso exige rectificación conservada.

**Reglas de negocio y validaciones:** Extracción no aprobación; imagen no certificación. Compra autorizada se vincula a versión de líneas; cualquier cambio requiere nueva revisión. Umbral relativo/puntos sigue Q-OBR-02.

**Datos y estados involucrados:** Reporte, evidencia/fecha/ubicación sugerida, campoExtraído/confianza, partida/versión, cantidad/unidad, referenciaPrecio y aprobación. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). Fallar cerrado si faltan evidencia, permiso o conectividad.

**Dependencias:** 000, presupuesto/programación/roles según Q-OBR-01/02/03; correspondencia con proyecto comercial opcional. No exige un módulo previo no entregado.

**Riesgos:** Error de transcripción, evidencia falsificada, orden indebida y ubicación sensible.

**Criterios de aceptación Given/When/Then:**

- AC-US-OBR-003-01: Dada nota que dice comprar e incluye instrucciones, cuando se procesa, entonces solo crea borrador con campos pendientes y no envía orden.
- AC-US-OBR-003-02: Dada IA desactivada, cuando se informa avance manualmente, entonces el reporte sigue disponible y conserva autor/evidencia con mismas validaciones.

**Métricas de éxito:** Campos correctos/campos revisados; reportes aprobados; minutos de revisión; costo/reporte y compras no autorizadas. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


### Historia US-OBR-004 — enriquecimiento de H4 (P2)

Como inspector y encargado de materiales, quiero registrar observaciones y recepciones contra evidencia y permisos, para cerrar fallas verificadas y conciliar materiales sin confundirlos con avance.

**Identidad y estado:** alias de `004-constructora-obra/H4`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Registrar observaciones y recepciones contra evidencia y permisos. Responde a cerrar fallas verificadas y conciliar materiales sin confundirlos con avance; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** O01, O02, O06, O09 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-015,FR-016,FR-017,FR-018,FR-019,FR-020 y NFR-001/002/003/006.

**Disparador:** un inspector registra ítem fallido, se propone su solución o bodega recibe material contra una orden.

**Precondiciones:** plantilla/partidas vigentes, unidades, roles de inspector/solucionador y política de recepción.

**Flujo principal:** Registrar inspección → detectar falla → abrir observación vinculada → asignar responsable/plazo → adjuntar solución → validar cierre; por separado registrar recepción parcial → comparar con compra aprobada → conciliar diferencia.

**Flujos alternativos y casos borde:** Solucionador sin permiso de cierre propone resuelto; inspector valida o reabre. Material sobrante/dañado queda en discrepancia; reintento de recepción no duplica.

**Reglas de negocio y validaciones:** Estado resuelto propuesto no equivale a cerrado aceptado. Recibir no consume; consumo no certifica avance. Sensor y reporte manual tienen procedencias distintas.

**Datos y estados involucrados:** Inspección/ítem, Observación, vínculo/origen, asignado, evidenciaSolución, revisor, recepción/línea, orden y discrepancia. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). No se exige IA para completar este flujo.

**Dependencias:** 000, presupuesto/programación/roles según Q-OBR-01/02/03; correspondencia con proyecto comercial opcional. No exige un módulo previo no entregado.

**Riesgos:** Cierre sin validación, cantidades duplicadas, unidad incompatible y falsa seguridad estructural.

**Criterios de aceptación Given/When/Then:**

- AC-US-OBR-004-01: Dado ítem de inspección fallido, cuando se crea observación, entonces conserva vínculo, responsable y estado; el reportante sin permiso no puede cerrarla.
- AC-US-OBR-004-02: Dada orden de 10 unidades y recepción de 6, cuando se confirma, entonces quedan 4 pendientes; repetir mismo evento no recibe 12.

**Métricas de éxito:** Observaciones con evidencia/cerradas; reaperturas; recepción conciliada/recibida; discrepancias abiertas por antigüedad. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


## Requisitos derivados de investigación competitiva

Son propuestas de comportamiento propio, sin atribuirlo como implementación observada del competidor.

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-019 | Vincular observación con ítem/evidencia de inspección, responsable y plazo; separar solución propuesta de cierre autorizado y conservar reaperturas | H4 |
| FR-020 | Mantener solicitudes y recepciones por línea, cantidad/unidad, referencia de precio/convenio y versión aprobada; admitir recepción parcial y discrepancias sin duplicar movimientos ni ejecutar compra desde extracción | H3/H4 |

- NFR-006: toda oferta, extracción o decisión derivada declara procedencia, vigencia e incertidumbre; si no hay evidencia suficiente, no genera compromiso automático ni se informa como éxito. La captura manual conserva permisos, trazabilidad e idempotencia equivalentes.

## Profundización funcional de las otras verticales

Estado **REQUISITO PROPUESTO**; evidencia adicional y límites en investigación competitiva/continuacion-01. Conserva IDs/historias previos y bloqueos.

### RF-OBR-01 — Registrar partes y extracción sin perder autoría, unidades o conectividad

**Historia US-OBR-003** (misma historia/ID, prioridad P1; no es historia nueva).

Como jefe de obra, colaborador y revisor de avance, quiero registrar partes y extracción sin perder autoría, unidades o conectividad, para consolidar cantidades aprobadas sin duplicar reportes ni presentar transcripción como avance certificado.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** O11, O14, O17, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** se recibe parte manual o evidencia de campo, o se reintenta enviar tras falla.

**Precondiciones:** obra/partida/versión y unidades identificadas; permisos de reporte/revisión y canal soportado.

**Flujo principal:**

1. Conservar original con autor, fecha de hecho/recepción y alcance turno/zona si aplica.
2. Verificar recepción antes de informar enviado; extracción IA solo si disponible.
3. Separar cantidades nuevas, acumuladas y correcciones; marcar ambigüedad.
4. Revisor aprueba o rechaza aportes y relaciona duplicados.
5. Consolidar avance solo desde cantidades aceptadas y denominador vigente.

**Flujos alternativos y excepciones:** Sin conectividad para IA: no afirmar extracción terminada; usar captura manual o envío diferido soportado, sin prometer aplicación offline no definida. Dos reportes del día pueden ser legítimos; porcentaje sin base no se suma.

**Reglas de negocio/validaciones:** La clave del reporte no es solo fecha+obra. Voz es evidencia no confiable; edición no sustituye original. Exportación offline consultable no demuestra captura/sincronización IA sin red.

**Datos y estados:** Parte, claveOrigen, autor, fechaHecho, recibidoEn, turno/zona/partida, tipoCantidad incremental/acumulada/corrección, extracción/revisión y versión base.

**Dependencias:** Q-OBR-01/02/03, canal y procedimiento de contingencia; no crea app móvil ni promete reconocimiento local.

**Riesgos:** Doble avance, falsa precisión, reporte perdido, prompt injection y ubicación personal expuesta.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-OBR-003-03: Dados dos partes legítimos de turnos distintos en una obra/día y un reenvío del primero, cuando se reciben, entonces conserva ambos aportes y no duplica el reenvío.
- AC-US-OBR-003-04: Dado porcentaje 40 % acumulado y nuevo reporte 45 % acumulado de la misma partida, cuando se revisa, entonces no produce 85 % por sumarlos y requiere la base/unidad definida.
- AC-US-OBR-003-05: Dada falta de conexión para transcribir, cuando se carga evidencia, entonces no se marca transcrita/aprobada; la vía manual soportada conserva mismos permisos y revisión.

**Métricas:** partes aceptados/recibidos, error por unidad/campo, retraso hecho→validación, duplicados y costo por parte aprobado. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


### RF-OBR-02 — Conciliar entrega, aceptación, rechazo y devolución de material

**Historia US-OBR-004** (misma historia/ID, prioridad P2; no es historia nueva).

Como encargado de bodega, comprador y aprobador de recepción, quiero conciliar entrega, aceptación, rechazo y devolución de material, para saber qué material se puede consumir y qué obligación sigue pendiente.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** O13, O15, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** llega entrega parcial o se comunica rechazo/devolución.

**Precondiciones:** orden/líneas/versiones autorizadas, unidades revisadas, documento de entrega y responsables.

**Flujo principal:**

1. Identificar orden, tramo/entrega y líneas de material.
2. Registrar cantidad física entregada y separar aceptada/rechazada con motivo/evidencia.
3. Actualizar existencias solo de lo aceptado y calcular pendiente según política de reposición.
4. Registrar devolución como movimiento vinculado, sin borrar recepción.
5. Conciliar con compra/guía/factura por proceso autorizado antes de pago.

**Flujos alternativos y excepciones:** Entrega repetida no es nueva recepción. Conversión de unidad, exceso o versión discrepante van a revisión. Una factura no demuestra que el material llegó ni fue aceptado.

**Reglas de negocio/validaciones:** Pendiente, aceptado, rechazado y devuelto son magnitudes distintas; reposición/cancelación requieren regla del comprador. No usar rechazo como borrado de evidencia ni como pago automático.

**Datos y estados:** EntregaProveedor, TramoOrden, RecepcionLinea, cantidadEntregada/aceptada/rechazada/devuelta, MotivoEvidencia y discrepanciaContable.

**Dependencias:** Q-OBR-03 y Q-CORE-02; contabilidad/facturación se integra si se decide, no se presume módulo existente.

**Riesgos:** Stock inexistente, recepción doble, pago de material rechazado y cambio de unidad oculto.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-OBR-004-03: Dada orden de diez unidades y entrega física de seis con cinco aceptadas y una rechazada a reponer por política configurada, cuando se valida, entonces stock aumenta cinco y pendientes de suministro son cinco, con rechazo documentado.
- AC-US-OBR-004-04: Dada misma entrega recibida dos veces por reintento, cuando se registra, entonces no duplica stock; una segunda entrega con identidad distinta sí se evalúa como nueva.
- AC-US-OBR-004-05: Dada devolución de una unidad previamente aceptada, cuando se aprueba, entonces conserva recepción y registra movimiento de devolución; no se infiere abono financiero ni cambio de contrato.

**Métricas:** cantidades aceptadas/entregadas, discrepancias por orden, días pendientes y costo de conciliación por recepción. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


### RF-OBR-03 — Controlar línea base y compromiso sin sumar estados del mismo gasto

**Historia US-OBR-004** (misma historia/ID, prioridad P2; no es historia nueva).

Como control de obra y administrador de compras, quiero controlar línea base y compromiso sin sumar estados del mismo gasto, para detectar desviaciones presupuestarias con unidades y obligaciones comparables.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** O16, O18, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** nueva propuesta de compra, cambio presupuestario o conciliación de obligación.

**Precondiciones:** presupuesto vigente por partida, reglas de compromiso/devengo/pago y aprobación definidos.

**Flujo principal:**

1. Seleccionar línea base y versión vigente.
2. Clasificar propuesta/compromiso/recepción/devengo/pago de cada obligación.
3. Calcular exposición y disponible con fórmula aprobada, sin doble contar estados de la misma obligación.
4. Alertar desvío o falta de clasificación y solicitar decisión humana.
5. Registrar cambio aprobado de presupuesto como nueva versión manteniendo comparación histórica.

**Flujos alternativos y excepciones:** Sin presupuesto o regla contable se informa no evaluable. Cancelación de compromiso ajusta saldo según política/evidencia; cambio de fecha no altera cantidades físicas.

**Reglas de negocio/validaciones:** Gasto, pago y avance físico no son equivalentes. El compromiso puede contener importes ya devengados/pagados, por lo que no se suman ciegamente. No aprobar excedente ni subcontrato desde IA.

**Datos y estados:** PresupuestoVersionado, Partida, ObligacionCosto y sus estados, compromisosVigentes, ajustes/causa/aprobador y FormulaControl versionada.

**Dependencias:** Q-OBR-01/02/03 y regla contable del cliente; gestión integral de subcontratos queda fuera del alcance activo hasta decisión.

**Riesgos:** Disponible inflado/negativo por doble cuenta, cambio de base invisible y compromiso no autorizado.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-OBR-004-06: Dado presupuesto de ejemplo 100 y compromiso total 50 que ya incluye devengo 20 y pago 10, cuando se calcula disponible sin otras obligaciones, entonces es 50 y no 20 al descontar los tres estados otra vez.
- AC-US-OBR-004-07: Dada modificación aprobada de presupuesto, cuando se compara avance/costo histórico, entonces conserva línea base, versión vigente y motivo/aprobador; no reescribe el pasado.
- AC-US-OBR-004-08: Dada partida sin fórmula o clasificación válida, cuando se evalúa compra, entonces indica control no evaluable y requiere revisión, sin aprobar automáticamente.

**Métricas:** partidas con exposición conciliada/partidas, error de disponible vs revisión y tiempo de detectar desvío; no ROI inventado. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


### RF-OBR-04 — Aceptar solución y distinguir respuesta técnica oficial

**Historia US-OBR-004** (misma historia/ID, prioridad P2; no es historia nueva).

Como inspector, solucionador y responsable técnico, quiero aceptar solución y distinguir respuesta técnica oficial, para cerrar una falla con autoridad y evidencia, sin confundir comentario de IA con instrucción de obra.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** O10, O12, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** se entrega solución, respuesta técnica o revisión de inspección.

**Precondiciones:** observación vinculada a evidencia/partida, responsables y permisos de solución/cierre definidos.

**Flujo principal:**

1. Relacionar solución/respuesta con observación y versión de evidencia.
2. Solucionador declara lista para revisión sin cerrar por sí solo.
3. Revisor autorizado acepta, no acepta o pide información con motivo.
4. Registrar cierre o reapertura y responsable de siguiente acción.
5. Si una respuesta exige cambio contractual/presupuestario, abrir decisión aparte sin ejecutarla.

**Flujos alternativos y excepciones:** Varios comentarios o revisores no equivalen a respuesta oficial. Caso duplicado se vincula sin borrar evidencia. Nueva falla tras cierre reabre o crea caso relacionado según política.

**Reglas de negocio/validaciones:** El sistema no certifica seguridad estructural. Respuesta oficial es declaración del rol habilitado, no texto de modelo. Flujo RFI enterprise no se incorpora por usarlo como comparación.

**Datos y estados:** Observacion, PropuestaSolucion, RespuestaTecnica con emisor/alcance, EvidenciaRevision, estado/revisor/motivo y referenciaDecisionCambio.

**Dependencias:** Q-OBR-03 y política de evidencia; interfaz con comercial/postventa solo por convenio, sin permisos compartidos por grupo.

**Riesgos:** Cerrar trabajo no inspeccionado, ejecutar instrucción técnica no válida y exposición de fotos.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-OBR-004-09: Dado solucionador sin permiso de aceptar, cuando informa reparación lista, entonces queda por revisar y no cerrada; el inspector puede no aceptar con motivo.
- AC-US-OBR-004-10: Dado comentario generado por IA que cambia una especificación técnica, cuando se adjunta al caso, entonces no se convierte en respuesta oficial ni modifica presupuesto o programa.
- AC-US-OBR-004-11: Dada observación reabierta por nueva evidencia, cuando se inspecciona historial, entonces conserva cierre previo, responsable, evidencia y motivo de reapertura.

**Métricas:** cierres aceptados/revisados, reaperturas, tiempo listo→aceptado y casos sin responsable. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


## Requisitos de recuperación y semántica de dominio

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-021 | Conservar partes por autor, alcance/turno, fecha del hecho/recepción, unidad y versión de partida; separar cantidad incremental, acumulada y corrección y estado de captura, extracción y aprobación | H3 |
| FR-022 | Conciliar entregas por línea/tramo y evidencia con cantidades entregadas, aceptadas, rechazadas y devueltas; actualizar stock solo según recepción aceptada y política de reposición, sin duplicar por reenvío | H4 |
| FR-023 | Controlar exposición presupuestaria por partida/versionado mediante regla aprobada que distinga propuesta, compromiso, devengo y pago; evitar doble cómputo y exigir revisión de excedentes o datos no evaluables | H4 |


### Bloqueos adicionales de la profundización

Q-OBR-04/05/06: ver [decisiones pendientes](../../docs/investigacion-competitiva/decisiones-pendientes.md). Son reglas para ratificar, no respuestas inferidas del mercado. Las historias permanecen propuestas y la feature **BLOCKED** para implementar.
