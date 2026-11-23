-- 0070: «Upgrade a tarifa Single» (SPEC-UPG-01). Aditiva e idempotente.
-- Una reserva de 1 persona sin single libre puede asignarse a un tipo superior cobrando la tarifa
-- Single; se guarda de dónde viene el precio para que la diferencia no parezca un error de cobro.
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS upgrade_desde_tipo TEXT;
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS tarifa_lista_clp INTEGER;
-- Diferencia ya cargada por haber pasado a 2 o más personas (append-only: se reversa, no se edita).
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS upgrade_ajustado_clp INTEGER NOT NULL DEFAULT 0;
