from datetime import date, datetime
import sys
import unittest

from hotel_inventario.dominio import Huesped
from hotel_inventario.empresa import EMPRESA_FIJA
from hotel_inventario.servicio import (
    AccesoDenegado,
    servicio_con_una_unidad,
)

EMPRESA = EMPRESA_FIJA.id
UNIDAD = "HAB-SINT-101"
INICIO = date(2026, 11, 10)
FIN = date(2026, 11, 12)
HUESPED = Huesped(nombre="Huésped Sintético Uno", documento="DOC-SINT-0001")
LAS_15 = datetime(2026, 11, 10, 15, 0)


class AT010Test(unittest.TestCase):
    def test_AT_010_huesped_autenticado_recibe_sus_datos_y_la_consulta_ajena_se_deniega(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id

        datos = servicio.datos_reserva(EMPRESA, reserva_id, solicitante=f"huesped:{reserva_id}")
        self.assertEqual(datos.id, reserva_id)

        with self.assertRaises(AccesoDenegado):
            servicio.datos_reserva(EMPRESA, reserva_id, solicitante="huesped:OTRA-RESERVA")
        self.assertIn(
            ("consulta_reserva", reserva_id, "consulta ajena"),
            servicio.evidencia_denegaciones(EMPRESA),
        )

    def test_AT_010_la_peticion_de_cambio_queda_borrador_y_escala(self):
        servicio = servicio_con_una_unidad()
        reserva_id = servicio.reservar(EMPRESA, UNIDAD, INICIO, FIN, HUESPED).reserva.id
        resultado = servicio.pedir_cambio(
            EMPRESA, reserva_id, solicitante=f"huesped:{reserva_id}", descripcion="cambiar a habitación 103"
        )
        self.assertFalse(resultado.aplicado)
        self.assertTrue(resultado.escalado)
        reserva = next(r for r in servicio.reservas_confirmadas(EMPRESA) if r.id == reserva_id)
        self.assertEqual(reserva.unidad_id, UNIDAD)
        self.assertEqual(
            [e for e in servicio.registro_acciones(EMPRESA) if e.fuente == "pedir_cambio"][0].resultado,
            "escalado",
        )


class AT013Test(unittest.TestCase):
    def test_AT_013_cada_respuesta_registra_fuente_regla_identidad_y_resultado(self):
        servicio = servicio_con_una_unidad()
        entrada = servicio.registrar_accion(
            EMPRESA,
            fuente="conserje",
            regla="consulta_disponibilidad",
            actor="recepcion",
            resultado="ok",
            cuando=LAS_15,
        )
        self.assertEqual(entrada.fuente, "conserje")
        self.assertEqual(entrada.regla, "consulta_disponibilidad")
        self.assertEqual(entrada.actor, "recepcion")
        self.assertEqual(entrada.resultado, "ok")
        self.assertEqual(entrada.cuando, LAS_15)

    def test_AT_013_el_registro_rechaza_el_documento_completo_del_huesped(self):
        servicio = servicio_con_una_unidad()
        with self.assertRaises(ValueError):
            servicio.registrar_accion(
                EMPRESA,
                fuente="conserje",
                regla="check_in",
                actor="recepcion",
                resultado="ok",
                cuando=LAS_15,
                datos={"documento": "DOC-SINT-0001"},
            )


class AT014Test(unittest.TestCase):
    def test_AT_014_la_proyeccion_publica_es_lectura_sin_datos_de_huesped(self):
        servicio = servicio_con_una_unidad()
        proyeccion = servicio.proyeccion_publica(EMPRESA, INICIO, FIN, 2)
        self.assertEqual(len(proyeccion), 1)
        self.assertTrue(hasattr(proyeccion[0], "unidad_id"))
        self.assertFalse(hasattr(proyeccion[0], "huesped"))
        with self.assertRaises(AccesoDenegado):
            servicio.modificar_desde_proyeccion(EMPRESA, "reservar", {"unidad_id": UNIDAD})


class AT015Test(unittest.TestCase):
    def test_AT_015_el_flujo_hotelero_no_depende_de_otras_verticales(self):
        servicio_con_una_unidad()
        prohibidas = ("cafeteria", "inmobiliaria", "constructora", "hotel_reservas")
        cargadas = []
        for nombre, modulo in list(sys.modules.items()):
            if nombre.startswith("hotel_inventario"):
                for valor in vars(modulo).values():
                    nombre_valor = getattr(valor, "__name__", "")
                    if nombre_valor and any(p in nombre_valor for p in prohibidas):
                        cargadas.append(nombre_valor)
        self.assertEqual(cargadas, [])


if __name__ == "__main__":
    unittest.main()
