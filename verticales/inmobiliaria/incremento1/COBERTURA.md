# Matriz de cobertura — casos de aceptación de inmobiliaria

Fecha: 2026-10-27. Sirve a `003/H1/T-ACC` y `003/H2/T-ACC`. Datos sintéticos,
sin red; 20 tests en verde (`tests/test_inmobiliaria_ids.py`).

## US-INM-001 / H1 — de lead a promesa

| Criterio | Prueba | Carga y fallos | Estado |
|---|---|---|---|
| AT-001 | test_AT_001_dos_canales_sugieren_coincidencia… | dos canales, un lead; sin seguimiento duplicado | verde |
| AC-US-INM-001-01 | test_AC_US_INM_001_01_presupuesto_declarado… | fallo: declaración no acredita financiamiento | verde |
| AT-003 / ADV-001 | test_AT_003_y_ADV_001_solo_una_reserva_vigente_por_unidad | carga: dos leads compiten; el segundo queda en conciliación | verde |
| AT-004 | test_AT_004_la_cotizacion_versionada… | versiones 1 y 2; la primera no cambia | verde |
| AC-US-INM-001-03 / AT-014 | test_AC_US_INM_001_03_aceptar_horario… | fallo: aceptación del interesado ≠ confirmación | verde |
| AC-US-INM-001-04 | test_AC_US_INM_001_04_la_cita_exige_zona_clara | fallo: sin zona se rechaza; misma fecha/hora a ambas partes | verde |
| AC-US-INM-001-05 | test_AC_US_INM_001_05_reprogramar_conserva_la_referencia_anterior | sin doble cita confirmada ni cancelación a ciegas | verde |
| AT-015 / AC-US-INM-001-06 | test_AT_015_y_AC_US_INM_001_06_dos_firmantes… | fallo: 1 de 2 firmas → pendiente, unidad no promesada | verde |
| AC-US-INM-001-07 | test_AC_US_INM_001_07_cambio_del_documento_genera_nueva_huella | fallo: nueva huella invalida la autorización previa | verde |
| AC-US-INM-001-02 / 001-08 | test_AC_US_INM_001_02_y_008_firma_fallida… | fallo: no promete, no libera, no devuelve; evidencia preservada | verde |
| AT-007 | test_AT_007_el_recordatorio_es_borrador… | carga: pago repetido con misma clave no reduce dos veces | verde |

## US-INM-002 / H2 — cobranza y postventa con agente

| Criterio | Prueba | Carga y fallos | Estado |
|---|---|---|---|
| AT-009 | test_AT_009_el_cliente_solo_ve_lo_suyo | fallo: recurso de otro cliente o empresa denegado | verde |
| AT-017 / AC-US-INM-002-03 | test_AT_017_y_AC_US_INM_002_03… | fallo: solo el acceso corriente se reasigna; U2 intacto | verde |
| AC-US-INM-002-04 | test_AC_US_INM_002_04_corregir_telefono… | sin cambio de titulares ni envíos | verde |
| AC-US-INM-002-01 / ADV-003 | test_AC_US_INM_002_01… y test_ADV_003… | fallo: «negar garantía» escala como contenido, sin rechazo | verde |
| AC-US-INM-002-06 | test_AC_US_INM_002_06_la_visita_fallida… | fallo: ausencia no marca reparado; motivo conservado | verde |
| AC-US-INM-002-07 | test_AC_US_INM_002_07_reparacion_sin_aceptacion… | fallo: propuesta ≠ resolución; queda por validar | verde |
| AC-US-INM-002-08 | test_AC_US_INM_002_08_la_reapertura_conserva_el_historial | historial, responsable y motivo preservados | verde |
| AT-013 | test_AT_013_permiso_retirado_suspende… | fallo: automatización suspendida con motivo | verde |

Sin construir (puerto o no drenado): AT-002 (calificación con consentimiento
y validación de ejecutivo — parcial), AT-005 (pago real de reserva: el
bloqueo de unidad sí está; el cobro real es puerto), AT-006 (envío por
proveedor autorizado), AT-008 (72 h con reloj), AT-010/AT-011 (adaptador del
core), AC-US-INM-002-02 (aceptación de receptor), AC-US-INM-002-05
(fusión de identidades).

Revisión: pendiente del visto bueno del propietario.
