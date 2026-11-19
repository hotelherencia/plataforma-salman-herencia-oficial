"""Auditoría de seguridad 2026-11-17 — cambio de clave.

SA-CLV-01 (regresión del hallazgo E2E CLV-01): al cambiar la clave, toda otra
           sesión del usuario cae y la actual sigue. El servidor ya lo hacía;
           el E2E leía la otra sesión antes del POST (carrera con el aviso de
           MFA, también role=status).
SA-CLV-02: un reintento con la misma Idempotency-Key y OTRA clave nueva no
           puede responder «clave actualizada» sin haberla cambiado.
"""
import unittest

from servicio.tests.secaudit_base import BaseSesiones


class CambioDeClaveTest(BaseSesiones):
    # --- SA-CLV-01 -------------------------------------------------------
    def test_clv01_cambio_propio_revoca_las_otras_sesiones(self):
        self.alta("admin_clv", "administrador", "ClaveVieja123", "clv-alta")
        uid = self.id_de("admin_clv")
        otra = self.cliente_como("admin_clv", "ClaveVieja123")
        actual = self.cliente_como("admin_clv", "ClaveVieja123")
        r = actual.post(f"/usuarios/{uid}/clave",
                        json={"clave": "ClaveNueva456", "clave_actual": "ClaveVieja123"},
                        headers={"Idempotency-Key": "clv-1"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertGreaterEqual(r.json()["sesiones_revocadas"], 1)
        self.assertEqual(otra.get("/sesion").status_code, 401)
        self.assertEqual(actual.get("/sesion").status_code, 200)

    def test_clv01_reintento_idempotente_con_otra_clave_no_finge_exito(self):
        """La misma Idempotency-Key con otra clave nueva no puede devolver
        «clave actualizada» sin haberla cambiado (el digest omite la clave)."""
        self.alta("rec_clv", "recepcion", "ClaveVieja123", "clv-alta-2")
        uid = self.id_de("rec_clv")
        r1 = self.admin.post(f"/usuarios/{uid}/clave", json={"clave": "ClaveNueva456"},
                             headers={"Idempotency-Key": "clv-rep"})
        self.assertEqual(r1.status_code, 200, r1.text)
        r2 = self.admin.post(f"/usuarios/{uid}/clave", json={"clave": "OtraClave789"},
                             headers={"Idempotency-Key": "clv-rep"})
        if r2.status_code == 200:
            # Si se informa éxito, la clave informada debe ser la vigente.
            self.cliente_como("rec_clv", "OtraClave789")
        else:
            self.assertEqual(r2.status_code, 409, r2.text)

    def test_clv01_cambio_por_admin_revoca_todas_las_sesiones_del_usuario(self):
        self.alta("rec_clv2", "recepcion", "ClaveVieja123", "clv-alta-3")
        uid = self.id_de("rec_clv2")
        sesion = self.cliente_como("rec_clv2", "ClaveVieja123")
        r = self.admin.post(f"/usuarios/{uid}/clave", json={"clave": "ClaveNueva456"},
                            headers={"Idempotency-Key": "clv-adm"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(sesion.get("/sesion").status_code, 401)


if __name__ == "__main__":
    unittest.main()
