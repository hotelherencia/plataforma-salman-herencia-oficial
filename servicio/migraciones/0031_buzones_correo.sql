-- #355 (2026-11-18): servidores de correo configurables desde la plataforma.
-- Un buzón lee enviados (para marcar leads contactados) o envía avisos.
-- Parámetros en claro (host, puerto, usuario...); secretos cifrados con
-- Fernet (CORREO_CLAVE_CIFRADO), nunca en claro ni en la API.
CREATE TABLE buzones_correo (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    etiqueta TEXT NOT NULL,
    proposito TEXT NOT NULL CHECK (proposito IN ('lectura_enviados', 'envio_avisos')),
    proveedor TEXT NOT NULL CHECK (proveedor IN ('imap', 'smtp', 'gmail_api', 'microsoft_graph')),
    parametros JSONB NOT NULL DEFAULT '{}',
    secretos_cifrados TEXT,
    activo BOOLEAN NOT NULL DEFAULT true,
    revisado_hasta TIMESTAMPTZ,
    ultima_revision_en TIMESTAMPTZ,
    ultimo_resultado TEXT,
    ultimo_error TEXT,
    actualizado_por TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_buzones_empresa ON buzones_correo (empresa_id, proposito, activo);
CREATE UNIQUE INDEX idx_buzones_etiqueta ON buzones_correo (empresa_id, proposito, lower(etiqueta));
