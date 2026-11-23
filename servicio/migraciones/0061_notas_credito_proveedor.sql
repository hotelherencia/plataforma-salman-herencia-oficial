-- 0061: notas de crédito de proveedor (#402). Aditiva e idempotente.
-- La nota de crédito (documento 61) referida a una factura ya cargada:
--   1. devuelve unidades al proveedor (baja de stock, tipo «devolucion»);
--   2. rebaja la cuenta por pagar al proveedor (PUR-004).
-- La cuenta por pagar es un libro append-only: nunca se edita ni se borra una fila;
-- una corrección es un asiento nuevo. Un documento mueve la cuenta una sola vez.

ALTER TABLE movimientos_stock DROP CONSTRAINT IF EXISTS movimientos_stock_tipo_check;
ALTER TABLE movimientos_stock
    ADD CONSTRAINT movimientos_stock_tipo_check
    CHECK (tipo IN ('entrada', 'salida', 'ajuste', 'transferencia', 'reverso', 'devolucion'));

ALTER TABLE documentos_proveedor DROP CONSTRAINT IF EXISTS documentos_proveedor_estado_check;
ALTER TABLE documentos_proveedor
    ADD CONSTRAINT documentos_proveedor_estado_check
    CHECK (estado IN ('pendiente', 'borrador', 'cargada', 'facturado', 'archivada', 'descartada', 'aplicada'));
ALTER TABLE documentos_proveedor ADD COLUMN IF NOT EXISTS factura_origen_id TEXT REFERENCES documentos_proveedor(id);
ALTER TABLE documentos_proveedor ADD COLUMN IF NOT EXISTS aplicacion JSONB;

CREATE TABLE IF NOT EXISTS cuenta_proveedor_movimientos (
    id BIGSERIAL PRIMARY KEY,
    emisor_rut TEXT NOT NULL,
    documento_id TEXT NOT NULL REFERENCES documentos_proveedor(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('factura', 'nota_credito')),
    monto_clp BIGINT NOT NULL,
    referencia_documento_id TEXT REFERENCES documentos_proveedor(id),
    actor TEXT NOT NULL,
    registrado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (documento_id, tipo),
    CHECK ((tipo = 'factura' AND monto_clp >= 0) OR (tipo = 'nota_credito' AND monto_clp <= 0))
);
CREATE INDEX IF NOT EXISTS idx_cuenta_proveedor ON cuenta_proveedor_movimientos (emisor_rut, registrado_en);

CREATE OR REPLACE FUNCTION cuenta_proveedor_solo_agregar() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'cuenta_proveedor_movimientos es append-only';
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS cuenta_proveedor_inmutable ON cuenta_proveedor_movimientos;
CREATE TRIGGER cuenta_proveedor_inmutable BEFORE UPDATE OR DELETE ON cuenta_proveedor_movimientos
    FOR EACH ROW EXECUTE FUNCTION cuenta_proveedor_solo_agregar();

-- Las facturas que ya están cargadas al inventario entran a la cuenta con su total.
INSERT INTO cuenta_proveedor_movimientos (emisor_rut, documento_id, tipo, monto_clp, actor)
SELECT emisor_rut, id, 'factura', monto_total_clp, actor
FROM documentos_proveedor
WHERE clase = 'factura' AND estado = 'cargada' AND emisor_rut IS NOT NULL AND monto_total_clp IS NOT NULL
  AND monto_total_clp >= 0
ON CONFLICT (documento_id, tipo) DO NOTHING;
