-- #298 (DECISIÓN 2026-11-06, opción a): las personas de la reserva se
-- persisten y se validan contra la capacidad al confirmar (hoy solo filtran
-- la oferta). Nullable: las conversiones y flujos operativos heredados no
-- siempre conocen el dato.
ALTER TABLE reservas ADD COLUMN personas INTEGER CHECK (personas IS NULL OR personas > 0);
