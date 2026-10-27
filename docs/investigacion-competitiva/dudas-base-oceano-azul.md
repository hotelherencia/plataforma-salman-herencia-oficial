# Dudas de base y océano azul — investigación con REA y fuentes públicas

Fecha: 2026-10-27. Investigación de las dudas de base (Q-HOT-01/02/03, Q-CORE-01/02/03)
con práctica de mercado. **No cierra ninguna Q ni T104/T105/T204**: la spec dice que la
documentación pública no cierra esas tareas. Ninguna propuesta queda ratificada: todas
siguen sin firma en `backlog/hotel/acta-para-firmar.md`. Una práctica de un competidor es
evidencia de mercado, no una decisión de Herencia.

Clases: **HECHO DOCUMENTADO** (fuente primaria abierta en esta sesión), **INFORMACIÓN NO
VERIFICADA** (fuente que no pude abrir o que solo conozco por un resumen de búsqueda),
**HIPÓTESIS** (afirmación de mercado sin prueba) y **NO MEDIDO** (no hay cifra con fuente).

## 0. Registro de verificación

Qué abrí yo en esta sesión y qué no. Una fila sin «abierta» no sostiene ninguna clase de
HECHO DOCUMENTADO.

| Fuente | Estado | Qué confirma |
|---|---|---|
| `github.com/morluto/rea` (clon) | Abierta | Clon OK; commit de HEAD `bcc6775dc1c29c06a08798b73049d0bf506e6b55` |
| `docs.mews.com/getting-started/glossary` | Abierta | El Access Token suele identificar una sola Property; existe un Portfolio Access Token para varias |
| `sii.cl/preguntas_frecuentes/factura_electronica/001_003_2167.htm` | Abierta | Anulación de DTE aceptado por el SII; corrección con Nota de Crédito electrónica en el mismo período o el siguiente, con campo de anulación |
| `sii.cl/portales/mipyme/guia_emision_nce_archivos.htm` | Abierta | Nota de Crédito Electrónica; **no** aparece el código numérico 61 |
| `docs.oracle.com/.../t_workflow_updating_housekeeping_room_status.htm` | Abierta | Estados de limpieza Clean, Dirty, Inspected (opcional), Pickup (opcional) |
| `developers.cloudbeds.com/reference` (redirige desde `hotels.cloudbeds.com/api/v1.1/docs/`) | Abierta, parcial (primeros 100 000 caracteres) | Campos `roomOccupied`, `roomCondition`, `roomBlocked` en `getHousekeepingStatus` y `postHousekeepingStatus`. **No** vi un endpoint de «fuera de servicio» en la parte leída |
| `myfrontdesk.cloudbeds.com/hc/...Housekeeping-room-conditions` | **403, no abierta** | — |
| `oracle.com/contracts/docs/hosp_retail_cloud_service_2511377.pdf` | **403, no abierta** | — |
| Búsqueda sobre registro de huéspedes en Chile (resumen de búsqueda) | Resumen, no página abierta | No aparece una fuente chilena que exija ficha de huésped; sí aparece el registro SERNATUR de prestadores turísticos |
| Búsqueda sobre Booking.com connectivity (resumen de búsqueda) | Resumen, no página abierta | Ver Q-HOT-02 |
| Resto de URLs citadas en la versión anterior de este archivo (Duve, Mercado Pago, SymSelling, GaosDev, LodgeHog, StayNTouch, cott.tv, socialanimal, comparatifchannelmanager, cloudbeds.com/articles, Amenitiz, docs de Mews `connector-api`) | **No abiertas en esta sesión** | Ninguna afirmación que dependía solo de ellas se conserva como HECHO |

**Corrección respecto de la versión anterior:** esa versión marcaba como «consultado 2026-10-27»
varias URLs que no pude abrir en esta sesión. Esas afirmaciones bajan a INFORMACIÓN NO VERIFICADA
o se retiran.

## 1. REA (solo lectura)

- Repositorio: `morluto/rea`. Clon: **OK** con `gh repo clone` en directorio temporal fuera
  de este repositorio. Commit de HEAD leído: `bcc6775dc1c29c06a08798b73049d0bf506e6b55`,
  fecha 2026-10-27 (+0800). Fecha de lectura: 2026-10-27.
- README: se presenta como «One MCP for reverse engineering across binaries, applications,
  and runtime behavior». Indica como fuentes oficiales `github.com/morluto/rea`, `rea.tools`
  y el paquete npm `rea-agents`.
- `package.json` exige Node `^22.23.4 || ^24.22.1 || >=26.12.1`. El runtime local
  registrado en las decisiones previas (Node 18.19.1) no cumple. No cambié la versión de Node.
- **No se ejecutó REA** (ni `npx rea-agents setup`, ni instalación global, ni bridge). Solo
  lectura de README, `package.json` y commit. No se copió código al producto.
- Nota: el historial de consolidación (`docs/historial-consolidacion.md`, sección
  «Investigación competitiva») dice que el clon falló por conectividad y cita el commit
  `4838f44`. Hoy el clon funcionó y el HEAD es otro. El historial queda desactualizado.
- Q-REA-01, Q-REA-02, Q-REA-03 y Q-TOOL-01 siguen sin ítem y sin respuesta. Esta
  investigación no las cierra.

## 2. Tablas por duda

### Q-HOT-01 — PMS: fuente de inventario, habitación, tipo y cupo por fecha

| Práctica observada | Fuente | Clase | Queda para la firma del propietario |
|---|---|---|---|
| Opera publica cuatro estados de limpieza: Clean, Dirty, Inspected (opcional, solo con el control Inspected Status activo) y Pickup (opcional, servicio mínimo de «touch-up») | Oracle, `t_workflow_updating_housekeeping_room_status.htm` (abierta) | HECHO DOCUMENTADO | Cuáles de estos estados entran en la spec de limpieza, y si Pickup existe en Herencia |
| Cloudbeds calcula el estado de housekeeping (`getHousekeepingStatus`, `postHousekeepingStatus`) a partir de `roomOccupied`, `roomCondition`, `roomBlocked` y `vacantPickup` | developers.cloudbeds.com/reference (abierta, parcial) | HECHO DOCUMENTADO | Qué campo de la unidad es fuente de verdad en Herencia (Q-HOT-01) |
| Cloudbeds tiene endpoints de bloqueo de habitación (`postRoomBlock`, `getRoomBlocks`, `putRoomBlock`, `deleteRoomBlock`) | Mismo reference (abierta, parcial) | HECHO DOCUMENTADO (nombres de endpoint) | Si el bloqueo técnico es una entidad propia o un estado de la unidad |
| Un endpoint de «fuera de servicio» en Cloudbeds | No visto en los primeros 100 000 caracteres | NO VERIFICADA | — |
| «Clean/Dirty no impacta la disponibilidad» en Cloudbeds | Artículo de ayuda, 403 | NO VERIFICADA | — |
| Estados de la unidad que excluyen del cupo vendible | No hay fuente abierta que lo confirme | NO MEDIDO | Regla de cupo vendible: propiedad del hotel |
| Ciclo de estados de tipo de habitación o tarifa | No encontrado en fuentes abiertas | NO MEDIDO | Q-HOT-03 |

### Q-HOT-02 — Channel manager: dos sentidos, acuse ≠ aceptación, último cupo

| Práctica observada | Fuente | Clase | Queda para la firma del propietario |
|---|---|---|---|
| Booking.com ofrece APIs de conectividad (disponibilidad, reservas, precios) con formato OTA 2003B y B.XML | developers.booking.com/connectivity/docs (resumen de búsqueda, **no abierta**) | INFORMACIÓN NO VERIFICADA | — |
| Booking.com recomienda certificación para APIs críticas y autoevaluación para algunas APIs básicas; la certificación incluye pruebas de endpoints | developers.booking.com/connectivity/docs/going_live (abierta) | HECHO DOCUMENTADO | Q-HOT-02 opción 3 exige certificación; el plazo lo fija Booking |
| Booking.com estaría pausando la incorporación de nuevos proveedores de conectividad | connect.booking.com (solo resumen de búsqueda; no abierta). La página `going_live` abierta **no** menciona pausa | INFORMACIÓN NO VERIFICADA. **Señal relevante**: si es cierta, la vía «conector directo a Booking» no está disponible hoy | Q-HOT-02: confirmar con Booking antes de elegir canal |
| Un PMS tarda 12 a 18 meses en certificar Booking | Blog de vendor (no abierto) | NO VERIFICADA | — |
| Acuse de recepción distinto de aceptación en la práctica de channel managers | Ninguna fuente abierta lo formaliza | NO MEDIDO | Q-HOT-04/05/06 (ya en `002/T202`) |
| Cifra de latencia de sincronización | Sin cifra publicada en fuentes abiertas | NO MEDIDO | Definir objetivo y medir (SC-002 propone <5 min, sin ratificar) |

### Q-HOT-03 — Tarifa, cancelación, anticipo, cuenta, cargo, datos de huésped, autonomía

| Práctica observada | Fuente | Clase | Queda para la firma del propietario |
|---|---|---|---|
| Ciclo de estados publicado para tarifa, política de cancelación o anticipo | No encontrado en fuentes abiertas | NO MEDIDO | Q-HOT-03 nombra esos estados |
| Autonomía de un agente de hotel con cobro: un límite monetario estándar de «cero hasta aprobación» | No hay fuente abierta. La versión anterior citaba Duve, no abierta | NO MEDIDO | Q-HOT-03: límite autónomo. La constitución 1.1.0 propone 0 CLP como control inicial (sin ratificar) |
| Datos de huésped exigidos en Chile | Búsqueda sin fuente chilena: el resultado fue el registro SERNATUR de **prestadores turísticos** (inscripción de la empresa), no la ficha de huésped. Las fuentes de registro de huéspedes encontradas son de España y Uruguay | NO VERIFICADA (no encontré norma chilena de ficha de huésped) | Q-HOT-03: documentación mínima de check-in. Consultar a un especialista en turismo y a SERNATUR (sernatur.cl) |

### Q-CORE-01 — Dueño del dato y origen de la empresa

| Práctica observada | Fuente | Clase | Queda para la firma del propietario |
|---|---|---|---|
| En Mews, el Access Token identifica una Property (hotel). Existe un Portfolio Access Token para varias propiedades de un portafolio. Un Enterprise puede ser un único cliente o un grupo de propiedades (por ejemplo, un campus) | docs.mews.com/getting-started/glossary (abierta) | HECHO DOCUMENTADO | Q-CORE-01: matriz empresa/rol/recurso. Mews muestra dos modos (token por propiedad o portafolio), no una regla única |
| El `x-hotelid` de Oracle OHIP fija el hotel | Artículo tercero (cott.tv), no abierto | NO VERIFICADA | — |
| Ninguna fuente abierta fija «empresa legal vs establecimiento» como regla única | — | NO MEDIDO | Q-CORE-01 sigue abierta; `company_id` vs `establishment_id` sin trazar (corrección 4) |

### Q-CORE-02 — Documento tributario en Chile

| Práctica observada | Fuente | Clase | Queda para la firma del propietario |
|---|---|---|---|
| Un DTE aceptado por el SII no se edita: se anula o se corrige con Nota de Crédito Electrónica. La NCE se emite en el mismo período tributario o, a más tardar, en el siguiente, e incluye un campo que indica anulación | SII, `001_003_2167.htm` (abierta) | HECHO DOCUMENTADO | Q-CORE-02: política de corrección y responsable tributario |
| Código numérico del tipo de documento de la NCE (61) | Las dos páginas del SII abiertas no lo citan | NO VERIFICADA (el código 61 no lo he comprobado en fuente abierta) | — |
| Proveedores de facturación en Chile (POS con emisión al SII, APIs de DTE, pasarelas) | Sitios de proveedores, no abiertos | NO VERIFICADA | Q-CORE-02: proveedor DTE |
| «Cuál usa un hotel en Chile» | — | NO MEDIDO | Q-CORE-02 |
| Anti-duplicidad por anticipo mediante folio del SII | Vendor no abierto. El folio es regla SII conocida, pero no la comprobé en fuente abierta | NO VERIFICADA | Q-CORE-02 con responsable tributario |

### Q-CORE-03 — Retención, exportación, recuperación, RPO/RTO

| Práctica observada | Fuente | Clase | Queda para la firma del propietario |
|---|---|---|---|
| Oracle publica una «Service Description» contractual de Opera Cloud | Existe la URL; el PDF devolvió 403 | NO MEDIDO (valores RPO/RTO no leídos) | — |
| Una guía de vendor recomienda RPO ≤ 1 h para PMS | No abierta | HIPÓTESIS | — |
| RPO/RTO publicados por Mews, Cloudbeds u otros PMS | No encontrados en fuentes abiertas | **No publicado** (en lo que pude leer) | Q-CORE-03 sigue sin propuesta. La investigación puede informar opciones, no elegir una |

## 3. Funcionamiento y rendimiento

| Métrica | Cifra con fuente abierta | Clase |
|---|---|---|
| Latencia de sincronización de canal | Ninguna | NO MEDIDO |
| Disponibilidad de PMS o CM | Ninguna | NO PUBLICADO |
| Tasa de conflicto de último cupo | Ninguna | NO MEDIDO |

## 4. Corrección de datos

| Práctica observada | Fuente | Clase |
|---|---|---|
| El DTE aceptado no se reescribe: se anula o se corrige con NCE en el período tributario siguiente | SII, `001_003_2167.htm` (abierta) | HECHO DOCUMENTADO |
| La NCE corrige con un documento nuevo que referencia al original | SII, guía de NCE (abierta) confirma el documento; no confirma el código numérico | HECHO DOCUMENTADO (parcial) |
| Edición directa de un documento emitido | No existe en fuentes abiertas. Coherente con la spec: «nunca borrar el rastro de rechazo» | Por ausencia, HIPÓTESIS |

## 5. Océano azul

**Qué se puede afirmar con fuente abierta:**
- Opera y Cloudbeds separan el estado de limpieza de la condición de la unidad (bloqueo, ocupada).
- Mews resuelve el dueño con token por propiedad o por portafolio. No hay regla única publicada.
- El SII trata el DTE aceptado como inmutable: se corrige con NCE, no con edición.

**Qué no se puede afirmar todavía (y lo que la versión anterior daba por sentado):**
- «Todos resuelven bien el flujo feliz»: HIPÓTESIS.
- «El mercado solo promete la última unidad con pooled inventory»: no lo he verificado en fuentes abiertas. HIPÓTESIS.
- «Un agente de cobro sin límite es práctica estándar»: NO VERIFICADA. La versión anterior citaba un vendor no abierto.
- «Booking ofrece conexión directa para cualquier PMS»: revisar. La señal de pausa de onboarding la vuelve dudosa.

**Palancas para la plataforma Salman, con su clase:**
- **Una sola regla de empresa para las cuatro verticales** (hotel, cafetería, inmobiliaria, constructora), con el identificador de empresa tomado del contexto autenticado. Mews muestra el patrón «token identifica la propiedad»: HECHO DOCUMENTADO como práctica; para Salman es propuesta sin firma (Q-CORE-01).
- **Reserva local que niega la doble confirmación de la última unidad**: el incremento 0 lo cumple en memoria (10 pruebas). Como ventaja frente al mercado: HIPÓTESIS, porque no tengo datos competitivos abiertos.
- **Puertos que responden «no configurado» en lugar de simular cobro, canal o PMS**: diferencia de diseño con el código propio (HECHO DOCUMENTADO local). Frente a demos de mercado: HIPÓTESIS.
- **Agente que prepara y no compromete dinero** mientras el límite autónomo esté en 0 CLP como control propuesto: HIPÓTESIS. Constitución 1.1.0 sin ratificar.

## 6. Qué puede informar la firma futura y qué sigue bloqueado

**Puede informar la firma (evidencia de mercado, no decisión):**
- Q-HOT-01: estados de limpieza de Opera y campos de housekeeping de Cloudbeds. La fuente de inventario (PMS o plataforma) sigue siendo del propietario.
- Q-HOT-02: la confirmación de si Booking acepta hoy nuevos proveedores de conectividad. Es la pregunta que más cambia la opción de canal.
- Q-CORE-01: el modelo de token por propiedad o por portafolio de Mews. La matriz empresa/rol sigue pendiente.
- Q-CORE-02: la NCE como mecanismo de corrección. Proveedor y código numérico pendientes.
- Q-CORE-03: solo se sabe que no encontré RPO/RTO publicados. Hay que abrir el PDF de Oracle (403) antes de decir más.

**Sigue bloqueado:** el modelo físico, los adaptadores (pago, documento, canal, PMS) y cualquier paso a base de datos, por Q-CORE-01, Q-CORE-02, Q-CORE-03, Q-HOT-01, Q-HOT-02 y Q-HOT-03 sin firma. Las siete líneas «Firma, nombre, fecha» del acta siguen en blanco; las cinco T003 siguen en Backlog. Q-REA-01/02/03 y Q-TOOL-01 siguen sin ítem. T104, T105 y T204 no se cerraron.

**Fuentes que faltan para cerrar la investigación:** Cloudbeds housekeeping (403), Oracle service description (403), página oficial de Booking «going live» y de connectivity partners, y una norma o página de SERNATUR sobre registro de huéspedes.
