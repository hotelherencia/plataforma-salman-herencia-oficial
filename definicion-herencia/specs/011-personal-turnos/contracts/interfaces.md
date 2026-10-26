# Interfaces F10

Contratos propios; proveedores externos se comprueban por adaptador y cuenta.

| Operación | Metodo/ruta | Entrada | Salida | Permiso |
| --- | --- | --- | --- | --- |
| scheduleShift | POST /companies/{company_id}/shifts | ShiftInput | ResourceResult | staff.schedule |
| recordAttendance | POST /companies/{company_id}/attendance | AttendanceInput | ResourceResult | staff.attendance |
| calculateIncentive | POST /companies/{company_id}/incentive-calculations | IncentiveCalculation | ResourceResult | staff.incentive |
| listShifts | GET /companies/{company_id}/shifts | - | Page | staff.read |

Eventos emitidos: shift.published, attendance.recorded, incentive.proposed, incentive.approved. Esquema comun `contratos/eventos.schema.json` y catálogo `contratos/eventos.csv`. Las lecturas detalladas y catálogos usan contratos de proyección versionados, no exponen secretos ni escritura de estados arbitraria.
