-- 0059: Corte 1 operativo pre-01/01/2027 (#415 Incidencias, #416 Tareas/Checklists y estado En limpieza).
-- Migración aditiva e idempotente.

-- 1. Tabla de incidencias operativas (#415)
CREATE TABLE IF NOT EXISTS incidencias (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    habitacion_id TEXT REFERENCES habitaciones(id),
    area TEXT NOT NULL DEFAULT 'habitacion',
    titulo TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    gravedad TEXT NOT NULL DEFAULT 'media'
        CHECK (gravedad IN ('baja', 'media', 'alta', 'critica')),
    estado TEXT NOT NULL DEFAULT 'abierta'
        CHECK (estado IN ('abierta', 'en_progreso', 'resuelta', 'cerrada')),
    responsable TEXT,
    plazo DATE,
    costo_clp INTEGER CHECK (costo_clp IS NULL OR costo_clp >= 0),
    bloquea_disponibilidad BOOLEAN NOT NULL DEFAULT false,
    evidencia_nombre TEXT,
    evidencia_mime TEXT,
    evidencia_datos BYTEA,
    resolucion TEXT,
    reportada_por TEXT NOT NULL,
    creada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizada_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    cerrada_en TIMESTAMPTZ,
    cerrada_por TEXT,
    CHECK (habitacion_id IS NOT NULL OR length(trim(area)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_incidencias_empresa_estado
    ON incidencias (empresa_id, estado, gravedad, creada_en DESC);

CREATE INDEX IF NOT EXISTS idx_incidencias_habitacion_abiertas
    ON incidencias (habitacion_id, estado)
    WHERE habitacion_id IS NOT NULL;

-- 2. Extensión de tareas_operativas (#416): áreas comunes, prioridad, vencimiento, estado en_proceso
ALTER TABLE tareas_operativas ALTER COLUMN habitacion_id DROP NOT NULL;

ALTER TABLE tareas_operativas ADD COLUMN IF NOT EXISTS empresa_id TEXT;
ALTER TABLE tareas_operativas ADD COLUMN IF NOT EXISTS area TEXT;
ALTER TABLE tareas_operativas ADD COLUMN IF NOT EXISTS titulo TEXT;
ALTER TABLE tareas_operativas ADD COLUMN IF NOT EXISTS prioridad TEXT NOT NULL DEFAULT 'media';
ALTER TABLE tareas_operativas ADD COLUMN IF NOT EXISTS responsable TEXT;
ALTER TABLE tareas_operativas ADD COLUMN IF NOT EXISTS vence_en TIMESTAMPTZ;
ALTER TABLE tareas_operativas ADD COLUMN IF NOT EXISTS iniciada_en TIMESTAMPTZ;
ALTER TABLE tareas_operativas ADD COLUMN IF NOT EXISTS iniciada_por TEXT;
ALTER TABLE tareas_operativas ADD COLUMN IF NOT EXISTS creada_por TEXT;

DO $$
DECLARE
    c RECORD;
BEGIN
    FOR c IN
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = 'tareas_operativas'::regclass
          AND contype = 'c'
          AND (
              pg_get_constraintdef(oid) ILIKE '%tipo%'
              OR pg_get_constraintdef(oid) ILIKE '%estado%'
              OR pg_get_constraintdef(oid) ILIKE '%prioridad%'
          )
    LOOP
        EXECUTE format('ALTER TABLE tareas_operativas DROP CONSTRAINT IF EXISTS %I', c.conname);
    END LOOP;

    ALTER TABLE tareas_operativas ADD CONSTRAINT tareas_operativas_tipo_valido
        CHECK (tipo IN ('limpieza', 'mantenimiento', 'banos', 'lavanderia', 'desayunos', 'general'));
    ALTER TABLE tareas_operativas ADD CONSTRAINT tareas_operativas_estado_valido
        CHECK (estado IN ('pendiente', 'en_proceso', 'completada', 'cancelada'));
    ALTER TABLE tareas_operativas ADD CONSTRAINT tareas_operativas_prioridad_valida
        CHECK (prioridad IN ('baja', 'media', 'alta', 'urgente'));
END $$;

CREATE INDEX IF NOT EXISTS idx_tareas_operativas_estado_prioridad
    ON tareas_operativas (estado, prioridad, creado_en DESC);

-- 3. Subtareas marcables individualmente por tarea (#416)
CREATE TABLE IF NOT EXISTS tarea_subtareas (
    id TEXT PRIMARY KEY,
    tarea_id TEXT NOT NULL REFERENCES tareas_operativas(id) ON DELETE CASCADE,
    descripcion TEXT NOT NULL,
    obligatoria BOOLEAN NOT NULL DEFAULT true,
    completada BOOLEAN NOT NULL DEFAULT false,
    completada_por TEXT,
    completada_en TIMESTAMPTZ,
    orden INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tarea_subtareas_tarea
    ON tarea_subtareas (tarea_id, orden, id);

-- 4. Plantillas base de checklist configurables por tipo de tarea (#416)
CREATE TABLE IF NOT EXISTS checklist_plantillas (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL CHECK (tipo IN ('limpieza', 'mantenimiento', 'banos', 'lavanderia', 'desayunos', 'general')),
    descripcion TEXT NOT NULL,
    obligatoria BOOLEAN NOT NULL DEFAULT true,
    orden INTEGER NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT true
);

INSERT INTO checklist_plantillas (id, tipo, descripcion, obligatoria, orden) VALUES
    ('CHK-LIMP-01', 'limpieza', 'Cambiar ropa de cama y verificar almohadas', true, 10),
    ('CHK-LIMP-02', 'limpieza', 'Limpiar y desinfectar baño completo', true, 20),
    ('CHK-LIMP-03', 'limpieza', 'Reponer toallas, papel higiénico y amenidades', true, 30),
    ('CHK-LIMP-04', 'limpieza', 'Aspirar/trapear piso y retirar basura', true, 40),
    ('CHK-LIMP-05', 'limpieza', 'Revisar luces, TV, aire acondicionado y cierre de ventanas', false, 50),
    ('CHK-BANO-01', 'banos', 'Desinfectar lavamanos, WC y espejos de áreas comunes', true, 10),
    ('CHK-BANO-02', 'banos', 'Reponer jabón, papel y toallas de papel', true, 20),
    ('CHK-LAV-01', 'lavanderia', 'Clasificar y lavar ropa blanca de habitaciones', true, 10),
    ('CHK-LAV-02', 'lavanderia', 'Doblar, contar y almacenar ropa limpia', true, 20),
    ('CHK-DES-01', 'desayunos', 'Montar buffet y revisar stock de insumos', true, 10),
    ('CHK-DES-02', 'desayunos', 'Limpiar mesas y sanitizar estación al cierre', true, 20),
    ('CHK-MANT-01', 'mantenimiento', 'Verificar reparación y seguridad eléctrica/sanitaria', true, 10)
ON CONFLICT (id) DO NOTHING;
