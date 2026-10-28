# Evidencia de implementación en memoria — HU-HOT-01, HU-HOT-02, HU-HOT-03 (2026-10-28)

Clase de evidencia: **REQUISITO PROPUESTO implementado en memoria**. Ninguna
historia está ratificada ni marcada como Hecha. Las firmas del acta siguen en blanco.
Datos sintéticos; sin pagos, documentos ni llamadas externas.

Código: `verticales/hotel/incremento1/hotel_inventario/servicio.py`.
Pruebas: `verticales/hotel/incremento1/tests/test_configuracion_tarifas_hu_hot_01.py`
y `verticales/hotel/incremento1/tests/test_cierre_indicadores_hu_hot_02_03.py`.
Resultado: hotel 118 pruebas OK (106 de antes de este corte + 5 de HU-HOT-01 + 7 de
HU-HOT-02/03).

## HU-HOT-01 — Configurar habitación y tarifa (issue #211)

- **Hecho en código:** `configurar_tarifa` (solo rol `administrador`; la denegación
  queda en `evidencia_denegaciones`); tarifa por unidad y fecha; `tarifa_vigente`;
  `consultar_oferta` usa la tarifa de la fecha de llegada; `reservar` fija el precio
  aceptado y un cambio posterior no lo altera; rechaza tarifa superpuesta con motivo.
- **Pendiente (no codificado):** temporadas, tarifas 2027, mínimos de estadía, anticipos
  y descuentos (Manual §9, decisión del propietario). El tipo de habitación se guarda
  como etiqueta; no hay catálogo de tipos.

## HU-HOT-02 — Conciliación y cierre financiero diario (issue #212)

- **Hecho en código:** `cierre_diario` (roles `caja` y `gerencia`; denegación auditada)
  relaciona cada pago del día con su reserva; `registrar_pago` acepta `fecha`. Ningún
  pago aparece como `conciliado`.
- **Pendiente:** documento tributario (puerto sin configurar, no emitido), caja (el
  modelo no tiene cajas), conciliación bancaria (sin proveedor, Manual §9), devoluciones
  sin fecha en el modelo, y pagos sin fecha que quedan fuera del cierre (se declara su
  número). La liquidación del check-out (002/H2) existe en código; el cierre no
  exige un estado de «cierre completado» porque ese estado no está modelado.

## HU-HOT-03 — Indicador mínimo de gerencia (issue #213)

- **Hecho en código:** `indicadores_diarios` (solo `gerencia`) calcula ocupación, ADR y
  RevPAR con fórmula, periodo, fuente y responsable declarados; una noche revertida no
  cuenta como vendida; sin noches vendidas, ADR es `None` (sin muestra).
- **Pendiente:** ingresos por canal (el modelo no registra canal de origen); objetivos
  numéricos (los SC de la spec son propuestos y no medidos); depende de HU-HOT-02 solo
  en el texto de la historia, no en el código.

## Qué no se hizo

- No se marcó ningún issue ni tarea como Hecha en GitHub; no hubo escritura remota.
- No se hizo commit ni push.
- Las tareas `T-IMP` de H1–H3 del hotel siguen marcadas «NO INICIAR: bloqueada». Estas
  historias son las propuestas HU-HOT del Manual, no esas tareas; el propietario debe
  confirmar si esa lectura es correcta.
