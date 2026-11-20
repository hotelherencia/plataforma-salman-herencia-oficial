"""Apoyo de pruebas: registrar los acompañantes que exige la Llegada (regla de negocio de #400)."""

import re


def registrar_acompanantes(cliente, reserva_id, cantidad, cabeceras):
    """Registra `cantidad` acompañantes con pasaporte distinto; `cabeceras` es un callable con Idempotency-Key."""
    for i in range(cantidad):
        r = cliente.post(
            f"/hotel/reservas/{reserva_id}/huespedes",
            json={"rol": "acompanante", "nombre": f"Acompañante {i + 1}", "documento_tipo": "pasaporte",
                  "documento": f"PA{re.sub(r'[^A-Za-z0-9]', '', reserva_id)[-6:]}{i}", "nacionalidad": "Chilena"},
            headers=cabeceras(),
        )
        assert r.status_code in (200, 201), r.text
