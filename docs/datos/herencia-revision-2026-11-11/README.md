# Herencia — revisión y datos 2026-11-11

Pasada de preflight + descubrimiento Salman V1 **sin migración**.

| Entregable | Contenido |
|---|---|
| `reporte_preflight.json` | Hashes vs manifiesto, conteos, nulos, R04–R06, bloqueos |
| `mapa_zip_a_salman_v1.md` | Campo ZIP → Salman V1 / warehouse + política de conflicto |
| `lista_decisiones_dueno.md` | Capacidad, ids, tarifas 2027, cuádruple, unidad ocupación, #314/#338 |
| `plan_lotes.md` | Qué entra a staging, qué puede ir a Salman, qué queda reservado |
| `lote_b1_inventario_propuesto.json` | 17 habitaciones + tarifas/políticas documentales para siembra borrador |

Fuente: `Hotel_Herencia_Revision_y_Datos_2026-11-11.zip` (fuera del árbol versionado o junto al monorepo local).

Siembra en plataforma (sin cobro ni oferta pública):

```text
EMPRESA_TITULAR=1
python scripts/aplicar_documental_desde_env.py   # comando puntual (W16-A02)
```

Desde la auditoría 2026-11-16 (W16-A02) la carga es un comando puntual y
nunca borra reservas, pagos ni historial; ver `docs/arquitectura/h7-despliegue.md`.

Código: `servicio/empresa_titular.py`, `servicio/inventario_documental.py`, migración `0017`.
