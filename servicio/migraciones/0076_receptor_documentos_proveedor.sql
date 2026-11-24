-- #469: RUT y razón social a quien se emitió la factura de proveedor. El grupo factura a varias
-- sociedades (Hotelera Quinchamalí SpA, Consorcio Hotelero El Roble SpA, Herencia SpA) y el IVA
-- crédito de una no se imputa a otra: el F29 solo suma lo emitido al RUT de la empresa (EMPRESA_RUT).
-- Aditiva e idempotente; los documentos ya cargados quedan con receptor NULL ("sin receptor").
ALTER TABLE documentos_proveedor ADD COLUMN IF NOT EXISTS receptor_rut TEXT;
ALTER TABLE documentos_proveedor ADD COLUMN IF NOT EXISTS receptor_razon_social TEXT;
CREATE INDEX IF NOT EXISTS idx_documentos_proveedor_receptor ON documentos_proveedor (receptor_rut);
