# Reglas financieras y ejemplos de aceptacion

Todos los importes siguientes son SINTÉTICOS. No son tarifas, tasas, precios ni saldos reales de Herencia. MonedaCLP, enteros; no flotantes binarios.

## R01 - Precio y redondeo
Resolver tarifa específica por fecha/tipo/ocupacion/canal; rechazar empates de prioridad antes de publicar. Aplicar descuentos autorizados en orden, con acumulabilidad explícita. Congelar componentes por noche y política. Si el precio incluye impuesto, neto=redondear(bruto/(1+tasa)); impuesto=bruto-neto. Si es neto, impuesto=redondear(neto*tasa). Total suma lineas; tasa y criterio se validanD07. Redondeo propuestaHALF_UP por linea, ajuste de centavos explícito para preservar total. No restar comisión como descuento.

## R02 - Reserva, devengo y pago
Dos noches a 70000: precio 140000. Anticipo 70 mil verificado: pago 70000, cuenta saldo 70000; no ingreso 210000. Cuando se presta la primera noche, cargo de alojamiento 70000 con fecha de servicio; la segunda genera otro 70000. Saldo final se cobra 70000: pagos totales 140000. La emisión fiscal sigue regla aprobada por contador, no se deduce del devengo gerencial. Garantía por daños es pasivo/custodia separado y no reduce automáticamente precio.

## R03 - Anticipo saliente
Reservaenero precio 200000, cliente abono 100000 al operador actual. Cuenta del huésped reconoce crédito 100000 sustentado; saldo a cobrar 100000. Traspaso registra fondos por rendir 100000 hasta acta/abono verificado, no bancoHerencia 100000 ficticio. Si entrega 60000, fondos por rendir 40000 y recibido 60000, sin aumentar deuda del huésped. Responsabilidad jurídica segun acuerdo/revision, no imposicion del sistema.

## R04 - Liquidación neta y comisión separada
CobrosA100000+B80000=180000. Comisión descontada 5400: abono 174600, desglose bruto 180000-comisión 5400=neto 174600. Conciliar dos cobros con un abono y una comisión. Variante: canal paga 180000 y factura 5400 aparte; banco 180000 y cuenta por pagar 5400. Nunca restar 5400 del abono si no se desconto. Repetir importación conserva mismo grupo.

## R05 - Aplicaciones y devoluciones
Pago 100000 aplicado 60000 areservaA y 40000 aB: disponible 0; no permitir tercer uso. Devolver 20000 deA confirmado: reversion de aplicacionA20000 y refund 20000. Si el cargo del servicio permanece, A vuelve a deber 20000; si hay cancelación, registrar ajuste de cargo 20000 por separado. No borrar pago ni asumir que devolver implica cancelar. Refund total acumulado<=pagado-originalmente-reembolsado. Cambiar monto inválida aprobación.

## R06 - Caja
Fondo 20000 + efectivo 150000 - retiro 100000 - devolución 10000 = esperado 60000. Contado 59000: diferencia-1000 abierta, con motivo/revisor; no crear venta 1000 ni borrar retiro. Depositar efectivo es traslado caja/banco, no un ingreso nuevo. Separar caja por moneda y operador de turno.

## R07 - Inventario y recepción
Orden 20 unidades, recepción 12: existencia+12 y pendiente 8. Factura 20 sin entrega completa genera excepción, no stock+8 ficticio. Transferencia bodegaA aB por 3 produce A-3/B+3, grupo neto 0. Corrección por conteo exige corte de movimientos y ajuste firmado. Unidades por presentacion: caja 12 botellas a 12000 equivale1000/botella antes de costos/impuestos aprobados; comparar contenido/calidad iguales.

## R08 - Producción y desayuno
Lote 10 porciones con ingredientes reales costo 18000: costo1800/porcion. Servir 8 usa 8 porciones=14400; restantes 2=3600 se conservan con vencimiento o se registran como merma. No consumir ingredientes otra vez por cada servicio. Derecho de desayuno no prueba consumo. Salida de hotel manana después de noche tiene derecho segun política; llegada temprano requiere inclusion/adicional aprobado. Restricciones necesarias sólo cocina.

## R09 - Textiles y lavado
Enviar 2 sábanas y recibir 1 aceptada: enviada 2=recibida 1+pendiente 1. No cerrar lote; sábana aceptada vuelve limpia, otra queda fuera. Lavado porpieza/kilo requiere base aprobada. La sábana usada no se da de baja patrimonial. Baja por daño requiere motivo y valor separado del costo de lavado.

## R10 - Incentivos
Propuesta de fórmula configurable: puntos=sum(peso_tipo*tarea_aceptada*participacion_trabajador*factor_calidad). Participaciones de una tarea suman 1; tareas duplicadas o no aceptadas cuentan 0. Bono=min(tope,redondear(puntos*valor_punto)). Ejemplo ficticio: tareas puntos 4 y 6, segunda compartida 50%: puntos 7; valor 1000 y tope 6000 =>bono 6000, no 7000. No define política laboral real; D17 debe aprobar pesos/topes y proceso de pago.

## R11 - Costos y margen
Costo directo exige fuente única y gradoMEDIDO/ESTIMADO. Una factura de compra no es simultaneamente costo consumido por todas las habitaciones. Bolsa comun excluye montos ya directos; distribuir proporcionalmente y asignar residuo de redondeo determinista. Ejemplo bolsa 10000, pesos 1:1:1 =>3334+3333+3333=10000. Si denominador 0 no repartir arbitrariamente: costo no asignado visible.

## R12 - Noches y ocupación
Una habitación con 2 personas por 2 noches=>2 habitaciones-noche y 4 personas-noche. Mudanza a medio día no genera otra venta de esa noche; si costo se distribuye entre cuartos, pesos suman 1. Enero 17*31=527 noches físicas; ocupadas 280=>53,13%. Si 10 noches fuera de venta, denominador comercial 517 y ocupación comercial 54,16%. No confundir esa base con número de camas.

## R13 - Presupuesto e inversion
Separar aprobado, comprometido, recibido/devengado y pagado; no sumarlos como gasto cuatro veces. Renovación costo total incluye equipo,despacho,instalación,retiro e impuestos segun criterio. Días bloqueados producen estimación de ingreso no realizado, no gasto contable inventado. Equipo pagado no es instalado/aceptado.

## R14 - Precio sugerido y medición
Pronostico sólo si historial suficiente y calidad visible; comparar con regla simple y reservar decisiones al aprobador. No adquirir datos competidores por acceso no permitido. Valor conversionreserva identifica un evento; anticipo no segunda venta. Cancelaciones ajustan reporte; plataformas externas admiten o no corrección segun contrato, no asumir.
