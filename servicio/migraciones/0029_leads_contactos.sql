-- #354 (2026-11-18): leads deduplicados por contacto. Un mismo cliente que
-- escribe varias veces queda bajo una sola ficha (clave: correo en
-- minúsculas; si coincide el teléfono normalizado, se enlaza al mismo).
CREATE TABLE contactos (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    correo TEXT,
    telefono_normalizado TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_contactos_correo ON contactos (empresa_id, correo) WHERE correo IS NOT NULL;
CREATE INDEX idx_contactos_telefono ON contactos (empresa_id, telefono_normalizado);

ALTER TABLE leads ADD COLUMN contacto_id TEXT REFERENCES contactos(id);
CREATE INDEX idx_leads_contacto ON leads (contacto_id);

-- Leads existentes: una ficha por correo (el más reciente da el nombre).
INSERT INTO contactos (id, empresa_id, nombre, correo, creado_en)
SELECT 'CTO-' || substr(md5(empresa_id || ':' || lower(correo)), 1, 12), empresa_id,
       (array_agg(nombre ORDER BY creado_en DESC))[1], lower(correo), min(creado_en)
FROM leads WHERE correo IS NOT NULL
GROUP BY empresa_id, lower(correo);
UPDATE leads SET contacto_id = 'CTO-' || substr(md5(empresa_id || ':' || lower(correo)), 1, 12)
WHERE correo IS NOT NULL;
