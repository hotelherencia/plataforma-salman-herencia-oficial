# Evaluación de costos y latencias por etapa — constructora

Fecha: 2026-10-27. Sirve a `004/T205`. Mediciones reales locales (Python 3.14, datos sintéticos); no son compromiso de rendimiento en producción.

## Etapas y medición
- Suite completa (14 tests): <1 s en `unittest` discover.
- Sin etapas externas: los puertos responden «no configurado»; la latencia de pago/documento/canal no es medible hasta contrato real.
- Carga aplicada: aportes de turno y recepciones repetidas (deduplicación).

## Plan
1. Al contratar proveedores, medir latencia p95 por etapa con NFR-005 (incluye errores y reintentos).
2. Repetir con persistencia real antes de pasar cualquier T-IMP a Lista.
