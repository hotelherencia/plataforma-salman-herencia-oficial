-- Leads / contacto de la landing (2026-11-04, spec-api-v1 «Contacto y leads
-- de la landing», V1-ISSUE-20 punto 8 resuelto: formulario propio, Formspree
-- retirado). Prospección: la consulta general del visitante queda en la
-- plataforma como agenda de seguimiento de recepción. Los datos de contacto
-- se guardan tal cual (igual que solicitudes.huesped_contacto); la redacción
-- NFR-A03 solo aplica si el texto sale a un modelo externo, que este canal
-- no hace. Espacio de claves propio: la clave del visitante nunca toca
-- claves_idempotencia. Nada se borra.
CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL,
    telefono TEXT NOT NULL,
    huespedes INTEGER,
    check_in DATE,
    check_out DATE,
    mensaje TEXT,
    estado TEXT NOT NULL DEFAULT 'nuevo',
    origen TEXT NOT NULL DEFAULT 'landing',
    nota TEXT,
    gestion_por TEXT,
    gestion_en TIMESTAMPTZ,
    idempotency_key TEXT NOT NULL,
    cuerpo_hash TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (empresa_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_leads_bandeja ON leads (empresa_id, estado, creado_en);
