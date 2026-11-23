-- 0067_corte2_turnos_biblioteca_activos.sql
-- Corte 2 Operativo P1 (#418 parte 2 — ref. Orquestia; comunicados ya cubiertos en 0066):
--   1) Vista semanal de turnos por área y cambios de turno aprobados
--   2) Biblioteca documental por rol y buzón de sugerencias
--   3) Inventario de activos por habitación/área y mantenimiento preventivo periódico
-- Migración estrictamente aditiva e idempotente.

CREATE TABLE IF NOT EXISTS turnos_personal (
    id BIGSERIAL PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    usuario_nombre TEXT NOT NULL,
    area TEXT NOT NULL CHECK (area IN ('recepcion', 'aseo', 'desayunos', 'mantencion')),
    fecha DATE NOT NULL,
    hora_inicio TEXT NOT NULL,
    hora_fin TEXT NOT NULL,
    nota TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'programado' CHECK (estado IN ('programado', 'cambiado', 'cancelado')),
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_turnos_personal_empresa_fecha
    ON turnos_personal (empresa_id, fecha, area);

CREATE TABLE IF NOT EXISTS cambios_turno (
    id BIGSERIAL PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    turno_id BIGINT NOT NULL REFERENCES turnos_personal (id) ON DELETE CASCADE,
    solicitante TEXT NOT NULL,
    reemplazo_usuario TEXT NOT NULL,
    motivo TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobado', 'rechazado')),
    revisado_por TEXT,
    revisado_en TIMESTAMPTZ,
    nota_revision TEXT NOT NULL DEFAULT '',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cambios_turno_empresa_estado
    ON cambios_turno (empresa_id, estado, creado_en DESC);

CREATE TABLE IF NOT EXISTS biblioteca_documentos (
    id BIGSERIAL PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    titulo TEXT NOT NULL,
    categoria TEXT NOT NULL CHECK (categoria IN ('manual', 'instructivo', 'politica', 'protocolo')),
    rol_objetivo TEXT NOT NULL DEFAULT 'todos',
    contenido TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT '1.0',
    creado_por TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_biblioteca_documentos_empresa_rol
    ON biblioteca_documentos (empresa_id, activo, rol_objetivo, categoria);

CREATE TABLE IF NOT EXISTS sugerencias_equipo (
    id BIGSERIAL PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'operacion' CHECK (categoria IN ('operacion', 'mantencion', 'huespedes', 'equipo', 'otro')),
    mensaje TEXT NOT NULL,
    anonimo BOOLEAN NOT NULL DEFAULT FALSE,
    autor TEXT,
    estado TEXT NOT NULL DEFAULT 'recibida' CHECK (estado IN ('recibida', 'en_revision', 'implementada', 'archivada')),
    respuesta_admin TEXT NOT NULL DEFAULT '',
    revisado_por TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sugerencias_equipo_empresa_estado
    ON sugerencias_equipo (empresa_id, estado, creado_en DESC);

CREATE TABLE IF NOT EXISTS activos_hotel (
    id BIGSERIAL PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL DEFAULT 'equipamiento',
    habitacion_id TEXT,
    area TEXT,
    numero_serie TEXT NOT NULL DEFAULT '',
    estado TEXT NOT NULL DEFAULT 'operativo' CHECK (estado IN ('operativo', 'en_mantencion', 'fuera_de_servicio', 'baja')),
    frecuencia_mantencion_dias INTEGER CHECK (frecuencia_mantencion_dias IS NULL OR frecuencia_mantencion_dias > 0),
    ultima_mantencion DATE,
    proxima_mantencion DATE,
    notas TEXT NOT NULL DEFAULT '',
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (habitacion_id IS NOT NULL OR area IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_activos_hotel_empresa_proxima
    ON activos_hotel (empresa_id, habitacion_id, proxima_mantencion);

CREATE TABLE IF NOT EXISTS activos_mantenciones (
    id BIGSERIAL PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    activo_id BIGINT NOT NULL REFERENCES activos_hotel (id) ON DELETE CASCADE,
    fecha_realizada DATE NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'preventiva' CHECK (tipo IN ('preventiva', 'correctiva')),
    descripcion TEXT NOT NULL,
    costo_clp INTEGER NOT NULL DEFAULT 0 CHECK (costo_clp >= 0),
    realizado_por TEXT NOT NULL,
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activos_mantenciones_activo
    ON activos_mantenciones (empresa_id, activo_id, fecha_realizada DESC);

CREATE OR REPLACE FUNCTION impedir_modificacion_activos_mantenciones()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'activos_mantenciones es inmutable (append-only)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_activos_mantenciones_inmutables ON activos_mantenciones;
CREATE TRIGGER trg_activos_mantenciones_inmutables
    BEFORE UPDATE OR DELETE ON activos_mantenciones
    FOR EACH ROW EXECUTE FUNCTION impedir_modificacion_activos_mantenciones();
