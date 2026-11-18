-- #357 (2026-11-18): catálogo de productos para los cargos, con precio (IVA
-- incluido) y stock opcional (minibar). El cargo copia el precio al
-- asentarse: el histórico no cambia si el producto cambia de precio.
CREATE TABLE productos (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL CHECK (categoria IN ('minibar', 'cafeteria', 'servicio', 'extra')),
    precio_clp INTEGER NOT NULL CHECK (precio_clp > 0),
    activo BOOLEAN NOT NULL DEFAULT true,
    controla_stock BOOLEAN NOT NULL DEFAULT false,
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_productos_nombre ON productos (lower(nombre));

-- Cada cambio de stock queda registrado (ajuste manual, cargo o reverso).
CREATE TABLE movimientos_stock (
    id TEXT PRIMARY KEY,
    producto_id TEXT NOT NULL REFERENCES productos(id),
    delta INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    actor TEXT NOT NULL,
    cargo_id TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idx_movimientos_stock_producto ON movimientos_stock (producto_id, creado_en);

ALTER TABLE cargos ADD COLUMN producto_id TEXT REFERENCES productos(id);
ALTER TABLE cargos ADD COLUMN cantidad INTEGER CHECK (cantidad > 0);
ALTER TABLE cargos ADD COLUMN precio_unitario_clp INTEGER;
