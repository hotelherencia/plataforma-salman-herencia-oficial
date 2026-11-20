-- PR A (2026-11-20): Ocupación real (adultos/niños) y registro de todos los huéspedes en la Llegada.
-- Migración aditiva e idempotente.

CREATE TABLE IF NOT EXISTS huespedes (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    documento_tipo TEXT CHECK (documento_tipo IN ('rut', 'pasaporte')),
    documento TEXT,
    nacionalidad TEXT,
    fecha_nacimiento DATE,
    telefono TEXT,
    correo TEXT,
    notas TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_huespedes_empresa_documento
    ON huespedes (empresa_id, documento_tipo, documento)
    WHERE documento IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_huespedes_empresa_documento
    ON huespedes (empresa_id, documento)
    WHERE documento IS NOT NULL;

CREATE TABLE IF NOT EXISTS reserva_huespedes (
    id TEXT PRIMARY KEY,
    reserva_id TEXT NOT NULL REFERENCES reservas(id) ON DELETE CASCADE,
    huesped_id TEXT NOT NULL REFERENCES huespedes(id) ON DELETE CASCADE,
    rol TEXT NOT NULL CHECK (rol IN ('titular', 'acompanante')),
    es_nino BOOLEAN NOT NULL DEFAULT false,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (reserva_id, huesped_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_reserva_huespedes_titular
    ON reserva_huespedes (reserva_id)
    WHERE rol = 'titular';

CREATE INDEX IF NOT EXISTS idx_reserva_huespedes_reserva
    ON reserva_huespedes (reserva_id);

ALTER TABLE reservas
    ADD COLUMN IF NOT EXISTS adultos INTEGER CHECK (adultos IS NULL OR adultos >= 1);

ALTER TABLE reservas
    ADD COLUMN IF NOT EXISTS ninos INTEGER DEFAULT 0 CHECK (ninos IS NULL OR ninos >= 0);

UPDATE reservas
SET adultos = COALESCE(adultos, personas, 1),
    ninos = COALESCE(ninos, 0)
WHERE adultos IS NULL OR ninos IS NULL;

-- Backfill idempotente de huéspedes titulares con documento tipificado.
INSERT INTO huespedes (id, empresa_id, nombre, documento_tipo, documento)
SELECT DISTINCT ON (r.empresa_id, r.huesped_documento_tipo, r.huesped_documento)
    'HSP-' || substr(md5(r.empresa_id || ':' || r.huesped_documento_tipo || ':' || r.huesped_documento), 1, 12),
    r.empresa_id,
    r.huesped_nombre,
    r.huesped_documento_tipo,
    r.huesped_documento
FROM reservas r
WHERE r.huesped_documento IS NOT NULL
  AND r.huesped_documento_tipo IS NOT NULL
ORDER BY r.empresa_id, r.huesped_documento_tipo, r.huesped_documento, r.creado_en ASC
ON CONFLICT (empresa_id, documento_tipo, documento) WHERE documento IS NOT NULL DO NOTHING;

INSERT INTO reserva_huespedes (id, reserva_id, huesped_id, rol, es_nino)
SELECT
    'RHP-' || substr(md5(r.id || ':titular'), 1, 12),
    r.id,
    h.id,
    'titular',
    false
FROM reservas r
JOIN huespedes h
  ON h.empresa_id = r.empresa_id
 AND h.documento_tipo = r.huesped_documento_tipo
 AND h.documento = r.huesped_documento
WHERE r.huesped_documento IS NOT NULL
  AND r.huesped_documento_tipo IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM reserva_huespedes rh WHERE rh.reserva_id = r.id AND rh.rol = 'titular'
  )
ON CONFLICT (reserva_id, huesped_id) DO NOTHING;

-- Backfill idempotente de titulares sin documento o sin tipo de documento.
INSERT INTO huespedes (id, empresa_id, nombre, documento_tipo, documento)
SELECT
    'HSP-' || substr(md5(r.id), 1, 12),
    r.empresa_id,
    r.huesped_nombre,
    r.huesped_documento_tipo,
    r.huesped_documento
FROM reservas r
WHERE (r.huesped_documento IS NULL OR r.huesped_documento_tipo IS NULL)
  AND NOT EXISTS (
      SELECT 1 FROM reserva_huespedes rh WHERE rh.reserva_id = r.id AND rh.rol = 'titular'
  )
ON CONFLICT (id) DO NOTHING;

INSERT INTO reserva_huespedes (id, reserva_id, huesped_id, rol, es_nino)
SELECT
    'RHP-' || substr(md5(r.id || ':titular'), 1, 12),
    r.id,
    'HSP-' || substr(md5(r.id), 1, 12),
    'titular',
    false
FROM reservas r
WHERE (r.huesped_documento IS NULL OR r.huesped_documento_tipo IS NULL)
  AND NOT EXISTS (
      SELECT 1 FROM reserva_huespedes rh WHERE rh.reserva_id = r.id AND rh.rol = 'titular'
  )
ON CONFLICT (reserva_id, huesped_id) DO NOTHING;
