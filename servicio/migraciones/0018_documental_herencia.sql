-- Almacén documental del paquete Hotel Herencia 2026-11-11.
-- No gobierna oferta ni cobro: las tablas operativas (habitaciones/tarifas/reservas)
-- siguen siendo la única fuente vendible. Aquí se consulta el levantamiento y
-- el histórico reportado (ocupación, condiciones, etc.).

CREATE TABLE IF NOT EXISTS doc_paquete (
    id TEXT PRIMARY KEY,
    fecha DATE NOT NULL,
    sha256_zip TEXT NOT NULL,
    clasificacion TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'America/Santiago',
    cargado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS doc_habitacion (
    paquete_id TEXT NOT NULL REFERENCES doc_paquete(id) ON DELETE CASCADE,
    habitacion_id TEXT NOT NULL,
    numero TEXT,
    tipo_declarado TEXT,
    tipo_salman TEXT,
    capacidad_propuesta INTEGER,
    capacidad_requiere_verificacion BOOLEAN NOT NULL DEFAULT FALSE,
    capacidad_personas_origen TEXT,
    estado_venta_origen TEXT,
    fuente TEXT,
    estado_evidencia TEXT,
    verificado_en_terreno BOOLEAN NOT NULL DEFAULT FALSE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (paquete_id, habitacion_id)
);

CREATE TABLE IF NOT EXISTS doc_tarifa (
    paquete_id TEXT NOT NULL REFERENCES doc_paquete(id) ON DELETE CASCADE,
    tarifa_id TEXT NOT NULL,
    tipo_comercial TEXT,
    monto_clp INTEGER,
    moneda TEXT,
    iva_incluido_declarado BOOLEAN,
    canal TEXT,
    vigente_desde DATE,
    vigente_hasta DATE,
    aprobada_2027 BOOLEAN NOT NULL DEFAULT FALSE,
    nota TEXT,
    publicar_activa BOOLEAN NOT NULL DEFAULT FALSE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (paquete_id, tarifa_id)
);

CREATE TABLE IF NOT EXISTS doc_ocupacion_reportada (
    paquete_id TEXT NOT NULL REFERENCES doc_paquete(id) ON DELETE CASCADE,
    registro_id TEXT NOT NULL,
    habitacion_id TEXT NOT NULL,
    periodo TEXT NOT NULL,
    valor_reportado NUMERIC,
    unidad_confirmada TEXT,
    interpretacion_propuesta TEXT,
    dias_calendario INTEGER,
    estado_valor TEXT,
    es_kpi BOOLEAN NOT NULL DEFAULT FALSE,
    fuente TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (paquete_id, registro_id)
);

CREATE INDEX IF NOT EXISTS idx_doc_ocupacion_periodo
    ON doc_ocupacion_reportada (paquete_id, periodo, habitacion_id);

CREATE TABLE IF NOT EXISTS doc_control_ocupacion (
    paquete_id TEXT NOT NULL REFERENCES doc_paquete(id) ON DELETE CASCADE,
    periodo TEXT NOT NULL,
    suma_reportada NUMERIC,
    porcentaje_guardado_fuente NUMERIC,
    porcentaje_calendario_hipotetico NUMERIC,
    denominador_hipotetico NUMERIC,
    supuesto TEXT,
    fuente TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (paquete_id, periodo)
);

CREATE TABLE IF NOT EXISTS doc_registro (
    paquete_id TEXT NOT NULL REFERENCES doc_paquete(id) ON DELETE CASCADE,
    tabla TEXT NOT NULL,
    clave TEXT NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (paquete_id, tabla, clave)
);

CREATE INDEX IF NOT EXISTS idx_doc_registro_tabla
    ON doc_registro (paquete_id, tabla);
