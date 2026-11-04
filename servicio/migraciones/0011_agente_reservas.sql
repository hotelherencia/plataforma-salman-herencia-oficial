-- Agente de reservas N0 (2026-11-04, spec 005, V1-ISSUE-29; D-AGT-01
-- ratificada 2026-11-04). Copiloto de recepción: el texto que se guarda ya
-- viene redactado (NFR-A03); las trazas solo agregan filas; el usuario de
-- servicio `agente` no tiene clave utilizable ni email. Nada se borra.
CREATE TABLE IF NOT EXISTS consultas_agente (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    canal_origen TEXT NOT NULL,
    texto_redactado TEXT NOT NULL,
    recibida_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    registrada_por TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente',
    motivo TEXT
);

CREATE INDEX IF NOT EXISTS idx_consultas_agente_bandeja ON consultas_agente (empresa_id, estado, recibida_en);

CREATE TABLE IF NOT EXISTS borradores_agente (
    id TEXT PRIMARY KEY,
    consulta_id TEXT NOT NULL REFERENCES consultas_agente(id),
    plantilla TEXT NOT NULL,
    campos JSONB NOT NULL DEFAULT '{}'::jsonb,
    texto_compuesto TEXT NOT NULL,
    oferta_emitida_en TIMESTAMPTZ,
    vigente_hasta TIMESTAMPTZ,
    estado TEXT NOT NULL DEFAULT 'pendiente_aprobacion',
    aprobado_por TEXT,
    aprobado_en TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_borradores_agente_consulta ON borradores_agente (consulta_id);

CREATE TABLE IF NOT EXISTS trazas_agente (
    id TEXT PRIMARY KEY,
    consulta_id TEXT NOT NULL REFERENCES consultas_agente(id),
    turno INTEGER NOT NULL,
    herramienta TEXT NOT NULL,
    argumentos JSONB NOT NULL DEFAULT '{}'::jsonb,
    resultado JSONB NOT NULL DEFAULT '{}'::jsonb,
    decision TEXT NOT NULL,
    verificacion TEXT NOT NULL,
    version_prompt TEXT NOT NULL,
    version_politica TEXT NOT NULL,
    modelo TEXT NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_trazas_agente_consulta ON trazas_agente (consulta_id);

CREATE TABLE IF NOT EXISTS politica_agente (
    empresa_id TEXT PRIMARY KEY,
    nivel TEXT NOT NULL DEFAULT 'N0',
    horario TEXT,
    max_noches INTEGER NOT NULL DEFAULT 30,
    max_personas INTEGER NOT NULL DEFAULT 30,
    tope_mensual_clp BIGINT,
    evaluacion_ref TEXT,
    actualizada_por TEXT,
    actualizada_en TIMESTAMPTZ
);
