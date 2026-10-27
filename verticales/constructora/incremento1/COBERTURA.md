# Matriz de cobertura — casos de aceptación de constructora

Fecha: 2026-10-27. Sirve a `004/H3/T-ACC` y `004/H4/T-ACC`. Datos sintéticos,
sin red; 14 tests en verde (`tests/test_constructora_ids.py`).

## US-OBR-003 / H3 — reportar avance y preparar compras

| Criterio | Prueba | Carga y fallos | Estado |
|---|---|---|---|
| AT-001 | test_AT_001_el_retroceso_no_sobrescribe_el_dato_aprobado | fallo: reporte menor no retrocede el avance | verde |
| AT-002 | test_AT_002_programado_cero_no_divide_ni_inventa_alerta | fallo: división por cero evitada; umbral ratificado | verde |
| AT-010 / AC-US-OBR-003-03 | test_AT_010_y_AC_US_OBR_003_03_dos_turnos… | carga: dos turnos + reenvío → ambos aportes, sin duplicar | verde |
| AC-US-OBR-003-04 | test_AC_US_OBR_003_04_porcentajes_acumulados_no_se_suman | fallo: 40 % + 45 % acumulado ≠ 85 % | verde |
| ADV-001 | test_ADV_001_reporte_contradictorio… | fallo: se conservan ambos y exige rectificación aprobada | verde |
| ADV-002 / AC-US-OBR-003-01 | test_AC_US_OBR_003_01_nota_de_compra… | fallo: instrucciones → solo borrador, sin orden | verde |

## US-OBR-004 / H4 — presupuesto, inspección y materiales

| Criterio | Prueba | Carga y fallos | Estado |
|---|---|---|---|
| AT-004 / AC-US-OBR-004-07 (parcial) | test_AT_004_el_presupuesto_versionado_conserva_la_linea_base | línea base, motivo y aprobador conservados | verde |
| AT-012 / AC-US-OBR-004-06 | test_AT_012_y_AC_US_OBR_004_06_disponible_50_y_no_20 | carga: 100 − compromiso 50 (con devengo y pago ya incluidos) = 50 | verde |
| AT-009 / AC-US-OBR-004-02 | test_AT_009_y_AC_US_OBR_004_02_recepcion_parcial_idempotente | carga: repetir el evento no recibe 12; quedan 4 | verde |
| AT-011 / AC-US-OBR-004-03 | test_AT_011_seis_entregadas_cinco_aceptadas… | fallo: rechazo documentado; pendientes 5 | verde |
| AC-US-OBR-004-05 | test_AC_US_OBR_004_05_la_devolucion_no_infere_abono | sin abono financiero ni cambio de contrato | verde |
| AT-008 / AC-US-OBR-004-01 | test_AT_008_y_AC_US_OBR_004_01_el_reportante_no_cierra… | fallo: cierre solo por inspector | verde |
| AC-US-OBR-004-10 | test_AC_US_OBR_004_10_comentario_de_ia_no_es_oficial | fallo: comentario no modifica presupuesto ni programa | verde |
| AT-007 / ADV-003 | test_AT_007_y_ADV_003_la_empresa_comercial_no_consulta… | fallo: sin convenio ni permiso → denegado | verde |

Sin construir (puerto o no drenado): AT-003 (envío a proveedor; la solicitud
y su aprobación son locales pero el envío es externo), AC-US-OBR-003-02
(IA desactivada con vía manual — parcial), AC-US-OBR-003-05 (falta de
conexión), AC-US-OBR-004-04 (segunda entrega con identidad distinta),
AC-US-OBR-004-08 (partida sin clasificación), AC-US-OBR-004-09
(solucionador sin permiso de aceptar), AC-US-OBR-004-11 (reapertura con
historial — parcial vía AT-001/ADV-001).

Revisión: pendiente del visto bueno del propietario.
