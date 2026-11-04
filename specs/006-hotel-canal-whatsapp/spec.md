# Especificación — Canal público WhatsApp del hotel

Feature: `006-hotel-canal-whatsapp`. Fecha: 2026-11-04.
Estado: **PROPUESTA DISEÑADA, NO CONSTRUIDA** — responde al issue #324 del
backlog v1 y a la orden del propietario del 2026-11-04 («el canal público
puede ser WhatsApp, algún agente que reciba la petición de reserva y responda
a consultas derivando a 1 agente; crear historias de usuario para integrar
Meta; lo mínimo es integrar asistencia por IA»). Ninguna historia de este
paquete se construye hasta que el propietario autorice el adaptador Meta
(D-WSP-01). La regla vigente no cambia: Meta/WhatsApp existe solo como
puerto; sin adaptador responde 503 «no configurado» y la operación queda
pendiente (AGENTS.md).

Antecedentes que este paquete acota y reemplaza para V1: historia 3 de
`specs/002-hotel-reservas-concierge` («Concierge agéntico por WhatsApp»),
ya acotada por `specs/005-hotel-agente-reservas` (D-AGT-03: canal de
respuesta para N1, cada opción es un adaptador que requiere autorización).
Este paquete es la cara pública de esa decisión: **entrada** por WhatsApp
(huésped escribe al hotel) y **salida** por el mismo canal cuando N1 lo
permita.

## 1. Problema, actores y límites

HECHO DOCUMENTADO (2026-11-04):

- Las consultas de https://hotelherencia.cl/ llegan a Formspree, fuera de la
  plataforma; la revisión de esa integración es materia del issue #308.
- El canal público propio (v1-issue-22/24) ya recibe solicitudes desde la
  landing y deja traza reconcilible: `solicitudes.origen = 'landing'` y
  `solicitudes.reserva_id`.
- El agente N0 (specs/005, V1-ISSUE-29) ya registra consultas entrantes con
  `canal_origen ∈ {manual, landing, correo, whatsapp}` y produce borradores
  verificados. **Ese N0 ya es la asistencia por IA mínima ordenada por el
  propietario.**
- La escalada a un humano ya existe: borrador `escalado` llega a la bandeja
  de recepción y esa bandeja es la cola de derivación a 1 agente.
- WhatsApp (Meta) no tiene adaptador: es un puerto. Ninguna llamada real a
  Meta se hace sin autorización específica.

**Problema.** El huésped quiere escribirle al hotel por WhatsApp (el canal
que ya usa) y espera una respuesta que hoy depende de que recepción vuelque
el mensaje a mano en la plataforma. El objetivo es que ese mensaje entre a
la plataforma como consulta del agente, el agente proponga el borrador y la
respuesta final la envía (o aprueba) una persona.

**Actores:**

- huésped (escribe por WhatsApp al número del hotel);
- recepción (atiende bandeja, aprueba, edita, escala y envía);
- agente N0/N1 (identidad de servicio, asistencia por IA; specs/005);
- Meta WhatsApp Business Platform (puerto externo, sin autoridad).

**Fuera de alcance en V1:**

- adaptador real de Meta (requiere D-WSP-01: cuenta, número, plantillas,
  autorización del propietario);
- pagos, enlaces de pago y cobro de garantías por WhatsApp;
- cancelaciones y cambios de fecha por WhatsApp;
- canales OTA y broadcast/marketing (plantillas promocionales).

## 2. Evaluación de la traza de canal (issue #324)

HECHO (verificación 2026-11-04): «ingresos por canal» completo no es
calculable con los datos actuales. El subconjunto landing es reconcilible
vía `solicitudes`; las reservas directas de recepción no registran canal.

PROPUESTA registrada (no implementada): columna `reservas.canal`
(orígenes `{recepcion, landing}`) obligatoria en `crear_reserva` y en la
conversión, o equivalente `reservas.solicitud_id`. Requiere decisión
explícita del propietario; este paquete no la implementa. Si se aprueba, la
métrica es suma de cargos por canal y debe pasar por el mismo ciclo
contrato-primero que cualquier cambio de contrato.

## 3. Alcance por fases

| Fase | Qué es | Estado |
|---|---|---|
| F0 — entrada manual | Recepción vuelca el mensaje de WhatsApp con `canal_origen = 'whatsapp'`; el agente N0 procesa y recepción responde por su celular | **EXISTE** (specs/005, V1-ISSUE-29) |
| F1 — entrada automática | Webhook inbound de Meta crea la consulta con `canal_origen = 'whatsapp'` y la deja en la bandeja del agente | Propuesta (este paquete); requiere D-WSP-01 |
| F2 — salida asistida | El borrador aprobado sale por el puerto de Meta (respuesta al hilo); sin adaptador → 503 y estado `pendiente_envio` | Propuesta; depende de F1 + D-AGT-03 (canal N1) |

La asistencia por IA (el «agente que responde a consultas») no se construye
en este paquete: ya es specs/005. Este paquete solo la **conecta** al canal
WhatsApp cuando exista adaptador.

## 4. Escenarios de usuario y pruebas

**Historia 1 (F1): el mensaje de WhatsApp entra a la bandeja**

Dado el webhook inbound configurado (D-WSP-01), cuando el huésped escribe al
número del hotel, entonces la plataforma crea una consulta del agente con
`canal_origen = 'whatsapp'`, el texto redactado y el identificador externo
de la conversación; el agente N0 produce su borrador y queda en la bandeja
de recepción como hoy.

- **Escenarios de aceptación:**
  1. Dado un mensaje de texto con fechas y personas, cuando llega por el
     webhook, entonces existe la consulta con `canal_origen = 'whatsapp'` y
     el borrador cita las cifras exactas de la oferta (mismo verificador de
     specs/005).
  2. Dado un mensaje ambiguo, cuando el agente procesa, entonces el borrador
     pide el dato faltante y recepción lo responde por el hilo.
  3. Dado un mensaje con inyección o datos sensibles, entonces aplica lo de
     specs/005 (escalada / redacción). El canal no debilita la política.
  4. Dada la firma inválida o el número no permitido, cuando llega el
     webhook, entonces se rechaza con 401/403 y nada se persiste.

**Historia 2 (F1): idempotencia y orden de la conversación**

- **Escenarios de aceptación:**
  1. Dado un reenvío del mismo mensaje de Meta, cuando llega duplicado,
     entonces no crea dos consultas (idempotencia por identificador externo
     + clave derivada).
  2. Dados dos mensajes del huésped en orden, cuando el agente procesa,
     entonces cada mensaje es un turno distinto de la misma conversación y
     el segundo ve el contexto del primero.
  3. Dado un webhook sin adaptador autorizado, cuando llega el mensaje,
     entonces la recepción lo atiende como hoy (vuelque manual, F0); nada
     se pierde.

**Historia 3 (F2): respuesta por el mismo hilo (solo con N1 y adaptador)**

Dado el borrador aprobado y la política en N1 (specs/005, D-AGT-03), cuando
recepción aprueba, entonces el puerto de Meta envía el borrador al hilo y la
consulta queda `enviado`. Sin adaptador o sin política, queda
`pendiente_envio` y recepción copia y envía a mano.

- **Escenarios de aceptación:**
  1. Dentro de la política (solo información, horario, sin datos sensibles),
     el mensaje sale y queda trazado.
  2. Fuera de la política, cae a N0 y la respuesta la envía una persona.
  3. Dado un fallo del puerto (Meta caído, plantilla rechazada), cuando se
     intenta el envío, entonces la consulta queda `pendiente_envio` con el
     motivo y se reintenta como máximo una vez (sin bucle).

**Historia 4 (F1): solicitud de reserva desde el chat**

Dado un huésped que acepta la cotización por WhatsApp, cuando recepción lo
confirma, entonces la reserva se crea por la misma operación interna
(`reservas.crear_reserva`) con la carrera por la última unidad; el canal no
abre una vía paralela. La solicitud pública por chat es materia de
v1-issue-22/24 y solo se reutiliza.

## 5. Requisitos

**Requisitos funcionales**

| ID | El sistema DEBE | Historia |
|---|---|---|
| FR-W01 | Exponer un endpoint webhook inbound que verifique firma/origen de Meta, normalice el mensaje a consulta del agente con `canal_origen = 'whatsapp'` y devuelva 2xx solo después de persistir | H1 |
| FR-W02 | Guardar el identificador externo (conversación y mensaje de Meta) en la consulta para idempotencia y respuesta al hilo | H1, H2 |
| FR-W03 | Persistir antes de responder al webhook: si la plataforma cae, Meta reintenta y la idempotencia absorbe el duplicado | H1, H2 |
| FR-W04 | Puerto `MensajeriaWhatsapp` con contrato `enviar(destino, texto)`: sin adaptador → 503 «no configurado» y estado `pendiente_envio`; con adaptador autorizado → envía al hilo | H3 |
| FR-W05 | Mantener el ciclo del borrador de specs/005 sin cambios: el canal solo cambia cómo entra el texto y cómo sale la respuesta | H1–H4 |
| FR-W06 | Rechazar webhooks con firma inválida o número no autorizado sin persistir nada | H1 |
| FR-W07 | La conversión a reserva pasa exclusivamente por `reservas.crear_reserva` (misma operación y carrera que recepción) | H4 |

**Requisitos no funcionales**

- **NFR-W01:** nada de Meta se persiste como hecho de negocio: cupo, tarifa
  y estado los produce el servidor; los mensajes entrantes son datos
  redactados igual que cualquier consulta (NFR-A03 de specs/005 aplica).
- **NFR-W02:** mínima superficie: el webhook solo acepta los campos que
  necesita la consulta (texto, conversación, remitente); adjuntos y
  ubicaciones se descartan en V1.
- **NFR-W03:** determinismo en las pruebas: el webhook se prueba con un
  emisor falso que reproduce payloads de Meta documentados; ninguna prueba
  de CI llama a Meta.
- **NFR-W04:** el freno de abuso del canal público (`FrenoDeSolicitudes`)
  aplica al webhook por remitente/numero, con el mismo patrón que
  `servicio/canal_publico.py`.
- **NFR-W05:** costo y límites de Meta (tope de mensajes, plantillas,
  ventana de 24 h) se configuran por empresa y al superarlos la respuesta
  cae a recepción sin pérdida.

## 6. Criterios de éxito (objetivos, no medidos)

| ID | Criterio |
|---|---|
| SC-W01 | 100 % de los mensajes webhook válidos quedan como consulta en la bandeja (medido en la suite con el emisor falso) |
| SC-W02 | 0 consultas duplicadas por reenvíos de Meta en la suite de idempotencia |
| SC-W03 | 0 respuestas enviadas fuera de la política de N1 (misma compuerta que SC-003 de specs/005) |

## 7. Decisiones pendientes (propietario)

- **D-WSP-01:** cuenta Meta / WhatsApp Business Platform, número, permisos
  de webhook y presupuesto. Sin esta decisión no hay adaptador; las
  historias F1/F2 quedan diseñadas pero no construidas.
- **D-WSP-02:** plantillas aprobadas y tono de las respuestas automáticas
  (ventana de 24 h, opt-in del huésped). Traslada D-AGT-06 al canal.
- **D-WSP-03:** horario de atención del canal y mensaje de fuera de horario
  (escalada a recepción o respuesta automática informativa).
- **D-CANAL-01 (del issue #324):** aprobar o descartar la columna
  `reservas.canal {recepcion, landing}` que habilita «ingresos por canal».
  Propuesta registrada en §2; requiere decisión explícita.

## 8. Supuestos

- SUPUESTO: el huésped escribe a un número del hotel ya existente (el de
  recepción); la migración a WhatsApp Business es parte de D-WSP-01.
- SUPUESTO: el volumen es bajo (hotel pequeño): el webhook persiste en la
  petición, sin cola, igual que el resto del servicio.
- SUPUESTO: mientras F1 no exista, F0 (vuelque manual con
  `canal_origen = 'whatsapp'`) ya deja la traza necesaria para medir el
  canal cuando D-CANAL-01 se apruebe.
