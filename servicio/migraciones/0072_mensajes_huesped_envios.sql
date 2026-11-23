-- 0072: registro de mensajes enviados al huésped (#452). Aditiva e idempotente, solo se agrega.
-- No guarda el cuerpo ni el destino completo: plantilla, canal, estado, actor y destino enmascarado.
CREATE TABLE IF NOT EXISTS mensajes_huesped_envios (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    reserva_id TEXT NOT NULL REFERENCES reservas(id),
    plantilla TEXT NOT NULL,
    canal TEXT NOT NULL CHECK (canal IN ('correo', 'whatsapp_manual')),
    destino_enmascarado TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('enviado', 'fallido', 'abierto')),
    detalle TEXT,
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS idx_mensajes_huesped_reserva ON mensajes_huesped_envios (reserva_id, creado_en);
