-- Carga amigable de productos (2026-11-19, pedido del propietario): factura
-- electrónica del SII (XML), planilla pegada o lector de códigos.
--
-- - `codigo`: código del proveedor o de barras (EAN). Único cuando existe:
--   el lector y la factura encuentran el producto por este código.
-- - `costo_clp`: último costo unitario neto conocido (informativo; el
--   precio de venta con IVA lo sigue fijando la administración).
-- - Cada carga queda registrada. Una factura (emisor + tipo + folio) se
--   importa una sola vez: el índice único impide sumar dos veces el stock.
ALTER TABLE productos ADD COLUMN codigo TEXT;
ALTER TABLE productos ADD COLUMN costo_clp INTEGER CHECK (costo_clp IS NULL OR costo_clp >= 0);
CREATE UNIQUE INDEX idx_productos_codigo ON productos (lower(codigo)) WHERE codigo IS NOT NULL;

CREATE TABLE importaciones_productos (
    id TEXT PRIMARY KEY,
    origen TEXT NOT NULL CHECK (origen IN ('factura_xml', 'planilla', 'lector', 'foto')),
    emisor_rut TEXT,
    emisor_razon_social TEXT,
    tipo_dte INTEGER,
    folio TEXT,
    fecha_emision DATE,
    lineas INTEGER NOT NULL CHECK (lineas >= 0),
    unidades INTEGER NOT NULL DEFAULT 0,
    productos_nuevos INTEGER NOT NULL DEFAULT 0,
    total_neto_clp INTEGER,
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX idx_importaciones_documento
    ON importaciones_productos (emisor_rut, tipo_dte, folio)
    WHERE emisor_rut IS NOT NULL AND tipo_dte IS NOT NULL AND folio IS NOT NULL;
CREATE INDEX idx_importaciones_creado ON importaciones_productos (creado_en DESC);

ALTER TABLE movimientos_stock ADD COLUMN importacion_id TEXT REFERENCES importaciones_productos(id);
