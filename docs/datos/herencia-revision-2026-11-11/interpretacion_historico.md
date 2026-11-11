# Interpretación del histórico (ZIP 2026-11-11)

Veredicto corto: **la lectura documental es correcta; no debe confundirse con KPI operativo ni con oferta.**

## Qué hay en el ZIP

| Capa | Contenido | Años |
|---|---|---|
| Ocupación reportada | 204 celdas = 17 hab × 12 meses | **solo 2026** |
| Con valor | 170 | ene–oct (y parcial) |
| Nulos | 34 | sobre todo nov–dic (no imputar 0) |
| Control mensual | 12 filas; supuesto «17 hab × días»; dice explícitamente *no es ocupación validada* | 2026 |
| Tarifas | 5 tipos comerciales, **sin** `vigente_desde`/`hasta`, `aprobada_2027=false` | no oferta |
| Reservas/pagos históricos | plantillas **vacías** | nada operable |
| Años previos (2024, 2025…) | **ausentes** del paquete | — |

## Interpretación correcta

1. `interpretacion_propuesta = NOCHES_OCUPADAS_POR_CONFIRMAR` + `unidad_confirmada` vacía → observación documental, **no** ocupación oficial.
2. `es_kpi=false` en API documental es deliberado. `/hotel/ocupacion` e indicadores siguen midiendo **reservas reales** Salman.
3. ADR / RevPAR / ingresos por canal / pagos del periodo / no-show en «No disponibles en esta versión» siguen bien: falta D-IND-02 (ingreso reconocido), no hay canal en tarifa V1, no-show no existe en V1. El ZIP **no** resuelve esas fórmulas.
4. «Oferta» histórica del Excel ≠ `GET /hotel/oferta`: sin vigencia de tarifas no hay precio vendible noche a noche.
5. Ciencia de datos útil hoy: serie mensual documental (`GET /hotel/documental/ocupacion/serie`), cobertura de nulos, control hipotético, tarifas por tipo como **referencia**, no cobro.

## Inventario operativo

Solo **HAB-01…17** son opción real del titular. `HAB-101…` creadas a mano y `HAB-SINT-*` se retiran al arrancar con `INVENTARIO_DOCUMENTAL`.
