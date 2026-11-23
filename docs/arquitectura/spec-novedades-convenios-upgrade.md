# SPEC: Libro de Novedades, Estacionamiento, Convenios/Eventos y Upgrade Flexible (2026-11-23)

**Fecha:** 2026-11-23  
**Estado:** Especificación propuesta para construcción (`main` base: `origin/main`)  
**Fuentes:** Observaciones operativas del propietario + Análisis de documentos de Catalina (21-11-2026) y Ricardo/Orquestia (22-11-2026).

---

## 0. Alcance ya cubierto (puntos 2, 3 y 6 parcial)
- **Puntos 2 y 3 (Análisis documentos Catalina y Ricardo):** completados e integrados en `docs/operacion/definiciones-administracion-2026-11-21.md`, `servicio/politicas.py` (PR #428) e issues `#415`–`#418` (Corte 1 ya en `main` por PRs #422 y #427).
- **Punto 6 (Registro de factura, caja y pasajeros):**
  - *Caja y factura:* cubiertos en base por `0050_caja_y_contabilidad.sql`, `0051_clientes_e_imputacion.sql` y `0040_facturas_proveedor.sql`.
  - *Pasajeros:* cubierto por `0060_huespedes_y_ocupacion_llegada.sql` (PR #412).
  - *Brecha a cerrar en este bloque:* unificar el acceso operativo entre el registro de pasajeros en Llegada, emisión/registro de boleta/factura (SII) y su visibilidad directa en la cuadratura de caja.

---

## 1. SPEC-NOV-01: Libro de Novedades de Turno, Estacionamiento y Conteos (Puntos 4 y 5)

### 1.1 Objetivo
Digitalizar el **libro de novedades turno a turno** (mañana / tarde / noche) junto con la **asignación de estacionamiento por habitación** (~14 cupos) y el **conteo operativo de desayunos y bebestibles** por turno/día.

### 1.2 Modelo de datos propuesto (migración aditiva)
- `libro_novedades`:
  - `id` (`NOV-...`), `empresa_id`, `fecha_contable` (`DATE`), `turno` (`manana | tarde | noche`), `autor`, `resumen` (`TEXT`), `estacionamientos_asignados` (`JSONB` o tabla hija), `desayunos_servidos` (`INTEGER`), `bebestibles_detalle` (`JSONB`), `creado_en`.
- `estacionamiento_asignaciones`:
  - `id`, `empresa_id`, `fecha` (`DATE`), `cupo` (`1..14` o etiqueta), `habitacion_id`, `reserva_id` (FK opcional), `patente` (`TEXT`), `estado` (`reservado | ocupado | liberado`), `creado_por`, `creado_en`.
- `conteos_turno_fnb`:
  - `id`, `empresa_id`, `fecha_contable` (`DATE`), `turno`, `categoria` (`desayuno | bebestible`), `producto_id` (FK opcional a `productos`), `cantidad` (`INTEGER >= 0`), `observacion`, `actor`, `creado_en`.

### 1.3 Reglas y endpoints
- `GET /hotel/novedades?fecha=`: devuelve novedades del día, mapa de los ~14 cupos de estacionamiento por habitación/patente y conteos de desayuno/bebestibles.
- `POST /hotel/novedades`: registra entrega de turno (con `Idempotency-Key` y auditoría).
- `PUT /hotel/estacionamiento/asignacion`: asigna o libera un cupo para una habitación/reserva (sin sobrepasar los cupos físicos configurados).
- `POST /hotel/novedades/conteos`: registra conteo de desayunos servidos y consumo de bebestibles (enlazable a reposición de stock `0055`).

### 1.4 Criterios de aceptación
- [ ] Recepción puede registrar entrega de turno con novedades, desayunos y bebestibles.
- [ ] Se visualiza qué habitación/patente ocupa cada cupo de estacionamiento (máximo cupos del mantenedor).
- [ ] No se agregan ítems nuevos al menú lateral (se integra como pestaña en `/hotel/panel` o `/hotel/estadia` / `/hotel/caja`).

---

## 2. SPEC-CONV-01: Convenios por Institución, Delegaciones y Eventos (Puntos 7 y 8)

### 2.1 Objetivo
Permitir tarifas especiales por **empresa/institución o evento anual** (ej. BMX, delegación de basketball, convenios institucionales) y reflejar explícitamente en el **cierre de caja** la institución aplicada y la **diferencia de precio** respecto a la tarifa lista.

### 2.2 Modelo de datos propuesto
- `convenios_tarifarios`:
  - `id` (`CNV-...`), `empresa_id`, `nombre` (`TEXT`, ej. *"Delegación BMX 2026"*), `tipo` (`empresa | evento | delegacion`), `cliente_id` (FK opcional a `clientes`), `vigencia_desde` (`DATE`), `vigencia_hasta` (`DATE`), `reglas_precio` (`JSONB`: tarifa fija por tipo de habitación o % descuento), `requiere_abono_pct` (`INTEGER`, por defecto `50` si `>10` personas), `activo` (`BOOLEAN`), `creado_en`.
- En `reservas`:
  - `convenio_id` (`TEXT REFERENCES convenios_tarifarios(id)`), `tarifa_lista_clp` (`INTEGER`), `diferencia_convenio_clp` (`INTEGER` = `tarifa_noche_aceptada_clp - tarifa_lista_clp`).

### 2.3 Reglas de negocio y cierre de caja (Punto 8)
- Al crear/cotizar una reserva interna (`/hotel/reserva`), si se selecciona un **convenio/institución** vigente:
  - El servidor calcula y guarda `tarifa_lista_clp`, `tarifa_noche_aceptada_clp` (tarifa convenio) y `diferencia_convenio_clp` (nunca calculado solo en el front).
  - Si el convenio/delegación supera 10 personas, sugiere/aplica la regla oficial del **50 % de abono al confirmar**.
- **En Cierre de Caja (`GET /hotel/caja/cierre` y vista `/hotel/caja`):**
  - El cierre diario debe incluir una sección/desglose **`convenios_aplicados`**: por cada reserva/pago con convenio, mostrar:
    - Institución / evento (`convenio_nombre`),
    - Tarifa lista vs. tarifa aplicada,
    - **Diferencia de precio (`diferencia_convenio_clp`)** acumulada por institución.

### 2.4 Criterios de aceptación
- [ ] Una reserva con convenio guarda `convenio_id`, `tarifa_lista_clp` y `diferencia_convenio_clp`.
- [ ] El cierre de caja lista cada institución aplicada en el día/período y su diferencia exacta en CLP.
- [ ] Solo `admin_hotel` / `administrador` crea o modifica convenios; recepción solo selecciona convenios vigentes.

---

## 3. SPEC-UPG-01: Upgrade Flexible por Agotamiento de Habitación Single (Punto 9)

### 3.1 Objetivo
Cuando no queden habitaciones **Single** disponibles para las fechas solicitadas, permitir asignar una habitación de categoría superior disponible (ej. **Doble** o **Matrimonial**) aplicándole el **precio de Single (tarifa flexible)** para 1 huésped.

### 3.2 Reglas de negocio
- Solo aplica cuando:
  1. La solicitud/reserva es para **1 persona**,
  2. No existen habitaciones de tipo `single` vendibles y disponibles en todo el rango `[inicio, fin)`, y
  3. El operador autorizado (`recepcion` o `admin_hotel`) selecciona explícitamente la opción **«Upgrade a tarifa Single»** en la oferta/nueva reserva.
- **Trazabilidad contable y de auditoría:**
  - En `reservas` / `reserva_noches` se guarda el precio efectivamente pactado (tarifa Single) y un campo `upgrade_desde_tipo = 'single'` + `tarifa_lista_clp` (la de la habitación asignada) para que la diferencia quede explicada en reportes y no parezca un error de cobro.
  - Si posteriormente en la Llegada se cambia la ocupación de `1` a `2` personas (`PUT /hotel/reservas/{id}/ocupacion`), el sistema recalcula automáticamente a la tarifa de la habitación real (2 personas) de forma append-only.
- **Seguridad:** el visitante público en `/reservar` no puede forzar un upgrade de precio por su cuenta; el flujo público sigue ofreciendo solo tipos con cupo real salvo que el hotel active explícitamente una regla comercial.

### 3.3 Criterios de aceptación
- [ ] Con todas las `single` ocupadas y una `doble`/`matrimonial` libre, recepción puede crear una reserva de 1 persona con «Upgrade a tarifa Single» cobrando `$47.000`/noche.
- [ ] Si hay al menos una `single` libre, el endpoint rechaza (`409`) el upgrade a precio Single.
- [ ] Si al hacer la Llegada pasan a ser 2 personas, se ajusta el cargo a tarifa Doble/Matrimonial (`$55.000`/noche).

---

## 4. SPEC-PROV-01: Reserva Provisoria a Nombre de Empresa o Institución (Bloqueo Multi-Huésped)

### 4.1 Objetivo
Permitir crear una reserva (individual o de grupo para N huéspedes, por ejemplo 5 huéspedes de *"Institución Arauco"*) con **nombre provisorio a nombre de la empresa/institución**, sin conocer aún los nombres ni RUTs definitivos de los pasajeros al momento de bloquear las habitaciones, y cargar los datos reales de cada cliente recién en la **Llegada**.

### 4.2 Modelo de datos y reglas de negocio
- En `reservas` (y `reservas_grupo` de PR B):
  - `es_huesped_provisorio BOOLEAN NOT NULL DEFAULT FALSE`: marca que el titular actual (`huesped_nombre`) corresponde a un nombre provisorio de empresa/institución (ej. `"Institución Arauco"`).
  - `cliente_id TEXT REFERENCES clientes(id)` / `convenio_id`: mantiene el vínculo con la empresa/institución pagadora para facturación y cierre de caja, incluso después de actualizar los nombres reales de los huéspedes.
- **Al reservar (estado `confirmada`):**
  - Se permite crear la reserva (o el bloque de habitaciones para 5 huéspedes) indicando la empresa/institución como nombre provisorio (`es_huesped_provisorio = TRUE`) sin exigir documento de los pasajeros finales.
- **Al momento de la Llegada (`POST /hotel/reservas/{id}/entrada`):**
  - Recepción carga los nombres reales y documentos (RUT/pasaporte) de los clientes que ingresan en cada habitación (vía pestaña «Huéspedes» / `0060_huespedes_y_ocupacion_llegada.sql` + `PUT /hotel/reservas/{id}/huesped`), pasando `es_huesped_provisorio = FALSE`.
  - **Bloqueo en Llegada:** no se puede pasar la reserva a `en_estadia` mientras `es_huesped_provisorio = TRUE` o falten huéspedes por registrar respecto a la ocupación real declarada (`409` en castellano).
  - La empresa/institución pagadora (`cliente_id` / `convenio_id`) permanece intacta en la reserva y en la imputación contable (`0051`).

### 4.3 Criterios de aceptación
- [ ] Recepción puede crear una reserva/grupo de 5 huéspedes a nombre provisorio de `"Institución Arauco"` sin cargar los 5 RUTs al reservar.
- [ ] Al intentar registrar la Llegada sin reemplazar el nombre provisorio por huéspedes reales, la API responde `409`.
- [ ] Al cargar los nombres y documentos reales en la Llegada, la reserva pasa a `en_estadia` manteniendo a `"Institución Arauco"` como empresa/convenio pagador para facturación y cierre de caja.

---

## 5. SPEC-ADM-01: Alta de Cuenta Administradora Adicional del Hotel

### 5.1 Objetivo y regla de seguridad
Incorporar una cuenta administradora adicional del hotel sin hardcodear correos, contraseñas ni secretos en el repositorio (ver `docs/operacion/alta-administrador-nominado.md`).

### 5.2 Implementación y flujo operativo (ya disponible en `main`)
1. **Endpoint y pantalla:** usar `POST /usuarios` o la pantalla `https://plataforma.hotelherencia.cl/hotel/usuarios` con sesión de `administrador` / `admin_plataforma`.
2. **Parámetros de alta:**
   - `nombre`: identificador nominado (ej. `admin_hotel_01`).
   - `rol`: `administrador` (acceso completo) o `admin_hotel` (gestión del hotel sin gestión de usuarios).
   - `email`: correo Google autorizado (ingresado solo en ejecución, nunca en el repo).
   - `clave`: clave temporal robusta (`>= 12` caracteres, entregada por canal privado).
3. **Primer ingreso y endurecimiento obligatorio:**
   - Al ingresar por primera vez (usuario/clave o Google), la persona debe **cambiar la clave temporal** en `/cuenta` y **activar el segundo factor TOTP (2FA)** (`POST /cuenta/2fa` + `POST /cuenta/2fa/activar`).
4. **Criterios de aceptación:**
   - [ ] La cuenta queda activa en `usuarios` con `google_vinculado = true` y 2FA activado.
   - [ ] Ninguna credencial ni correo real queda registrado en Git ni en logs de `auditoria`.
