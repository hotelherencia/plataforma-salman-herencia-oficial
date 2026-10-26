# Interfaces F20

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| stageMigration | POST /companies/{company_id}/migration-batches | MigrationInput | ResourceResult | migration.stage |
| commitMigration | POST /companies/{company_id}/migration-batches/{id}/commit | ApprovalDecision | ResourceResult | migration.commit |
| listMigration | GET /companies/{company_id}/migration-batches | - | Page | migration.read |

Eventos emitidos: migration.validated, migration.committed, handover.exception. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
