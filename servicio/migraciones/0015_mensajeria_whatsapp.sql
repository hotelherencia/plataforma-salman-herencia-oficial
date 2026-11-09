-- Entrada WhatsApp (spec 006, #324, 2026-11-09). El id externo deduplica
-- el reintento de Meta; la conversación enlaza el mensaje con la consulta
-- del agente. El texto del huésped no se copia aquí: queda redactado en
-- consultas_agente. Nada se borra.
CREATE TABLE IF NOT EXISTS mensajes_whatsapp (
    id_externo TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    conversacion_externa TEXT NOT NULL,
    consulta_id TEXT NOT NULL REFERENCES consultas_agente(id),
    recibido_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS idx_mensajes_whatsapp_conversacion
    ON mensajes_whatsapp (empresa_id, conversacion_externa, recibido_en);
