-- 2026-11-20: teléfono en clientes (para búsqueda y contacto) y vínculos explícitos lead ↔ cliente/solicitud.
-- Migración puramente aditiva: no modifica ni borra registros contables ni históricos.
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono TEXT;
CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes (telefono) WHERE telefono IS NOT NULL;

ALTER TABLE leads ADD COLUMN IF NOT EXISTS cliente_id TEXT REFERENCES clientes(id);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS solicitud_id TEXT REFERENCES solicitudes(id);
CREATE INDEX IF NOT EXISTS idx_leads_cliente ON leads (cliente_id) WHERE cliente_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_solicitud ON leads (solicitud_id) WHERE solicitud_id IS NOT NULL;
