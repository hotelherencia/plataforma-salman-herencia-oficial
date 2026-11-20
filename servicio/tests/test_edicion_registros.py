"""Edición de registros de clientes: leads, solicitudes, huésped de la reserva y fichas de cliente (RUT).
Datos 100 % sintéticos; base dedicada (exigir_base_libre)."""
import unittest
import uuid
from datetime import timedelta

import psycopg

from servicio.tests.test_leads import (
    EMPRESA, EN_3, HOY, MANANA, OTRA_EMPRESA, URL_TEST, LeadsBaseTest,
)


class _Base(LeadsBaseTest):
    def setUp(self):
        super().setUp()
        with psycopg.connect(URL_TEST) as c:
            c.execute("TRUNCATE contactos, clientes RESTART IDENTITY CASCADE")
            c.commit()

    def ejecutar(self, sql, parametros=()):
        with psycopg.connect(URL_TEST) as c:
            c.execute(sql, parametros)
            c.commit()


class EdicionLeadsTest(_Base):
    def cuerpo_edicion(self, **cambios):
        base = self.cuerpo_lead()
        base["nota"] = None
        base.update(cambios)
        return base

    def test_ed01_edita_en_cualquier_estado_y_audita_sin_valores(self):
        lead_id = self.crear_lead()
        self.cliente.post(f"/hotel/leads/{lead_id}/estado", json={"estado": "cerrado", "nota": "x"},
                          headers={"Idempotency-Key": self.clave()})
        r = self.cliente.put(f"/hotel/leads/{lead_id}", json=self.cuerpo_edicion(
            nombre="Nombre Corregido", telefono="+56 9 1111 2222", nota="corregido por recepción"))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["nombre"], r.json()["estado"]), ("Nombre Corregido", "cerrado"))
        self.assertEqual(self.select("SELECT nombre, telefono, nota FROM leads WHERE id = %s", (lead_id,))[0],
                         ("Nombre Corregido", "+56 9 1111 2222", "corregido por recepción"))
        aud = self.select("SELECT resultado FROM auditoria WHERE accion = 'lead_edicion' AND recurso = %s", (lead_id,))
        self.assertEqual(aud, [("nombre,telefono,nota",)])

    def test_ed02_sin_cambios_no_audita(self):
        lead_id = self.crear_lead()
        self.assertEqual(self.cliente.put(f"/hotel/leads/{lead_id}", json=self.cuerpo_edicion()).status_code, 200)
        self.assertEqual(self.select("SELECT 1 FROM auditoria WHERE accion = 'lead_edicion'"), [])

    def test_ed03_validaciones_y_fechas_antiguas_se_conservan(self):
        lead_id = self.crear_lead()
        put = lambda **c: self.cliente.put(f"/hotel/leads/{lead_id}", json=self.cuerpo_edicion(**c))
        self.assertEqual(put(correo="sin-arroba").status_code, 422)
        self.assertEqual(put(check_in=str(HOY - timedelta(days=5)), check_out=str(HOY - timedelta(days=3))).status_code, 422)
        self.assertEqual(self.cliente.put(f"/hotel/leads/{lead_id}", json={**self.cuerpo_edicion(), "otro": 1}).status_code, 422)
        # lead con llegada ya pasada: se corrige el nombre sin tocar las fechas
        self.ejecutar("UPDATE leads SET check_in = %s, check_out = %s WHERE id = %s",
                      (HOY - timedelta(days=10), HOY - timedelta(days=8), lead_id))
        r = put(nombre="Solo nombre", check_in=str(HOY - timedelta(days=10)), check_out=str(HOY - timedelta(days=8)))
        self.assertEqual(r.status_code, 200, r.text)

    def test_ed04_roles_ajeno_e_inexistente(self):
        lead_id = self.crear_lead()
        self.crear_usuario("caja1", "caja")
        self.assertEqual(self.login("caja1", "clave-usuario-1").put(
            f"/hotel/leads/{lead_id}", json=self.cuerpo_edicion()).status_code, 403)
        self.assertEqual(self.anonima.put(f"/hotel/leads/{lead_id}", json=self.cuerpo_edicion()).status_code, 401)
        self.assertEqual(self.cliente.put("/hotel/leads/LEAD-NOEXISTE", json=self.cuerpo_edicion()).status_code, 403)
        self.ejecutar("UPDATE leads SET empresa_id = %s WHERE id = %s", (OTRA_EMPRESA, lead_id))
        self.assertEqual(self.cliente.put(f"/hotel/leads/{lead_id}", json=self.cuerpo_edicion()).status_code, 403)

    def test_ed05_cambiar_correo_mueve_el_lead_a_su_ficha_sin_tocar_las_otras(self):
        a = self.crear_lead(correo="uno@example.test")
        b = self.crear_lead(correo="uno@example.test")  # mismo contacto
        antes = self.select("SELECT contacto_id FROM leads WHERE id = %s", (a,))[0][0]
        self.assertEqual(antes, self.select("SELECT contacto_id FROM leads WHERE id = %s", (b,))[0][0])
        # mismo teléfono = misma persona (ficha única por correo o teléfono): se cambia también el teléfono
        r = self.cliente.put(f"/hotel/leads/{a}", json=self.cuerpo_edicion(
            correo="otro@example.test", telefono="+56 9 4444 3333"))
        self.assertEqual(r.status_code, 200, r.text)
        nuevo = self.select("SELECT contacto_id, correo FROM leads WHERE id = %s", (a,))[0]
        self.assertNotEqual(nuevo[0], antes)
        self.assertEqual(self.select("SELECT contacto_id FROM leads WHERE id = %s", (b,))[0][0], antes)
        self.assertEqual(self.select("SELECT correo FROM contactos WHERE id = %s", (antes,))[0][0], "uno@example.test")

    def test_ed06_la_referencia_del_visitante_refleja_la_correccion(self):
        r = self.anonima.post("/publico/leads", json=self.cuerpo_lead(), headers={"Idempotency-Key": self.clave()})
        lead_id, token = r.json()["lead"]["id"], r.json()["referencia"]
        self.cliente.put(f"/hotel/leads/{lead_id}", json=self.cuerpo_edicion(nombre="Corregido Ref"))
        self.assertEqual(self.select("SELECT nombre FROM leads WHERE token_consulta = %s", (token,))[0][0], "Corregido Ref")


class EdicionSolicitudYReservaTest(_Base):
    def solicitud(self, estado="recibida"):
        sid = f"SOL-{uuid.uuid4().hex[:10]}"
        self.ejecutar(
            "INSERT INTO solicitudes (id, empresa_id, tipo, inicio, fin, personas, huesped_nombre, huesped_contacto, "
            "estado, idempotency_key, cuerpo_hash) VALUES (%s,%s,'doble',%s,%s,1,'Huésped Sintético','h@example.test',"
            "%s,%s,'x')", (sid, EMPRESA, MANANA, EN_3, estado, sid))
        return sid

    def test_ed10_solicitud_edita_contacto_y_personas_mientras_recibida(self):
        sid = self.solicitud()
        r = self.cliente.put(f"/hotel/solicitudes/{sid}", json={
            "huesped_nombre": "Corregido", "huesped_contacto": "Nuevo@Example.test", "personas": 2})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual((r.json()["huesped_nombre"], r.json()["personas"]), ("Corregido", 2))
        self.assertEqual(self.select("SELECT contacto_normalizado FROM solicitudes WHERE id = %s", (sid,))[0][0],
                         "nuevo@example.test")
        self.assertEqual(self.select("SELECT resultado FROM auditoria WHERE accion = 'solicitud_edicion'"),
                         [("huesped_nombre,huesped_contacto,personas",)])

    def test_ed11_solicitud_rechazada_corrige_contacto_pero_no_personas(self):
        sid = self.solicitud("rechazada")
        ok = self.cliente.put(f"/hotel/solicitudes/{sid}", json={
            "huesped_nombre": "Corregido", "huesped_contacto": "c@example.test", "personas": 1})
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(self.cliente.put(f"/hotel/solicitudes/{sid}", json={
            "huesped_nombre": "Corregido", "huesped_contacto": "c@example.test", "personas": 3}).status_code, 409)
        self.assertEqual(self.cliente.put("/hotel/solicitudes/SOL-NO", json={
            "huesped_nombre": "a", "huesped_contacto": "b", "personas": 1}).status_code, 403)
        self.crear_usuario("caja1", "caja")
        self.assertEqual(self.login("caja1", "clave-usuario-1").put(f"/hotel/solicitudes/{sid}", json={
            "huesped_nombre": "a", "huesped_contacto": "b", "personas": 1}).status_code, 403)

    def reservar(self, nombre="Huésped Uno", documento=None):
        huesped = {"nombre": nombre, "documento": documento}
        r = self.cliente.post("/hotel/reservas", json={
            "habitacion_id": "HAB-SINT-101", "inicio": str(MANANA), "fin": str(EN_3), "huesped": huesped},
            headers={"Idempotency-Key": self.clave()})
        self.assertEqual(r.status_code, 201, r.text)
        return r.json()["reserva_id"]

    def test_ed20_reserva_edita_nombre_y_documento_sin_perderlo(self):
        rid = self.reservar()
        put = lambda cuerpo: self.cliente.put(f"/hotel/reservas/{rid}/huesped", json=cuerpo)
        r = put({"nombre": "Huésped Corregido", "documento": "12345678-5", "documento_tipo": "rut"})
        self.assertEqual(r.status_code, 200, r.text)
        fila = lambda: self.select(
            "SELECT huesped_nombre, huesped_documento, huesped_documento_tipo FROM reservas WHERE id = %s", (rid,))[0]
        self.assertEqual(fila(), ("Huésped Corregido", "12.345.678-5", "rut"))
        self.assertEqual(put({"nombre": "Otro Nombre"}).status_code, 200)  # sin documento: no se borra
        self.assertEqual(fila(), ("Otro Nombre", "12.345.678-5", "rut"))
        self.assertEqual(self.cliente.get(f"/hotel/reservas/{rid}").json()["huesped_nombre"], "Otro Nombre")
        aud = self.select("SELECT resultado FROM auditoria WHERE accion = 'reserva_edicion_huesped' ORDER BY creado_en")
        self.assertEqual(aud, [("huesped_nombre,huesped_documento",), ("huesped_nombre",)])
        self.assertNotIn("12.345", str(aud))

    def test_ed21_documento_invalido_o_sin_tipo_422(self):
        rid = self.reservar()
        put = lambda cuerpo: self.cliente.put(f"/hotel/reservas/{rid}/huesped", json=cuerpo)
        self.assertEqual(put({"nombre": "X", "documento": "12345678-9", "documento_tipo": "rut"}).status_code, 422)
        self.assertEqual(put({"nombre": "X", "documento": "ABC12345"}).status_code, 422)

    def test_ed22_rut_de_otro_cliente_409(self):
        self.ejecutar("INSERT INTO clientes (id, rut, nombre, nombre_clave, creado_por) "
                      "VALUES ('CLI-1', '123456785', 'Empresa Dueña', 'empresa duena', 'test')")
        rid = self.reservar()
        r = self.cliente.put(f"/hotel/reservas/{rid}/huesped", json={
            "nombre": "Otra Persona", "documento": "12.345.678-5", "documento_tipo": "rut"})
        self.assertEqual(r.status_code, 409, r.text)
        self.assertEqual(self.cliente.put(f"/hotel/reservas/{rid}/huesped", json={
            "nombre": "Empresa Dueña", "documento": "12.345.678-5", "documento_tipo": "rut"}).status_code, 200)

    def test_ed23_roles_y_ajena(self):
        rid = self.reservar()
        self.crear_usuario("caja1", "caja")
        self.assertEqual(self.login("caja1", "clave-usuario-1").put(
            f"/hotel/reservas/{rid}/huesped", json={"nombre": "X"}).status_code, 403)
        self.assertEqual(self.cliente.put("/hotel/reservas/RES-NO/huesped", json={"nombre": "X"}).status_code, 403)


class EdicionClientesTest(_Base):
    def cliente_db(self, cid="CLI-1", rut="123456785", nombre="Empresa Uno"):
        self.ejecutar("INSERT INTO clientes (id, rut, nombre, nombre_clave, creado_por) VALUES (%s,%s,%s,%s,'test')",
                      (cid, rut, nombre, nombre.lower()))

    def cuerpo(self, **cambios):
        base = {"rut": "12.345.678-5", "nombre": "Empresa Uno", "tipo": "empresa", "giro": None,
                "direccion": None, "comuna": None, "correo": None, "activo": True}
        base.update(cambios)
        return base

    def test_ed30_lista_y_busca_por_nombre_y_rut(self):
        self.cliente_db()
        todos = self.cliente.get("/hotel/clientes").json()["clientes"]
        self.assertEqual([c["rut"] for c in todos], ["12.345.678-5"])
        self.assertEqual(len(self.cliente.get("/hotel/clientes", params={"q": "uno"}).json()["clientes"]), 1)
        self.assertEqual(len(self.cliente.get("/hotel/clientes", params={"q": "12.345.678"}).json()["clientes"]), 1)
        self.assertEqual(self.cliente.get("/hotel/clientes", params={"q": "zzz"}).json()["clientes"], [])

    def test_ed31_edita_ficha_y_audita(self):
        self.cliente_db()
        r = self.cliente.put("/hotel/clientes/CLI-1", json=self.cuerpo(
            nombre="Empresa Uno SpA", correo="Contacto@Example.test", comuna="Valdivia"))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.select("SELECT nombre, nombre_clave, correo, comuna FROM clientes WHERE id='CLI-1'")[0],
                         ("Empresa Uno SpA", "empresa uno spa", "contacto@example.test", "Valdivia"))
        self.assertEqual(self.select("SELECT resultado FROM auditoria WHERE accion = 'cliente_edicion'"),
                         [("nombre,comuna,correo",)])

    def test_ed32_rut_invalido_422_y_duplicado_409_y_desactivar(self):
        self.cliente_db()
        self.cliente_db("CLI-2", "222222222", "Otra Empresa")
        self.assertEqual(self.cliente.put("/hotel/clientes/CLI-1", json=self.cuerpo(rut="12.345.678-9")).status_code, 422)
        self.assertEqual(self.cliente.put("/hotel/clientes/CLI-1", json=self.cuerpo(rut="22.222.222-2")).status_code, 409)
        self.assertEqual(self.cliente.put("/hotel/clientes/CLI-1", json=self.cuerpo(correo="mal")).status_code, 422)
        self.assertEqual(self.cliente.put("/hotel/clientes/CLI-1", json=self.cuerpo(activo=False)).status_code, 200)
        self.assertFalse(self.select("SELECT activo FROM clientes WHERE id='CLI-1'")[0][0])

    def test_ed33_roles_e_inexistente(self):
        self.cliente_db()
        self.crear_usuario("aseo1", "aseo")
        otro = self.login("aseo1", "clave-usuario-1")
        self.assertEqual(otro.get("/hotel/clientes").status_code, 403)
        self.assertEqual(otro.put("/hotel/clientes/CLI-1", json=self.cuerpo()).status_code, 403)
        self.assertEqual(self.cliente.put("/hotel/clientes/CLI-NO", json=self.cuerpo()).status_code, 403)


if __name__ == "__main__":
    unittest.main()
