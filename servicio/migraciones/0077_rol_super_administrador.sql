-- 0077: rol «súper administrador». Gobierna las cuentas privilegiadas (administradores, dueño y otros
-- súper administradores) y exige segundo factor activo para operar. Aditiva e idempotente.
INSERT INTO roles_catalogo (codigo, modulo, etiqueta, descripcion, exige_doble_factor, activo, orden) VALUES
    ('super_admin', 'core', 'Súper administrador', 'Gobierna las cuentas privilegiadas (administradores, dueño y otros súper administradores) y la seguridad; tiene todo lo de la administración', true, true, 1)
ON CONFLICT (codigo) DO NOTHING;

-- Hay un solo súper administrador por empresa (la cuenta institucional).
CREATE UNIQUE INDEX IF NOT EXISTS uq_un_super_admin_por_empresa ON usuarios (empresa_id) WHERE rol = 'super_admin';

-- Cambios de rol pendientes de validación: quien pide no aprueba; aprueba la administración del hotel.
CREATE TABLE IF NOT EXISTS cambios_rol (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    usuario_id TEXT NOT NULL REFERENCES usuarios(id),
    rol_anterior TEXT,                                   -- NULL = alta de una cuenta con rol privilegiado
    rol_nuevo TEXT NOT NULL,
    motivo TEXT CHECK (motivo IS NULL OR length(motivo) <= 300),
    solicitado_por TEXT NOT NULL,
    solicitado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'aprobado', 'rechazado')),
    resuelto_por TEXT,
    resuelto_en TIMESTAMPTZ,
    comentario TEXT CHECK (comentario IS NULL OR length(comentario) <= 300),
    sin_aprobador BOOLEAN NOT NULL DEFAULT false          -- aplicado sin segunda persona (aún no existe aprobador)
);
CREATE INDEX IF NOT EXISTS idx_cambios_rol_estado ON cambios_rol (empresa_id, estado, solicitado_en);
CREATE UNIQUE INDEX IF NOT EXISTS uq_cambio_rol_pendiente_por_usuario ON cambios_rol (usuario_id) WHERE estado = 'pendiente';
