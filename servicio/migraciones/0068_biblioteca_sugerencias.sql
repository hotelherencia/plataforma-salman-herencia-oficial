-- 0068: biblioteca documental por rol y buzón de sugerencias (#418, Corte 2 parte 3). Aditiva e idempotente.
CREATE TABLE IF NOT EXISTS biblioteca_documentos (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL CHECK (length(titulo) BETWEEN 3 AND 120),
    categoria TEXT NOT NULL CHECK (categoria IN ('manual', 'instructivo', 'politica', 'otro')),
    contenido TEXT NOT NULL DEFAULT '' CHECK (length(contenido) <= 20000),
    enlace TEXT CHECK (enlace IS NULL OR enlace ~ '^https://'),
    roles TEXT[] NOT NULL DEFAULT '{}',          -- vacío = todo el personal
    archivado BOOLEAN NOT NULL DEFAULT false,
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (length(contenido) > 0 OR enlace IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS sugerencias (
    id TEXT PRIMARY KEY,
    texto TEXT NOT NULL CHECK (length(texto) BETWEEN 3 AND 1000),
    autor TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'nueva' CHECK (estado IN ('nueva', 'atendida')),
    respuesta TEXT CHECK (respuesta IS NULL OR length(respuesta) <= 500),
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    atendida_por TEXT,
    atendida_en TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sugerencias_estado ON sugerencias (estado, creada_en);
