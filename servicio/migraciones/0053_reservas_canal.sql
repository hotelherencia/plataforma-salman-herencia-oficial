-- #324 (2026-11-19): canal de origen en reservas para habilitar ingresos por
-- canal en el panel operativo sin depender solo de solicitudes.
ALTER TABLE reservas
    ADD COLUMN IF NOT EXISTS canal TEXT NOT NULL DEFAULT 'recepcion';

ALTER TABLE reservas
    DROP CONSTRAINT IF EXISTS reservas_canal_check;

ALTER TABLE reservas
    ADD CONSTRAINT reservas_canal_check
    CHECK (canal IN ('recepcion', 'landing', 'directo', 'google', 'ota', 'telefono', 'whatsapp', 'otro'));

CREATE INDEX IF NOT EXISTS idx_reservas_empresa_canal
    ON reservas (empresa_id, canal);

-- Backfill de reservas ya convertidas desde solicitudes públicas.
UPDATE reservas r
SET canal = CASE
    WHEN s.origen IN ('landing', 'directo', 'google', 'ota', 'telefono', 'whatsapp', 'otro') THEN s.origen
    ELSE 'landing'
END
FROM solicitudes s
WHERE s.reserva_id = r.id
  AND r.canal = 'recepcion';
