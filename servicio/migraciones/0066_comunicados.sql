-- 0066: comunicados internos con confirmación de lectura (#418, Corte 2). Aditiva e idempotente.
CREATE TABLE IF NOT EXISTS comunicados (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL CHECK (length(titulo) BETWEEN 3 AND 120),
    cuerpo TEXT NOT NULL CHECK (length(cuerpo) BETWEEN 3 AND 4000),
    -- Roles destinatarios; vacío = todo el personal.
    roles TEXT[] NOT NULL DEFAULT '{}',
    archivado BOOLEAN NOT NULL DEFAULT false,
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Confirmaciones de lectura: una por usuario y comunicado; solo se agregan.
CREATE TABLE IF NOT EXISTS comunicado_lecturas (
    comunicado_id TEXT NOT NULL REFERENCES comunicados(id),
    usuario TEXT NOT NULL,
    leido_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (comunicado_id, usuario)
);

CREATE OR REPLACE FUNCTION comunicado_lecturas_solo_agregar() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'las confirmaciones de lectura no se modifican ni se borran';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_comunicado_lecturas_solo_agregar ON comunicado_lecturas;
CREATE TRIGGER trg_comunicado_lecturas_solo_agregar
    BEFORE UPDATE OR DELETE ON comunicado_lecturas
    FOR EACH ROW EXECUTE FUNCTION comunicado_lecturas_solo_agregar();
