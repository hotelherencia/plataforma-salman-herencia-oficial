# Contrato lógico — constructora y control de obra

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada). Sirve a `004/T005` y a los T-DIS de H3-H4.

## Permisos y tenant
- Empresa única `EMP-SINTETICA-001`; la empresa comercial sin convenio → `AccesoDenegado`.

## Estados e invariantes
- Avance: porcentaje **acumulado** por partida; aportes deduplicados por clave; reporte menor conserva ambos y exige rectificación aprobada; nunca se suman porcentajes.
- Desvío: programado 0 → `sin_evaluacion` (sin división por cero ni alerta inventada).
- Presupuesto: versionado; la línea base nunca se reescribe; `disponible = monto − compromiso_total`.
- Recepción: idempotente por evento; aceptadas/rechazadas documentadas; pendientes = orden − aceptadas acumuladas.
- Observación: solo el `inspector` cierra; la solución propuesta queda `por_validar`.
- Notas de compra con instrucciones → solo borrador; comentarios de IA nunca oficiales.

Ver `COBERTURA.md`.
