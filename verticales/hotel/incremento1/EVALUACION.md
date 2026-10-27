# Evaluación de costos y latencias por etapa — hotel

Fecha: 2026-10-27. Sirve a `002/T205`. Mediciones reales locales (Python 3.14, datos sintéticos); no son compromiso de rendimiento en producción.

## Etapas y medición
- Suite completa (102 tests): <1 s en `unittest` discover.
- Sin etapas externas: los puertos responden «no configurado»; la latencia de pago/documento/canal no es medible hasta contrato real.
- Carga aplicada: carrera de 100 hilos sobre la última unidad (AT-005/ADV-001).

## Plan
1. Al contratar proveedores, medir latencia p95 por etapa con NFR-005 (incluye errores y reintentos).
2. Repetir con persistencia real antes de pasar cualquier T-IMP a Lista.
