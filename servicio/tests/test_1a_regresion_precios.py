"""Entrega 1A — regresión de precios antes/después de la migración 0021.

Prueba que la migración a tipos de habitación y el resolvedor único
(`servicio/precios.py`) no cambian NINGÚN precio efectivo de HAB-01..17:

1. Crea una base nueva y temporal, aplica solo las migraciones 0001–0020 (el
   esquema de producción de hoy) y siembra el inventario real (HAB-01..17
   con el lote documental y las tarifas fijas del dueño, igual que el
   arranque en Railway), más variaciones que ejercitan la regla de vigencia
   (rangos solapados, empates por recencia, unidades sin tarifa o con
   tarifa parcial, mantenimiento, fuera de servicio y una reserva).
2. Cotiza con el oráculo congelado de `27f9ccf` (legado_precios_27f9ccf):
   precio de cada habitación y noche en ~5 meses y la oferta completa para
   llegadas cada 4 días × 1/2/3/7 noches × 1/2/3 personas.
3. Aplica 0021 (y la vuelve a ejecutar: idempotente) y repite con el código
   nuevo. Todo debe ser idéntico, también después de fijar en los tipos el
   precio base referencial del dueño (47/55/65 mil).
"""
import os
import unittest
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
import shutil
import tempfile

import psycopg
from psycopg import conninfo

from servicio import inventario_documental, migracion, precios
from servicio import reservas as reservas_db
from servicio.tests import legado_precios_27f9ccf as legado

URL_TEST = os.environ.get(
    "DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test"
)
DESDE = date(2026, 11, 10)
HASTA = date(2027, 4, 10)
AHORA = datetime(2026, 11, 17, 10, 0)
IDS_REALES = list(inventario_documental.IDS_INVENTARIO_REAL)
MIGRACION_1A = "0021_tipos_habitacion"


def _noches(desde, hasta):
    d = desde
    while d < hasta:
        yield d
        d += timedelta(days=1)


def _combinaciones():
    llegada = DESDE
    while llegada < HASTA - timedelta(days=7):
        for noches in (1, 2, 3, 7):
            for personas in (1, 2, 3):
                yield llegada, llegada + timedelta(days=noches), personas
        llegada += timedelta(days=4)


def _sembrar(conexion):
    inventario_documental.sembrar_inventario_documental(
        conexion, establecimiento_id=inventario_documental.ESTABLECIMIENTO_HERENCIA
    )
    resultado = inventario_documental.aplicar_tarifas_fijas_referenciales(conexion)
    assert resultado["insertadas"] == 17, resultado

    def tarifa(hid, desde, hasta, monto):
        conexion.execute(
            "INSERT INTO tarifas (id, habitacion_id, fecha_desde, fecha_hasta, tarifa_noche_clp) "
            "VALUES (%s, %s, %s, %s, %s)",
            (f"TAR-{uuid.uuid4().hex[:12]}", hid, desde, hasta, monto),
        )

    # Empate por fecha_desde: gana la registrada después (CA-HAB-03).
    tarifa("HAB-03", date(2026, 12, 15), date(2027, 1, 5), 60000)
    tarifa("HAB-03", date(2026, 12, 15), date(2026, 12, 31), 62000)
    # Mayor fecha_desde gana aunque sea más antigua.
    tarifa("HAB-09", date(2027, 2, 1), date(2027, 2, 10), 70000)
    tarifa("HAB-09", date(2027, 1, 20), date(2027, 3, 1), 58000)
    # Unidades ajenas al inventario real: sin tarifa y con tarifa parcial.
    for n, tipo in ((101, "doble"), (102, "doble"), (103, "suite_prueba")):
        conexion.execute(
            "INSERT INTO habitaciones (id, establecimiento_id, tipo, capacidad) VALUES (%s, 'EST-SINT-001', %s, 2)",
            (f"HAB-SINT-{n}", tipo),
        )
    tarifa("HAB-SINT-102", date(2026, 12, 1), date(2026, 12, 20), 40000)
    conexion.execute("UPDATE habitaciones SET mantenimiento = true WHERE id = 'HAB-12'")
    conexion.execute(
        "UPDATE habitaciones SET estado_operativo = 'fuera_de_servicio', motivo_fuera_de_servicio = 'prueba' "
        "WHERE id = 'HAB-14'"
    )
    conexion.execute(
        "INSERT INTO reservas (id, empresa_id, habitacion_id, inicio, fin, huesped_nombre, "
        "tarifa_noche_aceptada_clp, estado) VALUES "
        "('RSV-REG-1', 'EMP-HERENCIA-001', 'HAB-01', '2026-12-24', '2026-12-27', 'Prueba', 55000, 'confirmada')"
    )


def _todas(conexion):
    return [f[0] for f in conexion.execute("SELECT id FROM habitaciones ORDER BY id").fetchall()]


class RegresionPreciosMigracion1ATest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nombre_base = f"plataforma_1a_reg_{os.getpid()}"
        cls.url_admin = conninfo.make_conninfo(URL_TEST, dbname="postgres")
        try:
            with psycopg.connect(cls.url_admin, autocommit=True) as admin:
                admin.execute(f'DROP DATABASE IF EXISTS "{cls.nombre_base}"')
                admin.execute(f'CREATE DATABASE "{cls.nombre_base}"')
        except psycopg.Error as error:  # pragma: no cover - entorno sin permiso
            raise unittest.SkipTest(f"no se puede crear una base temporal: {error}")
        cls.url = conninfo.make_conninfo(URL_TEST, dbname=cls.nombre_base)

    @classmethod
    def tearDownClass(cls):
        with psycopg.connect(cls.url_admin, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{cls.nombre_base}" WITH (FORCE)')

    def test_precios_identicos_antes_y_despues_de_0021(self):
        # --- 1. Esquema de hoy (0001–0020) + inventario real -------------
        anteriores = Path(tempfile.mkdtemp())
        try:
            for ruta in sorted(migracion.DIRECTORIO_MIGRACIONES.glob("*.sql")):
                if ruta.stem < MIGRACION_1A:
                    shutil.copy(ruta, anteriores / ruta.name)
            aplicadas = migracion.aplicar_migraciones(self.url, anteriores)
        finally:
            shutil.rmtree(anteriores)
        self.assertNotIn(MIGRACION_1A, aplicadas)
        with psycopg.connect(self.url) as conexion:
            _sembrar(conexion)
            conexion.commit()

        # --- 2. Cotizaciones con la regla anterior ------------------------
        with psycopg.connect(self.url) as conexion:
            ids = _todas(conexion)
            antes_noche = {
                (hid, noche): legado.tarifa_vigente(conexion, hid, noche)
                for hid in ids for noche in _noches(DESDE, HASTA)
            }
            antes_grilla = legado.tarifas_por_noche(conexion, DESDE, HASTA)
            antes_oferta = {c: legado.oferta(conexion, *c, AHORA) for c in _combinaciones()}
            antes_estadias = {
                (hid, llegada, salida): (
                    legado.primera_noche_sin_tarifa(conexion, hid, llegada, salida),
                    legado.precio_noches(conexion, hid, llegada, salida)
                    if legado.primera_noche_sin_tarifa(conexion, hid, llegada, salida) is None else None,
                )
                for hid in ids
                for llegada, salida, personas in _combinaciones() if personas == 1
            }
            conteos_antes = {
                t: conexion.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("habitaciones", "tarifas", "reservas", "cargos")
            }
        self.assertTrue(all(antes_noche[(h, n)] for h in IDS_REALES for n in _noches(DESDE, HASTA)
                            if (h, n) in antes_noche), "las 17 reales tienen precio todas las noches")

        # --- 3. Migración 0021 (dos veces: idempotente) -------------------
        nuevas = migracion.aplicar_migraciones(self.url)
        self.assertEqual(nuevas[0], MIGRACION_1A)
        sql_1a = (migracion.DIRECTORIO_MIGRACIONES / f"{MIGRACION_1A}.sql").read_text(encoding="utf-8")
        with psycopg.connect(self.url) as conexion:
            conexion.execute(sql_1a)
            conexion.commit()

        def comparar(etiqueta):
            with psycopg.connect(self.url) as conexion:
                despues_rango = precios.precios_del_rango(conexion, DESDE, HASTA)
                despues_noche = {
                    clave: (despues_rango[clave].precio_clp if clave in despues_rango else None)
                    for clave in antes_noche
                }
                self.assertEqual(despues_noche, antes_noche, f"{etiqueta}: precio por noche")
                self.assertEqual(reservas_db.tarifas_por_noche(conexion, DESDE, HASTA), antes_grilla,
                                 f"{etiqueta}: rejilla de ocupación")
                for combinacion, esperado in antes_oferta.items():
                    self.assertEqual(reservas_db.oferta(conexion, *combinacion, AHORA), esperado,
                                     f"{etiqueta}: oferta {combinacion}")
                for (hid, llegada, salida), (sin_tarifa, precio) in antes_estadias.items():
                    self.assertEqual(reservas_db.primera_noche_sin_tarifa(conexion, hid, llegada, salida),
                                     sin_tarifa, f"{etiqueta}: sin tarifa {hid} {llegada}")
                    if precio is not None:
                        self.assertEqual(reservas_db.precio_noches(conexion, hid, llegada, salida), precio,
                                         f"{etiqueta}: estadía {hid} {llegada}→{salida}")
                for hid in ids:
                    self.assertEqual(reservas_db.tarifa_vigente(conexion, hid, AHORA.date()),
                                     antes_noche[(hid, AHORA.date())], f"{etiqueta}: hoy {hid}")

        comparar("tras 0021")

        # --- 4. Estado de la migración ------------------------------------
        with psycopg.connect(self.url) as conexion:
            conteos_despues = {
                t: conexion.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("habitaciones", "tarifas", "reservas", "cargos")
            }
            self.assertEqual(conteos_despues, conteos_antes, "sin pérdida ni alta de datos")
            tipos = dict(conexion.execute(
                "SELECT id, nombre FROM tipos_habitacion ORDER BY id").fetchall())
            self.assertEqual(tipos, {
                "doble": "Doble", "matrimonial": "Matrimonial", "matrimonial_mas_1": "Matrimonial +1",
                "single": "Single", "suite_prueba": "Suite Prueba", "triple": "Triple",
            })
            self.assertEqual(conexion.execute(
                "SELECT count(*) FROM tipos_habitacion WHERE precio_base_clp IS NOT NULL").fetchone()[0], 0)
            reales = conexion.execute(
                "SELECT h.id, h.tipo, h.en_inventario, t.id IS NOT NULL FROM habitaciones h "
                "LEFT JOIN tipos_habitacion t ON t.id = h.tipo WHERE h.id = ANY(%s) ORDER BY h.id",
                (IDS_REALES,),
            ).fetchall()
            self.assertEqual(len(reales), 17)
            self.assertTrue(all(r[2] and r[3] for r in reales))
            por_tipo = {}
            for r in reales:
                por_tipo[r[1]] = por_tipo.get(r[1], 0) + 1
            self.assertEqual(por_tipo, {"matrimonial": 9, "doble": 4, "matrimonial_mas_1": 2,
                                        "single": 1, "triple": 1})
            self.assertFalse(conexion.execute(
                "SELECT bool_or(en_inventario) FROM habitaciones WHERE id LIKE 'HAB-SINT-%'").fetchone()[0])

            # --- 5. Fijar el precio base referencial no mueve a las 17 -----
            for tipo, monto in (("single", 47000), ("doble", 55000), ("matrimonial", 55000),
                                ("matrimonial_mas_1", 55000), ("triple", 65000)):
                conexion.execute("UPDATE tipos_habitacion SET precio_base_clp = %s WHERE id = %s", (monto, tipo))
            conexion.commit()
            reales_con_base = precios.precios_del_rango(conexion, DESDE, HASTA, IDS_REALES)
            self.assertEqual(
                {k: v.precio_clp for k, v in reales_con_base.items()},
                {k: v for k, v in antes_noche.items() if k[0] in IDS_REALES},
                "con precio base en los tipos, HAB-01..17 siguen con su precio",
            )
            self.assertTrue(all(v.origen.startswith("tarifa:") for v in reales_con_base.values()))
            # Las unidades ajenas sin tarifa sí heredan ahora la base del tipo.
            herencia = precios.precio_noche(conexion, "HAB-SINT-101", date(2026, 12, 1))
            self.assertEqual((herencia.precio_clp, herencia.origen), (55000, "tipo:doble"))
            # Se deja como estaba para no contaminar la comparación final.
            conexion.execute("UPDATE tipos_habitacion SET precio_base_clp = NULL")
            conexion.commit()

        comparar("tras reiniciar precios base")


if __name__ == "__main__":
    unittest.main()
