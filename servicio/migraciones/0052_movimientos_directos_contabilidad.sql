-- Contabilidad (2026-11-19): movimientos directos sin habitación ni reserva.
-- Permite asentar cargos, ventas de mostrador (productos con descuento de stock o
-- concepto libre) y egresos operacionales independientemente de que exista un
-- turno de caja abierto, sumando siempre a la contabilidad, caja del día y cierre diario.

CREATE TABLE movimientos_directos (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    fecha_contable DATE NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('cargo_directo', 'egreso_operacional', 'reverso_directo')),
    categoria TEXT NOT NULL DEFAULT 'otro_ingreso'
        CHECK (categoria IN ('cafeteria', 'minibar', 'estacionamiento', 'servicio', 'otro_ingreso', 'gasto_operacional')),
    concepto TEXT NOT NULL CHECK (length(btrim(concepto)) BETWEEN 1 AND 200),
    producto_id TEXT REFERENCES productos(id),
    cantidad INTEGER CHECK (cantidad IS NULL OR cantidad > 0),
    precio_unitario_clp INTEGER CHECK (precio_unitario_clp IS NULL OR precio_unitario_clp > 0),
    monto_clp INTEGER NOT NULL CHECK (monto_clp > 0),
    iva_pct NUMERIC(5,2) NOT NULL DEFAULT 19.00,
    neto_clp INTEGER NOT NULL CHECK (neto_clp >= 0),
    iva_clp INTEGER NOT NULL CHECK (iva_clp >= 0),
    estado_cobro TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado_cobro IN ('cobrado', 'pendiente', 'no_aplica')),
    medio TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (medio IN ('efectivo', 'debito', 'credito', 'transferencia', 'no_informado', 'pendiente')),
    turno_id TEXT REFERENCES caja_turnos(id) ON DELETE CASCADE,
    cobrado_en TIMESTAMPTZ,
    cobrado_por TEXT,
    documento_tipo TEXT NOT NULL DEFAULT 'pendiente'
        CHECK (documento_tipo IN ('boleta', 'factura', 'sin_documento', 'pendiente')),
    documento_folio TEXT,
    receptor JSONB,
    cliente_id TEXT REFERENCES clientes(id),
    tarjeta_marca TEXT,
    tarjeta_ultimos4 TEXT CHECK (tarjeta_ultimos4 IS NULL OR tarjeta_ultimos4 ~ '^[0-9]{4}$'),
    codigo_autorizacion TEXT,
    comprobante TEXT,
    referencia_id TEXT REFERENCES movimientos_directos(id),
    motivo TEXT,
    nota TEXT,
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_mov_directos_empresa_fecha ON movimientos_directos (empresa_id, fecha_contable);
CREATE INDEX idx_mov_directos_estado ON movimientos_directos (empresa_id, estado_cobro);
CREATE UNIQUE INDEX idx_mov_directos_un_reverso ON movimientos_directos (referencia_id) WHERE tipo = 'reverso_directo';

CREATE FUNCTION movimientos_directos_inmutables() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'los movimientos directos no se borran: registra un reverso' USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.empresa_id IS DISTINCT FROM OLD.empresa_id
       OR NEW.fecha_contable IS DISTINCT FROM OLD.fecha_contable
       OR NEW.tipo IS DISTINCT FROM OLD.tipo
       OR NEW.categoria IS DISTINCT FROM OLD.categoria
       OR NEW.concepto IS DISTINCT FROM OLD.concepto
       OR NEW.producto_id IS DISTINCT FROM OLD.producto_id
       OR NEW.cantidad IS DISTINCT FROM OLD.cantidad
       OR NEW.precio_unitario_clp IS DISTINCT FROM OLD.precio_unitario_clp
       OR NEW.monto_clp IS DISTINCT FROM OLD.monto_clp
       OR NEW.neto_clp IS DISTINCT FROM OLD.neto_clp
       OR NEW.iva_clp IS DISTINCT FROM OLD.iva_clp
       OR NEW.referencia_id IS DISTINCT FROM OLD.referencia_id THEN
        RAISE EXCEPTION 'los movimientos directos no se modifican: registra un reverso' USING ERRCODE = 'check_violation';
    END IF;
    -- Permite pasar una sola vez de pendiente -> cobrado al registrar el cobro posterior.
    IF OLD.estado_cobro = 'pendiente' AND NEW.estado_cobro = 'cobrado' THEN
        RETURN NEW;
    END IF;
    IF NEW.estado_cobro IS DISTINCT FROM OLD.estado_cobro
       OR NEW.medio IS DISTINCT FROM OLD.medio
       OR NEW.turno_id IS DISTINCT FROM OLD.turno_id THEN
        RAISE EXCEPTION 'un movimiento directo ya cobrado no se modifica: registra un reverso'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER movimientos_directos_inmutables BEFORE UPDATE OR DELETE ON movimientos_directos
    FOR EACH ROW EXECUTE FUNCTION movimientos_directos_inmutables();

-- Vincular caja_movimientos con movimientos directos y soportar cobro/reverso/egreso directo.
ALTER TABLE caja_movimientos
    ADD COLUMN movimiento_directo_id TEXT REFERENCES movimientos_directos(id) ON DELETE CASCADE;

CREATE INDEX caja_movimientos_directo ON caja_movimientos (movimiento_directo_id) WHERE movimiento_directo_id IS NOT NULL;

DO $$
DECLARE
    c_name TEXT;
BEGIN
    SELECT conname INTO c_name
    FROM pg_constraint
    WHERE conrelid = 'caja_movimientos'::regclass
      AND contype = 'c'
      AND pg_get_constraintdef(oid) LIKE '%retiro_deposito%';
    IF c_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE caja_movimientos DROP CONSTRAINT %I', c_name);
    END IF;
END $$;

ALTER TABLE caja_movimientos
    ADD CONSTRAINT caja_movimientos_tipo_check
    CHECK (tipo IN ('cobro', 'reverso_cobro', 'retiro_deposito', 'cobro_directo', 'reverso_directo', 'egreso_caja'));
