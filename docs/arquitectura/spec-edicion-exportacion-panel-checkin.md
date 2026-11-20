# SPEC: Edición amigable, Exportación única, Panel, Ocupación por tipo y Check-in (1/2 personas)

**Fecha:** 2026-11-20  
**Estado:** En ejecución (construcción 1 a 1)

## Requisitos

### SPEC-01: Edición amigable por registro (Reservas, Clientes, Leads, Solicitudes)
- Toda tabla operativa (/hotel/leads, /hotel/solicitudes, /hotel/clientes, /hotel/reservas, /hotel/reservas/[id]) debe permitir editar cada registro de forma directa y clara, con validación por campo, foco automático en el primer error y confirmación visual al guardar.
- En /hotel/reservas (listado), cada fila debe ofrecer acceso directo a la ficha de edición y edición rápida del huésped/contacto sin obligar a múltiples navegaciones.

### SPEC-02: Exportación con 1 formato único para todos los datos visibles
- Todos los datos visibles en las vistas operativas (/hotel/leads, /hotel/solicitudes, /hotel/clientes, /hotel/reservas, /hotel/ocupacion, /hotel/panel) deben poder exportarse bajo **1 formato único** en diseño, ordenamiento y presentación:
  - Encabezado estándar (Hotel Herencia, nombre de la vista, fecha/hora de emisión y rango/filtros aplicados).
  - Ordenamiento determinístico y columnas con etiquetas legibles en castellano (sin claves crudas internas cuando exista etiqueta).
  - CSV UTF-8 con BOM (\uFEFF) para apertura limpia en Excel.

### SPEC-03: Nombre del huésped en panel de entrada (en vez del código de reserva)
- En /hotel/panel, las tarjetas de «Situación de hoy» (Llegadas de hoy, Salidas de hoy, Huéspedes en casa, Llegadas/Salidas atrasadas) deben mostrar el **nombre del huésped** como texto visible del enlace, sin anteponer ni añadir el código de reserva visible (el enlace sigue apuntando a /hotel/reservas/{id} y conserva el 	itle completo).

### SPEC-04: Ocupación y reservas «por noche» con detalle desglosado por tipo de habitación
- Tanto en /hotel/panel («Ocupación y reservas por noche») como en /hotel/ocupacion, se debe presentar el desglose por tipo de habitación (capacidad, en casa, reservadas, disponibles).

### SPEC-05: Números visibles dentro de los colores («En casa», «Reservadas», «Disponibles») y diferenciación de alcance
- En el gráfico «Ocupación y reservas por noche» de /hotel/panel, cada bloque de color (En casa, Reservadas, Disponibles) debe mostrar su número de forma visible siempre que sea mayor que 0 (sin ocultarlo por umbral de porcentaje).
- La vista debe diferenciar explícitamente el alcance temporal seleccionado: **Distribución actual (Hoy)**, **Día**, **Semana** y **Mes**.

### SPEC-06: Check-in con especificación de 1 o 2 personas que ingresan
- Al registrar la llegada (POST /hotel/reservas/{reserva_id}/entrada y pantalla /hotel/estadia), recepción debe especificar si ingresan **1** o **2** personas (personas: 1 | 2).
- El backend valida la capacidad de la habitación, persiste eservas.personas dentro de la misma transacción e incluye personas en la clave de idempotencia y respuesta.
