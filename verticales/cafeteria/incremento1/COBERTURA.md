# Matriz de cobertura — casos de aceptación de la cafetería

Fecha: 2026-10-27. Sirve a `001/H1/T-ACC`, `001/H2/T-ACC` y `001/H3/T-ACC`.
19 tests en verde; los casos externos quedan en «puerto vacío».

## US-CAF-001 / H1

| Criterio | Prueba (tests/) | Estado |
|---|---|---|
| AC-US-CAF-001-01 | test_mesa_pedido_ids.py | verde |
| AC-US-CAF-001-02 | test_mesa_pedido_ids.py | verde |
| AT-001 | test_mesa_pedido_ids.py | verde |
| AT-002 | test_mesa_pedido_ids.py | verde |
| AT-003 | test_mesa_pedido_ids.py | verde |
| AT-004 | test_mesa_pedido_ids.py | verde |
| AT-015 | test_mesa_pedido_ids.py (×2: reparto y descuento/propina) | verde |
| ADV-001 | test_mesa_pedido_ids.py | verde |

## US-CAF-002 / H2

| Criterio | Prueba (tests/) | Estado |
|---|---|---|
| AC-US-CAF-002-01 | test_operacion_ids.py | verde |
| AC-US-CAF-002-02 | — | puerto vacío (archivo Eleventa real) |
| AT-007 | test_operacion_ids.py | verde |
| AT-008 | test_operacion_ids.py | verde |
| AT-009 | test_operacion_ids.py | verde |
| AT-010 | — | puerto vacío (archivo real) |

## US-CAF-003 / H3

| Criterio | Prueba (tests/) | Estado |
|---|---|---|
| AC-US-CAF-003-01 | test_mesa_pedido_ids.py | verde |
| AC-US-CAF-003-02 | test_operacion_ids.py | verde |
| AT-011 | test_operacion_ids.py | verde |
| AT-012 | test_operacion_ids.py | verde |
| AT-013 | ledger en servicio (propuestas, rechazos, expiraciones, ejecuciones) | verde (parcial local) |
| AT-016 | test_mesa_pedido_ids.py | verde |

Revisión: pendiente del visto bueno del propietario.
