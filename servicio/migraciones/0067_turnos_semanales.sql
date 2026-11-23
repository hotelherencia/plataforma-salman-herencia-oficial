-- 0067: turnos semanales por área y cambios de turno aprobados (#418, Corte 2 parte 2). Aditiva e idempotente.
CREATE TABLE IF NOT EXISTS turnos (
    id TEXT PRIMARY KEY,
    fecha DATE NOT NULL,
    area TEXT NOT NULL CHECK (area IN ('recepcion', 'aseo', 'desayunos', 'mantencion')),
    usuario TEXT NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    nota TEXT CHECK (nota IS NULL OR length(nota) <= 200),
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (hora_fin > hora_inicio)
);
CREATE INDEX IF NOT EXISTS idx_turnos_fecha ON turnos (fecha, area);
-- Una persona no repite el mismo bloque horario exacto el mismo día.
CREATE UNIQUE INDEX IF NOT EXISTS uq_turnos_persona_bloque ON turnos (fecha, usuario, hora_inicio, hora_fin);

-- Solicitudes de cambio: la historia queda; al aprobar, el turno pasa a la persona propuesta.
CREATE TABLE IF NOT EXISTS turno_cambios (
    id TEXT PRIMARY KEY,
    turno_id TEXT NOT NULL REFERENCES turnos(id),
    solicitante TEXT NOT NULL,
    propuesto TEXT NOT NULL,
    motivo TEXT NOT NULL CHECK (length(motivo) BETWEEN 3 AND 300),
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobado', 'rechazado')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    resuelto_por TEXT,
    resuelto_en TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_turno_cambios_estado ON turno_cambios (estado, creado_en);
-- Un solo cambio pendiente por turno.
CREATE UNIQUE INDEX IF NOT EXISTS uq_turno_cambio_pendiente ON turno_cambios (turno_id) WHERE estado = 'pendiente';
