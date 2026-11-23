-- PR B (RES-007): Titular con varias habitaciones bajo una cabecera de grupo.
-- Conserva intacta la invariante 1 reserva = 1 habitación en ServicioHotelInventario,
-- cargos, pagos e imputaciones_pago.
-- Migración aditiva e idempotente.

CREATE TABLE IF NOT EXISTS reservas_grupo (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    huesped_titular_id TEXT REFERENCES huespedes(id),
    titular_nombre TEXT NOT NULL,
    titular_documento_tipo TEXT CHECK (titular_documento_tipo IN ('rut', 'pasaporte')),
    titular_documento TEXT,
    canal TEXT NOT NULL DEFAULT 'recepcion',
    notas TEXT,
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reservas_grupo_empresa
    ON reservas_grupo (empresa_id, creado_en DESC);

ALTER TABLE reservas
    ADD COLUMN IF NOT EXISTS grupo_id TEXT REFERENCES reservas_grupo(id);

ALTER TABLE reservas
    ADD COLUMN IF NOT EXISTS titular_aloja BOOLEAN NOT NULL DEFAULT true;

CREATE INDEX IF NOT EXISTS idx_reservas_grupo_id
    ON reservas (grupo_id)
    WHERE grupo_id IS NOT NULL;
