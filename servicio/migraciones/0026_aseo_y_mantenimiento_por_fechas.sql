-- #362 / #363 / #349 (2026-11-18).
--
-- Aseo: quién completó cada limpieza y la verificación de la administración
-- (verificada o rechazada con observación).
ALTER TABLE tareas_operativas ADD COLUMN completada_por TEXT;
ALTER TABLE tareas_operativas ADD COLUMN verificacion TEXT
    CHECK (verificacion IN ('verificada', 'rechazada'));
ALTER TABLE tareas_operativas ADD COLUMN verificada_por TEXT;
ALTER TABLE tareas_operativas ADD COLUMN verificada_en TIMESTAMPTZ;
ALTER TABLE tareas_operativas ADD COLUMN observacion TEXT;

-- Observaciones de la administración para el personal de aseo, por
-- habitación, visibles hasta que se marcan como atendidas.
CREATE TABLE observaciones_habitacion (
    id TEXT PRIMARY KEY,
    habitacion_id TEXT NOT NULL REFERENCES habitaciones(id),
    texto TEXT NOT NULL,
    autor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    atendida_en TIMESTAMPTZ,
    atendida_por TEXT
);
CREATE INDEX idx_observaciones_pendientes ON observaciones_habitacion (habitacion_id) WHERE atendida_en IS NULL;

-- Mantenimiento con rango de fechas: la unidad solo sale del cupo en esos
-- días. Sin fechas, el mantenimiento abierto bloquea solo el día en curso
-- (la habitación sigue vendible para fechas futuras).
ALTER TABLE habitaciones ADD COLUMN mantenimiento_desde DATE;
ALTER TABLE habitaciones ADD COLUMN mantenimiento_hasta DATE;
