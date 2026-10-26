# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Costos, presupuestos e indicadores

  @FIN-007 @TC-FIN-007-P
  Escenario: TC-FIN-007-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Costo de lavado llega a lote y documento proveedor desde cuenta de estadía.
    Entonces Detalle llega a tarea, lote, compra o servicio fuente

  @FIN-007 @TC-FIN-007-N
  Escenario: TC-FIN-007-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Cargar mismo costo como linea directa y otra copia por reporte.
    Entonces Unicidad de fuente y base de distribución impiden duplicado.

  @FIN-008 @TC-FIN-008-P
  Escenario: TC-FIN-008-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Bolsa 100000 distribuye 60000/40000 y conserva total.
    Entonces Suma de asignaciones coincide con bolsa y no duplica salarios

  @FIN-008 @TC-FIN-008-N
  Escenario: TC-FIN-008-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Sumar sueldos completos y además horas directas ya incluidas sin descontar.
    Entonces Control de reconciliacion falla; corregir bolsa antes de cierre.

  @KPI-001 @TC-KPI-001-P
  Escenario: TC-KPI-001-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando 193/510 produce 37,84% como ejemplo histórico fechado, no pronostico.
    Entonces Marzo parcial no se muestra como un mes completo

  @KPI-001 @TC-KPI-001-N
  Escenario: TC-KPI-001-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Mes parcialmente informado presentado como ocupación mensual completa.
    Entonces Indicador etiqueta parcial y no compara sin advertencia.

  @KPI-002 @TC-KPI-002-P
  Escenario: TC-KPI-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Ingreso alojamiento 200000, 4 noches vendidas,10 disponibles: ADR50000 y RevPAR20000.
    Entonces Cada indicador permite reconstruir el calculo desde cargos

  @KPI-002 @TC-KPI-002-N
  Escenario: TC-KPI-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Denominador cero o ingreso incluye garantía e impuesto no configurado.
    Entonces NO_APLICA o validación de definición; nunca infinito o margen falso.

  @KPI-003 @TC-KPI-003-P
  Escenario: TC-KPI-003-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Click en tres habitaciones pendientes muestra tres tareas reales.
    Entonces Cada alerta abre registro fuente y responsable

  @KPI-003 @TC-KPI-003-N
  Escenario: TC-KPI-003-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Aseo intenta abrir desde tablero una cuenta de huésped.
    Entonces 403 y sin datos financieros aunque conozca URL.

  @SOC-012 @TC-SOC-012-P
  Escenario: TC-SOC-012-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reserva 140000 con anticipo70000 se reporta una conversion de140000, no210000.
    Entonces Una reserva enviada por navegador y servidor cuenta una vez; devolución se registra internamente sin inventar API externa de borrado.

  @SOC-012 @TC-SOC-012-N
  Escenario: TC-SOC-012-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Pixel y servidor usan IDs diferentes para el mismo hecho.
    Entonces Prueba bloquea configuración; dedup requerida antes de activar.

  @SOC-018 @TC-SOC-018-P
  Escenario: TC-SOC-018-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Diez reservas y seis canceladas muestran cuatro estadías, no diez ventas realizadas.
    Entonces Reporte distingue reserva captada, cobro y margen de estadía; trafico desconocido permanece visible.

  @SOC-018 @TC-SOC-018-N
  Escenario: TC-SOC-018-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Sumar comisión de canal y deducirla otra vez del neto recibido.
    Entonces Reconciliacion detecta duplicación y reporte queda observado.

  @REV-002 @TC-REV-002-P
  Escenario: TC-REV-002-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Modelo validado reporta error frente a baseline y rango.
    Entonces Con datos insuficientes no se pública recomendacion como precision demostrada.

  @REV-002 @TC-REV-002-N
  Escenario: TC-REV-002-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Datos escasos y cifra precisa presentada como certeza o actualizacion automática.
    Entonces Etiqueta EXPERIMENTAL/NO_APLICA y sin cambio de precio.

  @FIN-010 @TC-FIN-010-P
  Escenario: TC-FIN-010-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Compra equipo100000: compromiso100000 luego pago100000, flujo solo100000.
    Entonces Una compra de equipo no se suma dos veces a costos operativos y flujo por falta de clasificación.

  @FIN-010 @TC-FIN-010-N
  Escenario: TC-FIN-010-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Reporte suma compromiso+pago y muestra200000 gastados.
    Entonces Reconciliacion de estados falla; no publicar ese resultado.
