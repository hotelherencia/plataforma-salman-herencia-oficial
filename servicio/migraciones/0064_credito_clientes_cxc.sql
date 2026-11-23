-- Contable 2.2 (#392 / RES-008 / REC-003 / FIN-002):
-- Políticas de crédito por cliente o empresa y cuentas por cobrar con antigüedad.
-- Migración aditiva e idempotente. PCI: jamás almacena número completo de tarjeta ni CVV.

ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS politica_credito TEXT NOT NULL DEFAULT 'pago_al_registrarse'
        CHECK (politica_credito IN ('pago_al_registrarse', 'credito_autorizado', 'garantia_salida'));

ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS cupo_credito_clp BIGINT NOT NULL DEFAULT 0 CHECK (cupo_credito_clp >= 0);

ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS plazo_dias INTEGER NOT NULL DEFAULT 0 CHECK (plazo_dias BETWEEN 0 AND 365);

ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS garantia_tarjeta_marca TEXT;

ALTER TABLE clientes
    ADD COLUMN IF NOT EXISTS garantia_tarjeta_ultimos4 TEXT
        CHECK (garantia_tarjeta_ultimos4 IS NULL OR garantia_tarjeta_ultimos4 ~ '^[0-9]{4}$');

CREATE TABLE IF NOT EXISTS cuentas_por_cobrar (
    id TEXT PRIMARY KEY,
    empresa_id TEXT NOT NULL,
    reserva_id TEXT NOT NULL UNIQUE REFERENCES reservas(id),
    cliente_id TEXT NOT NULL REFERENCES clientes(id),
    monto_original_clp BIGINT NOT NULL CHECK (monto_original_clp > 0),
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    politica_aplicada TEXT NOT NULL CHECK (politica_aplicada IN ('credito_autorizado', 'garantia_salida')),
    estado TEXT NOT NULL DEFAULT 'abierta' CHECK (estado IN ('abierta', 'parcial', 'pagada', 'anulada')),
    nota TEXT,
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cxc_empresa_estado
    ON cuentas_por_cobrar (empresa_id, estado, fecha_vencimiento ASC);

CREATE INDEX IF NOT EXISTS idx_cxc_cliente
    ON cuentas_por_cobrar (cliente_id, estado);

CREATE TABLE IF NOT EXISTS cxc_abonos (
    id TEXT PRIMARY KEY,
    cxc_id TEXT NOT NULL REFERENCES cuentas_por_cobrar(id),
    monto_clp BIGINT NOT NULL CHECK (monto_clp > 0),
    medio TEXT NOT NULL CHECK (medio IN ('efectivo', 'debito', 'credito', 'transferencia')),
    comprobante TEXT,
    nota TEXT,
    clave_idempotencia TEXT UNIQUE,
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cxc_abonos_cxc
    ON cxc_abonos (cxc_id, creado_en ASC);

CREATE OR REPLACE FUNCTION impedir_mutacion_cxc_abonos() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'cxc_abonos es append-only: no se permite UPDATE ni DELETE';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_cxc_abonos_inmutables ON cxc_abonos;
CREATE TRIGGER trg_cxc_abonos_inmutables
    BEFORE UPDATE OR DELETE ON cxc_abonos
    FOR EACH ROW EXECUTE FUNCTION impedir_mutacion_cxc_abonos();
