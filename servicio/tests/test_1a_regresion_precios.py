"""Entregas 1A y 1A.2 — regresión de precios antes de 0021 / después de 0022/0023.

Prueba que ni la migración a tipos de habitación (0021) ni la unificación de
la fuente de precio (0022: tarifas por habitación → precio base del tipo,
precio propio y excepciones por fecha) cambian NINGÚN precio efectivo:

1. Crea una base temporal, aplica solo 0001–0020 (el esquema de producción
   antes de 1A) y siembra el inventario real tal como lo hacía el arranque
   en 27f9ccf (HAB-01..17 con el lote documental y las tarifas fijas del
   dueño 2020-01-01→2099-12-31), más variaciones que ejercitan la regla de
   vigencia y la conversión (empates por recencia, rangos solapados, una
   habitación con otro precio dominante, una temporada común a todo un tipo,
   unidades sin tarifa o con tarifa parcial, mantenimiento, fuera de
   servicio y una reserva).
2. Cotiza con el oráculo congelado de 27f9ccf: precio de cada habitación y
   noche del 2026-11-10 al 2027-04-10, la rejilla de ocupación, la oferta
   (llegadas cada 4 días × 1/2/3/7 noches × 1/2/3 personas), las estadías y
   la cotización pública de /reservar (canal_publico.disponibilidad) para
   llegadas desde hoy.
3. Aplica 0021, 0022 y 0023 (y vuelve a ejecutarlas: idempotentes) y repite con
   el código nuevo. Todo debe ser idéntico. Variante: un precio base fijado
   en el mantenedor entre 1A y 1A.2 (posible en producción) también se
   conserva.
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

from servicio import canal_publico, inventario_documental, migracion, precios
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
MIGRACION_1A2 = "0022_precio_unico"
MIGRACION_1A3 = "0023_politicas_hotel"


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
    insertadas = legado.aplicar_tarifas_fijas_referenciales(conexion, inventario_documental.cargar_lote())
    assert insertadas == 17, insertadas

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
    # Una habitación con otro precio desde 2026 (dominante distinto del tipo).
    tarifa("HAB-05", date(2026, 1, 1), date(2099, 12, 31), 58000)
    # Temporada común a TODAS las habitaciones de un tipo (matrimonial +1).
    for hid in conexion.execute(
        "SELECT id FROM habitaciones WHERE tipo = 'matrimonial_mas_1' ORDER BY id"
    ).fetchall():
        tarifa(hid[0], date(2026, 12, 24), date(2027, 1, 2), 75000)
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



def _esencia_precios(cuerpo):
    """Compara solo identidad de precio (1A.2). La 1A.3 añade desglose IVA y política editable."""
    keys = ("habitacion_id", "tipo", "capacidad", "tarifa_noche_clp", "total_clp")
    return {
        "oferta": [{k: item[k] for k in keys} for item in cuerpo["oferta"]],
        "emitida_en": cuerpo["emitida_en"],
        "vigencia_minutos": cuerpo["vigencia_minutos"],
        "capacidad_maxima_habitacion": cuerpo["capacidad_maxima_habitacion"],
    }


class RegresionPreciosMigraciones1ATest(unittest.TestCase):
    def setUp(self):
        # Una base nueva por prueba: cada una parte del esquema anterior a 1A.
        self.nombre_base = f"plataforma_1a_reg_{os.getpid()}"
        self.url_admin = conninfo.make_conninfo(URL_TEST, dbname="postgres")
        try:
            with psycopg.connect(self.url_admin, autocommit=True) as admin:
                admin.execute(f'DROP DATABASE IF EXISTS "{self.nombre_base}" WITH (FORCE)')
                admin.execute(f'CREATE DATABASE "{self.nombre_base}"')
        except psycopg.Error as error:  # pragma: no cover - entorno sin permiso
            raise unittest.SkipTest(f"no se puede crear una base temporal: {error}")
        self.url = conninfo.make_conninfo(URL_TEST, dbname=self.nombre_base)

    def tearDown(self):
        with psycopg.connect(self.url_admin, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{self.nombre_base}" WITH (FORCE)')

    def _esquema_previo_e_inventario(self):
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

    def _cotizar_legado(self):
        hoy = date.today()
        with psycopg.connect(self.url) as conexion:
            ids = _todas(conexion)
            r = {"ids": ids}
            r["noche"] = {
                (hid, noche): legado.tarifa_vigente(conexion, hid, noche)
                for hid in ids for noche in _noches(DESDE, HASTA)
            }
            r["grilla"] = legado.tarifas_por_noche(conexion, DESDE, HASTA)
            r["oferta"] = {c: legado.oferta(conexion, *c, AHORA) for c in _combinaciones()}
            r["publica"] = {c: legado.oferta(conexion, *c, AHORA) for c in _combinaciones() if c[0] >= hoy}
            r["estadias"] = {}
            for hid in ids:
                for llegada, salida, personas in _combinaciones():
                    if personas != 1:
                        continue
                    sin = legado.primera_noche_sin_tarifa(conexion, hid, llegada, salida)
                    r["estadias"][(hid, llegada, salida)] = (
                        sin, legado.precio_noches(conexion, hid, llegada, salida) if sin is None else None
                    )
            r["conteos"] = {
                t: conexion.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("habitaciones", "tarifas", "reservas", "cargos")
            }
        return r

    def _migrar_hasta_0022(self, entre_1a_y_1a2=None):
        # 0021 sola (estado de producción con 1A desplegado).
        solo_1a = Path(tempfile.mkdtemp())
        try:
            for ruta in sorted(migracion.DIRECTORIO_MIGRACIONES.glob("*.sql")):
                if ruta.stem <= MIGRACION_1A:
                    shutil.copy(ruta, solo_1a / ruta.name)
            self.assertEqual(migracion.aplicar_migraciones(self.url, solo_1a), [MIGRACION_1A])
        finally:
            shutil.rmtree(solo_1a)
        if entre_1a_y_1a2:
            with psycopg.connect(self.url) as conexion:
                entre_1a_y_1a2(conexion)
                conexion.commit()
        self.assertEqual(migracion.aplicar_migraciones(self.url), [MIGRACION_1A2, MIGRACION_1A3])
        # Repetir 0021–0023 a mano: idempotentes, sin cambios de precio.
        with psycopg.connect(self.url) as conexion:
            foto = self._foto_precios(conexion)
            for nombre in (MIGRACION_1A, MIGRACION_1A2, MIGRACION_1A3):
                conexion.execute((migracion.DIRECTORIO_MIGRACIONES / f"{nombre}.sql").read_text(encoding="utf-8"))
            conexion.commit()
            self.assertEqual(self._foto_precios(conexion), foto, "0021/0022/0023 repetidas no cambian nada")

    @staticmethod
    def _foto_precios(conexion):
        return (
            conexion.execute("SELECT id, precio_base_clp FROM tipos_habitacion ORDER BY id").fetchall(),
            conexion.execute("SELECT id, precio_propio_clp FROM habitaciones ORDER BY id").fetchall(),
            conexion.execute(
                "SELECT tipo_id, habitacion_id, fecha_desde, fecha_hasta, precio_clp, activa "
                "FROM excepciones_precio ORDER BY id"
            ).fetchall(),
            conexion.execute("SELECT count(*), count(archivada_en) FROM tarifas").fetchone(),
        )

    def _comparar(self, etiqueta, antes, noche_esperada=None):
        noche_esperada = noche_esperada or antes["noche"]
        grilla_esperada = {k: v for k, v in noche_esperada.items() if v is not None}
        with psycopg.connect(self.url) as conexion:
            rango = precios.precios_del_rango(conexion, DESDE, HASTA)
            self.assertEqual(
                {clave: (rango[clave].precio_clp if clave in rango else None) for clave in noche_esperada},
                noche_esperada, f"{etiqueta}: precio por noche",
            )
            self.assertEqual(precios.precio_por_noche(conexion, DESDE, HASTA), grilla_esperada,
                             f"{etiqueta}: rejilla de ocupación")
            if noche_esperada is antes["noche"]:
                for combinacion, esperado in antes["oferta"].items():
                    self.assertEqual(_esencia_precios(reservas_db.oferta(conexion, *combinacion, AHORA)),
                                     _esencia_precios(esperado), f"{etiqueta}: oferta {combinacion}")
                for combinacion, esperado in antes["publica"].items():
                    self.assertEqual(_esencia_precios(canal_publico.disponibilidad(conexion, *combinacion, AHORA)),
                                     _esencia_precios(esperado), f"{etiqueta}: /reservar {combinacion}")
                for (hid, llegada, salida), (sin_tarifa, precio) in antes["estadias"].items():
                    cotizacion = precios.cotizar(conexion, hid, llegada, salida)
                    self.assertEqual(cotizacion.sin_tarifa, sin_tarifa, f"{etiqueta}: sin tarifa {hid} {llegada}")
                    if precio is not None:
                        self.assertEqual((cotizacion.tarifa_primera, cotizacion.total), precio,
                                         f"{etiqueta}: estadía {hid} {llegada}→{salida}")

    def test_precios_identicos_antes_de_0021_y_despues_de_0022(self):
        self._esquema_previo_e_inventario()
        antes = self._cotizar_legado()
        self.assertTrue(all(antes["noche"][(h, n)] for h in IDS_REALES for n in _noches(DESDE, HASTA)),
                        "las 17 reales tienen precio todas las noches")
        self.assertGreater(len(antes["publica"]), 0)

        self._migrar_hasta_0022()
        self._comparar("tras 0022", antes)

        with psycopg.connect(self.url) as conexion:
            conteos = {
                t: conexion.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("habitaciones", "tarifas", "reservas", "cargos")
            }
            self.assertEqual(conteos, antes["conteos"], "sin pérdida ni alta de datos")
            self.assertEqual(conexion.execute("SELECT count(*) FROM tarifas WHERE archivada_en IS NULL").fetchone()[0],
                             0, "todas las tarifas heredadas quedan archivadas")
            bases = dict(conexion.execute("SELECT id, precio_base_clp FROM tipos_habitacion").fetchall())
            self.assertEqual(bases, {"single": 47000, "doble": 55000, "matrimonial": 55000,
                                     "matrimonial_mas_1": 55000, "triple": 65000, "suite_prueba": None})
            propios = dict(conexion.execute(
                "SELECT id, precio_propio_clp FROM habitaciones WHERE precio_propio_clp IS NOT NULL").fetchall())
            self.assertEqual(propios, {"HAB-05": 58000, "HAB-SINT-102": 40000})
            # Las 17 reales: precio de hoy = base del tipo (salvo HAB-05, propio).
            reales = precios.precios_del_rango(conexion, date(2027, 3, 1), date(2027, 3, 2), IDS_REALES)
            self.assertEqual({k[0]: v.origen.split(":")[0] for k, v in reales.items()},
                             {h: ("habitacion" if h == "HAB-05" else "tipo") for h in IDS_REALES})
            # La temporada común a matrimonial +1 queda como UNA excepción del tipo.
            del_tipo = conexion.execute(
                "SELECT tipo_id, fecha_desde, fecha_hasta, precio_clp FROM excepciones_precio "
                "WHERE tipo_id IS NOT NULL").fetchall()
            self.assertIn(("matrimonial_mas_1", date(2026, 12, 24), date(2027, 1, 2), 75000), del_tipo)
            resumen = conexion.execute(
                "SELECT resultado FROM auditoria WHERE actor = 'migracion_0022'").fetchall()
            self.assertEqual(len(resumen), 1)
            print("\n" + resumen[0][0])

            # Una sola fuente: cambiar el base del tipo mueve a todas las que heredan.
            conexion.execute("UPDATE tipos_habitacion SET precio_base_clp = 60000 WHERE id = 'matrimonial'")
            movidas = precios.precios_del_rango(conexion, date(2027, 3, 1), date(2027, 3, 2), IDS_REALES)
            heredan = {f[0] for f in conexion.execute(
                "SELECT id FROM habitaciones WHERE tipo = 'matrimonial' AND precio_propio_clp IS NULL "
                "AND id = ANY(%s)", (IDS_REALES,)).fetchall()}
            self.assertGreaterEqual(len(heredan), 8)
            self.assertEqual({h for (h, _), p in movidas.items() if p.precio_clp == 60000}, heredan)
            conexion.rollback()

    def test_precio_base_fijado_entre_1a_y_1a2_se_conserva(self):
        self._esquema_previo_e_inventario()
        antes = self._cotizar_legado()

        def base_en_el_mantenedor(conexion):
            # Con 1A desplegado, la administración fijó 50.000 al tipo doble:
            # las unidades doble sin tarifa ya se vendían a 50.000.
            conexion.execute("UPDATE tipos_habitacion SET precio_base_clp = 50000 WHERE id = 'doble'")

        self._migrar_hasta_0022(base_en_el_mantenedor)
        with psycopg.connect(self.url) as conexion:
            dobles = {f[0] for f in conexion.execute("SELECT id FROM habitaciones WHERE tipo = 'doble'").fetchall()}
        esperado = {
            (hid, noche): (50000 if precio is None and hid in dobles else precio)
            for (hid, noche), precio in antes["noche"].items()
        }
        self.assertNotEqual(esperado, antes["noche"])
        self._comparar("base fijada entre 1A y 1A.2", antes, esperado)


if __name__ == "__main__":
    unittest.main()
