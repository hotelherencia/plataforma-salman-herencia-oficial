-- Entrega 1A.2 del módulo hotel (2026-11-17): UNA sola fuente de precio.
--
-- Antes: precio base del tipo (1A) + tarifas por habitación y fechas (tabla
-- `tarifas`, editor aparte) mandando encima. Después: todo vive en el
-- mantenedor «Tipos, habitaciones y precios»:
--   1. precio base del tipo (tipos_habitacion.precio_base_clp, IVA incluido);
--   2. precio propio de la habitación (habitaciones.precio_propio_clp);
--   3. excepciones por fecha (excepciones_precio) del TIPO o, si hace falta,
--      de UNA habitación; precio NULL = «sin venta» esas noches.
-- Prioridad: excepción de la habitación > excepción del tipo > precio propio
-- > precio base. Ver servicio/precios.py.
--
-- Conversión de las tarifas heredadas (calculada desde las filas presentes
-- al migrar, sin valores fijos):
--   * Línea de tiempo efectiva de cada habitación con la regla de siempre
--     (mayor fecha_desde, luego creado_en y id más recientes; sin tarifa →
--     precio propio/base de 1A; si no, sin precio), dentro del horizonte
--     [min(fecha_desde), max(fecha_hasta)) de las tarifas activas.
--   * Precio dominante de la habitación = el de más noches en el horizonte
--     (empate: el menor).
--   * Precio base del tipo = el dominante más repetido entre sus habitaciones
--     (empate: el menor). Las habitaciones con otro dominante quedan con
--     precio propio.
--   * Cada tramo cuyo precio no coincide con el nuevo precio por defecto de
--     la habitación se vuelve excepción por fecha de la habitación (o «sin
--     venta» si no tenía precio); si el mismo tramo aplica a TODAS las
--     habitaciones del tipo, queda como una sola excepción del tipo.
--   * Resultado: el precio de cada habitación y noche dentro del horizonte es
--     idéntico al anterior (prueba test_1a_regresion_precios).
--
-- Seguridad en Railway (MIGRAR_AL_ARRANCAR): solo hacia adelante; no borra
-- nada. Las tarifas heredadas quedan archivadas (tarifas.archivada_en) y
-- consultables en la ficha. Repetible: si ya hay tarifas archivadas, la
-- conversión no se vuelve a ejecutar. Deja un resumen en auditoría.
--
-- IVA: tasa configurable (ajustes_plataforma 'iva_porcentaje', 19 por
-- defecto); los precios guardados son CON IVA (fuente de verdad), el neto se
-- deriva (servicio/iva.py).

CREATE TABLE IF NOT EXISTS ajustes_plataforma (
    clave TEXT PRIMARY KEY,
    valor NUMERIC(8, 3) NOT NULL,
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    actualizado_por TEXT
);
INSERT INTO ajustes_plataforma (clave, valor, actualizado_por)
VALUES ('iva_porcentaje', 19, 'migracion_0022')
ON CONFLICT (clave) DO NOTHING;

CREATE TABLE IF NOT EXISTS excepciones_precio (
    id TEXT PRIMARY KEY,
    tipo_id TEXT REFERENCES tipos_habitacion(id) ON UPDATE CASCADE,
    habitacion_id TEXT REFERENCES habitaciones(id),
    fecha_desde DATE NOT NULL,
    fecha_hasta DATE NOT NULL,
    precio_clp INTEGER CHECK (precio_clp IS NULL OR precio_clp > 0),
    motivo TEXT,
    origen TEXT NOT NULL DEFAULT 'mantenedor',
    activa BOOLEAN NOT NULL DEFAULT true,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    creado_por TEXT,
    retirada_en TIMESTAMPTZ,
    retirada_por TEXT,
    CHECK (fecha_hasta > fecha_desde),
    CHECK ((tipo_id IS NULL) <> (habitacion_id IS NULL))
);
CREATE INDEX IF NOT EXISTS idx_excepciones_habitacion
    ON excepciones_precio (habitacion_id, fecha_desde) WHERE activa;
CREATE INDEX IF NOT EXISTS idx_excepciones_tipo
    ON excepciones_precio (tipo_id, fecha_desde) WHERE activa;

ALTER TABLE tarifas ADD COLUMN IF NOT EXISTS archivada_en TIMESTAMPTZ;

DO $$
DECLARE
    h0 DATE;
    h1 DATE;
    n_activas INTEGER;
    resumen TEXT;
BEGIN
    IF EXISTS (SELECT 1 FROM tarifas WHERE archivada_en IS NOT NULL) THEN
        RAISE NOTICE '0022: las tarifas heredadas ya se convirtieron; nada que hacer';
        RETURN;
    END IF;
    SELECT min(fecha_desde), max(fecha_hasta), count(*) INTO h0, h1, n_activas FROM tarifas;
    IF n_activas = 0 THEN
        RAISE NOTICE '0022: sin tarifas heredadas; nada que convertir';
        RETURN;
    END IF;

    -- Precio sin tarifa según 1A (precio propio, si no base del tipo).
    CREATE TEMP TABLE m22_hab ON COMMIT DROP AS
    SELECT h.id, h.tipo, COALESCE(h.precio_propio_clp, t.precio_base_clp) AS respaldo
    FROM habitaciones h JOIN tipos_habitacion t ON t.id = h.tipo;

    -- Tramos de precio constante por habitación dentro del horizonte.
    CREATE TEMP TABLE m22_tramo ON COMMIT DROP AS
    WITH fronteras AS (
        SELECT id AS hab, h0 AS f FROM m22_hab
        UNION SELECT id, h1 FROM m22_hab
        UNION SELECT habitacion_id, fecha_desde FROM tarifas
        UNION SELECT habitacion_id, fecha_hasta FROM tarifas
    ), elementales AS (
        SELECT hab, f AS desde, lead(f) OVER (PARTITION BY hab ORDER BY f) AS hasta FROM fronteras
    ), con_precio AS (
        SELECT e.hab, e.desde, e.hasta,
               COALESCE((SELECT t.tarifa_noche_clp FROM tarifas t
                         WHERE t.habitacion_id = e.hab AND t.fecha_desde <= e.desde AND t.fecha_hasta > e.desde
                         ORDER BY t.fecha_desde DESC, t.creado_en DESC, t.id DESC LIMIT 1),
                        m.respaldo) AS precio
        FROM elementales e JOIN m22_hab m ON m.id = e.hab
        WHERE e.hasta IS NOT NULL
    ), marcados AS (
        SELECT *, CASE WHEN lag(precio) OVER (PARTITION BY hab ORDER BY desde) IS NOT DISTINCT FROM precio
                       AND lag(hasta) OVER (PARTITION BY hab ORDER BY desde) = desde
                       THEN 0 ELSE 1 END AS corte
        FROM con_precio
    ), grupos AS (
        SELECT *, sum(corte) OVER (PARTITION BY hab ORDER BY desde) AS grupo FROM marcados
    )
    SELECT hab, min(desde) AS desde, max(hasta) AS hasta, min(precio) AS precio
    FROM grupos GROUP BY hab, grupo;

    -- Precio dominante de cada habitación (más noches; empate: el menor).
    CREATE TEMP TABLE m22_dominante ON COMMIT DROP AS
    SELECT DISTINCT ON (hab) hab, precio
    FROM (SELECT hab, precio, sum(hasta - desde) AS noches FROM m22_tramo
          WHERE precio IS NOT NULL GROUP BY hab, precio) x
    ORDER BY hab, noches DESC, precio ASC;

    -- Precio base del tipo: el dominante mayoritario (empate: el menor).
    CREATE TEMP TABLE m22_base ON COMMIT DROP AS
    SELECT DISTINCT ON (tipo) tipo, precio
    FROM (SELECT m.tipo, d.precio, count(*) AS n FROM m22_hab m JOIN m22_dominante d ON d.hab = m.id
          GROUP BY m.tipo, d.precio) x
    ORDER BY tipo, n DESC, precio ASC;

    UPDATE tipos_habitacion t SET precio_base_clp = b.precio, actualizado_en = clock_timestamp()
    FROM m22_base b
    WHERE b.tipo = t.id AND t.precio_base_clp IS DISTINCT FROM b.precio;

    -- Precio propio solo donde el dominante difiere del base del tipo.
    UPDATE habitaciones h
    SET precio_propio_clp = CASE WHEN d.precio = t.precio_base_clp THEN NULL ELSE d.precio END
    FROM m22_dominante d, tipos_habitacion t
    WHERE d.hab = h.id AND t.id = h.tipo
      AND h.precio_propio_clp IS DISTINCT FROM (CASE WHEN d.precio = t.precio_base_clp THEN NULL ELSE d.precio END);

    -- Tramos que difieren del nuevo precio por defecto → excepciones.
    CREATE TEMP TABLE m22_excepcion ON COMMIT DROP AS
    SELECT tr.hab, h.tipo, tr.desde, tr.hasta, tr.precio
    FROM m22_tramo tr
    JOIN habitaciones h ON h.id = tr.hab
    JOIN tipos_habitacion t ON t.id = h.tipo
    WHERE tr.precio IS DISTINCT FROM COALESCE(h.precio_propio_clp, t.precio_base_clp);

    -- El mismo tramo en todas las habitaciones del tipo → excepción del tipo.
    CREATE TEMP TABLE m22_del_tipo ON COMMIT DROP AS
    SELECT e.tipo, e.desde, e.hasta, e.precio
    FROM m22_excepcion e
    GROUP BY e.tipo, e.desde, e.hasta, e.precio
    HAVING count(*) = (SELECT count(*) FROM habitaciones h WHERE h.tipo = e.tipo);

    INSERT INTO excepciones_precio (id, tipo_id, fecha_desde, fecha_hasta, precio_clp, motivo, origen, creado_por)
    SELECT 'EXC-M22-' || substr(md5('tipo|' || tipo || '|' || desde || '|' || hasta || '|' || COALESCE(precio::text, '-')), 1, 12),
           tipo, desde, hasta, precio,
           'Convertida desde las tarifas por habitación (migración 0022)', 'migracion_0022', 'migracion_0022'
    FROM m22_del_tipo
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO excepciones_precio (id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, motivo, origen, creado_por)
    SELECT 'EXC-M22-' || substr(md5('hab|' || e.hab || '|' || e.desde || '|' || e.hasta || '|' || COALESCE(e.precio::text, '-')), 1, 12),
           e.hab, e.desde, e.hasta, e.precio,
           'Convertida desde las tarifas por habitación (migración 0022)', 'migracion_0022', 'migracion_0022'
    FROM m22_excepcion e
    WHERE NOT EXISTS (
        SELECT 1 FROM m22_del_tipo d
        WHERE d.tipo = e.tipo AND d.desde = e.desde AND d.hasta = e.hasta AND d.precio IS NOT DISTINCT FROM e.precio
    )
    ON CONFLICT (id) DO NOTHING;

    UPDATE tarifas SET archivada_en = clock_timestamp() WHERE archivada_en IS NULL;

    SELECT format(
        'migración 0022: %s tarifas heredadas archivadas; horizonte [%s, %s); precio base por tipo: %s; '
        'habitaciones con precio propio: %s; excepciones del tipo: %s; excepciones de habitación: %s (sin venta: %s)',
        n_activas, h0, h1,
        COALESCE((SELECT string_agg(t.id || '=' || COALESCE(t.precio_base_clp::text, 'sin precio'), ', ' ORDER BY t.orden, t.id)
                  FROM tipos_habitacion t), '-'),
        (SELECT count(*) FROM habitaciones WHERE precio_propio_clp IS NOT NULL),
        (SELECT count(*) FROM excepciones_precio WHERE origen = 'migracion_0022' AND tipo_id IS NOT NULL),
        (SELECT count(*) FROM excepciones_precio WHERE origen = 'migracion_0022' AND habitacion_id IS NOT NULL),
        (SELECT count(*) FROM excepciones_precio WHERE origen = 'migracion_0022' AND precio_clp IS NULL)
    ) INTO resumen;
    RAISE NOTICE '%', resumen;
    INSERT INTO auditoria (id, actor, accion, recurso, resultado)
    VALUES ('AUD-M22-' || substr(md5(resumen || clock_timestamp()::text), 1, 12),
            'migracion_0022', 'precios.unificar', 'tipos_habitacion', resumen);
END $$;
