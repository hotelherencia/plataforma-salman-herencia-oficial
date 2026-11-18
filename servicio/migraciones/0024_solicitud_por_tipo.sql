-- #346 / #347 (2026-11-18): la solicitud pública se toma por TIPO de
-- habitación, no por unidad. El número lo asigna el hotel al convertir
-- (cualquier unidad libre del tipo) o en recepción.
--
-- Antes la solicitud guardaba la primera unidad del tipo y la conversión
-- exigía esa unidad exacta: dos solicitudes del mismo tipo apuntaban a la
-- misma habitación y la segunda daba un falso «sin cupo» aunque quedaran
-- otras libres.
--
-- Compatible: las filas existentes conservan su unidad (pasa a ser la
-- preferida al convertir) y reciben el tipo de esa unidad. Nada se borra.
ALTER TABLE solicitudes ADD COLUMN tipo TEXT;
UPDATE solicitudes s SET tipo = h.tipo FROM habitaciones h WHERE h.id = s.habitacion_id;
ALTER TABLE solicitudes ALTER COLUMN tipo SET NOT NULL;
ALTER TABLE solicitudes ALTER COLUMN habitacion_id DROP NOT NULL;
