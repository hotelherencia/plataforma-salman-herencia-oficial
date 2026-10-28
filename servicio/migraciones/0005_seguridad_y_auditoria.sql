ALTER TABLE sesiones ADD COLUMN expira_en TIMESTAMPTZ;

CREATE TABLE auditoria (
    id TEXT PRIMARY KEY,
    actor TEXT NOT NULL,
    accion TEXT NOT NULL,
    recurso TEXT NOT NULL,
    resultado TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_auditoria_creado ON auditoria (creado_en);
