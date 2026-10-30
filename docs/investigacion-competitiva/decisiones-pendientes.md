# Decisiones pendientes — registro consolidado

Fecha de corte: 2026-10-30. Clase de evidencia: **REGISTRO DE ESTADO** (HECHO
DOCUMENTADO). Este documento **no propone respuestas**: las propuestas no
ratificadas del hotel viven en `backlog/hotel/respuestas-propuestas.md`. Su
propósito es (1) reparar la referencia rota que los specs hacen a esta ruta
(`specs/000-core/spec.md`, `specs/002-hotel-reservas-concierge/spec.md` y
`specs/003-inmobiliaria-comercial/spec.md` apuntan aquí) y (2) darle al
propietario una única hoja para cerrar preguntas con fecha y evidencia.

## Cómo se cierra una pregunta

Convención vigente desde el 2026-10-27 (`backlog/hotel/resolucion-dudas-2026-10-27.md`):
respuesta registrada con **fecha y evidencia** en este repo, tarea T003/T202
marcada en el `specs/*/tasks.md` correspondiente y tarjeta del tablero movida a
Done. Salida exigida por cada tarjeta «Decisión humana»: «decisión firmada o
registrada con fecha y evidencia para cada Q listada».

## Resueltas (registradas 2026-10-27, instrucción «resuelve cualquier cuello de botella»)

| Pregunta | Resolución por defecto (síntesis) | Evidencia |
|---|---|---|
| Q-CORE-01 | Una sola empresa para V1 (Herencia), sin acceso cruzado; dueño canónico = empresa legal; empresa desde contexto autenticado | `backlog/hotel/resolucion-dudas-2026-10-27.md`; `specs/000-core/tasks.md` T003 (cerrada) |
| Q-CORE-02 | Proveedor DTE por API (short-list Alegra/Siigo/Defontana); boleta siempre; factura a empresas desde V1; DTE emitido no se reescribe | idem |
| Q-CORE-03 | Valores iniciales: retención 6 años, RPO 1 h, RTO 4 h (HIPÓTESIS hasta medir); responsable = administrador de la empresa; validación jurídica Ley 21.719 antes de producción | idem |
| Q-HOT-01 | Plataforma = fuente de inventario del canal directo; PMS actual como adaptador; estado operativo quita cupo, limpieza no | idem |
| Q-HOT-02 | Channel manager contratado con API; plataforma construye conector del canal directo + adaptador | idem |
| Q-HOT-03 | Cancelación gratis hasta 48 h (después, primera noche); garantía con tarjeta; factura a empresas sí; registro mínimo; agente 0 CLP | idem |

Tarjetas de decisión que estas resoluciones cierran: `#22`, `#26`, `#83`, `#87`
(movidas a Done el 2026-10-30 con comentario de evidencia) y parcialmente `#91`
(Q-HOT-03 resuelta; Q-HOT-04 sigue abierta).

## Pendientes

### Core

**Q-CORE-04 — Efectos laterales por herramienta/parámetro; quién autoriza
mensajes o cargos y cómo se deduplican.**
Registrada en `backlog/hotel/respuestas-propuestas.md` (§Q-CORE-04) con
evidencia ADR-006 y F-023. No tiene ítem propio de implementación; afecta a
`002/H3/T-IMP`. Falta para cerrar: perfil de operación real, prueba negativa de
herramientas, quién autoriza mensajes y cargos. Tarjetas: `#30` (junto con
Q-CORE-03 ya resuelta).

**Q-GOV-01 — Ratificación de la constitución 1.1.0.**
Responsable: Cristóbal Herrera. Tres opciones registradas en
`backlog/decisiones-hotel.md` §7. Sin propuesta del equipo. Bloquea
`000-core/T004` y el gate del núcleo. Tarjeta propia: ninguna en el tablero;
se tramita en `000-core/T004`.

### Hotel

**Q-HOT-04 — Cambios de fecha, categoría, tarifa, penalidad, saldo y
devolución.** Falta: reglas de penalidad y devolución; ejemplos aprobados.
**Q-HOT-05 — Extras por persona, noche o estadía; destino del cargo.** Falta:
matriz servicio, regla, cuenta, destino y contribuyente.
**Q-HOT-06 — Acuse por canal, mapeos, persistencia y conflictos.** Falta:
contrato real de operación del canal; casos de prueba en sandbox autorizado.

Las tres comparten cierre en `002/T202` y bloquean los mismos siete ítems:
`002/H1/T-DEC`, `H2/T-DEC`, `H3/T-DEC`, `H1/T-IMP`, `H2/T-IMP`, `H3/T-IMP` y
`002/T203`. Detalle en `backlog/hotel/respuestas-propuestas.md` (§Q-HOT-04/05/06).
Tarjetas: `#91` (Q-HOT-04).

### Cafetería (feature BLOCKED para implementar)

- **Q-CAF-01 — Momento de pago y propina** (define además el momento de consumo
  de stock: `specs/001-cafeteria-mesas-pos/data-model.md`).
- **Q-CAF-02 — Convivencia Eleventa y alcance offline.**
- **Q-CAF-03 — Carta, exportaciones, responsables de compras y sesión de
  cliente.**

Tarjetas: `#40` (las tres), `#50` (Q-CAF-01/02), `#54` (Q-CAF-02/03),
`#58` (Q-CAF-03).

### Inmobiliaria (feature BLOCKED para implementar)

- **Q-INM-01 — Proyectos, CRM y captura autorizada de leads.**
- **Q-INM-02 — Reserva, vigencia y reembolsos.**
- **Q-INM-03 — Revisión legal de promesa y firma.**
- **Q-INM-04 — Garantías y responsables.**

Además `specs/003-inmobiliaria-comercial/spec.md` (línea 405) referencia
**Q-INM-05/06/07** «para ratificar» apuntando a este documento: su contenido
detallado no existe en este repo (vivía en el repositorio origen, ruta
`R:investigacion-competitiva/decisiones-pendientes.md`, no migrada). Si se
retoma la vertical, recuperar el texto con el propietario antes de decidir.

Tarjetas: `#100` (las cuatro), `#115` (Q-INM-01/02/03), `#119` (Q-INM-01/04).

### Constructora (feature BLOCKED para implementar)

- **Q-OBR-01 — Obras propias o terceros, presupuesto y módulo previo no
  entregado.**
- **Q-OBR-02 — Unidad del avance, calendario y umbral.**
- **Q-OBR-03 — Aprobadores, compras, seguridad e inspecciones.**

Tarjetas: `#128` (las tres), `#143` (Q-OBR-01/02/03), `#147` (Q-OBR-03/04;
Q-OBR-04 no tiene texto desarrollado en este repo — mismo caso que Q-INM-05/06/07).

### Sin ítem en el tablero

**Q-REA-01, Q-REA-02, Q-REA-03 y Q-TOOL-01** siguen sin ítem y sin respuesta
(`backlog/hotel/cierre-dudas-decision-humana.md` §8). El clon de REA en solo
lectura no las responde; no se crean issues por iniciativa propia.

## Nota de alcance

Ninguna de estas respuestas puede ser inferida por el equipo: cada tarjeta lo
declara explícitamente en su «fuera de alcance». Avance posible sin el
propietario: ninguno, salvo preparación de evidencia (hecha). Lo que desbloquea
cada tarjeta es una respuesta registrada con fecha.
