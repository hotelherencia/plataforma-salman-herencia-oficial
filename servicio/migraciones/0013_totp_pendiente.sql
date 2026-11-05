-- SEC-A02 (#327): secreto TOTP pendiente separado del activo. El alta en
-- curso nunca toca la protección vigente; reemplazar o desactivar exige la
-- clave actual (reautenticación en la ruta HTTP).
ALTER TABLE usuarios ADD COLUMN totp_secreto_pendiente TEXT;
