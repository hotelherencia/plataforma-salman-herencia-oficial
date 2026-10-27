# Incremento 1 — inmobiliaria comercial

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada). Módulo
`inmobiliaria_comercial/` en memoria y sin red: leads con coincidencia, unidad
con reserva única, cotización versionada, citas con zona y aceptación
autorizada, promesas con firmas parciales y huella de documento, cuotas con
recordatorio borrador e imputación idempotente, portal por cliente y postventa
con escalamiento. Puertos de pago real y envío de documentos: externos.

Ids cerrados (tests/): AT-001, AT-003, AT-004, AT-007, AT-009, AT-013,
AT-014 (vía AC-US-INM-001-03), AT-015, AT-017, ADV-003, AC-US-INM-001-01 a
001-07 y AC-US-INM-002-01, 002-03, 002-04, 002-06, 002-07, 002-08.

```bash
python -m unittest discover -s tests -t .
```

Resultado real: `Ran 20 tests`, `OK`, exit 0.
