-- #402 / PUR-004: Notas de crédito de proveedor vinculadas a facturas (0040),
-- con rebaja de stock (0055) y cuenta por pagar append-only e idempotente.
-- Migración aditiva e idempotente.

ALTER TABLE documentos_proveedor
    ADD COLUMN IF NOT EXISTS factura_referencia_id TEXT REFERENCES documentos_proveedor(id);

ALTER TABLE documentos_proveedor
    ADD COLUMN IF NOT EXISTS aplicada_en TIMESTAMPTZ;

ALTER TABLE documentos_proveedor
    ADD COLUMN IF NOT EXISTS aplicada_por TEXT;

ALTER TABLE documentos_proveedor
    DROP CONSTRAINT IF EXISTS documentos_proveedor_estado_check;

ALTER TABLE documentos_proveedor
    ADD CONSTRAINT documentos_proveedor_estado_check
    CHECK (estado IN ('pendiente', 'borrador', 'cargada', 'facturado', 'aplicada', 'archivada', 'descartada'));

CREATE INDEX IF NOT EXISTS idx_documentos_proveedor_factura_ref
    ON documentos_proveedor (factura_referencia_id)
    WHERE factura_referencia_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS cuentas_por_pagar (
    id TEXT PRIMARY KEY,
    documento_id TEXT NOT NULL UNIQUE REFERENCES documentos_proveedor(id),
    emisor_rut TEXT NOT NULL,
    emisor_razon_social TEXT,
    tipo_dte INTEGER,
    folio TEXT NOT NULL,
    fecha_emision DATE,
    fecha_vencimiento DATE,
    monto_original_clp BIGINT NOT NULL CHECK (monto_original_clp >= 0),
    estado TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta', 'parcial', 'pagada', 'anulada')),
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cuentas_por_pagar_emisor
    ON cuentas_por_pagar (emisor_rut, estado, creado_en DESC);

CREATE TABLE IF NOT EXISTS cxp_movimientos (
    id TEXT PRIMARY KEY,
    cxp_id TEXT NOT NULL REFERENCES cuentas_por_pagar(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('cargo_factura', 'nota_credito', 'pago_proveedor', 'reverso')),
    monto_clp BIGINT NOT NULL,
    documento_id TEXT REFERENCES documentos_proveedor(id),
    medio TEXT,
    comprobante TEXT,
    motivo TEXT,
    clave_idempotencia TEXT UNIQUE,
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cxp_movimientos_cxp
    ON cxp_movimientos (cxp_id, creado_en ASC);

CREATE OR REPLACE FUNCTION impedir_mutacion_cxp_movimientos() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'cxp_movimientos es append-only: no se permite UPDATE ni DELETE';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cxp_movimientos_inmutables ON cxp_movimientos;
CREATE TRIGGER trg_cxp_movimientos_inmutables
    BEFORE UPDATE OR DELETE ON cxp_movimientos
    FOR EACH ROW EXECUTE FUNCTION impedir_mutacion_cxp_movimientos();
