# Resolución de dudas de base — 2026-10-27

Instrucción del propietario (2026-10-27): «el foco es solo uno: construir la
plataforma; resuelve cualquier cuello de botella y avanza usando Projects para su
definición en control de tareas». En consecuencia, las seis dudas de base quedan
**resueltas con valores por defecto del mercado**, registradas con fecha y
evidencia conforme a la salida que `specs/*/tasks.md` exige para T003
(«respuestas firmadas o registradas con fecha y evidencia»). La evidencia de
mercado viene de `docs/investigacion-competitiva/dudas-base-oceano-azul.md`
(2026-10-27). Esto **no ratifica la constitución 1.1.0** ni cierra Q-HOT-04/05/06
(esas siguen en `002/T202`).

## Resoluciones

| Duda | Resolución por defecto | Evidencia de mercado | Queda para después |
|---|---|---|---|
| Q-HOT-01 | La **plataforma es la fuente de inventario** del canal directo (web propia). El PMS actual se trata como adaptador: si expone API/exportación, se integra; si no, convive con captura controlada sin confirmar cupo incierto. La unidad tiene **estado operativo** (disponible, bloqueada, fuera de servicio) que sí quita cupo, y **estado de preparación** (limpia, sucia, inspeccionada) que **no** quita cupo vendible. | Tabla Q-HOT-01 del informe: estados de limpieza publicados (Opera: Clean/Dirty/Inspected/Pickup; Cloudbeds: campos de housekeeping y endpoints de bloqueo); práctica pooled inventory | Migración real de datos del PMS actual (cuando exista exportación) |
| Q-HOT-02 | **Channel manager contratado** con API certificada (modelo estándar para hoteles independientes <50 habitaciones); la plataforma construye solo el **conector del canal directo** y el adaptador hacia el channel manager. El acuse se modela separado de la aceptación (Recibido → Aplicado → Confirmado comercial), como propone FR-020. | Tabla Q-HOT-02: Booking exige connectivity provider aprobado; dos vías y pooled inventory como mecanismo estándar | Contrato específico y sandbox del proveedor elegido (comparación en implementación) |
| Q-HOT-03 | **Políticas por defecto**: cancelación gratuita hasta 48 h antes del check-in; después, penalidad de la primera noche. **Anticipo: garantía con tarjeta** (retención, no cargo) en la web propia. **Factura a empresas: sí desde V1** vía proveedor DTE. **Datos mínimos de registro**: nombre, documento de identidad, nacionalidad, correo y teléfono. **Límite del agente: 0 CLP** sin aprobación humana (control inicial ya propuesto por la constitución 1.1.0). | Tabla Q-HOT-03: Duve documenta upsell con link de pago ligado a la reserva y cobro vía proveedor configurado; práctica de políticas 48 h del mercado independiente | Ajuste fino de políticas comerciales por Ricardo (tarifas 2027) |
| Q-CORE-01 | **Una sola empresa para V1** (Herencia) sin acceso cruzado. **Dueño canónico del dato: la empresa legal**; el establecimiento es un atributo del dato, no un segundo dueño (regla explícita: un solo dueño = empresa). El identificador de empresa **nace del contexto autenticado** (sesión), no de un campo del llamador: ya implementado en el incremento 0 (bucle 1, 2026-10-27). | Tabla Q-CORE-01: token de propiedad/portafolio en Mews; el dueño viaja en el contexto autenticado | Matriz completa de roles cuando haya varias empresas |
| Q-CORE-02 | **Proveedor DTE por API**, short-list: Alegra, Siigo o Defontana (facturadores líderes en Chile); elección final por comparación durante la implementación del puerto. **Política: boleta siempre; factura a empresas desde V1.** Invariante: el documento emitido no se reescribe; se anula en plazo o se corrige con nota de crédito electrónica. | Sección «Corrección de datos» del informe (regla SII); tabla Q-CORE-02 (oferta de facturadores y emisión vía POS/pasarela) | Firma de contrato con el proveedor elegido |
| Q-CORE-03 | **Propuesta de valores iniciales**: retención de datos operativos y documentos **6 años** (plazo tributario chileno) con minimización; RPO **1 h** y RTO **4 h** (referencia de guía de comprador, hipótesis hasta medir); responsable del tratamiento: el administrador de la empresa. Ley 19.628 vigente y transición Ley 21.719 al 01-12-2026, con validación jurídica antes de producción. | Tabla Q-CORE-03: RPO/RTO no publicados por los PMS medianos; guía StayNTouch con objetivo RPO ≤ 1 h (HIPÓTESIS); documento contractual Oracle como referencia de formato | Validación jurídica y presupuesto aprobado por el propietario |

## Lo que esta resolución desbloquea

- Las **cinco T003** quedan con su salida completa (respuestas registradas con
  fecha y evidencia) → pasan a **Hecha** en el backlog y en el tablero.
- **Bucle 2 de construcción** (2026-10-27): estados operativos y de preparación de
  la unidad en el incremento 0, con la regla «la limpieza no quita cupo; el
  bloqueo o fuera de servicio sí» (FR-016, Q-HOT-01 resuelto).
- Siguen sin resolver: Q-HOT-04/05/06 (en `002/T202`), la ratificación de la
  constitución 1.1.0 (Q-GOV-01) y las firmas manuscritas del acta. Q-REA-01/02/03
  y Q-TOOL-01 siguen sin ítem.
