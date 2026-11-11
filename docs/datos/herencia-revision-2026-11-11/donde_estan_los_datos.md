# ¿Dónde están los datos reales ahora?

Fecha de este corte: 2026-11-11. Medición de producción y del repo en la misma pasada.

## Respuesta corta

| Dato | ¿En la base de producción? | ¿Dónde está hoy? |
|---|---|---|
| Empresa Herencia SpA / RUT | **No** — `GET /salud` → `EMP-SINTETICA-001` | Código `servicio/empresa_titular.py` + docs; falta `EMPRESA_TITULAR=1` en Railway |
| HAB-01…17 (tipos, capacidad propuesta) | **No** | JSON en git: `lote_b1_…` y `servicio/datos/documental/paquete_2026-11-11.json` |
| Precios / tarifas | **No** (tampoco como tarifa operativa) | 5 filas documentales en el paquete; `aprobada_2027=false`, sin vigencia |
| Histórico ocupación 2026 (204 celdas) | Tras redespliegue titular | `GET /hotel/documental/ocupacion` + serie mensual `/hotel/documental/ocupacion/serie`. **Solo 2026**; sin años previos en el ZIP. `es_kpi=false`. Ver `interpretacion_historico.md` |
| Condiciones, textiles, insumos, pendientes… | **No** (hasta redespliegue) | `doc_registro` + `GET /hotel/documental/tablas/{nombre}` |

**BD local del `.env` (aplicado 2026-11-11):** migraciones **18**, empresa
`EMP-HERENCIA-001` / Herencia SpA, `doc_*` cargado (17 hab., 5 tarifas, 204
ocupación, 1007 registros), HAB-01..17 operativas en `fuera_de_servicio`,
API local `http://127.0.0.1:8080` con `/hotel/documental/*` respondiendo.

Scripts: `scripts/aplicar_documental_wsl.sh`, `scripts/arrancar_servicio_wsl.sh`.

Producción Railway: el token del `.env` no autorizó el CLI; allí aún hay que
redesplegar con las mismas variables cuando el token/proyecto lo permitan.

## Tres capas (no confundir)

1. **ZIP / git (fuente)** — todo el paquete `GENERAL_DEPURADO` (17 hab., 5 tarifas, 204 ocupación, 442 condiciones, etc.).
2. **Tablas operativas Salman** (`habitaciones`, `tarifas`, `reservas`) — gobiernan oferta y cobro. Hoy en prod: sintéticas.
3. **Tablas documentales** (`doc_*`, migración 0018) — para **consultar** el levantamiento y el histórico reportado **sin** vender ni cobrar. Se cargan con `INVENTARIO_DOCUMENTAL=1` + titular.

## Qué NO es “dato real vendible” aunque esté en el ZIP

- Capacidad vacía en origen → solo **propuesta** desde tipo (HAB-08/16 exigen verificación).
- Tarifas sin `vigente_desde`/`hasta` y no aprobadas 2027 → no van a `tarifas` operativas.
- Ocupación con `unidad_confirmada` vacía → histórico **documental**, no KPI oficial (`es_kpi=false`).
- Nov/dic sin valor → `null`, no cero.
- Cuádruple → oferta comercial de 2 unidades; no hay fila de habitación física extra.

## Cómo queda consultable tras 0018 + siembra

| Recurso | Endpoint (sesión hotel) |
|---|---|
| Resumen del paquete | `GET /hotel/documental/resumen` |
| Habitaciones 1–17 | `GET /hotel/documental/habitaciones` |
| Tarifas documentales | `GET /hotel/documental/tarifas` |
| Histórico ocupación | `GET /hotel/documental/ocupacion` |
| Control mensual | `GET /hotel/documental/control-ocupacion` |
| Cualquier tabla del ZIP | `GET /hotel/documental/tablas/{nombre}` |

Activación Railway:

```text
EMPRESA_TITULAR=1
INVENTARIO_DOCUMENTAL=1
```

Sin eso, la plataforma sigue sintética y el ZIP solo vive en el repositorio.
