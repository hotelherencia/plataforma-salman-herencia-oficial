-- #353 (2026-11-18): avisos activos al administrador (correo y WhatsApp).
-- Bandeja de salida: el evento se registra en la misma transacción que la
-- solicitud; un despachador lo envía por cada canal configurado. Un fallo de
-- envío nunca impide guardar la solicitud y se reintenta (máximo 5 veces).
CREATE TABLE avisos_eventos (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL,
    referencia TEXT NOT NULL,
    datos JSONB NOT NULL DEFAULT '{}'::jsonb,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tipo, referencia)
);
CREATE INDEX idx_avisos_eventos_creado ON avisos_eventos (creado_en);

CREATE TABLE avisos_envios (
    evento_id TEXT NOT NULL REFERENCES avisos_eventos(id),
    canal TEXT NOT NULL CHECK (canal IN ('correo', 'whatsapp')),
    estado TEXT NOT NULL CHECK (estado IN ('enviado', 'fallido')),
    intentos INTEGER NOT NULL DEFAULT 0,
    ultimo_error TEXT,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (evento_id, canal)
);
