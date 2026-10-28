CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE habitaciones (
    id TEXT PRIMARY KEY,
    establecimiento_id TEXT NOT NULL,
    tipo TEXT NOT NULL,
    capacidad INTEGER NOT NULL CHECK (capacidad > 0),
    estado_operativo TEXT NOT NULL DEFAULT 'disponible',
    estado_preparacion TEXT NOT NULL DEFAULT 'limpia',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tarifas (
    id TEXT PRIMARY KEY,
    habitacion_id TEXT NOT NULL REFERENCES habitaciones(id),
    fecha_desde DATE NOT NULL,
    fecha_hasta DATE NOT NULL,
    tarifa_noche_clp INTEGER NOT NULL CHECK (tarifa_noche_clp > 0),
    CHECK (fecha_hasta > fecha_desde)
);

CREATE INDEX idx_tarifas_habitacion_fecha ON tarifas (habitacion_id, fecha_desde);

-- La base rechaza el solape: como máximo una reserva confirmada por
-- (habitación, rango de fechas). La carrera por la última unidad la gana una.
CREATE TABLE reservas (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    habitacion_id TEXT NOT NULL REFERENCES habitaciones(id),
    inicio DATE NOT NULL,
    fin DATE NOT NULL,
    huesped_nombre TEXT NOT NULL,
    huesped_documento TEXT,
    tarifa_noche_aceptada_clp INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'confirmada',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (fin > inicio),
    CONSTRAINT reservas_sin_solape EXCLUDE USING gist (
        habitacion_id WITH =,
        daterange(inicio, fin, '[)') WITH &&
    ) WHERE (estado = 'confirmada')
);

CREATE TABLE claves_idempotencia (
    empresa_id TEXT NOT NULL,
    clave TEXT NOT NULL,
    hash_cuerpo TEXT NOT NULL,
    codigo_respuesta INTEGER NOT NULL,
    cuerpo_respuesta JSONB NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (empresa_id, clave)
);
