# Decisiones del dueño (bloquean capa B y C)

Paquete 2026-11-11. Nada de esto se inventa en código.  
Tras decidir, anotar en el issue correspondiente (sin claves ni PII).

## D1 — Identificadores de habitación (#336)

Convención de `habitaciones.id` para las 17 unidades documentales:

| Opción | Ejemplo | Notas |
|---|---|---|
| A | `HAB-01` … `HAB-17` | Igual al ZIP |
| B | `HAB-101` … | Alineado a siembra sintética / numeración hotel |
| C | Otra (especificar) | |

**Decisión:** _[ ] A  [ ] B  [ ] C: _________  
**Fecha / quién:** ________

## D2 — Capacidad y tipo por unidad (#336 / PEN-001 / R02)

Completar solo tras verificación (no inferir de «Matrimonial +1»).

| id documental | numero | tipo_declarado ZIP | tipo Salman acordado | capacidad (≥1) | apta venta (sí/no) | notas camas/baño |
|---|---|---|---|---|---|---|
| HAB-01 | 1 | Matrimonial | | | | |
| HAB-02 | 2 | Matrimonial | | | | |
| HAB-03 | 3 | Doble | | | | |
| HAB-04 | 4 | Matrimonial | | | | |
| HAB-05 | 5 | Doble | | | | |
| HAB-06 | 6 | Matrimonial | | | | |
| HAB-07 | 7 | Single | | | | |
| HAB-08 | 8 | Matrimonial +1 | | | | |
| HAB-09 | 9 | Matrimonial | | | | |
| HAB-10 | 10 | Matrimonial | | | | |
| HAB-11 | 11 | Doble | | | | |
| HAB-12 | 12 | Matrimonial | | | | |
| HAB-13 | 13 | Matrimonial | | | | |
| HAB-14 | 14 | Doble | | | | |
| HAB-15 | 15 | Matrimonial | | | | |
| HAB-16 | 16 | Matrimonial +1 | | | | |
| HAB-17 | 17 | Triple | | | | |

**Retiro HAB-SINT-101..103 de oferta:** _[ ] fuera_de_servicio  [ ] quitar tarifa  [ ] ambos_

## D3 — Tarifas 2027 (R04)

ZIP: 5 filas, `aprobada_2027=false`, sin `vigente_desde`/`hasta`.  
Salman necesita por **cada habitación vendible**: monto CLP, desde, hasta.

| tipo comercial ZIP | monto_clp ZIP | ¿Aprueba 2027? | vigencia desde | vigencia hasta | IVA incluido (sí/no/n/d) | aplica a qué `habitacion_id` |
|---|---|---|---|---|---|---|
| Single | 47000 | | | | | |
| Doble | 55000 | | | | | |
| Matrimonial | 55000 | | | | | |
| Triple | 65000 | | | | | |
| Cuadruple | 82000 | | | | | ver D4 |

Canal declarado ZIP: `DIRECTO_POR_CONFIRMAR_MAPEO` → mapear a: ________

## D4 — Composición cuádruple (R01)

TAR-07: «Juntando 2 habitaciones unidas por el balcón».  
Salman V1 **no** modela `room_composition`.

| Opción | Efecto |
|---|---|
| A | No vender cuádruple en V1 (solo documental) |
| B | ADR + diseño (bloqueo atómico de 2 `habitacion_id`) antes de vender |
| C | Vender solo como dos reservas coordinadas manualmente (procedimiento, no producto) |

**Decisión:** _[ ] A  [ ] B  [ ] C_  
Pares de habitaciones si B/C: ________

## D5 — Unidad de ocupación (R06) — bloquea KPI/D1

Los 204 registros tienen `unidad_confirmada` vacía.  
`valor_reportado` ene–oct suma documental ≈ 2997 (control del paquete); **no** es KPI.

**Unidad confirmada:** _[ ] noches ocupadas  [ ] %  [ ] otra: _________  
**Denominador noches vendibles:** regla explícita (excluir fuera de servicio): ________  
**Feb/abr/jun/sep:** confirmar días calendario (28/30/30/30), nunca 31 para métrica diaria.

## D6 — Empresa / fiscal (#314)

Razón social, RUT, domicilio, tratamiento IVA en tarifa/cobro:  
**Estado:** _[ ] pendiente  [ ] entregado por canal seguro (no en este repo)_  
Sin esto no afirmar IVA en reportes de ingreso.

## D7 — Admin nominado (#338)

Nombre de usuario `administrador` (sin clave): ________  
Fecha alta: ________  
TOTP: **no obligatorio** (validado 2026-11-10: `totp_activado=false`; correo/Google sí).

## D8 — Fuentes transaccionales (capa C / G3)

¿Habrá exportación PMS/OTA/banco/POS/facturas?  
_[ ] sí, canal y fecha: ________  [ ] no en V1_

Sin hechos reconciliados: dashboard máximo D0 (documental).
