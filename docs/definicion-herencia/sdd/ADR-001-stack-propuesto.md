# ADR-001 - Arquitectura propuesta

Estado: PROPUESTA; decisionD45 por aprobar. Fecha 25 octubre 2026.

## Decisión propuesta
Monolito modular TypeScript: Next.js 16 para web/BFF/API propia; Node 24LTS para aplicación y worker; PostgreSQL17 como autoridad transaccional. Almacenamiento privado compatibleS3 para documentos; proveedorOIDC por elegir con MFA. Sesion navegador HttpOnly/Secure/SameSite y defensaCSRF; no JWT en localStorage. No se prescribe proveedor comercial ni se crean cuentas.

## Razón
Un sólo lenguaje reduce friccion entre agentes; esquema central permite transacciones para cupos y dinero. Worker despliega fuera del proceso web aunque comparte repositorio y contratos; colas outbox durables en Postgres inicialmente. Evita microservicios/Redis obligatorios sin carga demostrada. Equipo puede proponer alternativa con evidencia, no cambiar silenciosamente.

## Módulos
Core, inventoryHotel, booking, payments, reception, supplies, housekeeping, food, assets, workforce, finance, analytics, channels, CRM, messaging, assistant, campaigns, portal, migration. Dependencias por servicio/evento, no SQL libre desde otra capa. API3.1.1, validación de esquema, SQL parametrizado, migraciones versionadas, RLS y pruebas de alcance.

## Dinero, reserva y eventos
Transacción corta sin llamada externa bajo lock. Crear intento/outbox, llamar proveedor fuera del lock, verificar y aplicar idempotente al retorno. Filas inventario tipo/noche bloqueadas en orden; constraint físico no solape. Eventos conID y versión; reintentos no exactly-once prometido, efectos idempotentes demostrados.

## Despliegue y versiones
Contenedores/artefactos reproducibles, ambientes dev/test/staging/prod separados. Fijar parches soportados después de comprobar avisos de seguridad y licencias. No instalar una versión histórica 16.0 sólo por nombre de linea. ORM, libreria de tests y OIDC se eligen por prueba de transacciones/RLS y soporte, registrados en ADR derivado. SDK de proveedor oficial si disponible, no wrapper no verificado.

## Alternativas y consecuencias
Microservicios descartados inicialmente por costo de consistencia y operación. Backend separado puede aprobarse si el equipo demuestra necesidad. PMS externo puede usarse como contingencia/adaptador sin cambiar autoridad sin decisión. Dependencia OIDC exige recuperación de cuentas y acceso de emergencia controlado; respaldo de base no conserva secretos del proveedor por si sólo.

FuentesS02/S03/S08/S14/S18; no hay stack instalado ni benchmark medido. Objetivos de infraestructura quedan como metas sujetas a presupuestoD18/D20.
