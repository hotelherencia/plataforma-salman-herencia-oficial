-- #358 / V1-ISSUE-57 (2026-11-19): stock en el core compartido entre hotel
-- (minibar) y cafetería, con bodegas/ubicaciones y umbral mínimo de reposición.

ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0);

CREATE TABLE IF NOT EXISTS core_bodegas (
    id TEXT PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    nombre TEXT NOT NULL,
    modulo TEXT NOT NULL CHECK (modulo IN ('core', 'hotel', 'cafeteria')),
    activa BOOLEAN NOT NULL DEFAULT true,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO core_bodegas (id, codigo, nombre, modulo, activa) VALUES
    ('BOD-CORE', 'bodega_principal', 'Bodega principal', 'core', true),
    ('BOD-MINIBAR', 'minibar', 'Minibar habitaciones', 'hotel', true),
    ('BOD-CAFE', 'cafeteria', 'Cafetería', 'cafeteria', true)
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS core_stock_bodega (
    producto_id TEXT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    bodega_codigo TEXT NOT NULL REFERENCES core_bodegas(codigo),
    cantidad INTEGER NOT NULL DEFAULT 0 CHECK (cantidad >= 0),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (producto_id, bodega_codigo)
);

CREATE INDEX IF NOT EXISTS idx_core_stock_bodega_codigo
    ON core_stock_bodega (bodega_codigo);

-- Backfill: ubica el stock existente según la categoría del producto.
INSERT INTO core_stock_bodega (producto_id, bodega_codigo, cantidad)
SELECT
    p.id,
    CASE
        WHEN p.categoria = 'minibar' THEN 'minibar'
        WHEN p.categoria = 'cafeteria' THEN 'cafeteria'
        ELSE 'bodega_principal'
    END,
    p.stock
FROM productos p
WHERE p.controla_stock
ON CONFLICT (producto_id, bodega_codigo) DO NOTHING;

ALTER TABLE movimientos_stock
    ADD COLUMN IF NOT EXISTS bodega_codigo TEXT NOT NULL DEFAULT 'bodega_principal';

ALTER TABLE movimientos_stock
    ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'ajuste';

ALTER TABLE movimientos_stock
    DROP CONSTRAINT IF EXISTS movimientos_stock_tipo_check;

ALTER TABLE movimientos_stock
    ADD CONSTRAINT movimientos_stock_tipo_check
    CHECK (tipo IN ('entrada', 'salida', 'ajuste', 'transferencia', 'reverso'));

CREATE INDEX IF NOT EXISTS idx_movimientos_stock_bodega
    ON movimientos_stock (bodega_codigo, creado_en DESC);
