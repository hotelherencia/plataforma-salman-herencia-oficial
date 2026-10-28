CREATE TABLE usuarios (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    rol TEXT NOT NULL,
    clave_hash TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE sesiones (
    id TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL REFERENCES usuarios(id),
    empresa_id TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    revocada_en TIMESTAMPTZ
);

CREATE INDEX idx_sesiones_usuario ON sesiones(usuario_id);
