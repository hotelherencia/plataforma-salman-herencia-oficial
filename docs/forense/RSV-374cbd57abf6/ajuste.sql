-- SCRIPT DE AJUSTE CONTABLE APPEND-ONLY PARA RSV-374cbd57abf6
-- NO EJECUTAR SIN APROBACIÓN EXPRESA DEL PROPIETARIO.
-- Nota: `pagos` tiene trigger de inmutabilidad (`pagos_inmutables`).
-- No se hace UPDATE ni DELETE sobre pagos existentes; se asientan reversos de pago / devoluciones.
-- Reemplazar <PAGO_ID_DUPLICADO_100K>, <PAGO_ID_405K_O_EXCESO>, <TURNO_ID_ACTUAL> y <ACTOR> antes de aplicar.

BEGIN;

-- Ejemplo: reverso del/los pagos en exceso confirmados por error (total $399.500 o el pago duplicado específico):
-- INSERT INTO pagos (id, reserva_id, monto_clp, clave, modo, estado, tipo, referencia_pago_id, medio, fecha_contable, turno_id, documento_tipo, actor, motivo, es_anticipo)
-- VALUES ('PAG-REV-...', 'RSV-374cbd57abf6', 100000, 'reverso:<PAGO_ID_DUPLICADO_100K>', 'manual', 'confirmado', 'reverso', '<PAGO_ID_DUPLICADO_100K>', 'efectivo', CURRENT_DATE, '<TURNO_ID_ACTUAL>', 'sin_documento', '<ACTOR>', 'Reverso forense por pago duplicado RSV-374cbd57abf6', false);

-- Registrar movimiento de caja contrario si corresponde devolución real al cliente o ajuste de caja:
-- INSERT INTO caja_movimientos (id, empresa_id, turno_id, fecha_contable, tipo, medio, monto_clp, pago_id, actor, motivo)
-- VALUES ('MOV-REV-...', 'EMP-HERENCIA-001', '<TURNO_ID_ACTUAL>', CURRENT_DATE, 'reverso_cobro', 'efectivo', -100000, 'PAG-REV-...', '<ACTOR>', 'Ajuste forense RSV-374cbd57abf6');

COMMIT;
