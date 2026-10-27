# Evaluación de costos y latencias por etapa — inmobiliaria

Fecha: 2026-10-27. Sirve a `003/T205`. Mediciones reales locales (Python 3.14, datos sintéticos); no son compromiso de rendimiento en producción.

## Etapas y medición
- Suite completa (20 tests): <1 s en `unittest` discover.
- Sin etapas externas: los puertos responden «no configurado»; la latencia de pago/documento/canal no es medible hasta contrato real.
- Carga aplicada: competencia de dos leads por una unidad; pagos de cuota idempotentes.

## Plan
1. Al contratar proveedores, medir latencia p95 por etapa con NFR-005 (incluye errores y reintentos).
2. Repetir con persistencia real antes de pasar cualquier T-IMP a Lista.
