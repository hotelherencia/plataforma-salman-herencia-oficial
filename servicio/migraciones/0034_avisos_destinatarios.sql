-- Avisos por correo configurables (2026-11-19): qué eventos avisan y a quién.
-- Nombre distinto a propósito: main ya trae 0033_importacion_productos y otra rama puede sumar más; las
-- versiones se identifican por el nombre completo del archivo.
--
-- - avisos_preferencias: por empresa y tipo de evento, encendido/apagado y
--   lista de correos. Sin fila (o con lista vacía) se usa el destino por
--   defecto (buzón de envío, AVISO_CORREO_DESTINO o ADMIN_EMAIL).
-- - avisos_eventos.empresa_id: a qué hotel pertenece el evento (nullable:
--   los eventos anteriores usan la empresa del proceso).
-- - avisos_envios: estado «omitido» (aviso apagado, sin destinatarios o
--   resumen vencido) y a quién se envió.
CREATE TABLE avisos_preferencias (
    empresa_id TEXT NOT NULL,
    tipo TEXT NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT true,
    destinatarios JSONB NOT NULL DEFAULT '[]'::jsonb,
    actualizado_por TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (empresa_id, tipo)
);

ALTER TABLE avisos_eventos ADD COLUMN empresa_id TEXT;

ALTER TABLE avisos_envios DROP CONSTRAINT IF EXISTS avisos_envios_estado_check;
ALTER TABLE avisos_envios ADD CONSTRAINT avisos_envios_estado_check
    CHECK (estado IN ('enviado', 'fallido', 'omitido'));
ALTER TABLE avisos_envios ADD COLUMN destinatarios TEXT;
CREATE INDEX idx_avisos_envios_actualizado ON avisos_envios (actualizado_en DESC);
