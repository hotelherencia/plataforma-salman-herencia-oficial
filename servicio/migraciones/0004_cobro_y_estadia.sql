CREATE TABLE cargos (
    id TEXT PRIMARY KEY,
    reserva_id TEXT NOT NULL REFERENCES reservas(id),
    concepto TEXT NOT NULL,
    monto_clp INTEGER NOT NULL CHECK (monto_clp > 0),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un pago por (reserva, clave): el reintento de negocio no duplica el efecto.
CREATE TABLE pagos (
    id TEXT PRIMARY KEY,
    reserva_id TEXT NOT NULL REFERENCES reservas(id),
    monto_clp INTEGER NOT NULL CHECK (monto_clp > 0),
    clave TEXT NOT NULL,
    modo TEXT NOT NULL CHECK (modo IN ('manual', 'pasarela')),
    estado TEXT NOT NULL DEFAULT 'confirmado',
    efecto_nucleo_id TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (reserva_id, clave)
);

-- Efecto aplicado por el núcleo: registro durable del ledger (spec-backend-v1).
CREATE TABLE efectos_nucleo (
    id TEXT PRIMARY KEY,
    clave TEXT NOT NULL UNIQUE,
    estado TEXT NOT NULL,
    monto_clp INTEGER NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE liquidaciones (
    id TEXT PRIMARY KEY,
    reserva_id TEXT NOT NULL REFERENCES reservas(id),
    total_clp INTEGER NOT NULL,
    pagado_clp INTEGER NOT NULL,
    saldo_clp INTEGER NOT NULL,
    estado TEXT NOT NULL DEFAULT 'liquidada',
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (reserva_id)
);

ALTER TABLE reservas ADD CONSTRAINT reservas_estado_valido
    CHECK (estado IN ('confirmada', 'en_estadia', 'finalizada'));
