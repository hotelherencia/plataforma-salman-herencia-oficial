# Especificación — Core transversal

Feature: `000-core`. Fecha: 2026-10-16. Estado: **BLOCKED** para implementación.
Fuente: requisitos transversales de CAF §1, HOT §3 e INM §3 y encargo del cliente. Todos los FR y SC son **REQUISITOS PROPUESTOS**, pendientes de ratificación. Los resultados numéricos son objetivos; no se han medido.

## Problema, actores y límites

Core mínimo: identidad, permisos, adaptadores de pago/documentos/comunicación y auditoría. Catálogo, gastos, inventario, CRM y analítica de dominio no son core.

Actores: administrador de empresa, operador de pagos, auditor y responsable de privacidad. Las responsabilidades de aprobación no se transfieren al modelo.

## Escenarios de usuario y pruebas

### H1 (P1) — Administrar acceso por empresa

Valor: control verificable de la operación. Prueba independiente: ejecutar el escenario sin otra vertical, con adaptadores de prueba explícitos.

Dada una membresía activa, cuando se solicita un recurso de otra empresa, entonces se deniega y audita.

### H2 (P1) — Confirmar pagos y documentos sin duplicaciones

Valor: control verificable de la operación. Prueba independiente: ejecutar el escenario sin otra vertical, con adaptadores de prueba explícitos.

Dado un retorno repetido, cuando se procesa, entonces solo una imputación es efectiva y el documento se concilia.

### H3 (P2) — Gobernar acciones y contratos

Valor: control verificable de la operación. Prueba independiente: ejecutar el escenario sin otra vertical, con adaptadores de prueba explícitos.

Dada una acción crítica sin aprobación, cuando el agente intenta ejecutarla, entonces se deniega y registra.

## Requisitos funcionales

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-001 | Resolver identidad y pertenencia activa a una empresa antes de acceder a cualquier recurso | H1 |
| FR-002 | Autorizar por tenant, rol, recurso y acción con denegación por defecto, incluidos procesos asíncronos | H1 |
| FR-003 | Registrar intentos y estados de pago por empresa, moneda, monto y referencia de negocio, sin duplicar efectos al reintentar | H2 |
| FR-004 | Determinar y emitir el documento tributario aplicable mediante política aprobada por contribuyente; conciliar y evitar doble emisión | H2 |
| FR-005 | Registrar acciones críticas y de agentes con actor, tenant, evidencia, política, aprobación y resultado, con integridad verificable | H3 |
| FR-006 | Separar secretos, almacenamiento y comunicaciones por tenant; minimizar datos y aplicar retención aprobada | H1 |
| FR-007 | Denegar ejecuciones agénticas sin política vigente, identidad, evidencia o aprobación exigida | H3 |
| FR-008 | Recuperar fallos de conectividad mediante estados pendientes, reconciliación y alertas sin declarar éxito ficticio | H2 |
| FR-009 | Versionar contratos y registrar compatibilidad de productores y consumidores antes de cambios | H3 |

## Criterios de éxito

| ID | Objetivo propuesto |
|---|---|
| SC-001 | Cero accesos entre tenants en la batería adversarial aprobada |
| SC-002 | Un único efecto financiero ante diez repeticiones del mismo resultado |
| SC-003 | Toda acción crítica tiene actor, tenant, evidencia y resultado auditables |

## Supuestos y decisiones pendientes

Q-CORE-01: empresas, roles y autorización entre empresas; Q-CORE-02: tratamiento fiscal y proveedor DTE por contribuyente; Q-CORE-03: responsables de datos, retención, recuperación, presupuesto y autonomía.

## Reglas normativas y de aceptación añadidas

- NFR-001: toda lectura, escritura, trabajo en cola y evidencia queda limitada por empresa y permiso; probar denegación entre empresas y roles.
- NFR-002: ningún agente ejecuta una acción financiera, tributaria o contractual sin control determinista y autorización vigente; escritura MCP deshabilitada inicialmente.
- NFR-003: reintentos conservan un solo efecto; estados desconocidos no se muestran como éxitos.
- NFR-004: retención, restauración y objetivos de recuperación requieren aprobación en Q-CORE-03; ninguna cifra de disponibilidad se asume acordada.
- NFR-005: medir latencia desde recepción hasta resultado confirmado, incluyendo errores, reintentos y desconexión. No declarar cumplimiento en muestras vacías.

Q-CORE-01: empresas, roles y autorización entre empresas; Q-CORE-02: tratamiento fiscal y proveedor DTE por contribuyente; Q-CORE-03: responsables de datos, retención, recuperación, presupuesto y autonomía.

Las obligaciones fiscales y de recuperación se aplican solo a los efectos pertinentes del dominio; no se atribuyen reservas OTA ni latencias SII al control de obra.

Ver `acceptance.md` para pruebas por requisito; `../../docs/auditorias/trazabilidad.md` para origen y equivalencias. La investigación transversal está en `../../docs/investigacion/estado-del-arte.md`.


## Refinamiento competitivo de historias — 2026-10-16

Estado **PROPUESTO**, sin ratificación del cliente. Las siguientes definiciones amplían las historias originales con alias US, sin eliminarlas. Ante un caso específico se aplica la regla más explícita de esta sección; ninguna cambia los bloqueos comerciales. Evidencia por ID en `../../docs/investigacion-competitiva/matriz-evidencias.md`.

### Historia US-CORE-001 — enriquecimiento de H1 (P1)

Como administrador de empresa, quiero habilitar conectores con alcance y cuenta comprobados, para evitar que un acceso técnico se convierta en acceso a otra empresa.

**Identidad y estado:** alias de `000-core/H1`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Habilitar conectores con alcance y cuenta comprobados. Responde a evitar que un acceso técnico se convierta en acceso a otra empresa; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** C04, I10 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-001,FR-002,FR-006,FR-010 y NFR-001/002/003/006.

**Disparador:** el administrador solicita habilitar o revisar una integración para una empresa.

**Precondiciones:** empresa y membresía verificadas; proveedor y cuenta identificados.

**Flujo principal:** Elegir empresa y proveedor → consultar capacidad documentada/contratada → identificar plan, país y permisos → registrar habilitación revisada → permitir solo operaciones incluidas.

**Flujos alternativos y casos borde:** Cuenta sin acceso o plan incompatible: mostrar no habilitado y vía de revisión, sin simular disponibilidad. Cambio de plan revoca capacidad hasta revalidación.

**Reglas de negocio y validaciones:** Acceso público a documentación no habilita API privada; configuración pertenece a un tenant y no se copia entre empresas.

**Datos y estados involucrados:** PerfilConector, referencia de cuenta, plan/país, operaciones, permisos, revisión y versión. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). No se exige IA para completar este flujo.

**Dependencias:** Q-CORE-01/02/03; autoridad y permisos del proveedor cuando exista integración. El core no depende de ninguna vertical para funcionar.

**Riesgos:** Credencial cruzada, catálogo de capacidades obsoleto y exposición de cuenta.

**Criterios de aceptación Given/When/Then:**

- AC-US-CORE-001-01: Dado conector habilitado para A, cuando B intenta usar su referencia, entonces se deniega sin revelar secretos.
- AC-US-CORE-001-02: Dado plan sin permiso de leads, cuando se solicita captura, entonces se informa capacidad no habilitada y se registra motivo.

**Métricas de éxito:** N_habilitaciones_con_evidencia/N_habilitaciones; incidentes de acceso cruzado; no hay medición. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


### Historia US-CORE-002 — enriquecimiento de H2 (P1)

Como operador de conciliación, quiero distinguir una solicitud recibida de un efecto confirmado, para regularizar fallos sin duplicar cobros ni perder obligaciones.

**Identidad y estado:** alias de `000-core/H2`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Distinguir una solicitud recibida de un efecto confirmado. Responde a regularizar fallos sin duplicar cobros ni perder obligaciones; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** C06, H01 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-003,FR-004,FR-008,FR-011 y NFR-001/002/003/006.

**Disparador:** llega un resultado externo o el operador abre un intento pendiente para conciliarlo.

**Precondiciones:** referencia única de negocio, cuenta/proveedor y política fiscal aprobada.

**Flujo principal:** Registrar intento → enviar a proveedor autorizado → vincular respuesta a intento/monto → aplicar resultado una vez → conciliar o abrir pendiente con responsable.

**Flujos alternativos y casos borde:** Timeout tras envío: resultado desconocido; consultar estado antes de reintento. Evento anterior al estado vigente: conservar evidencia sin retroceder.

**Reglas de negocio y validaciones:** Recibir HTTP o cerrar pantalla no equivale a autorizar; reabrir caso no borra pago. La compensación necesita política y autorización nueva.

**Datos y estados involucrados:** Intento, resultado externo, secuencia/fecha de evento, correlación, motivo pendiente y revisión. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). No se exige IA para completar este flujo.

**Dependencias:** Q-CORE-01/02/03; autoridad y permisos del proveedor cuando exista integración. El core no depende de ninguna vertical para funcionar.

**Riesgos:** Desorden de eventos, crédito doble, exposición en errores.

**Criterios de aceptación Given/When/Then:**

- AC-US-CORE-002-01: Dado pago desconocido, cuando llega confirmación repetida diez veces, entonces se aplica un solo efecto y el caso se cierra con evidencia.
- AC-US-CORE-002-02: Dado pago rechazado posterior a operación offline registrada, cuando se concilia, entonces no figura autorizado ni se borra la deuda.

**Métricas de éxito:** Pendientes por antigüedad y motivo; tiempo p95 hasta conciliación; efectos duplicados/operaciones. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


### Historia US-CORE-003 — enriquecimiento de H3 (P2)

Como responsable de seguridad y operación, quiero revisar una acción propuesta con evidencia y alcance exactos, para impedir cambios de negocio autorizados solo por el lenguaje del modelo.

**Identidad y estado:** alias de `000-core/H3`; conserva historia y prioridad, **REQUISITO PROPUESTO**. No hay validación del cliente ni observación de runtime.

**Descripción funcional y necesidad de negocio:** Revisar una acción propuesta con evidencia y alcance exactos. Responde a impedir cambios de negocio autorizados solo por el lenguaje del modelo; la evidencia competitiva precisa el comportamiento, no demuestra demanda comercial.

**Fuente de inspiración y evidencia:** I06, I07, H10 en matriz-evidencias.md. Lectura documental, reconstrucción propia. Requisitos: FR-005,FR-007,FR-009,FR-010 y NFR-001/002/003/006.

**Disparador:** una propuesta de acción crítica solicita aprobación o intenta usar una autorización existente.

**Precondiciones:** política vigente, aprobador distinto al proponente y herramientas limitadas.

**Flujo principal:** Agente propone → servicio valida recurso/permiso/capacidad → humano revisa parámetros/evidencia → aprobar o rechazar → ejecutar solo dentro de alcance → registrar resultado.

**Flujos alternativos y casos borde:** Permiso revocado o fuente desactualizada: bloquear; cambio de monto invalida aprobación; reintento conserva identidad de efecto.

**Reglas de negocio y validaciones:** Capacidad agéntica se clasifica por efecto; una instrucción de prompt no sustituye control de servicio. No existe compra/cobro autónomo inicial.

**Datos y estados involucrados:** Política, versión herramienta, propuesta, huella aprobada, aprobador, vigencia y resultado. Transiciones conservan actor, tenant, fecha y versión; el modelo específico detalla los estados.

**Interacción humana/agéntica:** el humano responde por revisión y aprobación; el agente solo consulta o propone dentro del permiso. Herramientas candidatas, campos mínimos, límites cero para compromiso, evidencia y reversión se detallan en [gobernanza comparada](../../docs/investigacion-competitiva/agentes.md) y [seguridad compartida](../../docs/arquitectura/seguridad.md). Fallar cerrado si faltan evidencia, permiso o conectividad.

**Dependencias:** Q-CORE-01/02/03; autoridad y permisos del proveedor cuando exista integración. El core no depende de ninguna vertical para funcionar.

**Riesgos:** Confused deputy, prompt injection, aprobación reutilizada y elevación de privilegios.

**Criterios de aceptación Given/When/Then:**

- AC-US-CORE-003-01: Dada aprobación por 10000 CLP, cuando la propuesta cambia a 11000, entonces no se ejecuta con el permiso anterior.
- AC-US-CORE-003-02: Dado conector de lectura, cuando una respuesta solicita escritura, entonces la capa de autorización deniega y registra.

**Métricas de éxito:** Acciones fuera de política en suite; intervenciones/acciones propuestas; costo y p95 por acción. Valores objetivo y ventanas deben ratificarse; no hay resultados medidos ni beneficio financiero calculado.


## Requisitos derivados de investigación competitiva

Son propuestas de comportamiento propio, sin atribuirlo como implementación observada del competidor.

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-010 | Mantener por tenant un perfil de conector con proveedor/cuenta, país/plan cuando aplique, operaciones y permisos verificados, versión y evidencia de revisión; denegar capacidades no habilitadas | H1/H3 |
| FR-011 | Conciliar eventos externos correlacionados y sus estados sin retroceso por mensajes repetidos o antiguos; conservar pendientes con motivo y responsable de regularización | H2 |

- NFR-006: toda oferta, extracción o decisión derivada declara procedencia, vigencia e incertidumbre; si no hay evidencia suficiente, no genera compromiso automático ni se informa como éxito. La captura manual conserva permisos, trazabilidad e idempotencia equivalentes.

## Profundización funcional de las otras verticales

Estado **REQUISITO PROPUESTO**; evidencia adicional y límites en investigación competitiva/continuacion-01. Conserva IDs/historias previos y bloqueos.

### RF-CORE-01 — Declarar efectos externos de cada herramienta

**Historia US-CORE-003** (misma historia/ID, prioridad P2; no es historia nueva).

Como responsable de integraciones y aprobador, quiero declarar efectos externos de cada herramienta, para evitar que guardar un contacto o recibir un evento envíe mensajes o ejecute compromisos sin autorización.

**Descripción y necesidad:** refinamiento funcional de la necesidad anterior. La propuesta precisa responsabilidad, recuperación y significado del éxito; no presupone demanda ni beneficio medido.

**Inspiración y evidencia:** I11, I17, H13, H15, con URLs y límites en matriz-evidencias.md. Reconstrucción documental e **INFERENCIA PROPIA** para el diseño; no comportamiento ejecutado ni arquitectura observada.

**Disparador:** se habilita o invoca una operación de conector o se procesa una notificación.

**Precondiciones:** tenant/cuenta verificados, operación soportada y permisos/revisión definidos.

**Flujo principal:**

1. Consultar capacidad y efectos declarados por operación, incluidos flags de envío.
2. Validar intención, destinatario, datos mínimos y permiso para cada efecto.
3. Preparar vista previa o borrador sin envío cuando falte autorización.
4. Ejecutar solo alcance aprobado, registrar resultado y conciliar desconocidos.

**Flujos alternativos y excepciones:** Contrato incompleto o placeholder: operación no habilitada. Evento duplicado no repite envío. No inferir permiso de API desde documentación pública.

**Reglas de negocio/validaciones:** El método HTTP y la etiqueta MCP readOnly no prueban ausencia de efectos. Recepción/acuso, consulta, actualización y envío son resultados distintos; tenant se resuelve por identidad/cuenta autorizada, no texto o payload arbitrario.

**Datos y estados:** PerfilOperacion con efectos/flags; IntencionEnvio/destinatario; EventoExterno y evidencia mínima; estado propuesto/autorizado/intentado/confirmado/desconocido.

**Dependencias:** Q-CORE-01/03 y contrato real por operación; no incluye un motor CRM compartido.

**Riesgos:** Exfiltración, spam, cruce de empresas, firma de aprobación reutilizada y éxito aparente.

**Humano y agente:** consulta/borrador dentro de permiso; compromiso financiero/tributario/contractual o cierre técnico requiere control determinista y aprobación humana. Ningún MCP recibe escritura por defecto. Evidencia original, versión, aprobación y resultado se auditan; resultado desconocido se reconcilia, no se presenta confirmado. La capacidad concreta se delimita en [perfiles de agentes](../../docs/investigacion-competitiva/continuacion-01/perfiles-agentes.md).

**Aceptación Given/When/Then propuesta (no ejecutada):**

- AC-US-CORE-003-03: Dada herramienta de contacto con flag de envío, cuando solo se autorizó guardar datos, entonces el adaptador no envía correo y registra los efectos excluidos.
- AC-US-CORE-003-04: Dada página de contrato con placeholder o efectos desconocidos, cuando se intenta habilitar la herramienta, entonces queda bloqueada sin llamar al destino.
- AC-US-CORE-003-05: Dada notificación de cuenta A repetida con referencia de B, cuando se procesa, entonces no accede a B ni repite comunicación; registra discrepancia para revisar.

**Métricas:** efectos no autorizados/ejecuciones; duplicados por evento; costo completo y p95 de revisión por acción. Informar unidad, numerador/denominador y ventana; sin muestra no se informa porcentaje. Objetivos y políticas siguen pendientes de ratificación.


## Requisitos de recuperación y semántica de dominio

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-012 | Declarar y autorizar los efectos externos de cada operación y parámetro del conector, incluidos mensajes o cargos implícitos; impedir efectos no aprobados aunque la herramienta se etiquete de lectura o guardado | H3 |


### Bloqueos adicionales de la profundización

Q-CORE-04: ver [decisiones pendientes](../../docs/investigacion-competitiva/decisiones-pendientes.md). Son reglas para ratificar, no respuestas inferidas del mercado. Las historias permanecen propuestas y la feature **BLOCKED** para implementar.
