# Hallazgos documentales y reglas de migración
**Fecha: 23/10/2026.** Análisis de 15 libros y 255 hojas. Los archivos originales no fueron modificados. Este inventario registra procedencia; no certifica vigencia jurídica, tributaria ni operativa.

## 1. Inventario de fuentes
| Archivo | Hojas | SHA-256 |
| --- | ---: | --- |
| % de ocupación habitaciones hotel(1).xlsx | 3 | 02594846 f 8 dfc 81 eec 0 ed 083634 f 12190 ae 1733 fb 185 f 718189 dbe 71 e 777 c 649 |
| % de ocupación habitaciones hotel.xlsx | 1 | 3 ab 881 dbd 81765084047290 c 744 e 4 e 63453 e 9 f 510 eb 32 b 9 ccd 89240 b 84 de 1 e 06 |
| INVENTARIO BEBIDAS.xlsx | 32 | 92 a 55 c 9 b 87 a 2 c 2 ed 96283 e 216 c 325 cae 4 fa 99 e 2697 a 6 e 6 fb 112 dc 98 e 4 f 040 e 96 |
| INVENTARIO GOLOSINAS.xlsx | 32 | 7622181 b 976 d 03 ae 3918 cb 7 cb 7 c 8763 a 145148 a 8 eaf 0 fb 349 fd 8 fe 9441 d 066 c 1 |
| Lavandería ropa cama-toallas.xlsx | 31 | e 6 f 599 fc 77 a 35341290 c 3 f 2072 e 367 c 2 dc 79 bebbe 72 ef 2 b 19 fe 4 bdcc 1 aafe 3 ec |
| Nómina Inventarios  Junio Hotel.xlsx | 33 | 69545773 d 94316 ba 211 dc 630 d 3 b 5073 fc 953 c 38 f 7685 a 168 c 3 b 484 d 59 a 69 cdfe |
| Nómina Inventarios Hotel Agosto.xlsx | 33 | caa 4 fe 01 ce 70 d 8285 f 497 bd 670 d 66 e 248 a 6 d 08 d 3 f 63443 d 61791205602606552 |
| Nómina Inventarios Hotel Octubre.xlsx | 33 | 72 e 6 d 67 b 4177693 e 470 c 3 ded 0 ecbf 17068 a 26 bab 8 fbc 7 ee 05 d 4 f 8 d 403 a 9 f 02 a 5 |
| Nómina Inventarios Hotel SEPTIEMBRE.xlsx | 33 | 4 e 5 abb 8 a 7 a 2 ca 5 a 713 c 4657 b 79145451 a 774686 e 2388 dfa 6366520 d 7 d 3 a 81144 |
| RETIRO CAJA HERENCIA HOTEL.xlsx | 1 | 53 cb 9 eecc 8 a 56 b 0 aa 8540094 bc 2 d 5 baab 7850 ca 08 afafb 4 bc 6 c 641 c 02 a 14 e 687 |
| Resumen Valorizado Bebidas y Golosinas.xlsx | 1 | 7767 c 6 dd 6203 c 151 f 45142 efdd 392 ce 4004156369513 aacef 444 b 5641735 c 261 |
| Sueldos_HERENCIA HOTEL_ENERO 2019.xlsx | 9 | 4 ab 12 e 2 defd 32 b 6795 c 11 e 45 a 25 b 0 d 37 dabd 331 d 1 fc 909759 fe 838867 b 2 f 82 ac |
| VALORES DE LAS HABITACIONES.xlsx | 8 | 53854 e 3 f 138 ad 26 ea 93 b 052007 eb 32 a 2 e 3 e 7 ba 2 d 6 cb 0 ed 1 aedcb 6 b 664892 ab 1 a |
| Organigrama Holding Salman 2018.xls | 4 | 0 eeab 557 dea 9 ecff 3196 c 38 b 21 b 983960 c 9 a 4 b 1 ac 458 e 259 c 3 ba 5 e 0 d 49 f 60 d 54 |
| booking septiembre.xls | 1 | f 055157 a 8 f 40 b 631793 ccb 9 f 56158 ba 8 d 7 d 04 b 96479 bf 72 f 6 b 1 c 4 a 7 c 078 e 783 a |

## 2. Malla societaria
Fuente: Organigrama Holding Salman 2018.xls, Hoja 1. M12:M13: Wembé 50/50 Ricardo/Sandra. M23:M24: Inmobiliaria Salman 99,5% Wembé y 0,5% Ricardo. T13:T14: SB 72,66% Ricardo y 27,34% Sandra. Z13:Z14 y AE13:AE14: Constructora y Herencia 50/50. K27:K31 y filas 40:41: filiales inmobiliarias. Se recuperó texto tanto de celdas como de cuadros de texto; las cifras relevantes también están explícitas en celdas.

Interpretación: registrar antecedentes históricos. No convertir el encabezado informal "empresas no relacionadas" en una calificación tributaria/legal. No afirmar que todas las sociedades son filiales de Wembé. Validar vigencias antes de activar una malla actual.

## 3. Ocupación
% de ocupación habitaciones hotel.xlsx, Hoja 1, B8:I37: noviembre 2019. Suma C8:C37 = 193 habitaciones-noche; D8:D37 = 510; F = 100 directas; H = 93 Booking. Ocupación calculada: 37,84%.

% de ocupación habitaciones hotel(1).xlsx, Enero 2020, B8:I38: 294 habitaciones-noche sobre 527; 148 directas y 146 Booking; 55,79%. Febrero 2020, B8:I36: 330/493; 169 directas y 161 Booking; 66,94%. Marzo 2020 tiene 17 filas con fecha y todos los conteos numéricos requeridos; 92 habitaciones-noche en esas filas. Las filas incompletas no se convierten en ceros.

Los dos archivos no son duplicados binarios ni representan el mismo período. Las columnas G e I dividen las habitaciones por canal por el total de habitaciones, no por las habitaciones ocupadas: no confundirlas con participación del canal dentro de las ventas. Los libros no demuestran por sí solos cuántas habitaciones estaban fuera de servicio.

## 4. Booking septiembre
booking septiembre.xls, Sheet 1, A1:L106: doce columnas para identificador, fecha de reserva, quien reserva, huésped, habitaciones, personas, noches, porcentaje de comisión, importe original, final, comisión y estado. Existen 105 filas de reservas: 79 Stayed, 13 No-Show y 13 Cancelled. H2:H106 indica 17%. El total de comisiones almacenado figura en K108.

No se utiliza la fecha Booked on como fecha de llegada ni se presume una moneda que el encabezado no identifica. Para conciliación actual se requieren fechas de servicio, moneda, liquidaciones, documentos y movimientos de banco. Los nombres y datos personales de huéspedes no se reproducen en este anexo ni en las pruebas sintéticas.

## 5. Tarifas
VALORES DE LAS HABITACIONES.xlsx contiene ocho hojas con tarifas, pilotos y acuse de informativo. En "Lunes 25", B4:J5 distingue configuración, valor de canal, dólar y tarifas con/sin IVA. I4 menciona 25% y I5 calcula 10%; C4 menciona 15%, diferente del 17% del reporte Booking. Las hojas contienen referencias temporales antiguas: no son un tarifario 2027.

"hoja de registro de informativo", A1:D2, contempla fecha, nombre, habitación y firma. Diseñar acuse digital del reglamento o informativo con versión del documento y fecha, sin presumir que equivale a consentimiento para publicidad.

## 6. Inventarios generales
Nómina Inventarios Junio: 33 hojas; "Inv- PEDIDOS" F2:G2 indica JULIO 2019, y existe una hoja denominada "31-6". Agosto, septiembre y octubre contienen plantillas diarias y resumen. En septiembre "01-9", B6:L6: producto, unidad, stock inicial, entrada, proveedor, factura, salida, stock final, stock en área y precio.

Septiembre y octubre, "Inv- PEDIDOS", I66 e I117: valores de error #REF!. No se deben copiar fórmulas rotas. Normalizar producto, unidad, ubicación, documento y movimiento; reconciliar bodega frente a área sin duplicar stock. Distinguir alimentos, limpieza, insumos, elementos reutilizables y activos.

## 7. Bebidas, golosinas y ventas complementarias
INVENTARIO BEBIDAS.xlsx y INVENTARIO GOLOSINAS.xlsx: 32 hojas cada uno; resumen AGOSTO y hojas diarias. B5:I5 contiene producto, stock anterior, fechas y cantidades de compra/venta, saldo y recibido por. El libro de bebidas conserva en B2 un título de golosinas aunque B6 y siguientes contienen bebidas.

Resumen Valorizado Bebidas y Golosinas.xlsx, Hoja 1: ventas con producto, cantidad, número de boleta, monto y fecha. Vincular venta a salida real de stock y, cuando corresponda, a cuenta de estadía, sin duplicar cobro en recepción y punto de venta.

## 8. Lavandería
Lavandería ropa cama-toallas.xlsx: 31 hojas, RESUMEN y días de septiembre. B4:F20 contempla ropa de cama con saldo anterior, entrada bodega, salida lavandería y saldo; B26:F29 contiene toallas. No se observa en esos encabezados identificación de habitación, estadía, ejecutor o lote individual.

Conservar el catálogo, mejorar nomenclatura y agregar estados, procedencia, lote, recepción parcial, faltantes, calidad y costo. El lavado es un servicio sobre un elemento reutilizable, no una baja de inventario por cada uso.

## 9. Caja
RETIRO CAJA HERENCIA HOTEL.xlsx, Retiros Hotel, B3:D: mes e importes CLP/USD; no contiene por sí sólo el circuito de arqueo, documento y depósito. Convertir el control mensual de retiros en registro de movimientos con fecha, moneda, responsable, destino, evidencia y conciliación.

## 10. Personal y remuneraciones
Sueldos_HERENCIA HOTEL_ENERO 2019.xlsx: nueve hojas. MES F9:F17 registra seis cargos de RECEPCIONISTA y tres de MUCAMA. Esto no demuestra dotación actual ni simultaneidad de contratos. MES, fila 8, contiene conceptos de sueldo, horas, descuentos, aportes y pagos; otras hojas incluyen bonos y transferencia.

Se detectaron 82 celdas con valor almacenado #REF! y 74 con #N/A en el libro; los valores almacenados no son una recalculación independiente. Hay referencias rotas y búsquedas no resueltas que requieren revisión. Recuperar campos y necesidades de control, no importar las tasas legales, salarios, contratos ni fórmulas como vigentes. No reproducir datos personales de los trabajadores en el paquete de desarrollo.

## 11. Regla transversal
Archivo histórico no equivale a dato inicial de producción. Antes de migrar: preservar original, validar hoja/fecha, normalizar unidades, separar datos personales, registrar transformaciones, detectar duplicados y obtener aprobación del responsable. Pruebas y demostraciones usan datos ficticios.
