"""Siembra documental: 17 unidades operativas (disponible) + precio base referencial por tipo."""
import unittest
from pathlib import Path

from servicio.inventario_documental import (
    PRECIO_FIJO_POR_TIPO,
    aplicar_precios_base_referenciales,
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


class InventarioDocumentalPreciosBaseTest(unittest.TestCase):
    """1A.2: la referencial del dueño va al precio base del TIPO (fuente
    única), no a tarifas por habitación."""

    def _lote(self, *habitaciones):
        return {"habitaciones": [
            {"habitacion_id": hid, "tipo_salman": tipo_salman, "capacidad_propuesta": 2,
             "tarifa_propuesta_por_tipo": {"publicar_tarifa_activa": True, "monto_clp": 1}}
            for hid, tipo_salman in habitaciones
        ]}

    def _fake(self, tipos_db, bases):
        updates = []

        class FakeConn:
            def execute(self, sql, params=None):
                class R:
                    def fetchone(self_inner):
                        if "SELECT tipo FROM habitaciones" in sql:
                            return (tipos_db[params[0]],) if params[0] in tipos_db else None
                        if "SELECT precio_base_clp FROM tipos_habitacion" in sql:
                            return (bases.get(params[0]),)
                        return None

                if sql.startswith("UPDATE tipos_habitacion"):
                    updates.append((params[1], params[0]))
                    bases[params[1]] = params[0]
                return R()

        return FakeConn(), updates

    def test_precio_base_por_tipo_mayoritario(self):
        conn, updates = self._fake(
            {"HAB-07": "single", "HAB-03": "doble", "HAB-04": "doble", "HAB-17": "triple"}, {}
        )
        lote = self._lote(("HAB-07", "single"), ("HAB-03", "doble"), ("HAB-04", "doble"), ("HAB-17", "triple"))
        r = aplicar_precios_base_referenciales(conn, lote=lote)
        self.assertEqual(r["tipos_actualizados"], {"doble": 55000, "single": 47000, "triple": 65000})
        self.assertEqual(r["errores"], [])
        self.assertEqual(sorted(updates), [("doble", 55000), ("single", 47000), ("triple", 65000)])

    def test_arranque_no_pisa_el_precio_del_mantenedor(self):
        conn, updates = self._fake({"HAB-07": "single", "HAB-03": "doble"}, {"single": 50000})
        r = aplicar_precios_base_referenciales(
            conn, lote=self._lote(("HAB-07", "single"), ("HAB-03", "doble")), solo_sin_precio=True
        )
        self.assertEqual(r["tipos_actualizados"], {"doble": 55000})
        self.assertEqual(updates, [("doble", 55000)])
        # Idempotente: una segunda pasada no cambia nada.
        r2 = aplicar_precios_base_referenciales(conn, lote=self._lote(("HAB-03", "doble")))
        self.assertEqual(r2["tipos_actualizados"], {})


if __name__ == "__main__":
    unittest.main()
