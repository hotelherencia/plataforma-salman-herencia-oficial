-- 0073_novedades_estacionamiento_conteos.sql
-- SPEC-NOV-01 (#448): Libro de novedades de turno (mañana/tarde/noche),
-- asignación de cupos de estacionamiento (~14 cupos por habitación/patente)
-- y conteos operativos de desayunos y bebestibles por turno.
-- Migración estrictamente aditiva e idempotente.

CREATE TABLE IF NOT EXISTS libro_novedades (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    fecha_contable DATE NOT NULL,
    turno TEXT NOT NULL CHECK (turno IN ('manana', 'tarde', 'noche')),
    autor TEXT NOT NULL,
    resumen TEXT NOT NULL,
    desayunos_servidos INTEGER NOT NULL DEFAULT 0 CHECK (desayunos_servidos >= 0),
    bebestibles_detalle JSONB NOT NULL DEFAULT '[]'::jsonb,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_libro_novedades_empresa_fecha
    ON libro_novedades (empresa_id, fecha_contable DESC, creado_en DESC);

CREATE TABLE IF NOT EXISTS estacionamiento_asignaciones (
    id BIGSERIAL PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    fecha DATE NOT NULL,
    cupo INTEGER NOT NULL CHECK (cupo >= 1 AND cupo <= 50),
    habitacion_id TEXT,
    reserva_id TEXT REFERENCES reservas (id) ON DELETE SET NULL,
    patente TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'ocupado' CHECK (estado IN ('reservado', 'ocupado', 'liberado')),
    observacion TEXT NOT NULL DEFAULT '',
    creado_por TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (empresa_id, fecha, cupo)
);

CREATE INDEX IF NOT EXISTS idx_estacionamiento_empresa_fecha
    ON estacionamiento_asignaciones (empresa_id, fecha, cupo);

CREATE TABLE IF NOT EXISTS conteos_turno_fnb (
    id BIGSERIAL PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    fecha_contable DATE NOT NULL,
    turno TEXT NOT NULL CHECK (turno IN ('manana', 'tarde', 'noche')),
    categoria TEXT NOT NULL CHECK (categoria IN ('desayuno', 'bebestible')),
    producto_id TEXT REFERENCES productos (id) ON DELETE SET NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad >= 0),
    observacion TEXT NOT NULL DEFAULT '',
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conteos_turno_fnb_empresa_fecha
    ON conteos_turno_fnb (empresa_id, fecha_contable DESC, categoria);
