-- Contable 2.6 (#396 / FIN-003, FIN-004, FIN-006) y 2.7 (#397 / TAX-002, TAX-003):
-- Comisiones configurables por medio/proveedor, cartolas bancarias, conciliación muchos-a-muchos
-- append-only (sin auto-conciliar solo por monto en manual) y soporte tributario F29 (sin envío SII).
-- Migración aditiva e idempotente.

CREATE TABLE IF NOT EXISTS comisiones_medios (
    empresa_id TEXT NOT NULL,
    medio TEXT NOT NULL CHECK (medio IN ('efectivo', 'debito', 'credito', 'transferencia')),
    proveedor TEXT NOT NULL DEFAULT 'general',
    porcentaje_comision NUMERIC(6,3) NOT NULL DEFAULT 0 CHECK (porcentaje_comision >= 0 AND porcentaje_comision <= 30),
    iva_comision BOOLEAN NOT NULL DEFAULT true,
    dias_habiles_abono INTEGER NOT NULL DEFAULT 0 CHECK (dias_habiles_abono BETWEEN 0 AND 30),
    cuenta_deposito TEXT,
    mapeo_columnas JSONB NOT NULL DEFAULT '{}'::jsonb,
    actualizado_por TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (empresa_id, medio)
);

CREATE TABLE IF NOT EXISTS cartolas_bancarias (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    banco TEXT NOT NULL,
    cuenta TEXT NOT NULL,
    periodo TEXT NOT NULL,
    moneda TEXT NOT NULL DEFAULT 'CLP',
    sha256 TEXT NOT NULL,
    filas_totales INTEGER NOT NULL DEFAULT 0,
    filas_importadas INTEGER NOT NULL DEFAULT 0,
    filas_rechazadas INTEGER NOT NULL DEFAULT 0,
    errores JSONB NOT NULL DEFAULT '[]'::jsonb,
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (empresa_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_cartolas_empresa_periodo
    ON cartolas_bancarias (empresa_id, periodo DESC, creado_en DESC);

CREATE TABLE IF NOT EXISTS cartola_movimientos (
    id TEXT PRIMARY KEY,
    cartola_id TEXT NOT NULL REFERENCES cartolas_bancarias(id),
    empresa_id TEXT NOT NULL,
    fecha_movimiento DATE NOT NULL,
    descripcion TEXT NOT NULL,
    referencia TEXT,
    monto_clp BIGINT NOT NULL CHECK (monto_clp <> 0),
    tipo TEXT NOT NULL CHECK (tipo IN ('abono', 'cargo')),
    estado TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'parcial', 'conciliado')),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cartola_movs_empresa_estado
    ON cartola_movimientos (empresa_id, estado, fecha_movimiento DESC);

CREATE TABLE IF NOT EXISTS conciliaciones_bancarias (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    cartola_movimiento_id TEXT NOT NULL REFERENCES cartola_movimientos(id),
    caja_movimiento_id TEXT REFERENCES caja_movimientos(id),
    pago_id TEXT REFERENCES pagos(id),
    monto_asignado_clp BIGINT NOT NULL CHECK (monto_asignado_clp > 0),
    comision_clp BIGINT NOT NULL DEFAULT 0 CHECK (comision_clp >= 0),
    modo TEXT NOT NULL CHECK (modo IN ('automatico', 'manual')),
    justificacion TEXT,
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (caja_movimiento_id IS NOT NULL OR pago_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_conciliaciones_cartola_mov
    ON conciliaciones_bancarias (cartola_movimiento_id);

CREATE INDEX IF NOT EXISTS idx_conciliaciones_pago
    ON conciliaciones_bancarias (pago_id) WHERE pago_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_conciliaciones_caja_mov
    ON conciliaciones_bancarias (caja_movimiento_id) WHERE caja_movimiento_id IS NOT NULL;

CREATE OR REPLACE FUNCTION impedir_mutacion_conciliaciones_bancarias() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'conciliaciones_bancarias es append-only: no se permite UPDATE ni DELETE';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_conciliaciones_bancarias_inmutables ON conciliaciones_bancarias;
CREATE TRIGGER trg_conciliaciones_bancarias_inmutables
    BEFORE UPDATE OR DELETE ON conciliaciones_bancarias
    FOR EACH ROW EXECUTE FUNCTION impedir_mutacion_conciliaciones_bancarias();
