-- F20 (MIG-002..006): Bodegas operativas iniciales para carga de apertura
-- (Lavandería, Insumos Aseo, Insumos Desayuno y Cocina) sobre el stock compartido 0055.
-- Migración aditiva e idempotente.

INSERT INTO core_bodegas (id, codigo, nombre, modulo, activa) VALUES
    ('BOD-LAV', 'lavanderia', 'Lavandería', 'hotel', true),
    ('BOD-ASEO', 'insumos_aseo', 'Insumos Aseo', 'hotel', true),
    ('BOD-DES', 'insumos_desayuno', 'Insumos Desayuno', 'cafeteria', true),
    ('BOD-COC', 'cocina', 'Cocina', 'cafeteria', true)
ON CONFLICT (codigo) DO NOTHING;
