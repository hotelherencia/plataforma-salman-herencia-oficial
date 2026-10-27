# Operación y continuidad

## RB01 - Pago incierto
Recepción no vuelve a cobrar por ver timeout. Consultar intento mismoID; comprobar proveedor,monto,moneda. Si autorizado, registrar una vez y validar cupo. Si no resoluble, UNKNOWN y responsable finanzas; comunicar pendiente al huésped sin afirmar rechazo. Cobro alternativo sólo después de comprobar ausencia o plan de compensación aprobado.

## RB02 - Caida de Booking/conector
Detectar retraso/falla de capacidad. Pausar automatismos afectados, revisar reservas recientes, decidir stopsell/allotment segun política y acceso. No declarar sincronizado un CSV manual. Tras recuperación leer estado actual, reconciliar versiones,procesar pendientes y reabrir ventas con responsable.

## RB03 - Internet o sistema local caido
Usar exportación protegida de llegadas/salidas/saldos mínimos, hoja contingencia numerada y responsable. No registrar tarjetas ni copias PII innecesarias. Reserva nueva se verifica con autoridad de inventario; si no se puede, no confirmar online libremente. Al restaurar, reingresar poridcontingencia y cuadrar caja/ocupacion; doble reingreso rechazado.

## RB04 - IA o mensajeria caida
Núcleo transaccional continua. Pausar bot/herramientas; tomar bandeja por recepción; cola conserva finalidades/ventanas y revalida antes de enviar. Tokenrevocado no obliga a apagar hotel. No ejecutar orden sensible de texto del cliente.

## RB05 - Seguridad
Contener cuenta/conector,revocar sesiones,proteger evidencia con acceso mínimo,notificar responsable seguridad y propietario. Evaluar obligaciones de notificación conforme régimen vigente con asesor. No borrar logs ni exponer datos al investigar. Recuperar credenciales con prueba independiente y nueva autorización.

## RB06 - Restauración
Ensayar copia+PITR en entorno aislado; comprobar hash,conteos,reservas,cuentas,eventos. Antes de reabrir sincronización consultar hechos externos ocurridos después del punto restaurado. Marcar eventos/pagos ya ejecutados para no repetir. MedirRPO/RTO real contra metas,documentar perdidas/resoluciones. Restaurar base no acredita restaurar archivos ni identidad; verificar ambos.

## RB07 - Migración de versión
Expandir esquema compatible,backfill con totales,migrar lecturas y aplicar constraints. Ensayar con volumen de prueba. Ante fallo detener nuevas escrituras dependientes,compensar cambios o roll-forward aprobado. Revertir binario no borra efectos financieros. No soltar RLS para acelerar migración productiva.

## RB08 - Habitación insegura
Bloquear venta/entrega física,identificar huéspedes y reservas afectadas,derivar a administrador/mantenimiento. Plan de reubicación autorizado con comunicación; el bot no decide indemnizaciones. Reabrir sólo por inspección competente y trazabilidad.

## Responsables y presupuesto
D20/D42 deben nombrar responsable primario/suplente por incidentes y cobertura. Mikhail/Cristóbal no quedan designados 24 x 7 por recibir el paquete. Costos: IAconstruccion/revision,hosting,base,archivos,backups,monitorizacion,correo,mensajes,canales,DTE,pagos y soporte; cada uno costo fijo+uso+contingencia. No se presenta total inventado sin cotizaciones.
