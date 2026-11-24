"""Rol súper administrador: jerarquía de cuentas, segundo factor obligatorio y cuenta inicial."""
import os
import unittest

import psycopg
from fastapi.testclient import TestClient

from servicio import migracion, roles, seguridad
from servicio.aplicacion import crear_app
from servicio.configuracion import Configuracion

URL_TEST = os.environ.get("DATABASE_URL_TEST", "postgresql://plataforma:plataforma@127.0.0.1:5432/plataforma_test_superadmin")
CLAVE = "Clave123!"
EMPRESA = "EMP-SINTETICA-001"
NOMBRES = {"sa": "super_admin", "adm": "administrador", "ap": "admin_plataforma",
           "ah": "admin_hotel", "ah2": "admin_hotel", "dn": "dueno", "rc": "recepcion", "aseo": "aseo"}


class JerarquiaPuraTest(unittest.TestCase):
    def test_matriz_de_gestion(self):
        g = roles.puede_gestionar
        for objetivo in roles.ROLES_VALIDOS:
            self.assertEqual(g("super_admin", objetivo), objetivo != "super_admin", objetivo)  # hay uno solo: no se asigna
        self.assertTrue(g("administrador", "admin_plataforma"))
        self.assertTrue(g("administrador", "recepcion"))
        for objetivo in ("super_admin", "dueno", "administrador"):
            self.assertFalse(g("administrador", objetivo), objetivo)
        self.assertTrue(g("admin_plataforma", "recepcion"))
        for objetivo in ("super_admin", "dueno", "administrador", "admin_plataforma", "admin_hotel"):
            self.assertFalse(g("admin_plataforma", objetivo), objetivo)
        self.assertTrue(roles.es_admin_plataforma("administrador"))
        for actor in ("admin_hotel", "dueno", "recepcion", "caja", "aseo", None, "inventado"):
            for objetivo in roles.ROLES_VALIDOS:
                self.assertFalse(g(actor, objetivo), f"{actor}->{objetivo}")
        self.assertFalse(g("super_admin", "rol_inventado"))
        self.assertEqual(sorted(roles.ROLES_APROBADORES), ["admin_hotel", "administrador"])

    def test_super_admin_es_administracion_completa_con_doble_factor(self):
        self.assertTrue(roles.es_admin_hotel("super_admin") and roles.es_admin_plataforma("super_admin"))
        self.assertTrue(roles.exige_doble_factor("super_admin"))
        self.assertIn("super_admin", roles.ROLES_VALIDOS)
        self.assertTrue(roles.es_privilegiado("super_admin") and roles.es_privilegiado("admin_hotel"))
        self.assertFalse(roles.es_privilegiado("recepcion"))


class CuentasHttpTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)
        cls.app = crear_app(configuracion=Configuracion(
            host="127.0.0.1", puerto=0, database_url=URL_TEST, cookie_segura=False,
            origen_front=None, admin_usuario="root_sa", admin_clave=CLAVE))
        cls.cm = TestClient(cls.app)
        cls.cm.__enter__()
        cls._n = 0

    @classmethod
    def tearDownClass(cls):
        cls.cm.__exit__(None, None, None)

    def setUp(self):
        h = seguridad.hashear_clave(CLAVE)
        with psycopg.connect(URL_TEST) as c:
            c.execute("TRUNCATE sesiones, claves_idempotencia, auditoria, cambios_rol CASCADE")
            c.execute("DELETE FROM usuarios WHERE nombre LIKE 'zz_%' OR nombre LIKE 'sa_t_%'")
            c.execute("UPDATE usuarios SET rol = 'administrador' WHERE rol = 'super_admin'")  # solo puede haber uno
            for k, rol in NOMBRES.items():
                c.execute("INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo, totp_activado) VALUES "
                          "(%s,%s,%s,%s,%s,true,false) ON CONFLICT (id) DO UPDATE SET clave_hash=EXCLUDED.clave_hash, "
                          "rol=EXCLUDED.rol, activo=true, totp_activado=false",
                          (f"USR-SA-{k}", f"sa_t_{k}", h, rol, EMPRESA))
            c.commit()
        self.c = {k: self._login(f"sa_t_{k}") for k in NOMBRES}
        self._totp("sa")

    def _totp(self, *claves, valor=True):
        with psycopg.connect(URL_TEST) as c:
            for k in claves:
                c.execute("UPDATE usuarios SET totp_activado = %s WHERE id = %s", (valor, f"USR-SA-{k}"))
            c.commit()

    def _login(self, nombre):
        cl = TestClient(self.app)
        r = cl.post("/sesion", json={"usuario": nombre, "clave": CLAVE})
        self.assertEqual(r.status_code, 200, r.text)
        return cl

    def _h(self):
        self.__class__._n += 1
        return {"Idempotency-Key": f"sa-{self._n}-xxxxxxxxxxxxxxxxxx"}

    def _crear(self, k, rol, nombre="zz_nuevo"):
        return self.c[k].post("/usuarios", json={"nombre": nombre, "rol": rol, "clave": "ClaveSegura123!"}, headers=self._h())

    def _uid(self, k):
        return f"USR-SA-{k}"

    def _rol_de(self, nombre):
        with psycopg.connect(URL_TEST) as c:
            return c.execute("SELECT rol, activo FROM usuarios WHERE nombre = %s", (nombre,)).fetchone()

    # --- jerarquía ---------------------------------------------------------------------------
    def test_alta_respeta_el_tope_de_rol_y_nadie_crea_otro_super_admin(self):
        for rol in ("super_admin", "dueno", "administrador", "admin_plataforma", "admin_hotel"):
            self.assertEqual(self._crear("ap", rol, f"zz_ap_{rol}").status_code, 403, rol)
        self.assertEqual(self._crear("ap", "recepcion", "zz_ap_rec").status_code, 201)
        for rol in ("super_admin", "dueno", "administrador"):
            self.assertEqual(self._crear("adm", rol, f"zz_adm_{rol}").status_code, 403, rol)
        self.assertEqual(self._crear("sa", "super_admin", "zz_sa_otro").status_code, 403)  # hay uno solo

    def test_un_administrador_de_plataforma_no_toma_cuentas_superiores(self):
        ap = self.c["ap"]
        for objetivo in ("sa", "dn", "adm", "ah"):
            uid = self._uid(objetivo)
            self.assertEqual(ap.post(f"/usuarios/{uid}/clave", json={"clave": "OtraClave123!"}, headers=self._h()).status_code, 403, f"clave {objetivo}")
            self.assertEqual(ap.post(f"/usuarios/{uid}/email", json={"email": "zz.toma@example.com"}, headers=self._h()).status_code, 403, f"email {objetivo}")
            self.assertEqual(ap.post(f"/usuarios/{uid}/baja", headers=self._h()).status_code, 403, f"baja {objetivo}")
            self.assertEqual(ap.post(f"/usuarios/{uid}/revocacion", headers=self._h()).status_code, 403, f"revocacion {objetivo}")
            self.assertEqual(ap.post(f"/usuarios/{uid}/rol", json={"rol": "recepcion"}).status_code, 403, f"rol {objetivo}")
        with psycopg.connect(URL_TEST) as c:
            self.assertTrue(c.execute("SELECT activo FROM usuarios WHERE id = %s", (self._uid("dn"),)).fetchone()[0])
            n = c.execute("SELECT count(*) FROM auditoria WHERE accion = 'usuario-jerarquia'").fetchone()[0]
        self.assertGreaterEqual(n, 20)
        self.assertEqual(ap.post(f"/usuarios/{self._uid('rc')}/clave", json={"clave": "OtraClave123!"}, headers=self._h()).status_code, 200)
        self.assertEqual(ap.post(f"/usuarios/{self._uid('aseo')}/revocacion", headers=self._h()).status_code, 200)

    def test_el_super_admin_gobierna_cuentas_privilegiadas_pero_no_se_da_de_baja_ni_se_copia(self):
        sa = self.c["sa"]
        self.assertEqual(sa.post(f"/usuarios/{self._uid('sa')}/baja", headers=self._h()).status_code, 409)
        for k in ("ap", "adm", "ah"):  # nadie más puede tocar la cuenta institucional
            self.assertEqual(self.c[k].post(f"/usuarios/{self._uid('sa')}/baja", headers=self._h()).status_code, 403, k)
        self.assertEqual(sa.post(f"/usuarios/{self._uid('dn')}/clave", json={"clave": "OtraClave123!"}, headers=self._h()).status_code, 200)
        self.assertEqual(sa.post(f"/usuarios/{self._uid('adm')}/revocacion", headers=self._h()).status_code, 200)

    def test_hay_un_solo_super_admin_en_la_base(self):
        with psycopg.connect(URL_TEST) as c:
            with self.assertRaises(psycopg.errors.UniqueViolation):
                c.execute("UPDATE usuarios SET rol = 'super_admin' WHERE id = %s", (self._uid("adm"),))

    # --- cambios de rol con validación ------------------------------------------------------
    def test_alta_con_rol_privilegiado_queda_pendiente_hasta_que_valida_el_hotel(self):
        r = self._crear("sa", "administrador", "zz_admin_nuevo")
        self.assertEqual(r.status_code, 202, r.text)
        self.assertEqual(r.json()["estado"], "pendiente_validacion")
        self.assertEqual(self._rol_de("zz_admin_nuevo"), ("administrador", False))  # inactiva: no puede entrar
        login = TestClient(self.app).post("/sesion", json={"usuario": "zz_admin_nuevo", "clave": "ClaveSegura123!"})
        self.assertEqual(login.status_code, 401)
        cambio = r.json()["cambio_id"]
        # quien lo pidió no lo aprueba, ni tampoco quien no es de la administración del hotel
        self.assertEqual(self.c["sa"].post(f"/usuarios/cambios-rol/{cambio}/aprobacion").status_code, 403)
        for k in ("ap", "rc", "dn"):
            self.assertEqual(self.c[k].post(f"/usuarios/cambios-rol/{cambio}/aprobacion").status_code, 403, k)
        self.assertEqual(self._rol_de("zz_admin_nuevo"), ("administrador", False))
        ok = self.c["ah"].post(f"/usuarios/cambios-rol/{cambio}/aprobacion", json={"comentario": "ok"})
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(self._rol_de("zz_admin_nuevo"), ("administrador", True))
        self.assertEqual(TestClient(self.app).post("/sesion", json={"usuario": "zz_admin_nuevo", "clave": "ClaveSegura123!"}).status_code, 200)
        self.assertEqual(self.c["ah2"].post(f"/usuarios/cambios-rol/{cambio}/aprobacion").status_code, 409)  # ya resuelto

    def test_rechazo_deja_la_cuenta_inactiva(self):
        cambio = self._crear("sa", "admin_hotel", "zz_rechazada").json()["cambio_id"]
        self.assertEqual(self.c["ah"].post(f"/usuarios/cambios-rol/{cambio}/rechazo", json={"comentario": "no"}).status_code, 200)
        self.assertEqual(self._rol_de("zz_rechazada"), ("admin_hotel", False))

    def test_todo_cambio_de_rol_exige_validacion_y_no_se_aplica_solo(self):
        r = self.c["ap"].post(f"/usuarios/{self._uid('rc')}/rol", json={"rol": "caja", "motivo": "cambio de funciones"})
        self.assertEqual(r.status_code, 202, r.text)
        self.assertEqual(self._rol_de("sa_t_rc")[0], "recepcion")  # sigue igual hasta la validación
        self.assertEqual(self.c["ap"].post(f"/usuarios/{self._uid('rc')}/rol", json={"rol": "aseo"}).status_code, 409)  # ya hay uno pendiente
        self.assertEqual(self.c["ap"].post(f"/usuarios/cambios-rol/{r.json()['cambio_id']}/aprobacion").status_code, 403)
        self.assertEqual(self.c["ah"].post(f"/usuarios/cambios-rol/{r.json()['cambio_id']}/aprobacion").status_code, 200)
        self.assertEqual(self._rol_de("sa_t_rc")[0], "caja")
        # elevar a un rol privilegiado: solo quien gobierna ese rango puede pedirlo
        self.assertEqual(self.c["ap"].post(f"/usuarios/{self._uid('aseo')}/rol", json={"rol": "administrador"}).status_code, 403)
        self.assertEqual(self.c["sa"].post(f"/usuarios/{self._uid('aseo')}/rol", json={"rol": "super_admin"}).status_code, 403)
        self.assertEqual(self.c["sa"].post(f"/usuarios/{self._uid('sa')}/rol", json={"rol": "recepcion"}).status_code, 409)

    def test_el_afectado_no_valida_su_propio_cambio(self):
        r = self.c["sa"].post(f"/usuarios/{self._uid('ah2')}/rol", json={"rol": "recepcion"})
        self.assertEqual(r.status_code, 202, r.text)
        self.assertEqual(self.c["ah2"].post(f"/usuarios/cambios-rol/{r.json()['cambio_id']}/aprobacion").status_code, 403)
        self.assertEqual(self.c["ah"].post(f"/usuarios/cambios-rol/{r.json()['cambio_id']}/aprobacion").status_code, 200)

    def test_sin_ningun_aprobador_el_primer_cambio_se_aplica_y_queda_marcado(self):
        with psycopg.connect(URL_TEST) as c:
            ids = [f[0] for f in c.execute("UPDATE usuarios SET activo = false WHERE rol IN ('admin_hotel', 'administrador') "
                                           "AND activo RETURNING id").fetchall()]
            c.commit()
        self.addCleanup(lambda: psycopg.connect(URL_TEST).execute("UPDATE usuarios SET activo = true WHERE id = ANY(%s)", (ids,)).connection.commit())
        r = self._crear("sa", "admin_hotel", "zz_primero")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(self._rol_de("zz_primero"), ("admin_hotel", True))
        with psycopg.connect(URL_TEST) as c:
            self.assertTrue(c.execute("SELECT sin_aprobador FROM cambios_rol WHERE usuario_id = %s", (r.json()["id"],)).fetchone()[0])
            self.assertTrue(c.execute("SELECT 1 FROM auditoria WHERE accion = 'cambio-rol' AND resultado LIKE '%SIN aprobador%'").fetchone())

    def test_lista_de_cambios_la_ven_quien_pide_y_quien_valida(self):
        self._crear("sa", "administrador", "zz_lista")
        for k in ("sa", "ap", "ah"):
            self.assertEqual(len(self.c[k].get("/usuarios/cambios-rol?estado=pendiente").json()["cambios"]), 1, k)
        self.assertEqual(self.c["dn"].get("/usuarios/cambios-rol").status_code, 200)  # lectura global del dueño
        for k in ("rc", "aseo"):
            self.assertEqual(self.c[k].get("/usuarios/cambios-rol").status_code, 403, k)

    # --- segundo factor y listado -----------------------------------------------------------
    def test_sin_segundo_factor_el_super_admin_solo_puede_enrolarse(self):
        self._totp("sa", valor=False)
        sa = self.c["sa"]
        self.assertEqual(sa.get("/sesion").status_code, 200)
        self.assertTrue(sa.get("/sesion").json()["mfa_pendiente"])
        for met, ruta in (("GET", "/usuarios"), ("GET", "/hotel/solicitudes"), ("POST", "/usuarios")):
            self.assertEqual(sa.request(met, ruta, json={} if met == "POST" else None, headers=self._h()).status_code, 403, ruta)
        self.assertNotEqual(sa.get("/cuenta/2fa").status_code, 403)

    def test_listado_indica_que_cuentas_puede_gestionar_cada_rol(self):
        j = self.c["ap"].get("/usuarios").json()
        self.assertEqual(sorted(j["roles_que_puedes_crear"]), ["aseo", "caja", "recepcion"])
        gest = {u["nombre"]: u["gestionable"] for u in j["usuarios"]}
        self.assertFalse(gest["sa_t_dn"] or gest["sa_t_sa"] or gest["sa_t_adm"])
        self.assertTrue(gest["sa_t_rc"])
        self.assertNotIn("super_admin", self.c["sa"].get("/usuarios").json()["roles_que_puedes_crear"])

    def test_hotel_y_dueno_siguen_sin_gestionar_usuarios(self):
        for k in ("ah", "dn", "rc"):
            self.assertEqual(self.c[k].get("/usuarios").status_code, 403, k)


class CuentaInicialTest(unittest.TestCase):
    CORREO = "institucional@example.com"

    @classmethod
    def setUpClass(cls):
        migracion.aplicar_migraciones(URL_TEST)

    def setUp(self):
        h = seguridad.hashear_clave(CLAVE)
        with psycopg.connect(URL_TEST) as c:
            c.execute("UPDATE usuarios SET rol = 'administrador' WHERE rol = 'super_admin'")
            c.execute("DELETE FROM usuarios WHERE nombre LIKE 'ci_%'")
            for nombre, rol, email in (("ci_arranque", "administrador", self.CORREO), ("ci_otro", "administrador", "otro@example.com"),
                                       ("ci_recep", "recepcion", self.CORREO.replace("institucional", "r"))):
                c.execute("INSERT INTO usuarios (id, nombre, clave_hash, rol, empresa_id, activo, email) VALUES (%s,%s,%s,%s,%s,true,%s)",
                          (f"USR-{nombre}", nombre, h, rol, EMPRESA, email))
            c.commit()

    def test_solo_se_promueve_la_cuenta_con_el_correo_institucional(self):
        with psycopg.connect(URL_TEST) as c:
            f = seguridad.asegurar_super_admin_inicial
            self.assertFalse(f(c, EMPRESA, None, self.CORREO))
            self.assertFalse(f(c, EMPRESA, "ci_arranque", None))              # sin correo exigido: no promueve
            self.assertFalse(f(c, EMPRESA, "ci_otro", self.CORREO))           # otro correo: no
            self.assertFalse(f(c, EMPRESA, "ci_recep", "r@example.com"))      # operativa: no
            self.assertFalse(f(c, EMPRESA, "no_existe", self.CORREO))
            self.assertTrue(f(c, EMPRESA, "ci_arranque", self.CORREO.upper()))
            self.assertEqual(c.execute("SELECT rol FROM usuarios WHERE nombre='ci_arranque'").fetchone()[0], "super_admin")
            self.assertFalse(f(c, EMPRESA, "ci_otro", "otro@example.com"))    # ya hay uno
            self.assertTrue(c.execute("SELECT 1 FROM auditoria WHERE accion = 'super_admin'").fetchone())
            c.rollback()


if __name__ == "__main__":
    unittest.main()
