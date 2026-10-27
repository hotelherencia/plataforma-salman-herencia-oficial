# Cierre de dudas de base — cierre documental o decisión humana

> Nota de reconciliación (2026-10-27): esta nota registra el momento anterior a
> `backlog/hotel/resolucion-dudas-2026-10-27.md`. El estado vigente de las cinco
> T003 se fija por evidencia en `backlog/indice.md` (nota de reconciliación):
> `000-core/T003` y `002-hotel-reservas-concierge/T003` Hechas; las demás Bloqueadas.

Fecha: 2026-10-27. Clasificación de las dudas de base usando únicamente lo medido
en `docs/investigacion-competitiva/dudas-base-oceano-azul.md`. Una práctica de un
competidor no es una decisión de Herencia. Esta nota **no firma nada**: las siete
líneas «Firma, nombre, fecha» del acta siguen en blanco, las cinco T003 siguen en
Backlog y las seis correcciones de `backlog/hotel/correccion-datos-backend.md` no se
reabren.

## 1. Q-HOT-01 — PMS, habitación, tipo y cupo

**CIERRE DOCUMENTAL.** Opera publica Clean, Dirty, Inspected y Pickup. Cloudbeds
publica campos de housekeeping y endpoints de bloqueo. La regla «la limpieza no
saca la unidad del cupo» y el endpoint de fuera de servicio siguen NO VERIFICADOS.

**DECISIÓN HUMANA PENDIENTE.** Pregunta para el propietario: «¿Cuál es la fuente de
inventario de verdad: el PMS actual, el sistema de la plataforma, o ambos con
sincronización?». Lo informa: tabla Q-HOT-01 (multi-propiedad por token en Mews;
estados publicados) y la propuesta no ratificada de `backlog/hotel/respuestas-propuestas.md`
(inventariar antes de construir, F-005). No es una firma.

Queda bloqueado: FR-003 (sincronización con canales) y cualquier puerto PMS real.

## 2. Q-HOT-02 — Channel manager y contrato

**DECISIÓN HUMANA PENDIENTE.** Pregunta: «¿Channel manager contratado con API,
conector propio con certificación, o captura controlada mientras tanto (aceptando
que no cumple FR-003 en su forma actual)?». Lo informa: tabla Q-HOT-02 del informe
(inventario pooled y dos vías como mecanismo anti-sobreventa; Booking exige
connectivity provider aprobado — INFORMACIÓN NO VERIFICADA de tercero, coherente
con F-009).

**En espera, no cerrado:** el acuse de recepción distinto de la aceptación quedó
«No medido» en fuentes primarias; no se cierra. Q-HOT-04, Q-HOT-05 y Q-HOT-06
siguen en `002/T202`; T202 no se parte. La latencia de sincronización queda «no
medido»: no se adopta el eslogan «real time» como indicador.

Queda bloqueado: FR-003 y los conectores Booking/Airbnb.

## 3. Q-HOT-03 — Tarifa, cancelación, anticipo, cuenta, cargo, huésped, autonomía

**DECISIÓN HUMANA PENDIENTE.** Pregunta: «¿Qué política de cancelación y de cobro
anticipado aplica (total, parcial o garantía), y qué documentación mínima exige el
check-in?». Lo informa: tabla Q-HOT-03 del informe (Duve documenta upsell con link
de pago ligado a la reserva y cobro a través del proveedor configurado; no se
publica ciclo de estados para tarifa/cancelación/anticipo — no medido). No se
nombran los estados que faltan.

**Condición no decidida:** el límite autónomo de 0 CLP sigue siendo un control
propuesto de la constitución 1.1.0, **sin ratificar**; no se convierte en umbral.

**FALTA INFORMACIÓN.** El registro de huésped en Chile no tiene fuente oficial en
el informe (solo España, RD 933/2021 y SES.Hospedajes). No se formula el dato a
pedir ni el que no se guarda. Ver «Base nueva» al final.

Queda bloqueado: los ciclos de tarifa, política de cancelación, anticipo, cuenta y
cargo (corrección 2: DEFINICIÓN PENDIENTE DE FIRMA).

## 4. Q-CORE-01 — Dueño del dato y origen de la empresa

**CIERRE DOCUMENTAL.** en Mews el token identifica una propiedad, o varias si es
token de portafolio. x-hotelid sigue NO VERIFICADO. El dueño canónico, empresa
legal o establecimiento, sigue en DECISIÓN HUMANA PENDIENTE y SIN TRAZA.

**DECISIÓN HUMANA PENDIENTE.** Pregunta: «¿Una sola empresa para V1 sin acceso
cruzado, o varias del grupo separadas, y cuál es el dueño canónico del dato: la
empresa legal o el establecimiento?». Lo informa: tabla Q-CORE-01 (conviven
propiedad-por-cuenta, grupo y cadena sin regla única publicada). `company_id` y
`establishment_id` siguen **SIN TRAZA** (corrección 4): no se elige dueño.

Queda bloqueado: el modelo físico y la matriz empresa/rol/recurso.

## 5. Q-CORE-02 — Documento tributario

**CIERRE DOCUMENTAL.** un DTE aceptado por el SII no se edita; se anula o se
corrige con nota de crédito electrónica, en el mismo período o a más tardar en el
siguiente. El código 61 y Mercado Pago siguen NO VERIFICADOS.

**DECISIÓN HUMANA PENDIENTE.** Pregunta: «¿Qué proveedor de boleta/factura
electrónica usará el hotel y qué política de emisión aplica por contribuyente
(boleta siempre, ¿factura a empresas desde V1?)?». Lo informa: tabla Q-CORE-02
(existe oferta de facturadores y emisión vía POS/pasarela; «cuál usa un hotel en
Chile» no se midió). Queda con el responsable tributario, sin firma.

Queda bloqueado: el adaptador de documento tributario (corrección 6).

## 6. Q-CORE-03 — Retención, exportación, recuperación

**DECISIÓN HUMANA PENDIENTE.** Pregunta: «¿Quién es el responsable o encargado del
tratamiento, con qué finalidad y plazo de retención, y qué objetivos RPO/RTO y
presupuesto se fijan?». Lo informa: tabla Q-CORE-03 del informe (RPO/RTO de los
PMS medianos: **No publicado**; Oracle publica un documento contractual cuyos
valores no se leyeron; la guía StayNTouch con objetivo RPO ≤ 1 h es **HIPÓTESIS**).
No se elige hora ni presupuesto y esta nota **no agrega propuesta**:
`backlog/hotel/respuestas-propuestas.md` sigue mostrando Q-CORE-03 sin propuesta.

Queda bloqueado: NFR de retención/restauración y cualquier decisión de
infraestructura.

## 7. Océano azul — las cuatro palancas

Quedan como **propuesta, no como requisito**, conservando la clase que el informe
ya dio a cada una, sin agregar una quinta:
1. Una sola regla de empresa para cuatro verticales con identificador desde
   contexto autenticado — práctica de mercado HECHO DOCUMENTADO (token/x-hotelid);
   para Salman es propuesta sin firma (Q-CORE-01).
2. Reserva local que ya niega la doble confirmación de la última unidad —
   HECHO DOCUMENTADO local (código y 10 pruebas); la venta frente a mercado que
   solo promete pooled inventory sin cifra es HIPÓTESIS.
3. Puertos que responden «no configurado» en lugar de simular cobro, canal o PMS —
   HECHO DOCUMENTADO local.
4. Agente que prepara y no compromete dinero mientras el límite autónomo sea 0 CLP
   como control propuesto no ratificado — HIPÓTESIS como diferenciador hasta
   medirlo contra Duve y pares.

## 8. Q-REA-01, Q-REA-02, Q-REA-03 y Q-TOOL-01

Siguen **sin ítem y sin respuesta**. El clon de REA en solo lectura (commit
`bcc6775`) no las responde. No se cierran, no se crean issues y no se declara REA
ejecutado. T104, T105 y T204 quedan intactas: la documentación pública no las
cierra.

## Qué puede informar una firma futura

- Q-HOT-01: la separación limpieza/inventario y los estados de unidad publicados
  respaldan FR-016 como práctica de mercado.
- Q-CORE-01: el origen de la empresa desde contexto autenticado (token/x-hotelid)
  como modelo a exigir en la matriz.
- Q-CORE-02: la prohibición de reescribir el DTE y el mecanismo nota de crédito
  como invariante del puerto documental.
- Q-CORE-03: el rango de opciones observado (documento contractual tipo Oracle;
  objetivos tipo guía de comprador) para la futura propuesta.

## Qué sigue bloqueado

El modelo físico, los adaptadores (pago, documento tributario, canal, PMS) y
cualquier paso a base de datos; las siete firmas del acta en blanco; las cinco
T003 en Backlog; Q-HOT-04/05/06 en `002/T202` sin partir; Q-REA-01/02/03 y
Q-TOOL-01 sin ítem.

## Base nueva

Base nueva: ¿Qué datos del huésped debe registrar y reportar un hotel en Chile, ante qué organismo oficial y dentro de qué plazo?
Dónde buscar: fuente primaria chilena — Policía de Investigaciones (denuncia de alojamiento), SERNATUR o la norma legal aplicable (ley/decreto publicado en LeyChile); no blogs.
Por qué esta y no otra: llena la FALTA INFORMACIÓN de Q-HOT-03 (datos de registro y check-in digital) y alimenta Q-CORE-03 (finalidad y base legal del tratamiento, Ley 19.628 y transición 21.719 ya citadas en la constitución propuesta). Q-HOT-02 (acuse≠aceptación), Q-CORE-01 (dueño canónico) y Q-CORE-02 (proveedor DTE) quedan en espera: sus huecos no se llenan con otra búsqueda documental, sino con la firma del propietario.
