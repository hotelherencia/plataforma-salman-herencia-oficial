-- 0073: rol «dueño» (lectura global + observaciones a la administración) y sus observaciones.
-- Aditiva e idempotente. El dueño lee todo lo que lee la administración del hotel, pero no cambia
-- datos: solo deja observaciones y las cierra (control contra el fraude de suplantación del dueño).
INSERT INTO roles_catalogo (codigo, modulo, etiqueta, descripcion, exige_doble_factor, activo, orden) VALUES
    ('dueno', 'core', 'Dueño (lectura global)', 'Ve ventas, caja, ocupación y cuentas de todo el grupo y deja observaciones a la administración; no cambia datos', true, true, 5)
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS observaciones_direccion (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    autor TEXT NOT NULL,
    texto TEXT NOT NULL CHECK (length(texto) BETWEEN 3 AND 1000),
    referencia TEXT CHECK (referencia IS NULL OR length(referencia) <= 120),   -- pantalla o dato al que se refiere
    estado TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta', 'respondida', 'cerrada')),
    respuesta TEXT CHECK (respuesta IS NULL OR length(respuesta) BETWEEN 1 AND 1000),
    respondida_por TEXT,
    respondida_en TIMESTAMPTZ,
    cerrada_en TIMESTAMPTZ,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS idx_observaciones_estado ON observaciones_direccion (empresa_id, estado, creado_en);
