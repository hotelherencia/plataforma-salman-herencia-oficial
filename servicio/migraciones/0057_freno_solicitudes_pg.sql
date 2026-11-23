-- 0057: Persistencia del freno de solicitudes del canal público en PostgreSQL (OBS-01 / #414).
-- Evita reinicios de ventana en despliegues serverless o con múltiples instancias.
-- Almacena únicamente hashes SHA-256 de claves (sin IP ni datos personales en texto plano).

CREATE TABLE IF NOT EXISTS freno_solicitudes_eventos (
    id BIGSERIAL PRIMARY KEY,
    ambito TEXT NOT NULL,
    clave_hash TEXT NOT NULL,
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_freno_solicitudes_ambito_fecha
    ON freno_solicitudes_eventos (ambito, registrado_en DESC);

CREATE INDEX IF NOT EXISTS idx_freno_solicitudes_ambito_clave_fecha
    ON freno_solicitudes_eventos (ambito, clave_hash, registrado_en DESC);
