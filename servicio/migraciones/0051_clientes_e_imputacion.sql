-- Contabilidad fase 2.1 (2026-11-19): clientes con RUT normalizado e imputación de pagos y abonos.
-- Se apoya en la fase 1 (0050): `pagos` ya trae medio, documento, receptor, turno y es_anticipo.
--
-- Todo es solo de agregar: lo corrige un movimiento contrario con `revierte_id`, nunca un UPDATE ni un DELETE.

-- Clientes: el RUT se guarda solo con números y dígito verificador, sin puntos ni guion (la pantalla lo formatea).
-- Un RUT es un solo cliente; `nombre_clave` (sin tildes, minúsculas, un espacio) permite que la aplicación rechace
-- el mismo RUT con otro nombre.
CREATE TABLE clientes (
    id TEXT PRIMARY KEY,
    tipo TEXT NOT NULL DEFAULT 'empresa' CHECK (tipo IN ('persona', 'empresa')),
    rut TEXT NOT NULL UNIQUE CHECK (rut ~ '^[0-9]{7,8}[0-9K]$'),
    nombre TEXT NOT NULL CHECK (length(btrim(nombre)) BETWEEN 1 AND 200),
    nombre_clave TEXT NOT NULL,
    giro TEXT,
    direccion TEXT,
    comuna TEXT,
    correo TEXT,
    activo BOOLEAN NOT NULL DEFAULT true,
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Imputación: a qué reserva, habitación, noche y cliente va cada peso recibido.
--   anticipo             recibido antes de la Llegada (o de más): abono sin noche.
--   aplicacion_anticipo  parte de un anticipo aplicada al consumo de una noche ya asentada.
--   consumo              pago imputado a una noche o a un cargo suelto (noche NULL).
--   ajuste               corrección sin tipo propio.
-- Un reverso de pago agrega filas negativas con `revierte_id` apuntando a la fila que anula.
CREATE TABLE imputaciones_pago (
    id TEXT PRIMARY KEY,
    pago_id TEXT NOT NULL REFERENCES pagos(id),
    reserva_id TEXT NOT NULL REFERENCES reservas(id),
    habitacion_id TEXT NOT NULL REFERENCES habitaciones(id),
    noche DATE,
    cliente_id TEXT REFERENCES clientes(id),
    monto_clp INTEGER NOT NULL CHECK (monto_clp <> 0),
    tipo TEXT NOT NULL CHECK (tipo IN ('anticipo', 'aplicacion_anticipo', 'consumo', 'ajuste')),
    revierte_id TEXT REFERENCES imputaciones_pago(id),
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (monto_clp > 0 OR revierte_id IS NOT NULL),
    CHECK (tipo <> 'aplicacion_anticipo' OR noche IS NOT NULL)
);
CREATE INDEX idx_imputaciones_reserva ON imputaciones_pago (reserva_id, noche);
CREATE INDEX idx_imputaciones_pago ON imputaciones_pago (pago_id);
CREATE UNIQUE INDEX idx_imputaciones_una_reversa ON imputaciones_pago (revierte_id) WHERE revierte_id IS NOT NULL;

CREATE FUNCTION imputaciones_pago_solo_agrega() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'las imputaciones son solo de agregar: corrige con un movimiento contrario, no editando ni borrando'
        USING ERRCODE = 'check_violation';
END $$ LANGUAGE plpgsql;
CREATE TRIGGER imputaciones_pago_inmutables BEFORE UPDATE OR DELETE ON imputaciones_pago
    FOR EACH ROW EXECUTE FUNCTION imputaciones_pago_solo_agrega();
