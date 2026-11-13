-- Observabilidad: IP del cliente en cada evento auditado (detección de
-- ataques distribuidos por usuario) e índice para consultar por actor.
ALTER TABLE auditoria ADD COLUMN IF NOT EXISTS ip TEXT;
CREATE INDEX IF NOT EXISTS idx_auditoria_accion_resultado ON auditoria (accion, resultado, creado_en);
