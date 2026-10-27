# Incremento 1 — núcleo (000-core)

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada). Módulo `nucleo/` en
memoria y sin red: la empresa nace del contexto fijado al construir el servicio
(no de un campo libre del llamador), conectores con permisos, efectos de pago
idempotentes, aprobaciones con monto/parámetros/vigencia/uso único y
herramientas con efectos explícitos excluidos y registrados.

Ids cerrados (pruebas con el id en el nombre, en `tests/`):
AC-US-CORE-001-01/02, AC-US-CORE-002-01/02, AC-US-CORE-003-01 a 003-05.

```bash
python -m unittest discover -s tests -t .
```

Resultado real: `Ran 9 tests`, `OK`, exit 0.
