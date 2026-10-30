-- El nombre de usuario es único: con duplicados, autenticar devolvía el
-- primero y la tabla ya filtra por nombre. Índice único en una sola pasada
-- (IF NOT EXISTS: compatible con reaplicar tras una interrupción).
CREATE UNIQUE INDEX IF NOT EXISTS usuarios_nombre_unico ON usuarios (nombre);
