-- Consultas forenses de solo lectura para RSV-374cbd57abf6
BEGIN READ ONLY;

SELECT id, empresa_id, habitacion_id, inicio, fin, estado, tarifa_noche_aceptada_clp,
       huesped_nombre, huesped_documento, huesped_documento_tipo, personas, canal, creado_en
FROM reservas WHERE id = 'RSV-374cbd57abf6';

SELECT reserva_id, noche, precio_clp
FROM reserva_noches WHERE reserva_id = 'RSV-374cbd57abf6' ORDER BY noche;

SELECT id, reserva_id, tipo, concepto, monto_clp, referencia, producto_id, cantidad, precio_unitario_clp, creado_en
FROM cargos WHERE reserva_id = 'RSV-374cbd57abf6' ORDER BY creado_en, id;

SELECT id, reserva_id, monto_clp, clave, modo, estado, tipo, referencia_pago_id, medio,
       fecha_contable, turno_id, documento_tipo, actor, motivo, es_anticipo, efecto_nucleo_id, creado_en
FROM pagos WHERE reserva_id = 'RSV-374cbd57abf6' ORDER BY creado_en, id;

SELECT id, empresa_id, turno_id, fecha_contable, tipo, medio, monto_clp, pago_id, actor, motivo, creado_en
FROM caja_movimientos
WHERE pago_id IN (SELECT id FROM pagos WHERE reserva_id = 'RSV-374cbd57abf6')
ORDER BY creado_en, id;

SELECT id, empresa_id, fecha_contable, estado, saldo_inicial_clp, usuario_apertura, abierto_en,
       usuario_cierre, cerrado_en, efectivo_contado_clp, diferencia_clp
FROM caja_turnos WHERE fecha_contable BETWEEN '2026-11-18' AND '2026-11-20' ORDER BY abierto_en;

SELECT id, empresa_id, fecha_contable, estado, total_cobrado_clp, total_egresos_clp, cerrado_por, cerrado_en
FROM cierres_diarios WHERE fecha_contable BETWEEN '2026-11-18' AND '2026-11-20' ORDER BY fecha_contable;

-- Barrido de reservas afectadas
SELECT reserva_id, COUNT(*), SUM(monto_clp)
FROM pagos
WHERE estado = 'confirmado' AND tipo = 'cobro' AND (medio IS NULL OR medio = 'no_informado')
GROUP BY reserva_id ORDER BY SUM(monto_clp) DESC;

WITH c AS (
  SELECT reserva_id, SUM(CASE WHEN tipo='cargo' THEN monto_clp ELSE -monto_clp END) AS neto
  FROM cargos GROUP BY reserva_id
),
p AS (
  SELECT reserva_id, SUM(CASE WHEN estado='confirmado' THEN (CASE WHEN tipo='reverso' THEN -monto_clp ELSE monto_clp END) ELSE 0 END) AS pagado
  FROM pagos GROUP BY reserva_id
)
SELECT r.id, r.estado, COALESCE(c.neto, 0) AS neto, COALESCE(p.pagado, 0) AS pagado,
       COALESCE(c.neto, 0) - COALESCE(p.pagado, 0) AS saldo
FROM reservas r
LEFT JOIN c ON c.reserva_id = r.id
LEFT JOIN p ON p.reserva_id = r.id
WHERE COALESCE(c.neto, 0) - COALESCE(p.pagado, 0) < 0
ORDER BY saldo ASC;

ROLLBACK;
