-- Entrega 1A.3 del módulo hotel (2026-11-17): políticas del hotel como
-- única fuente editable (mantenedor, rol admin_hotel). Horarios de
-- llegada/salida, recargos, cancelación, no-show, depósito, mínimo de
-- noches, niños/cama adicional, mascotas, desayuno, estacionamiento,
-- medios de pago, registro de llegada/salida y FAQ.
--
-- El cuerpo vive en JSONB validado por servicio/politicas.py. Los valores
-- iniciales no se insertan aquí: el servicio los materializa por empresa
-- la primera vez (hechos ya publicados en la landing o en el código, y
-- los no ratificados marcados pendiente_confirmar). Nada se borra.
--
-- La reserva conserva un snapshot de la política y de los recargos
-- vigentes al confirmar (el cambio posterior del mantenedor no altera
-- reservas ya hechas). El IVA sigue en ajustes_plataforma (admin de
-- plataforma).

CREATE TABLE IF NOT EXISTS politicas_hotel (
    empresa_id TEXT PRIMARY KEY,
    cuerpo JSONB NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    actualizada_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    actualizada_por TEXT
);

ALTER TABLE reservas ADD COLUMN IF NOT EXISTS politica_snapshot JSONB;
ALTER TABLE reservas ADD COLUMN IF NOT EXISTS recargos JSONB;
