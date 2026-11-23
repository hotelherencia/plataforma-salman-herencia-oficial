-- 0059: Corte 1 operativo (#415, #416, #417). Aditiva e idempotente.
-- Incidencias con evidencia y bloqueo de disponibilidad; tareas generales con
-- checklists y subtareas; estado «En limpieza» sin tocar estado_preparacion
-- (el dominio en memoria no lo conoce y lo reescribiría al persistir).

CREATE TABLE IF NOT EXISTS incidencias (
    id TEXT PRIMARY KEY,
    habitacion_id TEXT REFERENCES habitaciones(id),
    area TEXT,
    descripcion TEXT NOT NULL CHECK (length(descripcion) BETWEEN 3 AND 1000),
    gravedad TEXT NOT NULL DEFAULT 'media' CHECK (gravedad IN ('baja', 'media', 'alta', 'critica')),
    responsable TEXT,
    plazo DATE,
    estado TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta', 'en_curso', 'resuelta', 'cerrada')),
    costo_clp INTEGER CHECK (costo_clp IS NULL OR costo_clp >= 0),
    bloquea_disponibilidad BOOLEAN NOT NULL DEFAULT false,
    bloqueo_aplicado BOOLEAN NOT NULL DEFAULT false,
    creada_por TEXT NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    cerrada_en TIMESTAMPTZ,
    CHECK (habitacion_id IS NOT NULL OR area IS NOT NULL),
    CHECK (NOT bloquea_disponibilidad OR habitacion_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_incidencias_estado ON incidencias (estado, gravedad);
CREATE INDEX IF NOT EXISTS idx_incidencias_habitacion ON incidencias (habitacion_id) WHERE estado IN ('abierta', 'en_curso');

-- Evidencia fotográfica ligera (la API limita el tamaño; el front la reduce en el móvil).
CREATE TABLE IF NOT EXISTS incidencia_evidencias (
    id TEXT PRIMARY KEY,
    incidencia_id TEXT NOT NULL REFERENCES incidencias(id),
    mime TEXT NOT NULL CHECK (mime IN ('image/jpeg', 'image/png', 'image/webp')),
    contenido BYTEA NOT NULL,
    subida_por TEXT NOT NULL,
    subida_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_incidencia_evidencias ON incidencia_evidencias (incidencia_id);

-- Bitácora append-only: creación, cambios de estado y cierre.
CREATE TABLE IF NOT EXISTS incidencia_eventos (
    id BIGSERIAL PRIMARY KEY,
    incidencia_id TEXT NOT NULL REFERENCES incidencias(id),
    accion TEXT NOT NULL,
    detalle TEXT,
    actor TEXT NOT NULL,
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE OR REPLACE FUNCTION incidencia_eventos_solo_agregar() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'incidencia_eventos es append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS incidencia_eventos_inmutable ON incidencia_eventos;
CREATE TRIGGER incidencia_eventos_inmutable BEFORE UPDATE OR DELETE ON incidencia_eventos
    FOR EACH ROW EXECUTE FUNCTION incidencia_eventos_solo_agregar();

-- Tareas generales (baños, lavandería, desayunos, mantención…) con subtareas.
-- Aparte de tareas_operativas: esa tabla la gobierna el dominio de limpieza.
CREATE TABLE IF NOT EXISTS tareas_generales (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL CHECK (length(titulo) BETWEEN 2 AND 160),
    area TEXT NOT NULL DEFAULT 'general' CHECK (area IN ('limpieza', 'banos', 'lavanderia', 'desayunos', 'mantencion', 'general')),
    habitacion_id TEXT REFERENCES habitaciones(id),
    prioridad TEXT NOT NULL DEFAULT 'normal' CHECK (prioridad IN ('baja', 'normal', 'alta', 'urgente')),
    vence DATE,
    responsable TEXT,
    observaciones TEXT CHECK (observaciones IS NULL OR length(observaciones) <= 1000),
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'completada')),
    creada_por TEXT NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    completada_por TEXT,
    completada_en TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_tareas_generales_estado ON tareas_generales (estado, vence);

CREATE TABLE IF NOT EXISTS tarea_subtareas (
    id TEXT PRIMARY KEY,
    tarea_id TEXT NOT NULL REFERENCES tareas_generales(id),
    orden INTEGER NOT NULL DEFAULT 0,
    texto TEXT NOT NULL CHECK (length(texto) BETWEEN 2 AND 200),
    obligatoria BOOLEAN NOT NULL DEFAULT true,
    hecha BOOLEAN NOT NULL DEFAULT false,
    hecha_por TEXT,
    hecha_en TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_tarea_subtareas ON tarea_subtareas (tarea_id, orden);

CREATE TABLE IF NOT EXISTS checklist_plantillas (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE CHECK (length(nombre) BETWEEN 2 AND 120),
    area TEXT NOT NULL DEFAULT 'general' CHECK (area IN ('limpieza', 'banos', 'lavanderia', 'desayunos', 'mantencion', 'general')),
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    creada_por TEXT NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- «En limpieza»: la habitación sucia que aseo ya tomó.
ALTER TABLE habitaciones ADD COLUMN IF NOT EXISTS en_limpieza_desde TIMESTAMPTZ;
ALTER TABLE habitaciones ADD COLUMN IF NOT EXISTS en_limpieza_por TEXT;
