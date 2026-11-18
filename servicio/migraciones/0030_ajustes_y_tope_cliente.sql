-- #348 (2026-11-18, decisión del propietario: tope por cliente).
-- Ajustes operativos editables desde Configuración (no en código), por
-- empresa y clave. El primero: tope de solicitudes por cliente y período.
CREATE TABLE ajustes (
    empresa_id TEXT NOT NULL,
    clave TEXT NOT NULL,
    valor JSONB NOT NULL,
    actualizado_por TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (empresa_id, clave)
);

-- Contacto normalizado de la solicitud (correo en minúsculas o teléfono
-- solo dígitos con +56 para móviles chilenos) para contar por cliente.
ALTER TABLE solicitudes ADD COLUMN contacto_normalizado TEXT;
UPDATE solicitudes SET contacto_normalizado = CASE
    WHEN huesped_contacto LIKE '%@%' THEN lower(btrim(huesped_contacto))
    WHEN length(regexp_replace(huesped_contacto, '\D', '', 'g')) = 9
         AND left(regexp_replace(huesped_contacto, '\D', '', 'g'), 1) = '9'
        THEN '+56' || regexp_replace(huesped_contacto, '\D', '', 'g')
    WHEN regexp_replace(huesped_contacto, '\D', '', 'g') <> ''
        THEN '+' || regexp_replace(huesped_contacto, '\D', '', 'g')
    ELSE lower(btrim(huesped_contacto))
END;
CREATE INDEX idx_solicitudes_contacto ON solicitudes (empresa_id, contacto_normalizado, creado_en);
