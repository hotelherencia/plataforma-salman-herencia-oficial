# Informe: reconciliación de ocupación y panel (veracidad operativa)

**Fecha:** 2026-11-03 · **Ámbito:** `/hotel/ocupacion`, `/hotel/panel` (issues #320 y relacionados)
**Resultado:** 20/20 E2E operación, 12/12 pruebas de servicio nuevas, 56/56 base sin regresión.

## 1. Trazabilidad: de cada dato a su fuente

| Dato | Endpoint | Consulta (servicio) | Fórmula | Zona horaria |
|---|---|---|---|---|
| Celda de noche (rejilla) | `GET /hotel/ocupacion` | `servicio/panel.py` (construcción noche a noche) | prioridad: `confirmada`/`en_estadia` que contiene la noche → su estado y `reserva_id`; luego `no_vendible`; si `d < hoy` → `finalizada`/`sin_ocupar`; si `d ≥ hoy` sin reserva → `disponible`; sin tarifa → `sin_tarifa` | fecha local del servidor (Chile, UTC-3); noches inclusivas `[inicio, fin)` |
| Resumen de la noche | `GET /hotel/ocupacion` → `resumen[]` | misma construcción | `disponibles` = celdas `disponible`; `ocupadas` = celdas `confirmada`+`en_estadia` (**cupo comprometido**, cualquier noche del periodo); `no_vendibles` = celdas `no_vendible` | igual |
| Serie diaria del panel | `GET /hotel/indicadores` | `servicio/panel.py` §4.3 | por noche: `unidades`, `ocupadas` = **estadías reales** (`en_estadia`+`finalizada`, solo noches `d ≤ hoy`), `reservadas` | igual |
| KPIs del panel | `GET /hotel/indicadores` | `servicio/panel.py` | los que el contrato define; los no calculables se declaran en `no_disponibles` con motivo (p. ej. `no-show` → «V1 no tiene ese estado; ver `llegadas_vencidas`», `panel.py:192`) | periodo del filtro |

El front **no recalcula ninguna regla**: pinta la respuesta del servidor (casos E2E OCU-03 e IND-05 comparan UI contra API en el mismo periodo y exigen igualdad exacta).

## 2. Causa raíz de las discrepancias encontradas y corrección

1. **Doble significado de `ocupadas` (defecto de contrato, no de cálculo).**
   El `ocupadas` del resumen de `/hotel/ocupacion` (cupo comprometido: `confirmada`+`en_estadia`, cualquier noche) y el `ocupadas` de la serie del panel (estadías reales: noches pasadas ya consumidas) son **métricas distintas con el mismo nombre en dos endpoints**. Los números eran correctos cada uno según su fórmula, pero el nombre inducía a compararlos como si fueran el mismo dato.
   - Corrección: cada respuesta lleva su fórmula y la spec gobernante define ambas — `spec-hotel-operacion-v1.md` §4.3 (nota 2026-11-03 en la serie) y §5 (definición de `resumen`). El pie de la rejilla pasó de «Disponibles / ocupadas» a «Disponibles / cupo ocupado» (`front/app/hotel/ocupacion/page.js`).
   - Unificación de nombres en el contrato: **REQUISITO PROPUESTO**, issue #320 (rompería front y E2E al renombrar; va en revisión de contrato, no en esta iteración).
2. **Datos viejos junto al error (defecto UI).** En `/hotel/ocupacion` y `/hotel/panel`, un rechazo de la API (p. ej. periodo inválido) dejaba la rejilla/tarjetas anteriores visibles bajo el mensaje de error, contradiciendo la propia UI.
   - Corrección: ante `estado >= 400` se limpia el estado (`setDatos(null)`) antes de mostrar el error. Caso E2E OCU-04 (recepción): periodo invertido → alerta «hasta debe ser mayor…» y la rejilla anterior desaparece.

## 3. Pruebas agregadas (TDD: roja por la discrepancia real, luego verde)

`servicio/tests/test_panel_ocupacion.py` (12, dataset sintético determinista en PostgreSQL aislado):

- celdas: oferta de una noche coincide con la celda; multinoche si y solo si todas sus noches disponibles; capacidad filtra oferta pero no la celda; salida anticipada libera noches futuras; reserva gana sobre `no_vendible`; cancelada no pinta.
- resumen: suma solo `disponible`+ocupadas+`no_vendible`; situación de hoy recompone desde reservas; periodo recompone noche a noche; periodo todo futuro = ocupación nula (no cero); canceladas y registradas recomponen; filtro por tipo restringe unidades y reservas.
- **reconciliación cruzada:** `test_serie_del_panel_coincide_con_el_resumen_de_ocupacion` — con el mismo dataset y periodo, la serie del panel y el resumen de ocupación no se contradicen sobre la misma habitación y noche.

E2E (`e2e/e2e-operacion.mjs`, rol recepción/administrador): OCU-03 (rejilla y resumen pintan exactamente la API), OCU-04 (error limpia datos), IND-05 (KPIs y serie sin recalcular). Evidencia: `capturas/e2e-2026-11-03/op-07-ocu-03-ui-igual-api.png`, `op-08-ind-05-ui-igual-api.png`.

## 4. Reglas y límites que quedan definidos

- **HECHO DOCUMENTADO:** fórmulas de §1; `sin_tarifa` se muestra como dato ausente, no como cero ni disponible; canceladas no pintan celda ni resumen.
- **REQUISITO PROPUESTO:** unificar el nombre `ocupadas` en contrato (#320).
- **DECISIÓN PENDIENTE:** denominador de ocupación con unidades fuera de servicio (#299, brief en `decisiones-pendientes-v1.md` §5); indicadores financieros ADR/RevPAR e ingresos (#297, §4).
- **SUPUESTO:** la fecha «de hoy» es la del servidor (Chile); no hay normalización a medianoche UTC en el cálculo de noches.

## 5. Verificación final

- Servicio: 206/206 (`unittest discover`, base sintética `plataforma_test_operacion`).
- E2E: base 56/56, operación 20/20, vendible 3/3, tarifa-noches 3/3, reserva-pública 6/6.
- Sin cambios en producción; todo verificado en local con datos sintéticos desechables.
