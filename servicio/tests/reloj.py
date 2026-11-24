"""Reloj de pruebas: las reglas que dependen de la hora (llegada 14:00, 24 h) leen `hotel_sql.ahora`."""
from datetime import date, datetime, time
from unittest import mock


def a_las(dia: date, hora: time = time(14, 0)):
    """Fija el reloj del servidor en `dia` a `hora` (por defecto, la hora de llegada). Sirve de decorador o de contexto."""
    instante = datetime.combine(dia, hora)
    return mock.patch("servicio.hotel_sql.ahora", new=lambda: instante)
