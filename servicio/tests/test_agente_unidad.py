"""Agente N0 — capa de dominio pura (V1-ISSUE-29, spec 005).

AG-U01..AG-U06 (specs/005-hotel-agente-reservas/acceptance.md): sin base ni
red. Ninguna prueba llama a un proveedor real de modelo: el puerto se ejerce
con el guionado y el SinAdaptador.
"""
import unittest
from datetime import date, timedelta

from servicio.agente import (
    DecisionInvalida,
    MAX_SALUDO,
    NIVELES,
    componer,
    redactar,
    validar_decision,
    verificar,
)
from servicio.modelo_lenguaje import ModeloGuionado, NoConfigurado, SinAdaptador

HOY = date.today()
MANANA = HOY + timedelta(days=1)
EN_3 = HOY + timedelta(days=3)

OFERTA_EJEMPLO = {
    "oferta": [
        {
            "habitacion_id": "HAB-SINT-101",
            "tipo": "doble",
            "tarifa_noche_clp": 50000,
            "total_clp": 100000,
            "politica_cancelacion": "cancelación gratuita hasta 48 horas antes",
            "vigente_hasta": "2026-12-01T10:00:00",
        }
    ],
    "emitida_en": "2026-12-01T09:45:00",
    "vigencia_minutos": 15.0,
}

POLITICA = {"nivel": "N0", "max_noches": 30, "max_personas": 30}


class RedactarTest(unittest.TestCase):
    def test_ag_u01_redacta_datos_personales_y_conserva_fechas_y_personas(self):
        texto = (
            "Hola, somos 2 personas del 10 al 12 de diciembre. "
            "Mi RUT es 12.345.678-5, mi tarjeta 1234 5678 9012 3456, "
            "correo juan.perez@example.com y teléfono +56 9 8765 4321. "
            "Mi otro mail es maria@hotel.cl y mi celu 987654321."
        )
        salida = redactar(texto)
        for prohibido in (
            "12.345.678-5",
            "1234567890123456",
            "1234 5678 9012 3456",
            "juan.perez@example.com",
            "maria@hotel.cl",
            "+56 9 8765 4321",
            "987654321",
        ):
            self.assertNotIn(prohibido, salida, f"quedó sin redactar: {prohibido}")
        self.assertIn("2 personas", salida)
        self.assertIn("10 al 12 de diciembre", salida)


class ValidarDecisionTest(unittest.TestCase):
    def test_ag_u04_rechaza_herramienta_desconocida(self):
        with self.assertRaises(DecisionInvalida):
            validar_decision(
                {"herramienta": "crear_reserva", "argumentos": {}},
                POLITICA,
                herramientas_permitidas=NIVELES["N0"],
            )

    def test_ag_u04_rechaza_argumentos_invalidos(self):
        casos = [
            {"herramienta": "consultar_disponibilidad",
             "argumentos": {"inicio": EN_3.isoformat(), "fin": MANANA.isoformat(), "personas": 2}},
            {"herramienta": "consultar_disponibilidad",
             "argumentos": {"inicio": MANANA.isoformat(), "fin": EN_3.isoformat(), "personas": 0}},
            {"herramienta": "consultar_disponibilidad",
             "argumentos": {"inicio": MANANA.isoformat(), "fin": HOY.isoformat(), "personas": 2}},
        ]
        for decision in casos:
            with self.assertRaises(DecisionInvalida, msg=str(decision)):
                validar_decision(decision, POLITICA, herramientas_permitidas=NIVELES["N0"])

    def test_ag_u04_rechaza_rango_sobre_el_maximo_de_la_politica(self):
        politica_corta = {**POLITICA, "max_noches": 5}
        decision = {
            "herramienta": "consultar_disponibilidad",
            "argumentos": {"inicio": MANANA.isoformat(), "fin": (MANANA + timedelta(days=9)).isoformat(), "personas": 2},
        }
        with self.assertRaises(DecisionInvalida):
            validar_decision(decision, politica_corta, herramientas_permitidas=NIVELES["N0"])

    def test_ag_u05_rechaza_campos_no_permitidos(self):
        for campo in ("empresa_id", "tarifa", "total", "rol", "precio"):
            decision = {
                "herramienta": "consultar_disponibilidad",
                "argumentos": {
                    "inicio": MANANA.isoformat(),
                    "fin": EN_3.isoformat(),
                    "personas": 2,
                    campo: "valor-inyectado",
                },
            }
            with self.assertRaises(DecisionInvalida, msg=campo):
                validar_decision(decision, POLITICA, herramientas_permitidas=NIVELES["N0"])

    def test_decision_valida_pasa(self):
        validar_decision(
            {
                "herramienta": "consultar_disponibilidad",
                "argumentos": {"inicio": MANANA.isoformat(), "fin": EN_3.isoformat(), "personas": 2},
            },
            POLITICA,
            herramientas_permitidas=NIVELES["N0"],
        )


class VerificarTest(unittest.TestCase):
    def test_ag_u02_rechaza_referencia_a_item_ajeno_al_turno(self):
        borrador = {
            "plantilla": "cotizacion",
            "campos": {"item": 0},
            "saludo": "Buenas tardes",
        }
        veredicto = verificar(borrador, resultados={"otra_herramienta": {}})
        self.assertEqual(veredicto, "rechazo:referencia_inexistente")

    def test_ag_u03_rechaza_saludo_con_digitos_o_monto(self):
        for saludo in ("Total $50.000", "llámenes al 555", "son 45000 pesos"):
            borrador = {"plantilla": "cotizacion", "campos": {"item": 0}, "saludo": saludo}
            veredicto = verificar(borrador, resultados={"consultar_disponibilidad": OFERTA_EJEMPLO})
            self.assertEqual(veredicto, "rechazo:cifra_en_texto_libre", saludo)

    def test_verificacion_ok(self):
        borrador = {"plantilla": "cotizacion", "campos": {"item": 0}, "saludo": "Buenas tardes"}
        self.assertEqual(
            verificar(borrador, resultados={"consultar_disponibilidad": OFERTA_EJEMPLO}),
            "ok",
        )


class ComponerTest(unittest.TestCase):
    def test_ag_u06_cotizacion_con_las_cifras_exactas_de_la_oferta(self):
        texto = componer(
            "cotizacion",
            {"item": 0},
            saludo="Buenas tardes",
            resultados={"consultar_disponibilidad": OFERTA_EJEMPLO},
        )
        item = OFERTA_EJEMPLO["oferta"][0]
        self.assertIn("HAB-SINT-101", texto)
        self.assertIn("$50.000", texto)   # tarifa por noche
        self.assertIn("$100.000", texto)  # total
        self.assertIn(item["politica_cancelacion"], texto)
        self.assertIn(item["vigente_hasta"], texto)
        self.assertIn("Buenas tardes", texto)

    def test_componer_sin_disponibilidad_no_contiene_montos(self):
        texto = componer(
            "sin_disponibilidad",
            {},
            saludo="Hola",
            resultados={"consultar_disponibilidad": {"oferta": []}},
        )
        self.assertNotIn("$", texto)


class PuertoModeloTest(unittest.TestCase):
    def test_sin_adaptador_lanza_no_configurado(self):
        with self.assertRaises(NoConfigurado):
            SinAdaptador().decidir(mensajes=[{"rol": "user", "texto": "hola"}], herramientas=[])

    def test_guionado_entrega_decisiones_en_orden(self):
        guionado = ModeloGuionado([
            {"herramienta": "consultar_disponibilidad",
             "argumentos": {"inicio": MANANA.isoformat(), "fin": EN_3.isoformat(), "personas": 2}},
        ])
        decision = guionado.decidir(mensajes=[], herramientas=["consultar_disponibilidad"])
        self.assertEqual(decision["herramienta"], "consultar_disponibilidad")


if __name__ == "__main__":
    unittest.main()
