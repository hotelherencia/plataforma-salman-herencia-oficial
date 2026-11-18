"""#348 (2026-11-18): tope de solicitudes por cliente, configurable por la
administración del hotel desde Configuración (decisión del propietario)."""
import unittest
import uuid

import psycopg

from servicio.canal_publico import contacto_normalizado
from servicio.tests.aislamiento import exigir_base_libre
from servicio.tests.test_canal_publico import CanalPublicoBaseTest, URL_TEST


class TopeClienteTest(CanalPublicoBaseTest):
    def setUp(self):
        super().setUp()
        with psycopg.connect(URL_TEST) as conexion:
            exigir_base_libre(conexion)
            conexion.execute("DELETE FROM ajustes")  # vuelve al valor inicial: 3 en 7 días
            conexion.commit()

    def solicitar(self, contacto, clave=None):
        cuerpo = self.cuerpo_solicitud() | {"huesped_contacto": contacto}
        return self.anonima.post("/publico/solicitudes", json=cuerpo,
                                 headers={"Idempotency-Key": clave or f"t-{uuid.uuid4().hex[:10]}"})

    def ajustar(self, **valor):
        return self.cliente.put("/hotel/ajustes/tope_solicitudes_cliente", json=valor,
                                headers={"Idempotency-Key": f"a-{uuid.uuid4().hex[:10]}"})

    def test_normalizacion_de_contacto(self):
        self.assertEqual(contacto_normalizado(" Ana@Example.TEST "), "ana@example.test")
        self.assertEqual(contacto_normalizado("9 8765 4321"), "+56987654321")
        self.assertEqual(contacto_normalizado("+56 9 8765-4321"), "+56987654321")

    def test_valor_inicial_3_en_7_dias_y_cuarta_rechazada(self):
        self.assertEqual(self.cliente.get("/hotel/ajustes").json()["ajustes"]["tope_solicitudes_cliente"],
                         {"activo": True, "max_solicitudes": 3, "dias": 7})
        for _ in range(3):
            self.assertEqual(self.solicitar("cliente@example.test").status_code, 201)
        cuarta = self.solicitar("CLIENTE@example.test")
        self.assertEqual(cuarta.status_code, 409, cuarta.text)
        self.assertIn("últimos 7 días", cuarta.json()["detail"])
        # otro cliente no se ve afectado; el mismo teléfono con otro formato sí cuenta
        self.assertEqual(self.solicitar("otra@example.test").status_code, 201)
        with psycopg.connect(URL_TEST) as conexion:
            (n,) = conexion.execute("SELECT count(*) FROM solicitudes").fetchone()
        self.assertEqual(n, 4)

    def test_reintento_idempotente_no_cuenta(self):
        self.assertEqual(self.ajustar(max_solicitudes=1).status_code, 200)
        primera = self.solicitar("+56 9 1111 2222", clave="misma-clave-1")
        self.assertEqual(primera.status_code, 201)
        repetida = self.solicitar("+56 9 1111 2222", clave="misma-clave-1")
        self.assertEqual(repetida.json()["solicitud_id"], primera.json()["solicitud_id"])
        self.assertEqual(self.solicitar("911112222").status_code, 409)

    def test_rechazada_libera_y_tope_desactivable(self):
        self.assertEqual(self.ajustar(max_solicitudes=1).status_code, 200)
        sid = self.solicitar("libera@example.test").json()["solicitud_id"]
        self.assertEqual(self.solicitar("libera@example.test").status_code, 409)
        with psycopg.connect(URL_TEST) as conexion:
            conexion.execute("UPDATE solicitudes SET estado = 'rechazada' WHERE id = %s", (sid,))
            conexion.commit()
        self.assertEqual(self.solicitar("libera@example.test").status_code, 201)
        self.assertEqual(self.ajustar(activo=False).status_code, 200)
        self.assertEqual(self.solicitar("libera@example.test").status_code, 201)

    def test_validacion_y_permisos(self):
        self.assertEqual(self.ajustar(max_solicitudes=0).status_code, 422)
        self.assertEqual(self.ajustar(dias=400).status_code, 422)
        self.assertEqual(self.ajustar(otro=1).status_code, 422)
        self.assertEqual(self.cliente.put("/hotel/ajustes/no-existe", json={},
                                          headers={"Idempotency-Key": "a-x"}).status_code, 422)
        self.assertEqual(self.anonima.get("/hotel/ajustes").status_code, 401)
        r = self.ajustar(max_solicitudes=5, dias=30)
        self.assertEqual(r.json()["valor"], {"activo": True, "max_solicitudes": 5, "dias": 30})


if __name__ == "__main__":
    unittest.main()
