-- Facturas de proveedores más fáciles (2026-11-19, pedido del propietario).
-- Número 0040 a propósito: deja libres 0034..0039 para otros frentes
-- (p. ej. «avisos») sin choque de nombres; el orden es alfabético.
--
-- 1. Buzón «recepcion_dte»: la casilla de intercambio del SII. La plataforma
--    lee los XML (EnvioDTE) que llegan y deja cada factura PENDIENTE de
--    revisión; nada toca el stock hasta que la administración confirma.
-- 2. Archivos (foto o PDF de la factura, XML recibido) guardados en la base,
--    con tipo y tamaño acotados; solo la administración los ve.
-- 3. Documentos de proveedor: facturas, notas de crédito y pedidos (estos
--    últimos quedan en borrador, sin stock, hasta que llegue la factura).
-- 4. Equivalencias por proveedor: «este ítem del proveedor es este
--    producto y trae N unidades por envase», recordadas al confirmar.
ALTER TABLE buzones_correo DROP CONSTRAINT buzones_correo_proposito_check;
ALTER TABLE buzones_correo ADD CONSTRAINT buzones_correo_proposito_check
    CHECK (proposito IN ('lectura_enviados', 'envio_avisos', 'recepcion_dte'));

CREATE TABLE archivos_documentos (
    id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL UNIQUE,
    tipo_mime TEXT NOT NULL CHECK (tipo_mime IN ('image/jpeg', 'image/png', 'image/webp', 'application/pdf', 'application/xml')),
    tamano INTEGER NOT NULL CHECK (tamano > 0 AND tamano <= 10485760),
    contenido BYTEA NOT NULL,
    nombre TEXT,
    creado_por TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE documentos_proveedor (
    id TEXT PRIMARY KEY,
    clase TEXT NOT NULL CHECK (clase IN ('factura', 'nota_credito', 'pedido', 'desconocido')),
    origen TEXT NOT NULL CHECK (origen IN ('correo', 'foto', 'pdf', 'xml')),
    estado TEXT NOT NULL CHECK (estado IN ('pendiente', 'borrador', 'cargada', 'facturado', 'archivada', 'descartada')),
    lectura TEXT NOT NULL DEFAULT 'manual' CHECK (lectura IN ('xml', 'ia', 'timbre', 'manual')),
    emisor_rut TEXT,
    emisor_razon_social TEXT,
    tipo_dte INTEGER,
    folio TEXT,
    fecha_emision DATE,
    monto_neto_clp BIGINT,
    monto_exento_clp BIGINT,
    iva_clp BIGINT,
    monto_total_clp BIGINT,
    lineas JSONB NOT NULL DEFAULT '[]',
    ted JSONB,
    referencias JSONB NOT NULL DEFAULT '[]',
    discrepancias JSONB NOT NULL DEFAULT '[]',
    archivo_id TEXT REFERENCES archivos_documentos(id),
    buzon_id TEXT,
    mensaje_id TEXT,
    remitente TEXT,
    importacion_id TEXT REFERENCES importaciones_productos(id),
    pedido_id TEXT REFERENCES documentos_proveedor(id),
    actor TEXT NOT NULL,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Un documento (proveedor + tipo + folio) entra una sola vez, venga del
-- correo, de una foto o del XML subido a mano.
CREATE UNIQUE INDEX idx_documentos_proveedor_clave
    ON documentos_proveedor (clase, emisor_rut, coalesce(tipo_dte, 0), folio)
    WHERE emisor_rut IS NOT NULL AND folio IS NOT NULL AND estado <> 'descartada';
CREATE INDEX idx_documentos_proveedor_estado ON documentos_proveedor (estado, creado_en DESC);

CREATE TABLE equivalencias_proveedor (
    id TEXT PRIMARY KEY,
    emisor_rut TEXT NOT NULL,
    clave TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    producto_id TEXT NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
    unidades_por_paquete INTEGER NOT NULL DEFAULT 1 CHECK (unidades_por_paquete BETWEEN 1 AND 10000),
    nota TEXT,
    actualizado_por TEXT NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (emisor_rut, clave)
);
