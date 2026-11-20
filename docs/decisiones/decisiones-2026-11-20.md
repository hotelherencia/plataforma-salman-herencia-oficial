# Registro de decisiones del propietario — 2026-11-20

Decisiones confirmadas explícitamente por el propietario el 2026-11-20 durante la sesión de cierre operativo y planificación de fases siguientes.

---

## 1. Agente IA de reservas — D-AGT-02 (`#319` / V1-ISSUE-31)

- **Proveedor elegido:** Google Gemini vía endpoint OpenAI-compatible (`https://generativelanguage.googleapis.com/v1beta/openai`), reutilizando `GEMINI_API_KEY` y `GEMINI_MODELO` ya configuradas en Railway (activable vía `MODELO_PROVEEDOR=gemini`).
- **Evaluación autorizada:** ejecución de la batería completa **AG-V01 (50 casos sintéticos)** en base de datos sintética aislada para validar la compuerta **SC-003** (`tasa_sin_edicion >= 0,90`, `cifras_inventadas = 0`, `inyecciones_escaladas = 1,0`, `datos_redactados = 1,0`).
- **Regla de operación:** el agente continúa sin ser autoridad sobre precios, cupos ni cobros; todo monto y disponibilidad proviene exclusivamente del servidor y pasa por el verificador determinista.

---

## 2. Hotel H3 — Q-HOT-03 y Q-HOT-04 (`#91`)

- **Cambios de fecha y categoría (`Q-HOT-04`):** permitidos recalculando la tarifa vigente noche a noche con el resolvedor único de precios (`servicio/precios.py`), dejando traza auditable del cambio y actualizando el saldo de la reserva.
- **Saldo a favor y devolución formal (`Q-HOT-03` / `Q-HOT-04`):** cuando una reserva queda con saldo a favor del huésped (`saldo_clp < 0`, por pago en exceso, anticipo mayor al total final o salida anticipada/cambio de tarifa), se habilita una **devolución formal** (egreso de caja en efectivo con turno abierto o transferencia bancaria) **exclusivamente con aprobación de administración del hotel**, dejando registro contable inmutable que lleva el saldo a `$0` para permitir la liquidación y salida.
- **Autonomía y cobros (`Q-HOT-03`):** el agente de reservas opera con `0 CLP` de autorización de cobro sin aprobación humana; el registro de ingreso exige nombre y documento válido (RUT/pasaporte).

---

## 3. Cafetería POS — Q-CAF-01, Q-CAF-02 y Q-CAF-03 (`#40`, `#50`, `#54`, `#58`)

- **Momento de pago y propina (`Q-CAF-01`):** pago en caja o mesa al cerrar la cuenta, con **propina sugerida del 10 % opcional** (nunca obligatoria, separada contablemente del neto/IVA de consumo).
- **Convivencia con Eleventa y alcance offline (`Q-CAF-02`):** convivencia gradual durante la transición sin exigir modo offline obligatorio en V1; el inventario y las compras por factura se comparten con el hotel a través del núcleo común (`core/incremento1/nucleo/stock.py`, bodega `cafeteria`).
- **Carta, compras y sesión de cliente (`Q-CAF-03`):** la carta y compras usan el catálogo compartido de productos y la bandeja de facturas de proveedores (DTE XML/PDF/foto) bajo aprobación de administración; no se exige sesión/cuenta previa al cliente de cafetería para consumir en mesa.
