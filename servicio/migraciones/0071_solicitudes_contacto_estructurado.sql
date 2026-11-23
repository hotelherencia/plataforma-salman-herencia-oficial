-- 0071: contacto de la solicitud en columnas propias (#453). Aditiva e idempotente.
-- Hasta hoy el correo, el teléfono y el documento viajaban dentro de `huesped_contacto`
-- («correo · Tel: … · Doc: …») y las pantallas lo descomponían con expresiones regulares.
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS huesped_correo TEXT;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS huesped_telefono TEXT;       -- E.164 (+569XXXXXXXX)
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS huesped_documento TEXT;
ALTER TABLE solicitudes ADD COLUMN IF NOT EXISTS contacto_verificado BOOLEAN NOT NULL DEFAULT FALSE;

-- Relleno de lo ya recibido (solo donde falta; no pisa datos).
UPDATE solicitudes SET huesped_correo = lower(substring(huesped_contacto from '[^\s·]+@[^\s·]+'))
 WHERE huesped_correo IS NULL AND huesped_contacto ~ '[^\s·]+@[^\s·]+';
UPDATE solicitudes SET huesped_documento = btrim(substring(huesped_contacto from 'Doc:\s*([^·]+)'))
 WHERE huesped_documento IS NULL AND huesped_contacto ~ 'Doc:\s*[^·]+';
UPDATE solicitudes SET huesped_telefono = CASE
        WHEN length(d) = 9 AND left(d, 1) = '9' THEN '+56' || d
        WHEN length(d) BETWEEN 8 AND 15 THEN '+' || d END
  FROM (SELECT id AS sid, regexp_replace(COALESCE(substring(huesped_contacto from 'Tel:\s*([^·]+)'),
              CASE WHEN huesped_contacto !~ '@' THEN huesped_contacto END, ''), '\D', '', 'g') AS d
          FROM solicitudes) t
 WHERE solicitudes.id = t.sid AND solicitudes.huesped_telefono IS NULL AND t.d <> '';
