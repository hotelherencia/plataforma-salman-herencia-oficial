# Corrección de la definición de datos — registro, no esquema

> Nota de reconciliación (2026-10-27): esta corrección registra el momento anterior a
> `backlog/hotel/resolucion-dudas-2026-10-27.md`. El estado vigente de las cinco
> T003 se fija por evidencia en `backlog/indice.md` (nota de reconciliación), no el
> «siguen en Backlog» que se afirma más abajo.

Fecha: 2026-10-27. Este archivo registra **cómo se corrige** la definición de datos
de backend. No es un esquema SQL, no fusiona las tres capas y no ratifica
ninguna Q ni la constitución. Las clases de corrección son tres:
**DEFINICIÓN PENDIENTE DE FIRMA** (la spec no instancia el dato; se completa solo
cuando la Q indicada tenga firma en el acta), **SIN TRAZA** (el diccionario V1.0
no se usa para renombrar ni para elegir dueño) y **SUPUESTO DE CONSTRUCCIÓN**
(el incremento 0 ya se comporta así en memoria y caduca cuando `000-core/T003`
se firme).

Hechos medidos el 2026-10-27 (no recalculados): 10 pruebas del incremento 0 en
OK (exit 0); `scripts/validar_modelo_datos.py` termina en `FileNotFoundError`
(línea 35, falta `docs/auditorias/catalogo-requisitos.json`, exit real 1;
`docs/arquitectura/datos/` no existe y no se creó para obtener un PASS).

## Las seis correcciones

| # | Hallazgo | Evidencia (ruta) | Corrección | Clase |
|---|---|---|---|---|
| 1 | Ningún data-model cita un FR por entidad | `specs/000-core/data-model.md` y `specs/002-hotel-reservas-concierge/data-model.md`: las entidades se enumeran sin mapear a FR; los FR viven solo en `specs/*/spec.md` | No se asigna FR-00n a ninguna entidad. El mapeo entidad→FR se completa cuando las Q del gate tengan firma en `backlog/hotel/acta-para-firmar.md` | **DEFINICIÓN PENDIENTE DE FIRMA** |
| 2 | Estados no nombrados para la mayoría de las entidades | `specs/000-core/data-model.md:17` nombra IntentoPago, DocumentoTributario y Aprobación; `specs/002-hotel-reservas-concierge/data-model.md:17` nombra Reserva y Sincronización. Sin ciclo: Tenant, Membresía, Rol (core) y Propiedad, Habitación, TipoHabitación, Tarifa, PolíticaCancelación, Huésped, CuentaEstadía, Cargo, CupoPorFechaTipo (hotel) | No se inventa ningún ciclo. Tarifa, cuenta, cargo y política de cancelación esperan **Q-HOT-03**; tenant, membresía y rol esperan **Q-CORE-01** | **DEFINICIÓN PENDIENTE DE FIRMA** |
| 3 | Nombres de habitación, tipo y reserva sin traza entre diccionario y spec | `docs/definicion-herencia/modelos/entidades.csv`: establishment, room, room_type, reservation. Spec: Propiedad, TipoHabitación, Habitación, Reserva. Ningún nombre coincide; paquetes F01–F03 sin traza a `specs/` | Los nombres de la spec siguen siendo los de la spec; los del diccionario V1.0 siguen en el diccionario. No se renombra nada en ninguna dirección | **SIN TRAZA** |
| 4 | Dueño doble company_id frente a establishment_id | `docs/definicion-herencia/modelos/diccionario_datos.csv`: company_id en 343 filas, establishment_id en 9; room declara ambos con `UNIQUE(establishment_id, code)` | No se elige uno. Un solo dueño por entidad se fija cuando **Q-CORE-01** tenga firma | **SIN TRAZA** |
| 5 | Origen de la empresa en el servicio | `verticales/hotel/incremento0/hotel_reservas_incremento0/servicio.py`: `reservar()` y `consultar_disponibilidad()` reciben `empresa_id` del llamador y lanzan `AccesoDenegado` si no es `EMPRESA_FIJA.id`; el efecto niega el acceso cruzado, pero el origen es el parámetro, no una identidad autenticada | **Implementado el 2026-10-27 (bucle 1):** la reserva confirmada y la rechazada guardan `self._empresa.id` después del rechazo; el parámetro del llamador solo se usa para exigir. Queda identidad autenticada real para el core (Q-CORE-01 abierta en la spec) | **SUPUESTO DE CONSTRUCCIÓN** (caduca cuando `000-core/T003` se firme) |
| 6 | Puertos de pago, documento tributario, canal y PMS sin configuración | `verticales/hotel/incremento0/hotel_reservas_incremento0/puertos.py`: cada método devuelve `configurado=False`, detalle «no configurado»; `_puertos` se guarda en `servicio.py` y no se invoca | Siguen en «no configurado»; no pasan a base de datos. Esperan **Q-CORE-02** (documento tributario), **Q-HOT-02** (canal) y **Q-HOT-01** (PMS) | **DEFINICIÓN PENDIENTE DE FIRMA** |

Notas sin corrección nueva: la reserva de código usa `confirmada/rechazada`
(`dominio.py`), no el ciclo de la spec (`propuesta → retenida →
confirmada/cancelada/expirada`); queda como diferencia conocida entre código de
prueba y spec, sin ajustar ninguna de las dos capas. El límite de 0 CLP ya
quedó citado en `verticales/hotel/incremento0/README.md` como control inicial de
la versión propuesta 1.1.0 (sin ratificar), separado del hecho del módulo; esa
frase no se reescribe. Las constituciones 1.1.0 (`.specify/memory/constitution.md`,
ratificación pendiente) y 1.0 (`docs/definicion-herencia/sdd/constitucion.md`,
no aprobada) siguen siendo dos textos distintos y ninguno vigente.

## Puede seguir en memoria

Disponibilidad, reserva de la última unidad con cerrojo, empresa y huéspedes
sintéticos, y puertos «no configurado». Las 10 pruebas ya pasaron el 2026-10-27
(exit 0); no se reejecutaron en esta corrección y no se vuelven a marcar.

## No puede pasar a base de datos mientras la firma siga en blanco

Pago, documento tributario, canal, PMS, habitación, tipo, reserva, tarifa,
cuenta, cargo y política de cancelación. El modelo físico sigue bloqueado por
Q-CORE-01, Q-CORE-02, Q-CORE-03, Q-HOT-01, Q-HOT-02 y Q-HOT-03; las siete
líneas «Firma, nombre, fecha» del acta siguen vacías y las cinco T003 siguen en
Backlog. No se propone esquema SQL.
