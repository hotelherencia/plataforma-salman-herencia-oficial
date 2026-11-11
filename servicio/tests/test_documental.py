"""Paquete documental: JSON embebido + siembra/consulta sin KPI."""
import json
import unittest
from pathlib import Path

from servicio import documental


class DocumentalPaqueteTest(unittest.TestCase):
    def test_paquete_incluye_historico_completo(self):
        ruta = documental.ruta_paquete()
        self.assertTrue(ruta.is_file(), ruta)
        paquete = documental.cargar_json_paquete()
        datos = paquete["datos"]
        self.assertEqual(len(datos["habitaciones"]), 17)
        self.assertEqual(len(datos["tarifas_declaradas"]), 5)
        self.assertEqual(len(datos["ocupacion_reportada"]), 204)
        self.assertEqual(len(datos["control_ocupacion"]), 12)
        self.assertEqual(len(datos["condiciones_habitacion"]), 442)
        # nov/dic: 34 celdas sin valor
        vacias = [
            r for r in datos["ocupacion_reportada"]
            if r.get("periodo") in ("2026-11", "2026-12") and not str(r.get("valor_reportado") or "").strip()
        ]
        self.assertEqual(len(vacias), 34)
        for t in datos["tarifas_declaradas"]:
            self.assertIn(str(t.get("aprobada_2027")).lower(), ("false", "0", ""))


class DocumentalSiembraTest(unittest.TestCase):
    def test_sembrar_idempotente_y_conteos(self):
        sqls = []
        paquetes = set()

        class Fake:
            def execute(self, sql, params=None):
                sqls.append((sql.strip().split()[0].upper(), params))
                class R:
                    def fetchone(self_inner):
                        if "SELECT 1 FROM doc_paquete" in sql:
                            return (1,) if params and params[0] in paquetes else None
                        return (0,)
                    def fetchall(self_inner):
                        return []
                if sql.strip().upper().startswith("INSERT INTO DOC_PAQUETE"):
                    paquetes.add(params[0])
                return R()

        mini = {
            "id": "DOC-PKG-TEST",
            "fecha": "2026-11-11",
            "sha256_zip": "abc",
            "clasificacion": "GENERAL_DEPURADO",
            "timezone": "America/Santiago",
            "datos": {
                "habitaciones": [{
                    "habitacion_id": "HAB-01", "numero": "1", "tipo_declarado": "Matrimonial",
                    "tipo_salman": "matrimonial", "capacidad_propuesta": 2,
                    "capacidad_requiere_verificacion": False, "fuente": "x",
                    "estado_evidencia": "CONSTATADO_DOCUMENTAL", "verificado_en_terreno": False,
                }],
                "tarifas_declaradas": [{
                    "tarifa_id": "TAR-05", "tipo_comercial": "Matrimonial", "monto_clp": "55000",
                    "moneda": "CLP", "iva_incluido_declarado": "true", "canal": "DIRECTO",
                    "vigente_desde": "", "vigente_hasta": "", "aprobada_2027": "false",
                }],
                "ocupacion_reportada": [{
                    "registro_id": "OCU-1", "habitacion_id": "HAB-01", "periodo": "2026-01",
                    "valor_reportado": "22", "unidad_confirmada": "", "interpretacion_propuesta": "x",
                    "dias_calendario": "31", "estado_valor": "CONSTATADO_DOCUMENTAL", "fuente": "x",
                }],
                "control_ocupacion": [{
                    "periodo": "2026-01", "suma_reportada": "355", "porcentaje_guardado_fuente": "0.6",
                    "porcentaje_calendario_hipotetico": "0.6", "denominador_hipotetico": "527",
                    "supuesto": "hipotesis", "fuente": "x",
                }],
                "proveedores": [{"proveedor_id": "PROV-001", "nombre_comercial_declarado": "Ganga"}],
            },
        }
        r1 = documental.sembrar_paquete_documental(Fake(), mini)
        self.assertFalse(r1["ya_cargado"])
        self.assertEqual(r1["habitaciones"], 1)
        self.assertEqual(r1["tarifas"], 1)
        self.assertEqual(r1["ocupacion_reportada"], 1)
        r2 = documental.sembrar_paquete_documental(Fake(), mini)
        self.assertTrue(r2["ya_cargado"])


if __name__ == "__main__":
    unittest.main()
