# Mapa ZIP → Salman V1

Paquete: `Hotel_Herencia_Revision_y_Datos_2026-11-11.zip` (clasificación `GENERAL_DEPURADO`).  
Destino código: `hotelherencia/plataforma-salman-herencia-oficial` @ `main` / `e8671e5`.  
Preflight: `reporte_preflight.json` (G0 hashes OK).

## Destino real (descubrimiento)

| Recurso Salman V1 | Origen | Notas |
|---|---|---|
| `habitaciones` | `servicio/migraciones/0003_reserva_persistente.sql` + `0009` | `id`, `tipo`, `capacidad`, `estado_operativo`, `fuera_de_servicio_*` |
| `tarifas` | `0003` + `0009` | Por `habitacion_id` + `fecha_desde`/`fecha_hasta` + `tarifa_noche_clp` (entero). Append-only con `creado_en` |
| `reservas` | `0003` | `daterange(inicio,fin,'[)')` + `EXCLUDE USING gist` si `estado='confirmada'` |
| `pagos` / `cargos` / `liquidaciones` | `0004` | CLP entero; no hay IVA desglosado en fila |
| `solicitudes` / `leads` | `0010` / `0012`+`0016` | Canal público; `origen` en solicitud |
| `usuarios` / sesión | `0002`+ | Roles: `administrador`, `recepcion`, `caja`, `agente`. Empresa desde sesión |
| `auditoria` / idempotencia | `0005` / `0003` | Sin RLS multi-tenant genérico |

**Fechas:** estadía = `DATE` (sin TZ en columna). Auditoría/creación = `TIMESTAMPTZ`. El ZIP declara `America/Santiago`; Salman no fija esa TZ en el esquema — el corte diario operativo debe acordarse (medianoche local Chile).

**No existen en V1 (solo warehouse propuesto):** `hotel`, `room_type_assignment`, `room_composition`, `rate_plan`, `rate_version`, `room_night`, `financial_event`, `import_batch`, `staging_record`, marts RevPAR/ADR.

**Cuádruple:** TAR-07 nota «Juntando 2 habitaciones…». V1 reserva **una** `habitacion_id` por reserva. Gap: sin `room_composition` no se puede vender la oferta combinada sin inventar habitación física (R01) o bloquear hasta ADR.

**Siembra actual:** `HAB-SINT-101..103` al arranque (`sembrar_habitaciones`, `ON CONFLICT DO NOTHING`). Retiro de oferta: `fuera_de_servicio` o sin tarifa vigente — no borrar historial (#336 / h7-despliegue).

## Leyenda de política de conflicto

- **NEW** — no existe en Salman; candidato a alta tras aprobación.
- **UNCHANGED** — ya igual (no aplica en preflight sin lectura DB).
- **UPDATED** — existe y el documental aporta cambio verificado.
- **CONFLICT** — documental vs verificado o vs regla V1.
- **REJECTED** — no cargar (nulo, inactivo, reservado, o gap de producto).
- **WAREHOUSE** — solo capa A/C; no tabla Salman.

## `csv/habitaciones.csv` → `habitaciones`

| Campo ZIP | Transformación | Campo Salman V1 | Política |
|---|---|---|---|
| `habitacion_id` (HAB-01..17) | Dueño elige convención final (`HAB-01` vs `HAB-101` vs otra) | `habitaciones.id` | CONFLICT hasta decisión; NEW tras acuerdo |
| `numero` | Metadato / posible parte del id | *(no hay columna `numero`)* | WAREHOUSE o embeber en `id` |
| `tipo_declarado` | Normalizar catálogo acordado; **no** inferir capacidad de «Matrimonial +1» (R02) | `habitaciones.tipo` | REJECTED hasta verificación terreno; luego NEW/UPDATED |
| `capacidad_personas` | 17/17 vacías en paquete | `habitaciones.capacidad` (CHECK > 0) | REJECTED — bloquea oferta (#336 / PEN-001) |
| `numero_camas` / `configuracion_camas` | Solo evidencia | *(no existe)* | WAREHOUSE |
| `estado_venta` | Vacío; ≠ operativo | `estado_operativo` | REJECTED — no abrir vendible desde documental |
| `fuente` / `estado_evidencia` / `verificado_en_terreno` / `fecha_levantamiento` | Lineage | *(no existe)* | WAREHOUSE (`source_document` / `lineage`) |

Tipos documentales observados: Matrimonial 9, Doble 4, Matrimonial +1 2, Single 1, Triple 1.

## `csv/tarifas_declaradas.csv` → `tarifas` (R04)

| Campo ZIP | Transformación | Campo Salman V1 | Política |
|---|---|---|---|
| `tarifa_id` | Id documental | `tarifas.id` (si se publica) | WAREHOUSE mientras inactiva |
| `tipo_comercial` | No hay tarifa por tipo en V1: hay que **expandir a cada `habitacion_id`** del tipo | `habitacion_id` | CONFLICT — falta matriz tipo→unidades + decisión dueño |
| `monto_clp` | Entero > 0 | `tarifa_noche_clp` | WAREHOUSE; REJECTED para cobro activo |
| `moneda` | CLP | implícito (solo CLP) | OK documental |
| `iva_incluido_declarado` | true en las 5 | *(no hay columna IVA)* | WAREHOUSE / decisión fiscal #314 |
| `canal` | `DIRECTO_POR_CONFIRMAR_MAPEO` | *(tarifas V1 sin canal)* | WAREHOUSE; canal en solicitud=`origen` |
| `vigente_desde` / `vigente_hasta` | **Vacíos en las 5** | `fecha_desde` / `fecha_hasta` (obligatorios, hasta > desde) | REJECTED para PUT activo |
| `aprobada_2027` | `false` en las 5 | — | REJECTED cobro 2027 hasta aprobación |
| TAR-07 Cuadruple | Composición 2 unidades | — | REJECTED / gap producto (R01) |

## `csv/ocupacion_reportada.csv` → analítica (R05, R06)

| Campo ZIP | Destino | Política |
|---|---|---|
| `valor_reportado` | observación staging | WAREHOUSE |
| `unidad_confirmada` vacía (204/204) | — | REJECTED para KPI |
| nov/dic sin valor (34 celdas) | null | REJECTED imputar 0 (R05) |
| `interpretacion_propuesta` | `NOCHES_OCUPADAS_POR_CONFIRMAR` | no ADR/RevPAR/ocupación oficial |

## Plantillas reservadas → `reservas` / `pagos` / personas

Archivos bajo `plantillas_reservadas_sin_datos/` **sin filas de datos**.  
Política: REJECTED cualquier alta operativa. Recepción futura por canal cifrado (LEEME).

## Otros CSV → no operación

| ZIP | Salman V1 | Política |
|---|---|---|
| `insumos`, `proveedores`, `textiles`, `activos_*`, `servicios` | no hay inventario de insumos/POS | WAREHOUSE (R07: sin saldos) |
| `matriz_cumplimiento`, `riesgos`, `pendientes`, `validaciones` | no hay módulo compliance | WAREHOUSE / gestión documental |
| `politicas_declaradas` | parcial (`politica_cancelacion` en oferta pública es texto de dominio) | WAREHOUSE hasta decisión |
| `control_ocupacion`, `observaciones_operativas`, `fuentes`, `diccionario_datos`, `cobertura_hojas` | — | WAREHOUSE |

## Issues de bloqueo (capa B)

| Issue | Efecto en el mapa |
|---|---|
| #336 | Sin listado verificado (id, tipo, capacidad, tarifa) no hay NEW vendible |
| #314 | Empresa/RUT/IVA: no afirmar tratamiento fiscal en cobro |
| #313 | CTA producción: no depende del ZIP; hosting marketing |
| #338 | Admin nominado: operativo; TOTP no obligatorio |

## Gaps explícitos a documentar (no silenciar)

1. Tarifa por **tipo** en ZIP vs tarifa por **habitación** en Salman.  
2. Oferta **Cuádruple** (2 habitaciones) sin modelo de composición.  
3. Capacidad y camas vacías → no inferir.  
4. Warehouse canónico ≠ migraciones V1.  
5. Ocupación agregada 2026 sin unidad → solo D0 documental.
