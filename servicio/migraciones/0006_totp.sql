-- Segundo factor TOTP (Google Authenticator): secreto por usuario y estado.
-- Nadie queda fuera al migrar: la columna nace desactivada.
ALTER TABLE usuarios ADD COLUMN totp_secreto TEXT;
ALTER TABLE usuarios ADD COLUMN totp_activado BOOLEAN NOT NULL DEFAULT FALSE;
