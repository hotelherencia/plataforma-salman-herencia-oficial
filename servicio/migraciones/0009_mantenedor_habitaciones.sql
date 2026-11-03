-- Mantenedor de habitaciones (2026-11-03, spec-hotel-operacion-v1 §2).
-- Baja lógica: retirar de operación es estado_operativo = 'fuera_de_servicio'
-- (EstadoUnidad.FUERA_DE_SERVICIO del dominio) con motivo y fecha; nada se
-- borra. Las FK de reservas, tarifas y tareas_operativas ya impiden el DELETE
-- de una habitación con registros.
ALTER TABLE habitaciones ADD COLUMN motivo_fuera_de_servicio TEXT;
ALTER TABLE habitaciones ADD COLUMN fuera_de_servicio_desde TIMESTAMPTZ;

-- Tarifas append-only: el instante de registro desempata la vigencia cuando
-- dos tarifas comparten fecha_desde (gana la más reciente). Las filas
-- anteriores a esta migración quedan con el instante de la migración.
ALTER TABLE tarifas ADD COLUMN creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp();

CREATE INDEX idx_auditoria_recurso ON auditoria (recurso);
