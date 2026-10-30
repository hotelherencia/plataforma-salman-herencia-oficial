-- Maduración de la operación del hotel V1 (2026-10-30).
-- Fuentes: spec-api-v1 (secciones «Gestión de usuarios», «Operación de la
-- habitación», «Cancelación», «Cargos de la estadía») y dominio
-- hotel_inventario (Estados vendibles, tareas de limpieza, reversos).

-- Usuarios: alta/baja y nombre único por empresa.
ALTER TABLE usuarios ADD COLUMN activo BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE usuarios ADD CONSTRAINT usuarios_nombre_unico UNIQUE (empresa_id, nombre);

-- Reservas: el estado cancelada entra al CHECK vigente.
ALTER TABLE reservas DROP CONSTRAINT reservas_estado_valido;
ALTER TABLE reservas ADD CONSTRAINT reservas_estado_valido
    CHECK (estado IN ('confirmada', 'en_estadia', 'finalizada', 'cancelada'));

-- No solape: el rango queda tomado en confirmada y en_estadia; cancelada y
-- finalizada lo sueltan.
ALTER TABLE reservas DROP CONSTRAINT reservas_sin_solape;
ALTER TABLE reservas ADD CONSTRAINT reservas_sin_solape EXCLUDE USING gist (
    habitacion_id WITH =,
    daterange(inicio, fin, '[)') WITH &&
) WHERE (estado IN ('confirmada', 'en_estadia'));

-- Habitaciones: el mantenimiento saca la unidad del cupo (distinto de la
-- limpieza, que no quita cupo vendible).
ALTER TABLE habitaciones ADD COLUMN mantenimiento BOOLEAN NOT NULL DEFAULT false;

-- Tareas operativas durables: limpieza (nace al check-out) y mantenimiento.
CREATE TABLE tareas_operativas (
    id TEXT PRIMARY KEY,
    habitacion_id TEXT NOT NULL REFERENCES habitaciones(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('limpieza', 'mantenimiento')),
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'completada')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    completada_en TIMESTAMPTZ
);
CREATE INDEX idx_tareas_operativas_habitacion ON tareas_operativas (habitacion_id, estado);

-- Cargos: los cargos son inmemoriales; la corrección es un asiento reverso
-- de monto positivo que referencia al cargo original.
ALTER TABLE cargos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'cargo' CHECK (tipo IN ('cargo', 'reverso'));
ALTER TABLE cargos ADD COLUMN referencia TEXT;
