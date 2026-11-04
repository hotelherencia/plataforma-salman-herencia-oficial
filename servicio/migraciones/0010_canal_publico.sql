-- Canal público (2026-11-03, spec-api-v1 «Canal público», V1-ISSUE-22/24).
-- Solicitudes de reserva desde la landing: se persisten como «recibida», las
-- convierte recepción por la misma operación de reserva (trazabilidad
-- solicitud → reserva_id + auditoría). Espacio de claves propio: la clave
-- del visitante nunca toca claves_idempotencia. Nada se borra.
CREATE TABLE solicitudes (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    habitacion_id TEXT NOT NULL REFERENCES habitaciones(id),
    inicio DATE NOT NULL,
    fin DATE NOT NULL,
    personas INTEGER NOT NULL,
    huesped_nombre TEXT NOT NULL,
    huesped_contacto TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'recibida',
    origen TEXT NOT NULL DEFAULT 'landing',
    idempotency_key TEXT NOT NULL,
    cuerpo_hash TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    convertida_en TIMESTAMPTZ,
    convertida_por TEXT,
    reserva_id TEXT REFERENCES reservas(id),
    rechazo_motivo TEXT,
    UNIQUE (empresa_id, idempotency_key)
);

CREATE INDEX idx_solicitudes_bandeja ON solicitudes (empresa_id, estado, creado_en);
