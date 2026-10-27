# Contrato lógico — núcleo (000-core)

Fecha: 2026-10-27. **PROPUESTA TÉCNICA** (no ratificada). Sirve a `000-core/T005` y a los T-DIS de H1-H3.

## Permisos y tenant
- Empresa única `EMP-SINTETICA-001` fijada al construir el `Nucleo`; otra empresa → `AccesoDenegado`.
- Conectores con permisos explícitos (lectura/escritura); referencias vinculadas; placeholder con efectos desconocidos → bloqueado sin llamar al destino.

## Estados e invariantes
- Efecto de pago: una sola imputación por clave (`autorizado | rechazado | desconocido`); repetir devuelve el efecto existente.
- Deuda: solo un `autorizado` con el monto la cancela; un `rechazado` posterior no la borra.
- Aprobación: monto + parámetros exactos + vigencia + uso único; cualquier cambio → `EfectoNoAplicable`.
- Herramientas: efectos explícitos; lo no autorizado se excluye y registra sin ejecutar.

Ver `COBERTURA.md` (matriz AC → prueba con carga y fallos).
