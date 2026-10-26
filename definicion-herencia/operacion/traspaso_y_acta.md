# Protocolo de traspaso y acta con observaciones

## Preparación
Confirmar operador/emisor/empleador actual y receptor, contrato de arriendo, fecha/hora de autoridad. Responsable empresario y contador por designar. Inventariar todos los canales y reservas de 2027, estadías cruzadas, grupos/convenios, vouchers, promesas de compensación. Registrar cada pago, cuenta de ingreso, quien cobro, evidencia, garantía y devolución. Reserva futura no implica fondos recibidos por Herencia.

## Anexos de entrega
A.Reservas y condiciones congeladas. B.Anticipos,garantías,saldos y fondos por rendir. C.Estadías que cruzan 31 diciembre, noches/desayunos/consumos/comisiones asignados segun acuerdo escrito. D.Caja,cartolas,liquidaciones,cuentasporcobrar/pagar y diferencias tardias. E.Inventario por ubicacion/lote,ropa dentro/fuera del hotel,propiedad y condición de activos. F.Personal,contratos,descansos y obligaciones revisados legalmente; no presumir despidos/recontratacion. G.Proveedores,permisos,seguros y servicios. H.Dominios,redes,Booking,correo,pagos,usuarios y revocacion segura. I.Reclamos,incidentes,objetos y promesas. J.Acta firmada con observaciones y responsables.

## Corte en sistema
1.Exportación controlada y hash,staging por esquema y origen.2.Validar identidad/fechas/unidades/monedas/duplicados y reglas por fila.3.Conteos y totales por reserva,pago,cuenta,inventario.4.Simulacro con copia anonima y conciliación comparada.5.Respaldo y aprobación formal.6.Congelar escrituras salientes segun ventana acordada manteniendo recepción 24 h y registro contingencia numerado.7.Carga idempotente,verificación de saldos y autoridad nueva.8.Reconciliar operaciones durante ventana.9.Retirar accesos anteriores después de verificar nuevos y conservar auditoría.

## Cuadraturas
Todas las reservas abiertas tienen quien presta servicio y quien custodia fondos. Anticipo acreditado cliente se conserva aunque fondos por rendir no lleguen. Total por moneda del acta coincide con saldos iniciales; cuentas por rendir no se suman como banco. Inventario aceptado=conteo documentado por ubicacion, no libros históricos. El origen de cada activo es propio/tercero/en disputa. No firmar recibido conforme para datos no comprobados.

## Modelo de observacion
ID,anexo,objeto,cantidad/importe,moneda,fuente,entregado/pendiente/disputa,explicacion,responsable propuesto,acuerdo/evidencia,fecha compromiso y cierre. Acta definitiva requiere revisión contractual/contable; esta estructura no adjudica responsabilidades jurídicas.

## Ventana posterior
Revisar liquidaciones tardias,comisiones,devoluciones y cargos deperiodos previos segun mecanismo acordado. Mantener identificadores y fecha del servicio para no crear venta nueva. Reversion técnica de carga no revierte pagos reales; compensar y conciliar con autorización. Fecha 1 enero 2027 es objetivo, no prueba de readiness.
