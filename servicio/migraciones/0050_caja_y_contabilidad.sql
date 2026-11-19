-- Caja y contabilidad del hotel, fase 1 (2026-11-19, pedido del propietario).
-- Número 0050 a propósito: deja libres 0041..0049 para otros frentes; el
-- orden es alfabético y la versión es el nombre completo del archivo.
--
-- 1. Turnos de caja (apertura con fondo inicial, arqueo por denominación,
--    cierre con cuadratura y diferencia justificada, entrega al turno siguiente).
-- 2. Movimientos de caja inmutables: cobros por medio, reversos y retiros de
--    efectivo para depósito en el banco (con número de comprobante).
-- 3. Pagos con medio (efectivo, débito, crédito, transferencia), documento
--    tributario (boleta/factura + receptor), anticipo, datos del voucher sin
--    número completo de tarjeta ni CVV (PCI: solo marca, últimos 4 y código
--    de autorización) y fecha contable en hora de Chile; reverso por
--    administración en vez de editar o borrar.
-- 4. Cierre diario (auditoría nocturna) con su conciliación congelada; un día
--    cerrado no recibe movimientos: lo nuevo cae en el siguiente día abierto.

-- 1. Turnos ---------------------------------------------------------------
CREATE TABLE caja_turnos (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    caja TEXT NOT NULL DEFAULT 'principal',
    usuario_id TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    usuario_nombre TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'abierto' CHECK (estado IN ('abierto', 'cerrado')),
    fecha_contable DATE NOT NULL,
    abierto_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    fondo_inicial_clp INTEGER NOT NULL CHECK (fondo_inicial_clp >= 0),
    recibido_de_turno_id TEXT REFERENCES caja_turnos(id) ON DELETE CASCADE,
    diferencia_recepcion_clp INTEGER,
    nota_apertura TEXT,
    cerrado_en TIMESTAMPTZ,
    cerrado_por TEXT,
    efectivo_esperado_clp INTEGER,
    efectivo_contado_clp INTEGER,
    diferencia_clp INTEGER,
    justificacion TEXT,
    arqueo JSONB,
    cuadratura JSONB,
    entrega_siguiente_clp INTEGER CHECK (entrega_siguiente_clp IS NULL OR entrega_siguiente_clp >= 0)
);
-- Una sola caja abierta a la vez por caja física.
CREATE UNIQUE INDEX caja_turnos_uno_abierto ON caja_turnos (empresa_id, caja) WHERE estado = 'abierto';
-- Un turno cerrado entrega su efectivo a un solo turno siguiente.
CREATE UNIQUE INDEX caja_turnos_recepcion_unica ON caja_turnos (recibido_de_turno_id) WHERE recibido_de_turno_id IS NOT NULL;
CREATE INDEX caja_turnos_fecha ON caja_turnos (empresa_id, fecha_contable);

-- Un turno cerrado no cambia más.
CREATE FUNCTION caja_turno_cerrado_inmutable() RETURNS trigger AS $$
BEGIN
    IF OLD.estado = 'cerrado' THEN
        RAISE EXCEPTION 'turno de caja cerrado: no admite cambios' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER caja_turnos_inmutable BEFORE UPDATE ON caja_turnos
    FOR EACH ROW EXECUTE FUNCTION caja_turno_cerrado_inmutable();

-- 2. Pagos: medio, documento, anticipo, fecha contable y reverso ---------
ALTER TABLE pagos ADD COLUMN tipo TEXT NOT NULL DEFAULT 'pago' CHECK (tipo IN ('pago', 'reverso'));
ALTER TABLE pagos ADD COLUMN referencia_pago_id TEXT REFERENCES pagos(id);
ALTER TABLE pagos ADD COLUMN medio TEXT NOT NULL DEFAULT 'no_informado'
    CHECK (medio IN ('efectivo', 'debito', 'credito', 'transferencia', 'no_informado'));
ALTER TABLE pagos ADD COLUMN fecha_contable DATE;
UPDATE pagos SET fecha_contable = (creado_en AT TIME ZONE 'America/Santiago')::date;
ALTER TABLE pagos ALTER COLUMN fecha_contable SET DEFAULT ((now() AT TIME ZONE 'America/Santiago')::date);
ALTER TABLE pagos ALTER COLUMN fecha_contable SET NOT NULL;
ALTER TABLE pagos ADD COLUMN turno_id TEXT REFERENCES caja_turnos(id) ON DELETE CASCADE;
ALTER TABLE pagos ADD COLUMN es_anticipo BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE pagos ADD COLUMN documento_tipo TEXT NOT NULL DEFAULT 'pendiente'
    CHECK (documento_tipo IN ('boleta', 'factura', 'sin_documento', 'pendiente'));
ALTER TABLE pagos ADD COLUMN documento_folio TEXT;
ALTER TABLE pagos ADD COLUMN receptor JSONB;
ALTER TABLE pagos ADD COLUMN tarjeta_marca TEXT;
ALTER TABLE pagos ADD COLUMN tarjeta_ultimos4 TEXT CHECK (tarjeta_ultimos4 IS NULL OR tarjeta_ultimos4 ~ '^[0-9]{4}$');
ALTER TABLE pagos ADD COLUMN codigo_autorizacion TEXT;
ALTER TABLE pagos ADD COLUMN comprobante TEXT;
ALTER TABLE pagos ADD COLUMN actor TEXT;
ALTER TABLE pagos ADD COLUMN motivo TEXT;
CREATE UNIQUE INDEX pagos_un_reverso ON pagos (referencia_pago_id) WHERE tipo = 'reverso';
CREATE INDEX pagos_fecha_contable ON pagos (fecha_contable);

-- Inmutabilidad: el dinero ya registrado no se edita ni se borra; se corrige
-- con un reverso. (Se permite corregir metadatos sin monto, p. ej. el folio
-- del documento emitido después, y las marcas de tiempo de pruebas.)
CREATE FUNCTION pagos_inmutables() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'los pagos no se borran: registra un reverso' USING ERRCODE = 'check_violation';
    END IF;
    IF NEW.monto_clp IS DISTINCT FROM OLD.monto_clp OR NEW.reserva_id IS DISTINCT FROM OLD.reserva_id
       OR NEW.tipo IS DISTINCT FROM OLD.tipo OR NEW.estado IS DISTINCT FROM OLD.estado
       OR NEW.referencia_pago_id IS DISTINCT FROM OLD.referencia_pago_id THEN
        RAISE EXCEPTION 'los pagos no se modifican: registra un reverso' USING ERRCODE = 'check_violation';
    END IF;
    -- La fila la proyecta el dominio (hotel_sql.persistir) sin datos contables; la
    -- misma transacción que la creó la completa una sola vez (medio, fecha, turno).
    IF OLD.actor IS NULL AND OLD.medio = 'no_informado'
       AND OLD.xmin::text::numeric = pg_current_xact_id()::text::numeric % 4294967296 THEN
        RETURN NEW;
    END IF;
    IF NEW.medio IS DISTINCT FROM OLD.medio
       OR NEW.fecha_contable IS DISTINCT FROM OLD.fecha_contable OR NEW.turno_id IS DISTINCT FROM OLD.turno_id
       OR NEW.es_anticipo IS DISTINCT FROM OLD.es_anticipo THEN
        RAISE EXCEPTION 'los pagos no se modifican: registra un reverso' USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER pagos_inmutables BEFORE UPDATE OR DELETE ON pagos
    FOR EACH ROW EXECUTE FUNCTION pagos_inmutables();

-- 3. Movimientos de caja ---------------------------------------------------
CREATE TABLE caja_movimientos (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    turno_id TEXT REFERENCES caja_turnos(id) ON DELETE CASCADE,
    fecha_contable DATE NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('cobro', 'reverso_cobro', 'retiro_deposito')),
    medio TEXT NOT NULL CHECK (medio IN ('efectivo', 'debito', 'credito', 'transferencia', 'no_informado')),
    monto_clp INTEGER NOT NULL CHECK (monto_clp <> 0),
    pago_id TEXT REFERENCES pagos(id) ON DELETE CASCADE,
    comprobante TEXT,
    banco TEXT,
    nota TEXT,
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX caja_movimientos_fecha ON caja_movimientos (empresa_id, fecha_contable);
CREATE INDEX caja_movimientos_turno ON caja_movimientos (turno_id);

CREATE FUNCTION caja_movimientos_inmutables() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'los movimientos de caja no se modifican ni se borran' USING ERRCODE = 'check_violation';
END $$ LANGUAGE plpgsql;
CREATE TRIGGER caja_movimientos_inmutables BEFORE UPDATE OR DELETE ON caja_movimientos
    FOR EACH ROW EXECUTE FUNCTION caja_movimientos_inmutables();

-- 4. Cierre diario ----------------------------------------------------------
CREATE TABLE cierres_diarios (
    empresa_id TEXT NOT NULL,
    fecha DATE NOT NULL,
    estado TEXT NOT NULL DEFAULT 'cerrado' CHECK (estado IN ('cerrado', 'reabierto')),
    usuario_id TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    cerrado_por TEXT NOT NULL,
    cerrado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    nota TEXT,
    resumen JSONB NOT NULL,
    reabierto_por TEXT,
    reabierto_en TIMESTAMPTZ,
    motivo_reapertura TEXT,
    PRIMARY KEY (empresa_id, fecha)
);
