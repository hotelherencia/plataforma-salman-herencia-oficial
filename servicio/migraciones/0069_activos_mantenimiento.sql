-- 0069: inventario de activos por habitación y mantenimiento preventivo periódico (#418, Corte 2 parte 4).
-- Aditiva e idempotente. No toca habitaciones ni tareas_operativas (el dominio en memoria las reescribe).
CREATE TABLE IF NOT EXISTS activos (
    id TEXT PRIMARY KEY,
    habitacion_id TEXT REFERENCES habitaciones(id),     -- NULL = área común
    area TEXT CHECK (area IS NULL OR length(area) BETWEEN 2 AND 60),
    nombre TEXT NOT NULL CHECK (length(nombre) BETWEEN 2 AND 80),
    categoria TEXT NOT NULL DEFAULT 'otro' CHECK (categoria IN ('mobiliario', 'electrico', 'climatizacion', 'sanitario', 'electronico', 'otro')),
    estado TEXT NOT NULL DEFAULT 'operativo' CHECK (estado IN ('operativo', 'en_reparacion', 'de_baja')),
    notas TEXT CHECK (notas IS NULL OR length(notas) <= 300),
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (habitacion_id IS NOT NULL OR area IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_activos_habitacion ON activos (habitacion_id);

CREATE TABLE IF NOT EXISTS mantenciones_plan (
    id TEXT PRIMARY KEY,
    activo_id TEXT NOT NULL REFERENCES activos(id),
    descripcion TEXT NOT NULL CHECK (length(descripcion) BETWEEN 3 AND 200),
    cada_dias INTEGER NOT NULL CHECK (cada_dias BETWEEN 1 AND 1830),
    proxima DATE NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT true,
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mantenciones_proxima ON mantenciones_plan (proxima) WHERE activo;

-- Historial de mantenciones hechas: solo se agrega.
CREATE TABLE IF NOT EXISTS mantenciones_realizadas (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL REFERENCES mantenciones_plan(id),
    fecha DATE NOT NULL,
    realizada_por TEXT NOT NULL,
    nota TEXT CHECK (nota IS NULL OR length(nota) <= 300),
    registrada_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mantenciones_realizadas ON mantenciones_realizadas (plan_id, fecha);

CREATE OR REPLACE FUNCTION mantenciones_realizadas_solo_agregar() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'el historial de mantenciones no se modifica ni se borra';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_mantenciones_realizadas_solo_agregar ON mantenciones_realizadas;
CREATE TRIGGER trg_mantenciones_realizadas_solo_agregar
    BEFORE UPDATE OR DELETE ON mantenciones_realizadas
    FOR EACH ROW EXECUTE FUNCTION mantenciones_realizadas_solo_agregar();
