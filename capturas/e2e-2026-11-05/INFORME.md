# INFORME E2E — Regresión de certificación 2026-11-05

**Fecha:** 2026-11-05 · **Tipo:** regresión de certificación (no es revisión de
aceptación formal; no hubo cambios de código de producto desde el 2026-11-04).
**Motivo:** certificar el candidato a publicación de la landing (#313) y
verificar que nada se moviera tras la sincronización del tablero.

**Ambiente:** local y aislado — base `plataforma_e2e_landing` (sintética,
desechable; incluye el decoy `HAB-PUB-000000DECOY` que exige
`e2e-reserva-publica`), backend `127.0.0.1:8080`, front en build de
producción `127.0.0.1:3000` (`API_BASE_URL` horneado), navegador Chromium vía
Playwright. Sin producción, sin datos reales, sin adaptadores externos.

**Resultados:**

| Suite | Casos | Resultado |
|---|---|---|
| `e2e.mjs` (base: acceso, cuenta, operación hotel) | 56 | 56/56 APROBADO |
| `e2e-reserva-publica.mjs` (canal público) | 6 | 6/6 aprobados |
| `e2e-leads.mjs` (formulario propio de la landing) | 5 | 5/5 aprobados |
| `e2e-landing.mjs` (CTA «Consultar reserva», candidato #313) | 3 | 3/3 aprobados |

Complementos: servicio 260/260 en cinco corridas consecutivas (la primera
corrida del día tuvo 1 fallo no identificado que no reprodujo en las cinco
siguientes — intermitente registrado en `backlog/v1/indice.md`); dominio
180/180 en las 5 raíces; landing unitarios 12/12.

**No corrida hoy** (requieren base dedicada/guion; última evidencia en verde
2026-11-04, sin cambios de código desde entonces): `e2e-operacion.mjs` (20/20)
y `e2e-agente.mjs` (4/4).

**Hallazgo de la sesión (comportamiento esperado, no bug):** el freno de
abuso del canal público (`FrenoDeSolicitudes`, 6 por IP/min en memoria por
proceso, spec «Contacto y leads») responde 429 al repetir la suite de leads
dos veces seguidas contra el mismo proceso API. Corrida única contra un
proceso recién arrancado: 5/5. La suite no es repetible contra la misma
instancia dentro de la misma ventana de 60 s.

**Conclusión para #313:** la carpeta `landing/` queda certificada para
publicación (CTA + formulario propio en verde con navegador real). Único paso
restante: subir los estáticos al hosting de hotelherencia.cl y verificar el
CTA en producción (requiere acceso del propietario; el repo no tiene
herramienta de despliegue para ese hosting).
