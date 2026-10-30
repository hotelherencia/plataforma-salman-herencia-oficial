-- Maduración operativa V1 (2026-10-30): usuarios activos y nombre único por
-- empresa, mantenimiento de habitación, estado cancelada, solape que cubre
-- en_estadia, reversos de cargos y tareas operativas durables.
-- DECISIÓN 2026-10-30: el archivo se numera 0007 porque 0006 quedó ocupado
-- por la migración de nombre de usuario único del trabajo pre-H7 en curso;
-- ambas conviven (la otra impone unicidad global de nombre, esta la
-- unicidad por empresa que exige spec-api-v1).
-- El DDL es deliberadamente tolerante a reaplicación parcial (ADD COLUMN
-- IF NOT EXISTS, DROP CONSTRAINT IF EXISTS antes de re-crear, CREATE TABLE
-- IF NOT EXISTS): la base de desarrollo compartida registró versiones
-- ajenas con parte de este mismo esquema y el arranque no debe romperse.

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE habitaciones ADD COLUMN IF NOT EXISTS mantenimiento BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE cargos ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'cargo';
ALTER TABLE cargos ADD COLUMN IF NOT EXISTS referencia TEXT;

-- El estado cancelada entra al dominio (DECISIÓN 2026-10-30, fuente
-- hotel_inventario.servicio.cancelar); los nombres en_estadia y finalizada
-- ya publicados no se renombran.
ALTER TABLE reservas DROP CONSTRAINT IF EXISTS reservas_estado_valido;
ALTER TABLE reservas ADD CONSTRAINT reservas_estado_valido
    CHECK (estado IN ('confirmada', 'en_estadia', 'finalizada', 'cancelada'));

-- El rango ocupa cupo en confirmada y en_estadia; cancelada y finalizada lo
-- sueltan (DECISIÓN 2026-10-30, fuente hotel_inventario.servicio._libre:
-- ocupantes = CONFIRMADA, HOSPEDADA).
ALTER TABLE reservas DROP CONSTRAINT IF EXISTS reservas_sin_solape;
ALTER TABLE reservas ADD CONSTRAINT reservas_sin_solape EXCLUDE USING gist (
    habitacion_id WITH =,
    daterange(inicio, fin, '[)') WITH &&
) WHERE (estado IN ('confirmada', 'en_estadia'));

-- Cargos inmutables (HECHO DOCUMENTADO, fuente hotel_inventario/dominio.py:
-- Cargo, TipoCargo): la corrección es otro asiento; el reverso guarda monto
-- positivo y referencia al cargo original.
ALTER TABLE cargos DROP CONSTRAINT IF EXISTS cargos_tipo_valido;
ALTER TABLE cargos ADD CONSTRAINT cargos_tipo_valido CHECK (tipo IN ('cargo', 'reverso'));

ALTER TABLE usuarios DROP CONSTRAINT IF EXISTS usuarios_empresa_nombre_unico;
ALTER TABLE usuarios ADD CONSTRAINT usuarios_empresa_nombre_unico UNIQUE (empresa_id, nombre);

-- Tareas de limpieza y mantenimiento, durables al reinicio (DECISIÓN
-- 2026-10-30, fuente hotel_inventario.servicio.check_out y
-- _fijar_mantenimiento).
CREATE TABLE IF NOT EXISTS tareas_operativas (
    id TEXT PRIMARY KEY,
    habitacion_id TEXT NOT NULL REFERENCES habitaciones(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('limpieza', 'mantenimiento')),
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'completada')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    completada_en TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tareas_habitacion ON tareas_operativas (habitacion_id);
