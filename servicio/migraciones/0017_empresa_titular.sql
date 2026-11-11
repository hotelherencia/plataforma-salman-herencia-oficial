-- Reetiqueta el tenant sintético al titular real Herencia SpA.
-- Idempotente: solo mueve filas que aún llevan EMP-SINTETICA-001.
UPDATE usuarios SET empresa_id = 'EMP-HERENCIA-001' WHERE empresa_id = 'EMP-SINTETICA-001';
UPDATE sesiones SET empresa_id = 'EMP-HERENCIA-001' WHERE empresa_id = 'EMP-SINTETICA-001';
UPDATE reservas SET empresa_id = 'EMP-HERENCIA-001' WHERE empresa_id = 'EMP-SINTETICA-001';
UPDATE claves_idempotencia SET empresa_id = 'EMP-HERENCIA-001' WHERE empresa_id = 'EMP-SINTETICA-001';
UPDATE solicitudes SET empresa_id = 'EMP-HERENCIA-001' WHERE empresa_id = 'EMP-SINTETICA-001';
UPDATE leads SET empresa_id = 'EMP-HERENCIA-001' WHERE empresa_id = 'EMP-SINTETICA-001';
UPDATE consultas_agente SET empresa_id = 'EMP-HERENCIA-001' WHERE empresa_id = 'EMP-SINTETICA-001';
UPDATE politica_agente SET empresa_id = 'EMP-HERENCIA-001' WHERE empresa_id = 'EMP-SINTETICA-001';
UPDATE mensajes_whatsapp SET empresa_id = 'EMP-HERENCIA-001' WHERE empresa_id = 'EMP-SINTETICA-001';
