-- Referencia opaca para continuar la reserva sin repetir nombre ni correo
-- y sin poner esos datos en la URL. El token no es el id del lead.
ALTER TABLE leads ADD COLUMN IF NOT EXISTS token_consulta TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_token_consulta
    ON leads (token_consulta)
    WHERE token_consulta IS NOT NULL;
