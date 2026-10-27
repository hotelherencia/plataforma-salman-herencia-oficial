# Matriz de cobertura — casos de aceptación del hotel

Fecha: 2026-10-27. Sirve a `002/H1/T-ACC` y `002/H2/T-ACC`. Cada AC/AT de las
historias con prueba local lleva el nombre del test (todos en verde: 101 tests).
Los que exigen sistema externo quedan en «puerto vacío» (documentado, no simulado).

## US-HOT-001 / H1

| Criterio | Prueba (tests/) | Estado |
|---|---|---|
| AC-US-HOT-001-01 | test_concurrencia_ids.py::test_AC_US_HOT_001_01_… | verde |
| AC-US-HOT-001-02 | test_concurrencia_ids.py::test_AC_US_HOT_001_02_… | verde |
| AC-US-HOT-001-03 | test_AC_US_HOT_001_03.py | verde |
| AC-US-HOT-001-04 | test_AC_US_HOT_001_04.py | verde |
| AC-US-HOT-001-05 | test_lote_f_ids.py::test_AC_US_HOT_001_05_… | verde |
| AC-US-HOT-001-06/07/08 | — | puerto vacío (canal) |
| AT-001 | test_AT_001.py | verde |
| AT-002/003/004 | — | puerto vacío (pago/canal/SII) |
| AT-005 | test_concurrencia_ids.py::test_AT_005_… | verde |
| AT-017 | test_politica_upsell_vigencia_ids.py | verde |
| AT-018 | test_lote_f_ids.py::test_AT_018_… | verde |
| ADV-001 | test_concurrencia_ids.py::test_ADV_001_… | verde |

## US-HOT-002 / H2

| Criterio | Prueba (tests/) | Estado |
|---|---|---|
| AC-US-HOT-002-01 | test_mantenimiento_ids.py | verde |
| AC-US-HOT-002-02 | test_mantenimiento_ids.py | verde |
| AC-US-HOT-002-03 | test_AC_US_HOT_002_03.py | verde |
| AC-US-HOT-002-04 | test_lote_f_ids.py::test_AC_US_HOT_002_04_… | verde |
| AC-US-HOT-002-05 | test_lote_f_ids.py::test_AC_US_HOT_002_05_… | verde |
| AT-006 | test_AT_006.py | verde |
| AT-007 | test_AT_007.py | verde |
| AT-008 | test_mantenimiento_ids.py | verde |
| AT-009 | test_AT_009.py | verde |
| AT-016 | test_AT_016.py (proceso paralelo) | verde |

## US-HOT-003 / H3

| Criterio | Prueba (tests/) | Estado |
|---|---|---|
| AC-US-HOT-003-01 | test_concierge_ids.py | verde |
| AC-US-HOT-003-02 | test_concierge_ids.py | verde |
| AC-US-HOT-003-03 | test_concierge_ids.py | verde |
| AC-US-HOT-003-04 | test_concierge_ids.py | verde |
| AC-US-HOT-003-05 | test_concierge_ids.py | verde |
| AT-010 | test_acceso_registro_proyeccion_ids.py | verde |
| AT-011 | test_politica_upsell_vigencia_ids.py | verde |
| AT-012 | test_politica_upsell_vigencia_ids.py | verde |
| AT-013 | test_acceso_registro_proyeccion_ids.py | verde |
| AT-014 | test_acceso_registro_proyeccion_ids.py | verde |

El envío por WhatsApp (FR-010 en su parte de mensajería) queda como puerto
externo: el concierge local no envía; el contrato está en `CONTRATO-H3.md`.

Revisión: pendiente del visto bueno del propietario (lista completa salvo los
casos de puerto, que quedan explícitamente fuera hasta contrato externo).
