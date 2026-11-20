-- #323 (2026-11-19): catálogo transversal de roles fuera del módulo hotel.
-- Permite administrar roles del núcleo y de cada módulo habilitado por empresa
-- manteniendo intactos los seis roles operativos actuales.

CREATE TABLE IF NOT EXISTS roles_catalogo (
    codigo TEXT PRIMARY KEY,
    modulo TEXT NOT NULL CHECK (modulo IN ('core', 'hotel', 'cafeteria', 'inmobiliaria', 'constructora')),
    etiqueta TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    exige_doble_factor BOOLEAN NOT NULL DEFAULT false,
    activo BOOLEAN NOT NULL DEFAULT true,
    orden INTEGER NOT NULL DEFAULT 100,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS empresa_modulos (
    empresa_id TEXT NOT NULL,
    modulo TEXT NOT NULL CHECK (modulo IN ('core', 'hotel', 'cafeteria', 'inmobiliaria', 'constructora')),
    activo BOOLEAN NOT NULL DEFAULT true,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (empresa_id, modulo)
);

INSERT INTO roles_catalogo (codigo, modulo, etiqueta, descripcion, exige_doble_factor, activo, orden) VALUES
    ('administrador', 'core', 'Administrador (hotel y plataforma)', 'Acceso completo de negocio y plataforma', true, true, 10),
    ('admin_plataforma', 'core', 'Administrador de plataforma', 'Usuarios, seguridad y ajustes transversales del sistema', true, true, 20),
    ('admin_hotel', 'hotel', 'Administrador del hotel', 'Precios, habitaciones, reservas, caja, productos y reportes del hotel', true, true, 30),
    ('recepcion', 'hotel', 'Recepción', 'Reservas, llegadas, salidas, solicitudes y coordinación de aseo', false, true, 40),
    ('caja', 'hotel', 'Caja', 'Cobros, apertura y cierre de turno de caja', false, true, 50),
    ('aseo', 'hotel', 'Aseo', 'Lista de habitaciones por limpiar y confirmación de limpieza', false, true, 60)
ON CONFLICT (codigo) DO NOTHING;

-- Habilita core y hotel para las empresas ya registradas en usuarios.
INSERT INTO empresa_modulos (empresa_id, modulo, activo)
SELECT DISTINCT empresa_id, m.modulo, true
FROM usuarios
CROSS JOIN (VALUES ('core'), ('hotel')) AS m(modulo)
ON CONFLICT (empresa_id, modulo) DO NOTHING;
