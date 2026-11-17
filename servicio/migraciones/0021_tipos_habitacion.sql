-- Entrega 1A del módulo hotel (2026-11-17, plan modulo-hotel §3): tipos de
-- habitación con precio base heredado, precio propio por habitación
-- (reservado), alta por lote y precio congelado noche a noche en la reserva.
--
-- Seguridad en Railway (MIGRAR_AL_ARRANCAR): solo hacia adelante, sin DELETE
-- ni DROP de datos; todas las sentencias son repetibles (IF NOT EXISTS,
-- ON CONFLICT, CREATE OR REPLACE, guardas en DO). Los tipos nacen con
-- precio_base_clp NULL: ningún precio efectivo cambia con esta migración
-- (las tarifas por habitación y fecha siguen mandando; ver servicio/precios.py).

CREATE TABLE IF NOT EXISTS tipos_habitacion (
    id TEXT PRIMARY KEY CHECK (length(id) BETWEEN 1 AND 50),
    nombre TEXT NOT NULL CHECK (length(btrim(nombre)) BETWEEN 1 AND 80),
    capacidad_base INTEGER NOT NULL CHECK (capacidad_base > 0),
    precio_base_clp INTEGER CHECK (precio_base_clp IS NULL OR precio_base_clp > 0),
    orden INTEGER NOT NULL DEFAULT 0,
    activo BOOLEAN NOT NULL DEFAULT true,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    actualizado_en TIMESTAMPTZ
);

-- Un tipo por cada valor de habitaciones.tipo que exista hoy (HAB-01..17 y
-- cualquier otra unidad), 1:1 y sin tocar habitaciones.tipo. Nombre legible
-- para los tipos conocidos. Los ids nuevos se validan en la API.
INSERT INTO tipos_habitacion (id, nombre, capacidad_base, orden)
SELECT h.tipo,
       CASE h.tipo
           WHEN 'single' THEN 'Single'
           WHEN 'doble' THEN 'Doble'
           WHEN 'matrimonial' THEN 'Matrimonial'
           WHEN 'matrimonial_mas_1' THEN 'Matrimonial +1'
           WHEN 'triple' THEN 'Triple'
           ELSE initcap(replace(h.tipo, '_', ' '))
       END,
       max(h.capacidad),
       CASE h.tipo
           WHEN 'single' THEN 10 WHEN 'doble' THEN 20 WHEN 'matrimonial' THEN 30
           WHEN 'matrimonial_mas_1' THEN 40 WHEN 'triple' THEN 50 ELSE 100
       END
FROM habitaciones h
GROUP BY h.tipo
ON CONFLICT (id) DO NOTHING;

-- Toda alta o cambio de tipo por cualquier camino (API heredada con tipo en
-- texto, siembra de arranque, scripts) asegura su fila en tipos_habitacion.
CREATE OR REPLACE FUNCTION asegurar_tipo_habitacion() RETURNS trigger AS $$
BEGIN
    INSERT INTO tipos_habitacion (id, nombre, capacidad_base, orden)
    VALUES (NEW.tipo, initcap(replace(NEW.tipo, '_', ' ')), NEW.capacidad, 100)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS habitaciones_asegurar_tipo ON habitaciones;
CREATE TRIGGER habitaciones_asegurar_tipo
    BEFORE INSERT OR UPDATE OF tipo ON habitaciones
    FOR EACH ROW EXECUTE FUNCTION asegurar_tipo_habitacion();

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'habitaciones_tipo_fk') THEN
        ALTER TABLE habitaciones ADD CONSTRAINT habitaciones_tipo_fk
            FOREIGN KEY (tipo) REFERENCES tipos_habitacion(id) ON UPDATE CASCADE;
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_habitaciones_tipo ON habitaciones (tipo);

-- Precio propio de la unidad (reservado para la entrega 1B): si existe, gana
-- al precio base del tipo; una tarifa por fechas de la unidad gana a ambos.
ALTER TABLE habitaciones ADD COLUMN IF NOT EXISTS precio_propio_clp INTEGER
    CHECK (precio_propio_clp IS NULL OR precio_propio_clp > 0);

-- Inventario operativo del titular más allá de HAB-01..17: las unidades que
-- la administración da de alta por lote. HAB-01..17 se marcan también.
ALTER TABLE habitaciones ADD COLUMN IF NOT EXISTS en_inventario BOOLEAN NOT NULL DEFAULT false;
UPDATE habitaciones SET en_inventario = true
WHERE id ~ '^HAB-(0[1-9]|1[0-7])$' AND en_inventario = false;

-- Precio congelado de cada noche al confirmar (lo cotizado es lo cargado;
-- cambiar precios después no altera reservas aceptadas).
CREATE TABLE IF NOT EXISTS reserva_noches (
    reserva_id TEXT NOT NULL REFERENCES reservas(id),
    noche DATE NOT NULL,
    precio_clp INTEGER NOT NULL CHECK (precio_clp > 0),
    origen TEXT NOT NULL,
    PRIMARY KEY (reserva_id, noche)
);
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS total_aceptado_clp INTEGER
    CHECK (total_aceptado_clp IS NULL OR total_aceptado_clp > 0);
