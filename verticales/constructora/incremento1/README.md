# Incremento 1 — constructora y control de obra

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada). Módulo
`constructora_obra/` en memoria y sin red: avance acumulado por partida con
aportes deduplicados y rectificación aprobada, desvío sin división por cero,
presupuesto versionado con línea base y disponible = monto − compromiso total,
órdenes y recepciones parciales idempotentes con rechazo documentado,
inspección que el reportante no cierra, notas de compra que solo crean
borrador y comentarios de IA no oficiales.

Ids cerrados (tests/): AT-001, AT-002, AT-004, AT-007, AT-008, AT-009,
AT-010, AT-011, AT-012, ADV-001, ADV-003, AC-US-OBR-003-01, 003-03, 003-04,
AC-US-OBR-004-01, 004-02, 004-05, 004-06, 004-10.

```bash
python -m unittest discover -s tests -t .
```

Resultado real: `Ran 14 tests`, `OK`, exit 0.
