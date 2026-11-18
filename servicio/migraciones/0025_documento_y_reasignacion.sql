-- #367 / #360 / #361 (2026-11-18).
--
-- Documento del huésped con tipo: RUT (validado por dígito verificador) o
-- pasaporte. Las reservas existentes quedan con tipo NULL (texto heredado);
-- no se reescribe ningún documento.
ALTER TABLE reservas ADD COLUMN huesped_documento_tipo TEXT
    CHECK (huesped_documento_tipo IN ('rut', 'pasaporte'));

-- Historial de cambios de habitación de una reserva (antes de llegar, en la
-- entrada o durante la estadía). La reserva conserva la tarifa pactada.
CREATE TABLE reasignaciones (
    id TEXT PRIMARY KEY,
    reserva_id TEXT NOT NULL REFERENCES reservas(id),
    desde_habitacion_id TEXT NOT NULL REFERENCES habitaciones(id),
    hacia_habitacion_id TEXT NOT NULL REFERENCES habitaciones(id),
    motivo TEXT NOT NULL,
    actor TEXT NOT NULL,
    estado_reserva TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idx_reasignaciones_reserva ON reasignaciones (reserva_id, creado_en);
