"""Siembra documental: 17 unidades operativas (disponible) + tarifas fijas referenciales."""
import unittest
from pathlib import Path

from servicio.inventario_documental import (
    PRECIO_FIJO_POR_TIPO,
    aplicar_tarifas_fijas_referenciales,
    cargar_lote,
    es_id_inventario_real,
    precio_fijo_referencial,
    ruta_lote,
    sembrar_inventario_documental,
)


class InventarioDocumentalLoteTest(unittest.TestCase):
    def test_lote_tiene_17_habitaciones_y_tarifas_fijas_activas(self):
        lote = cargar_lote()
        self.assertEqual(lote["conteos"]["habitaciones"], 17)
        self.assertEqual(lote["conteos"]["requieren_verificacion_capacidad"], 2)
        self.assertTrue(ruta_lote().is_file())
        self.assertEqual(lote["decision_precios_fijos"]["single_clp"], 47000)
        self.assertEqual(lote["decision_precios_fijos"]["doble_o_matrimonial_clp"], 55000)
        self.assertEqual(lote["decision_precios_fijos"]["triple_clp"], 65000)
        for hab in lote["habitaciones"]:
            self.assertEqual(hab["estado_operativo_carga"], "fuera_de_servicio")
            self.assertGreaterEqual(hab["capacidad_propuesta"], 1)
            tarifa = hab.get("tarifa_propuesta_por_tipo") or {}
            self.assertTrue(bool(tarifa.get("publicar_tarifa_activa")))
            self.assertEqual(
                tarifa["monto_clp"], precio_fijo_referencial(hab["tipo_salman"])
            )
            self.assertTrue(hab["en_oferta_publica"])
        for tarifa in lote["tarifas_documentales"]:
            if tarifa["tarifa_id_documental"] == "TAR-07":
                self.assertFalse(tarifa["publicar_tarifa_activa"])
            else:
                self.assertTrue(tarifa["publicar_tarifa_activa"])
                self.assertTrue(tarifa["aprobada_2027"])

    def test_matrimonial_mas_1_requiere_verificacion(self):
        lote = cargar_lote()
        marcadas = [h for h in lote["habitaciones"] if h["capacidad_requiere_verificacion"]]
        self.assertEqual({h["habitacion_id"] for h in marcadas}, {"HAB-08", "HAB-16"})
        self.assertTrue(all(h["tipo_salman"] == "matrimonial_mas_1" for h in marcadas))


class InventarioDocumentalSiembraTest(unittest.TestCase):
    """Siembra contra una conexión falsa mínima (lista de SQL)."""

    def test_sembrar_inserta_disponible_e_idempotente(self):
        sqls = []
        existentes = set()

        class FakeConn:
            def execute(self, sql, params=None):
                sqls.append((sql, params))

                class R:
                    def fetchone(self_inner):
                        if "SELECT 1 FROM habitaciones" in sql:
                            return (1,) if params and params[0] in existentes else None
                        return None

                    def fetchall(self_inner):
                        if "RETURNING id" in sql.upper():
                            return []
                        if "SELECT id FROM habitaciones" in sql:
                            return []
                        return []

                if sql.strip().upper().startswith("INSERT"):
                    existentes.add(params[0])
                return R()

        lote = {
            "paquete_fecha": "2026-11-11",
            "habitaciones": [
                {
                    "habitacion_id": "HAB-01",
                    "tipo_salman": "matrimonial",
                    "capacidad_propuesta": 2,
                }
            ],
        }
        conn = FakeConn()
        r1 = sembrar_inventario_documental(conn, lote=lote, retirar_sinteticas=False)
        self.assertEqual(r1["creadas"], 1)
        self.assertTrue(any("disponible" in (s[0] or "") for s in sqls if s[0]))
        r2 = sembrar_inventario_documental(conn, lote=lote, retirar_sinteticas=False)
        self.assertEqual(r2["creadas"], 0)
        self.assertEqual(r2["omitidas"], 1)

    def test_solo_hab_01_a_17_son_inventario_real(self):
        self.assertTrue(es_id_inventario_real("HAB-01"))
        self.assertTrue(es_id_inventario_real("HAB-17"))
        self.assertFalse(es_id_inventario_real("HAB-18"))
        self.assertFalse(es_id_inventario_real("HAB-101"))
        self.assertFalse(es_id_inventario_real("HAB-SINT-101"))

    def test_precios_fijos_por_tipo(self):
        self.assertEqual(PRECIO_FIJO_POR_TIPO["single"], 47000)
        self.assertEqual(precio_fijo_referencial("doble"), 55000)
        self.assertEqual(precio_fijo_referencial("matrimonial_mas_1"), 55000)
        self.assertEqual(precio_fijo_referencial("triple"), 65000)


class InventarioDocumentalTarifasTest(unittest.TestCase):
    def test_aplicar_tarifas_inserta_segun_tipo(self):
        inserts = []

        class FakeConn:
            def execute(self, sql, params=None):
                class R:
                    def fetchone(self_inner):
                        if "FROM habitaciones" in sql and "SELECT 1" in sql:
                            return (1,)
                        if "FROM tarifas" in sql and "SELECT 1" in sql:
                            return None
                        return None

                    def fetchall(self_inner):
                        return []

                # insertar_tarifa: 5 params (id, hab, desde, hasta, precio)
                if params is not None and len(params) == 5 and "tarifas" in (sql or "").lower():
                    inserts.append(
                        {
                            "habitacion_id": params[1],
                            "fecha_desde": str(params[2]),
                            "fecha_hasta": str(params[3]),
                            "tarifa_noche_clp": int(params[4]),
                        }
                    )
                return R()

        lote = {
            "habitaciones": [
                {
                    "habitacion_id": "HAB-07",
                    "tipo_salman": "single",
                    "capacidad_propuesta": 1,
                    "tarifa_propuesta_por_tipo": {
                        "publicar_tarifa_activa": True,
                        "monto_clp": 47000,
                    },
                },
                {
                    "habitacion_id": "HAB-03",
                    "tipo_salman": "doble",
                    "capacidad_propuesta": 2,
                    "tarifa_propuesta_por_tipo": {
                        "publicar_tarifa_activa": True,
                        "monto_clp": 55000,
                    },
                },
                {
                    "habitacion_id": "HAB-17",
                    "tipo_salman": "triple",
                    "capacidad_propuesta": 3,
                    "tarifa_propuesta_por_tipo": {
                        "publicar_tarifa_activa": True,
                        "monto_clp": 65000,
                    },
                },
            ]
        }
        r1 = aplicar_tarifas_fijas_referenciales(FakeConn(), lote=lote)
        self.assertEqual(r1["insertadas"], 3)
        by_id = {i["habitacion_id"]: i["tarifa_noche_clp"] for i in inserts}
        self.assertEqual(by_id, {"HAB-07": 47000, "HAB-03": 55000, "HAB-17": 65000})
        self.assertTrue(all(i["fecha_desde"] == "2020-01-01" for i in inserts))
        self.assertTrue(all(i["fecha_hasta"] == "2099-12-31" for i in inserts))


if __name__ == "__main__":
    unittest.main()
