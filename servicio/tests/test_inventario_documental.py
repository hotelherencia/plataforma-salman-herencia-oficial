"""Siembra documental: 17 unidades fuera de servicio, sin tarifas activas."""
import unittest
from pathlib import Path

from servicio.inventario_documental import cargar_lote, ruta_lote, sembrar_inventario_documental


class InventarioDocumentalLoteTest(unittest.TestCase):
    def test_lote_tiene_17_habitaciones_y_ninguna_tarifa_activa(self):
        lote = cargar_lote()
        self.assertEqual(lote["conteos"]["habitaciones"], 17)
        self.assertEqual(lote["conteos"]["requieren_verificacion_capacidad"], 2)
        self.assertTrue(ruta_lote().is_file())
        for hab in lote["habitaciones"]:
            self.assertEqual(hab["estado_operativo_carga"], "fuera_de_servicio")
            self.assertFalse(hab["en_oferta_publica"])
            self.assertGreaterEqual(hab["capacidad_propuesta"], 1)
            tarifa = hab.get("tarifa_propuesta_por_tipo") or {}
            self.assertFalse(bool(tarifa.get("publicar_tarifa_activa")))
        for tarifa in lote["tarifas_documentales"]:
            self.assertFalse(tarifa["publicar_tarifa_activa"])
            self.assertFalse(tarifa["aprobada_2027"])

    def test_matrimonial_mas_1_requiere_verificacion(self):
        lote = cargar_lote()
        marcadas = [h for h in lote["habitaciones"] if h["capacidad_requiere_verificacion"]]
        self.assertEqual({h["habitacion_id"] for h in marcadas}, {"HAB-08", "HAB-16"})
        self.assertTrue(all(h["tipo_salman"] == "matrimonial_mas_1" for h in marcadas))


class InventarioDocumentalSiembraTest(unittest.TestCase):
    """Siembra contra una conexión falsa mínima (lista de SQL)."""

    def test_sembrar_inserta_fuera_de_servicio_e_idempotente(self):
        sqls = []
        existentes = set()

        class FakeConn:
            def execute(self, sql, params=None):
                sqls.append((sql, params))
                class R:
                    def fetchone(self_inner):
                        if "SELECT 1 FROM habitaciones" in sql:
                            return (1,) if params and params[0] in existentes else None
                        if "SELECT estado_operativo" in sql:
                            return ("disponible",) if params and params[0] in {"HAB-SINT-101", "HAB-SINT-102", "HAB-SINT-103"} else None
                        return None
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
                    "motivo_fuera_de_servicio": "prueba",
                }
            ],
        }
        conn = FakeConn()
        r1 = sembrar_inventario_documental(conn, lote=lote, retirar_sinteticas=True)
        self.assertEqual(r1["creadas"], 1)
        self.assertEqual(r1["sinteticas_retiradas"], 3)
        r2 = sembrar_inventario_documental(conn, lote=lote, retirar_sinteticas=False)
        self.assertEqual(r2["creadas"], 0)
        self.assertEqual(r2["omitidas"], 1)


if __name__ == "__main__":
    unittest.main()
