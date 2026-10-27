# Incremento 0 — reserva local del hotel

Fecha: 2026-10-27. Único código autorizado por la instrucción de cierre de definición. Módulo local, sin UI de producción y sin red. El hotel de cara al huésped sigue **Bloqueado**: esta prueba no desbloquea ninguna historia (H1/H2/H3 permanecen Bloqueadas y sus T-IMP no pasan a Lista).

## Alcance

- Una empresa fija en memoria (`EMPRESA_FIJA`), con datos sintéticos marcados como tales (`EMP-SINTETICA-001`, huéspedes `DOC-SINT-*`).
- Consulta de disponibilidad por rango de fechas y ocupación.
- Reserva local de la última unidad con prueba de que dos reservas simultáneas no confirman las dos (control de concurrencia con cerrojo en memoria).
- Puertos vacíos, sin implementación real, para PMS, canal, pago y documento tributario. Cada puerto devuelve `no configurado` y no simula éxito.
- Ningún mensaje, cobro ni emisión.

## Fuera del incremento 0

H2 completo, H3, FR-003 (conectores Booking/Airbnb), FR-004 (cobro y DTE), FR-007 (pedido a habitación), FR-010 a FR-014, T-IMP de las tres historias, cualquier adaptador y cualquier migración.

## Supuestos de construcción (no decisiones ratificadas)

- **Q-CORE-01:** el módulo opera con una sola empresa en memoria y niega el acceso cruzado (`AccesoDenegado`). SUPUESTO DE CONSTRUCCIÓN, 2026-10-27: caduca cuando 000-core/T003 se firme.
- **Q-HOT-01:** no se construye un PMS ni se declara fuente de verdad; el inventario del incremento 0 es un puerto local con prueba de una sola reserva para la última habitación, sin canales.
- **Q-HOT-03:** sin concierge, WhatsApp ni autonomía; el límite de 0 CLP de la constitución no se ejerce aquí porque no hay agente ni cobro.
- **Q-CORE-02:** no se elige proveedor DTE ni se emiten boletas ni facturas; el cobro queda detrás del puerto de pago, que devuelve `no configurado`.
- **FR-003:** sin contrato con Booking/Airbnb; el puerto de canal devuelve `no configurado`.

## Ejecutar las pruebas

Desde esta carpeta (`verticales/hotel/incremento0`):

```bash
python -m unittest discover -s tests -t . -v
```

Solo biblioteca estándar de Python; no instala dependencias ni toca la red.
