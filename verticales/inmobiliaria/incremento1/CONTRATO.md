# Contrato lógico — inmobiliaria comercial

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada). Sirve a `003/T005` y a los T-DIS de H1-H2.

## Permisos y tenant
- Empresa única `EMP-SINTETICA-001`; otra empresa → `AccesoDenegado` con evidencia.
- Portal por cliente: `vista_cliente` solo expone unidades vinculadas; recurso ajeno → denegado.

## Estados e invariantes
- Unidad: `reserva_vigente` única (la segunda queda «en conciliacion»); `promesada` solo con firmas completas.
- Cotización: versionada; variar el precio crea versión nueva sin alterar la anterior.
- Cita: requiere zona; la aceptación del interesado la deja `pendiente_autorizacion`; la reprogramación conserva referencia.
- Promesa: firmas parciales → `pendiente`; documento con huella sha256 que cambia al cambiar el contenido.
- Cuota: imputación idempotente por clave; recordatorio siempre borrador.
- Postventa: clasificación provisional; «negar garantía» escala; reapertura preserva historial.

Ver `COBERTURA.md`.
