-- SCRIPT DE REVERSA DEL AJUSTE FORENSE RSV-374cbd57abf6
-- En contabilidad append-only, revertir un reverso se realiza asentando un cobro compensatorio
-- o deshaciendo la transacción antes del COMMIT.
BEGIN;
-- Asentar cobro compensatorio en caso de revertir el ajuste anterior (si ya fue comiteado).
COMMIT;
