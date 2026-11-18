"""#354 (2026-11-18): leads deduplicados por contacto y ventana de «nuevo»."""
import unittest

import psycopg

from servicio.leads import normalizar_telefono
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.test_leads import LeadsBaseTest, URL_TEST


class LeadsContactosTest(LeadsBaseTest):
    def setUp(self):
        super().setUp()
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("TRUNCATE contactos CASCADE")
            conexion.commit()

    def bandeja(self, **q):
        r = self.cliente.get("/hotel/leads", params=q)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def test_mismo_correo_o_telefono_queda_bajo_un_contacto(self):
        a = self.crear_lead(correo="Ana@Example.test", telefono="+56 9 1111 1111")
        b = self.crear_lead(correo="ana@example.test", telefono="+56 9 2222 2222", mensaje="otra vez")
        c = self.crear_lead(correo="otro-correo@example.test", telefono="9 1111 1111", mensaje="por teléfono")
        d = self.crear_lead(correo="distinta@example.test", telefono="+56 9 3333 3333", nombre="Otra Persona")
        leads = {l["id"]: l for l in self.bandeja()["leads"]}
        self.assertEqual(len({leads[x]["contacto_id"] for x in (a, b, c)}), 1)
        self.assertNotEqual(leads[a]["contacto_id"], leads[d]["contacto_id"])
        self.assertEqual(leads[a]["leads_del_contacto"], 3)
        contactos = self.cliente.get("/hotel/leads/contactos").json()["contactos"]
        self.assertEqual(sorted(c["leads"] for c in contactos), [1, 3])
        # filtro por contacto
        self.assertEqual(len(self.bandeja(contacto_id=leads[a]["contacto_id"])["leads"]), 3)

    def test_ventana_de_nuevo_con_corte_visible(self):
        reciente = self.crear_lead(correo="reciente@example.test")
        antiguo = self.crear_lead(correo="antiguo@example.test")
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("UPDATE leads SET creado_en = now() - interval '45 days' WHERE id = %s", (antiguo,))
            conexion.commit()
        cuerpo = self.bandeja()
        self.assertEqual([l["id"] for l in cuerpo["leads"]], [reciente])
        self.assertEqual(cuerpo["corte"]["ventana_nuevo_dias"], 30)
        self.assertIsNotNone(cuerpo["corte"]["desde"])
        self.assertEqual(cuerpo["sin_gestionar_antiguos"], 1)
        todos = {l["id"]: l["situacion"] for l in self.bandeja(todos=True)["leads"]}
        self.assertEqual(todos, {reciente: "nuevo", antiguo: "sin_gestionar_antiguo"})

    def test_normalizar_telefono(self):
        self.assertEqual(normalizar_telefono("+56 9 1234 5678"), "+56912345678")
        self.assertEqual(normalizar_telefono("9 1234 5678"), "+56912345678")
        self.assertIsNone(normalizar_telefono(""))


if __name__ == "__main__":
    unittest.main()
