-- Auditoría de seguridad 2026-11-17 (SA-TOTP-01): un código TOTP aceptado no
-- puede volver a usarse (RFC 6238 §5.2). Se guarda el último paso de 30 s
-- consumido por usuario; un código de ese paso o de uno anterior se rechaza.
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS totp_ultimo_paso bigint;
