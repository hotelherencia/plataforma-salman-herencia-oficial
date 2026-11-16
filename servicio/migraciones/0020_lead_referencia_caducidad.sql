-- SOC-016 (auditoría 2026-11-16): la referencia opaca del lead caduca.
-- token_expira NULL = sin referencia vigente. Las referencias ya emitidas
-- quedan con la caducidad por defecto (72 h desde la creación del lead), así
-- que un enlace antiguo reenviado deja de mostrar datos personales.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS token_expira TIMESTAMPTZ;

UPDATE leads
   SET token_expira = creado_en + interval '72 hours'
 WHERE token_consulta IS NOT NULL AND token_expira IS NULL;
