-- Contabilidad 2.4 (#394): Cierre mensual congelado (auditoría mensual y exportación matriz Ocupación).
-- Migración aditiva e idempotente.

CREATE TABLE IF NOT EXISTS cierres_mensuales (
    empresa_id TEXT NOT NULL,
    anio INTEGER NOT NULL CHECK (anio BETWEEN 2020 AND 2100),
    mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
    estado TEXT NOT NULL CHECK (estado IN ('cerrado', 'reabierto')),
    usuario_id TEXT NOT NULL,
    cerrado_por TEXT NOT NULL,
    cerrado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    nota TEXT,
    resumen JSONB NOT NULL,
    reabierto_por TEXT,
    reabierto_en TIMESTAMPTZ,
    motivo_reapertura TEXT,
    PRIMARY KEY (empresa_id, anio, mes)
);

CREATE INDEX IF NOT EXISTS idx_cierres_mensuales_empresa
    ON cierres_mensuales (empresa_id, anio DESC, mes DESC);
