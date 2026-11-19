-- ADP-4 AC-3 (2026-11-19): la cuenta de una reserva nace vacía y el alojamiento se asienta en la entrada,
-- noche a noche (check_in del dominio). Una reserva confirmada ANTES de este cambio ya trae un cargo
-- «Alojamiento N noches»; sin esta migración la entrada asentaría las noches otra vez y cobraría doble.
--
-- Se reversa (movimiento contrario, nunca UPDATE ni DELETE) el cargo de alojamiento de las reservas que
-- siguen `confirmada` y aún no lo tienen reversado. Las estadías en curso conservan su cargo: ya entraron y
-- la salida liquida contra él. Los pagos no se tocan: un anticipo queda como saldo a favor hasta la entrada.
-- Idempotente: repetirla no agrega reversos.
INSERT INTO cargos (id, reserva_id, concepto, monto_clp, tipo, referencia)
SELECT 'CRG-M32-' || substr(md5(c.id), 1, 12),
       c.reserva_id,
       left('Reverso de ' || c.concepto || ': el alojamiento se asienta en la entrada', 200),
       c.monto_clp,
       'reverso',
       c.id
FROM cargos c
JOIN reservas r ON r.id = c.reserva_id
WHERE r.estado = 'confirmada'
  AND c.tipo = 'cargo'
  AND c.concepto LIKE 'Alojamiento % noche%'
  AND NOT EXISTS (
      SELECT 1 FROM cargos x
      WHERE x.reserva_id = c.reserva_id AND x.tipo = 'reverso' AND x.referencia = c.id
  )
ON CONFLICT (id) DO NOTHING;
