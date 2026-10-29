-- Login con Google (OAuth 2.0 / OIDC): vínculo opcional por email.
-- NULL = sin vincular: ese usuario no puede entrar con Google hasta que
-- alguien le defina email. La unicidad es parcial: admite varios NULL.
ALTER TABLE usuarios ADD COLUMN email TEXT;
CREATE UNIQUE INDEX idx_usuarios_email ON usuarios (email) WHERE email IS NOT NULL;
