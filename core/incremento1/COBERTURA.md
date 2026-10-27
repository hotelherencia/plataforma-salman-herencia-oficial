# Matriz de cobertura — casos de aceptación del núcleo (000-core)

Fecha: 2026-10-27. Sirve a `000-core/H1/T-ACC`, `H2/T-ACC` y `H3/T-ACC`. Datos
sintéticos, sin red; 9 tests en verde (`tests/test_AC_US_CORE_ids.py`).

## US-CORE-001 / H1 — acceso por empresa

| Criterio | Prueba | Carga y fallos | Estado |
|---|---|---|---|
| AC-US-CORE-001-01 | test_…_001_01_otra_empresa_no_usa_la_referencia_del_conector | fallo: empresa ajena denegada sin revelar la referencia | verde |
| AC-US-CORE-001-02 | test_…_001_02_capacidad_no_habilitada_se_informa_y_registra | fallo: operación sin permiso denegada | verde |

## US-CORE-002 / H2 — pagos y documentos sin duplicaciones

| Criterio | Prueba | Carga y fallos | Estado |
|---|---|---|---|
| AC-US-CORE-002-01 | test_…_002_01_resultado_repetido_diez_veces_un_solo_efecto | carga: 10 repeticiones del mismo retorno → un efecto; deuda conciliada una vez | verde |
| AC-US-CORE-002-02 | test_…_002_02_rechazo_posterior_no_figura_autorizado_ni_borra_la_deuda | fallo: rechazo posterior al offline no borra la deuda ni cambia el estado | verde |

## US-CORE-003 / H3 — gobernar acciones y contratos

| Criterio | Prueba | Carga y fallos | Estado |
|---|---|---|---|
| AC-US-CORE-003-01 | test_…_003_01_la_propuesta_cambia_de_monto_y_no_se_ejecuta | fallo: 10.000 → 11.000 invalida la aprobación | verde |
| AC-US-CORE-003-02 | test_…_003_02_conector_de_lectura_deniegue_escritura | fallo: escritura sobre conector de lectura denegada | verde |
| AC-US-CORE-003-03 | test_…_003_03_flag_de_envio_no_autorizado_no_envia_y_registra | fallo: efecto excluido, sin llamar al destino, registrado | verde |
| AC-US-CORE-003-04 | test_…_003_04_placeholder_queda_bloqueada_sin_llamar_al_destino | fallo: efectos desconocidos bloquean la herramienta | verde |
| AC-US-CORE-003-05 | test_…_003_05_referencia_de_otra_cuenta_no_accede_ni_repite | fallo: referencia de B sobre cuenta A denegada; sin repetir comunicación | verde |

Revisión: pendiente del visto bueno del propietario. Los adaptadores reales
(pagos, documentos, comunicación) siguen como puertos externos.
