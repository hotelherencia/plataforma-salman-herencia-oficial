-- SPEC-CONV-01 y SPEC-PROV-01: convenios tarifarios por institución/delegación/evento
-- y reservas provisorias a nombre de empresa o institución (carga de pasajeros reales en la Llegada).

CREATE TABLE IF NOT EXISTS convenios_tarifarios (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('empresa', 'evento', 'delegacion')),
    cliente_id TEXT REFERENCES clientes(id),
    vigencia_desde DATE NOT NULL,
    vigencia_hasta DATE NOT NULL,
    reglas_precio JSONB NOT NULL DEFAULT '{}'::jsonb,
    requiere_abono_pct INTEGER NOT NULL DEFAULT 50 CHECK (requiere_abono_pct BETWEEN 0 AND 100),
    notas TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (vigencia_hasta >= vigencia_desde)
);

CREATE INDEX IF NOT EXISTS idx_convenios_empresa_activo
    ON convenios_tarifarios (empresa_id, activo, vigencia_desde, vigencia_hasta);

ALTER TABLE reservas
    ADD COLUMN IF NOT EXISTS convenio_id TEXT REFERENCES convenios_tarifarios(id),
    ADD COLUMN IF NOT EXISTS cliente_id TEXT REFERENCES clientes(id),
    ADD COLUMN IF NOT EXISTS tarifa_lista_clp INTEGER,
    ADD COLUMN IF NOT EXISTS diferencia_convenio_clp INTEGER,
    ADD COLUMN IF NOT EXISTS es_huesped_provisorio BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_reservas_convenio
    ON reservas (empresa_id, convenio_id)
    WHERE convenio_id IS NOT NULL;

ALTER TABLE reservas_grupo
    ADD COLUMN IF NOT EXISTS convenio_id TEXT REFERENCES convenios_tarifarios(id),
    ADD COLUMN IF NOT EXISTS cliente_id TEXT REFERENCES clientes(id),
    ADD COLUMN IF NOT EXISTS es_huesped_provisorio BOOLEAN NOT NULL DEFAULT FALSE;
