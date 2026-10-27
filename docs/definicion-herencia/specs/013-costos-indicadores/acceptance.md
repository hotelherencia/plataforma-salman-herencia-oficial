# Aceptacion F12

Estado: NO_EJECUTADA. Revisor por nombrar D42. Las afirmaciones siguientes son resultados esperados, no resultados obtenidos.

| Caso | Requisito | Estimulo | Resultado esperado |
| --- | --- | --- | --- |
| TC-FIN-007-P | FIN-007 | Costo de lavado llega a lote y documento proveedor desde cuenta de estadía. | Detalle llega a tarea, lote, compra o servicio fuente |
| TC-FIN-007-N | FIN-007 | Cargar mismo costo como linea directa y otra copia por reporte. | Unicidad de fuente y base de distribución impiden duplicado. |
| TC-FIN-008-P | FIN-008 | Bolsa 100000 distribuye 60000/40000 y conserva total. | Suma de asignaciones coincide con bolsa y no duplica salarios |
| TC-FIN-008-N | FIN-008 | Sumar sueldos completos y además horas directas ya incluidas sin descontar. | Control de reconciliacion falla; corregir bolsa antes de cierre. |
| TC-KPI-001-P | KPI-001 | 193/510 produce 37,84% como ejemplo histórico fechado, no pronostico. | Marzo parcial no se muestra como un mes completo |
| TC-KPI-001-N | KPI-001 | Mes parcialmente informado presentado como ocupación mensual completa. | Indicador etiqueta parcial y no compara sin advertencia. |
| TC-KPI-002-P | KPI-002 | Ingreso alojamiento 200000, 4 noches vendidas,10 disponibles: ADR50000 y RevPAR20000. | Cada indicador permite reconstruir el cálculo desde cargos |
| TC-KPI-002-N | KPI-002 | Denominador cero o ingreso incluye garantía e impuesto no configurado. | NO_APLICA o validación de definición; nunca infinito o margen falso. |
| TC-KPI-003-P | KPI-003 | Click en tres habitaciones pendientes muestra tres tareas reales. | Cada alerta abre registro fuente y responsable |
| TC-KPI-003-N | KPI-003 | Aseo intenta abrir desde tablero una cuenta de huésped. | 403 y sin datos financieros aunque conozca URL. |
| TC-SOC-012-P | SOC-012 | Reserva 140000 con anticipo 70000 se reporta una conversion de 140000, no 210000. | Una reserva enviada por navegador y servidor cuenta una vez; devolución se registra internamente sin inventar API externa de borrado. |
| TC-SOC-012-N | SOC-012 | Pixel y servidor usan IDs diferentes para el mismo hecho. | Prueba bloquea configuración; dedup requerida antes de activar. |
| TC-SOC-018-P | SOC-018 | Diez reservas y seis canceladas muestran cuatro estadías, no diez ventas realizadas. | Reporte distingue reserva captada, cobro y margen de estadía; trafico desconocido permanece visible. |
| TC-SOC-018-N | SOC-018 | Sumar comisión de canal y deducirla otra vez del neto recibido. | Reconciliacion detecta duplicación y reporte queda observado. |
| TC-REV-002-P | REV-002 | Modelo validado reporta error frente a baseline y rango. | Con datos insuficientes no se pública recomendacion como precision demostrada. |
| TC-REV-002-N | REV-002 | Datos escasos y cifra precisa presentada como certeza o actualizacion automática. | Etiqueta EXPERIMENTAL/NO_APLICA y sin cambio de precio. |
| TC-FIN-010-P | FIN-010 | Compra equipo 100000: compromiso 100000 luego pago 100000, flujo sólo 100000. | Una compra de equipo no se suma dos veces a costos operativos y flujo por falta de clasificación. |
| TC-FIN-010-N | FIN-010 | Reporte suma compromiso+pago y muestra 200000 gastados. | Reconciliacion de estados falla; no publicar ese resultado. |

El cierre exige registrar comando/herramienta realmente usada, fecha, entorno, build, dataset, resultado, evidencia y aprobador; controles transversales F21 y enlaces del paquete completos. Si sólo se usa simulador de proveedor, conservar el estado SANDBOX/SIMULADO.
