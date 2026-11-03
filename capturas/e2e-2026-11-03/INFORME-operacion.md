# Informe — operación del hotel: mantenedor, consulta, ocupación e indicadores (2026-11-03)

Orden del propietario (2026-11-03): evaluar y completar el flujo operativo del
hotel con enfoque spec-driven. Entorno: **local y aislado**, datos 100 %
sintéticos; sin producción, sin adaptadores externos, sin `.env` (la API de la
E2E se lanzó con configuración explícita: `GET /auth/google/estado` →
`configurado:false`), **sin commit, push ni despliegue** de este trabajo.

Especificación gobernante nueva:
[`docs/arquitectura/spec-hotel-operacion-v1.md`](../../docs/arquitectura/spec-hotel-operacion-v1.md).
Contrato ampliado en `spec-api-v1.md` (27 → **32 operaciones**), con ajustes en
`spec-backend-v1.md` y `spec-front-v1.md`.

## 1. Diagnóstico (antes de cambiar)

| Capacidad pedida | Realidad encontrada (HECHO, con fuente) | Brecha |
|---|---|---|
| Dashboard e indicadores | Ninguna pantalla ni endpoint. El dominio define `indicadores_diarios` (ocupación, ADR, RevPAR) con cargos **de noche** y solo para rol `gerencia` (`hotel_inventario/servicio.py`). V1 asienta **un** cargo de alojamiento al reservar (`reservas.crear_reserva`) y no crea `gerencia`. `backlog/v1/indice.md` dejaba HU-HOT-03 fuera de V1. | Sin métricas; las financieras no se pueden calcular sin inventar la fórmula |
| Consulta de registros | `GET /hotel/reservas` filtra una noche (`fecha`), estado y texto; no hay periodo, habitación ni detalle; la cuenta (saldo) solo se ve al fallar la salida | Sin periodo, sin detalle, sin cuenta visible |
| Mantenedor de habitaciones | `PUT /hotel/habitaciones/{id}` es upsert ciego (no distingue alta/edición, sobrescribe en silencio, **sin auditoría**); `PUT /hotel/tarifas` sin auditoría y con vigencia **no determinista** a igual `fecha_desde` (`ORDER BY fecha_desde DESC LIMIT 1`); no hay ficha, historial de tarifas ni retiro de operación (el estado `fuera_de_servicio` existía en dominio y oferta, pero nada lo escribía); las FK ya impedían borrar | Faltan ficha, baja lógica, auditoría, desempate, historial |
| Disponibilidad y ocupación | Solo `GET /hotel/oferta` (un rango, solo lo libre) | Sin vista por noche y habitación |
| Pruebas | 129 pruebas del servicio en verde (tras `d101569`); E2E 41 casos (hoy 44) | Nada cubría lo anterior |

## 2. Matriz requisito → especificación → implementación → prueba / evidencia

| Requisito | Spec | Implementación | Prueba unitaria (HTTP + PostgreSQL) | E2E (navegador) |
|---|---|---|---|---|
| Alta sin sobrescribir | §2.2, CA-HAB-01 | `PUT` con `If-None-Match: *` → 409; patrón de id (422); `tipo` sin bordes; `reservas.guardar_habitacion` | `test_ca_hab_01_*` | HAB-02, MAN-01 |
| Editar habitación con reservas previas | §2.3, CA-HAB-02 | `cambios {antes, después}`, auditoría `habitacion`; solo toca tipo/capacidad | `test_ca_hab_02_*` | MAN-03 |
| Cambiar tarifa sin tocar reservas | §2.5, CA-HAB-03 | append-only; `ORDEN_VIGENCIA_TARIFA` única (oferta, reserva, ficha, rejilla); `tarifas.creado_en` (migración 0009); auditoría `tarifa` | `test_ca_hab_03_*` (+ mutación del desempate: falla) | MAN-04 |
| Retirar de operación (baja lógica) | §2.4, CA-HAB-04 | `POST /hotel/habitaciones/{id}/servicio`; precondición sin reservas vigentes (409 + ids); motivo obligatorio; reincorporación | `test_ca_hab_04_*` ×2 (+ mutación de la precondición: falla) | MAN-05, MAN-06 |
| Sin borrado físico | §2.1, CA-HAB-05 | no existe `DELETE`; FK impiden borrar | `test_ca_hab_05_*` | MAN-08 (DELETE → 405) |
| Permisos del mantenedor | §1, CA-HAB-06 | `_exigir_admin`; auditoría solo admin; documento por `ROLES_DOCUMENTO` | `test_ca_hab_06_*` | MAN-07 (recepción), MAN-08 (caja) |
| Ficha / historial | §2.6 | `GET /hotel/habitaciones/{id}`; ruta `/hotel/habitaciones/[id]` | `test_ca_hab_03/04` | MAN-02 + captura `op-01`, `op-03` |
| Búsqueda por periodo y habitación | §3.1, CA-RES-01 | `desde`, `hasta`, `habitacion_id`, `noches` | `test_ca_res_01_*` | RSV-01 |
| Detalle de reserva con cuenta | §3.2, CA-RES-02 | `GET /hotel/reservas/{id}`; `cobro.cuenta_de_reserva` única fórmula (la usa la salida) | `test_ca_res_02_*` (saldo = el que bloquea la salida) | RSV-01, RSV-02 + `op-04` |
| Ocupación por noche | §5, CA-OCU-01 | `GET /hotel/ocupacion` (`servicio/panel.py`); ruta `/hotel/ocupacion` | `test_ca_ocu_01_*` ×2, `test_periodo_invalido` | OCU-01 + `op-05`; OCU-02 (cada celda de 10 noches × todas las habitaciones = oferta; 130 en la última corrida) |
| Panel de indicadores | §4, CA-IND-01/02 | `GET /hotel/indicadores`; ruta `/hotel/panel` (entrada del módulo) | `test_ca_ind_01_*` ×3 (conjunto calculado a mano), `test_ca_ind_02_*` | IND-01 (recuento independiente), IND-02, IND-03 + `op-06` |
| Navegación desde el menú | CA-NAV-01 | `barra.jsx`: Panel y Ocupación; Hotel → `/hotel/panel` | — | NAV-01 |
| Persistencia | spec-backend «al reiniciar» | PostgreSQL | `ReinicioTest` (existente) | ficha, detalle, ocupación e indicadores **idénticos byte a byte** tras reiniciar la API |

## 3. Resultados de ejecución

- **Servicio:** `DATABASE_URL_TEST=…/plataforma_test_operacion python -m unittest discover -s servicio/tests -t .`
  → **147/147 OK** en tres corridas seguidas (129 previas + 18 nuevas en
  `test_operacion_mantenedor.py`; `test_h5` ampliado con las 5 rutas nuevas).
  Contra la base compartida `plataforma_test` hubo corridas con 1 a 94 fallos
  (401 «sesión inválida», usuarios borrados a mitad de prueba): se observó otro
  cliente escribiendo en esa base al mismo tiempo (otro trabajo concurrente
  en el mismo árbol). Con base dedicada no se reproduce.
- **Dominio:** 180 pruebas en verde (core 9, hotel 118, cafetería 19,
  inmobiliaria 20, constructora 14).
- **E2E de operación** (`e2e/e2e-operacion.mjs`, API :8090 + front build de
  producción :3010, base nueva `plataforma_e2e_operacion`): **16/16 APROBADO**
  (primera corrida, y tercera tras reinicio y suite base). La segunda corrida
  falló IND-01 (6 vs 9 noches): el recuento de la prueba ignoraba el fin
  efectivo de una estadía liquidada antes de empezar — el servidor aplicaba la
  spec (§4.3); se corrigió la prueba y se abrió **V1-ISSUE-07** por la causa.
- **E2E base** (`e2e/e2e.mjs`, copia ejecutada fuera del repo para no pisar
  su evidencia versionada): **44/44 APROBADO** con estos cambios.
- **Migraciones:** 0001→0009 aplicadas desde cero en base nueva.

## 4. Decisiones pendientes (no inventadas; backlog V1-ISSUE-08..10)

D-ROL-01 (rol gerencia), D-IND-01 (ingreso por noche → ADR/RevPAR), D-IND-02
(pagos por periodo), D-IND-03 (habitaciones retiradas en el denominador),
D-HAB-01 (personas en la reserva vs. capacidad), D-HAB-02 (reasignar reserva),
D-HAB-03 (catálogo de tipos), D-TAR-01 (superposición: reemplazo V1 vs.
rechazo del dominio), D-OCU-01 (mantenimiento programado), D-AUD-01
(auditoría para otros roles). Detalle en la spec §7.

## 5. Limitaciones y supuestos declarados

- SUPUESTO: noche de estadía (en_estadia/finalizada) = «noche vendida» del
  dominio, porque V1 no asienta cargos por noche.
- La fecha de cancelación no está en `reservas`: las canceladas se miden por
  fecha de estadía. No existe estado no-show: se informa `llegadas_vencidas`.
- Mantenimiento y fuera de servicio son estados actuales; se proyectan a todas
  las noches futuras (igual que la oferta).
- El histórico de una reserva muestra el tipo actual de la habitación (la
  reserva no copia el tipo).
- **V1-ISSUE-07 (P1):** `cobro.entrada` no aplica la regla de fecha/hora ni la
  del documento del dominio; la suite base hace check-in y salida 30 días antes
  de la llegada.

## 6. Notas de coordinación (trabajo concurrente)

- Durante esta sesión otro trabajo editó, commiteó y **pusheó** `main`
  (`d101569`, `831e116`). `831e116` incluyó mis tres ediciones de `e2e/e2e.mjs`
  (HAB-02/RES-02: botón «Dar de alta» e id por corrida). Mientras el front de
  este trabajo no se integre, HAB-02 falla en `main` (allí el botón sigue
  siendo «Guardar habitación»). No se revirtió nada ajeno.
- Un `npm run build` temprano en `front/` reescribió `front/.next`, que usaba
  el `next start` del otro trabajo en :3000. Desde ahí, las builds E2E se
  hicieron en una copia fuera del repo.
- Bases sintéticas creadas y dejadas en el PostgreSQL local:
  `plataforma_e2e_operacion`, `plataforma_test_operacion` (desechables).

---

## Verificación independiente (segunda pasada, mismo árbol, 2026-11-03)

Verificación propia sobre el mismo código, sin repetir las pruebas del
trabajo original: API `:8080` + front build `:3000` contra la base dedicada
`plataforma_e2e_operacion` (sintética), en Chromium.

| Chequeo propio | Método | Resultado |
|---|---|---|
| `PUT` con `If-None-Match: *`: alta `creada:true, cambios{...}`; repetida → 409 «ya existe» | curl directo | APROBADO |
| Ficha `GET /hotel/habitaciones/{id}`: `auditoria` presente con admin (2 filas tras alta+edición); **ausente** con recepción | curl con dos sesiones | APROBADO |
| `GET /hotel/habitaciones` lista `en_servicio`, `motivo_fuera_de_servicio`, `tarifa_vigente_hoy_clp` | curl | APROBADO |
| `GET /hotel/indicadores`: cada indicador `{valor, unidad, formula, fuente, limitaciones}`; `no_disponibles` con ADR/RevPAR/ingresos (D-IND-01), canal y pagos | curl + json | APROBADO |
| `GET /hotel/ocupacion`: `noches`, `habitaciones`, `resumen {disponibles, ocupadas, no_vendibles}` | curl | APROBADO |
| Contrato: spec-api-v1 con **32 operaciones** listadas; spec-front-v1 con 13 rutas y criterio «trece pantallas» | lectura de specs | APROBADO |
| Panel operativo en navegador: filtros, rangos rápidos, situación de hoy, «Cómo se calcula» por indicador | captura `verificacion-panel.png` | APROBADO |
| Ocupación con leyenda de estados (C/E/F/disponible/sin tarifa) | captura `verificacion-ocupacion.png` | APROBADO |
| Ficha: datos, tarifa vigente hoy, edición explicada | captura `verificacion-ficha.png` | APROBADO |

**Reproducción del hallazgo de interferencia:** con otro proceso escribiendo
en la base de pruebas compartida, la suite completa llegó a 49 fallos + 40
errores (deadlocks en TRUNCATE, 401, datos borrados a mitad de prueba); con
base dedicada, tres corridas completas seguidas en verde (147/147). Se
registra **V1-ISSUE-08** para aislar la base de pruebas por defecto.

**Deuda viva tras esta pasada:** V1-ISSUE-07 (el servicio no aplica la regla
de fecha/hora ni de documento del dominio en check-in/salida — divergencia
documentada; requiere decisión del propietario) y V1-ISSUE-08 (aislamiento de
la base de pruebas). Las decisiones de negocio D-* de la spec §7 siguen
pendientes del propietario; no se inventaron criterios.
