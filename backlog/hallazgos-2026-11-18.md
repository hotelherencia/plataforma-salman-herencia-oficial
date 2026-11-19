# Hallazgos de operación del propietario — 2026-11-18

Épica: **#368**. Revisión operativa del flujo de reserva entre la landing y la plataforma, el stock, la recepción, el aseo y la caja.

Todo el detalle de cada cambio está en su issue y su PR. Este registro reúne qué se hizo, qué se decidió y qué queda pendiente.

## Entregado en producción

Cada PR pasó estos pasos en orden:

1. Suite completa del servicio contra PostgreSQL 16, pruebas del front y `next build`.
2. Merge a `main` con rebase.
3. Aprobación del despliegue en Railway.
4. Verificación en producción: `readiness` y la ruta nueva respondiendo 401 sin sesión, no 404.

| PR | Qué cambió | Issues |
|---|---|---|
| #370 | Solicitud pública por **tipo** de habitación; la conversión toma cualquier unidad libre del tipo, sin el falso «no hay capacidad». | #346, #347 |
| #371 | Next.js 16.4.5 (el build abortaba por la vulnerabilidad GHSA-mfr8-8qww-v76h). | #369 |
| #372 | Botón «ver contraseña»; el login con Google deja reintentar con otra cuenta. | #350, #351 |
| #373 | Huésped visible en el pago y en la caja; aviso de pago parcial o en exceso; el código de reserva queda fijo al asentar un cargo; borrar un cargo es un reverso contable. | #356, #359, #364, #365, #366 |
| #374 | Nueva reserva con habitación elegida de una lista y RUT o pasaporte validado; habitación confirmable o cambiable al llegar; mover a un huésped de habitación. | #360, #361, #367 |
| #375 | Rol **aseo** (lista, confirmación, verificación y observaciones); el mantenimiento **por rango de fechas** solo quita la habitación de la venta dentro del rango. Migración 0026. | #349, #362, #363 |
| #376 | Catálogo de **productos** con búsqueda, precio automático en el cargo y stock de minibar. Migración 0027. | #357 |
| #377 | **Avisos** de cada solicitud (contador en el menú, correo, WhatsApp) y **leads por contacto**, con ventana de 30 días para «nuevo». Migraciones 0028 y 0029. | #353, #354 |
| #378 | `/reservar?tipo=` preselecciona el tipo elegido en la landing; ni el visitante ni el agente ven números de habitación. | #346, landinpage#1 |
| #379 | Alta de usuarios con **correo de Google** y vinculación desde «Usuarios», sin pasar por variables de entorno. | #352 |
| #380 | **Tope de solicitudes por cliente**, configurable. Migración 0030. | #348 |
| #382 | **Servidores de correo** configurables y lead «contactado» automático. Migración 0031. | #355 |

En la landing, `hotelherencia/landinpage#2` agrega «Reservar este tipo» en cada tarjeta de habitación (`?tipo=doble` y `?tipo=matrimonial`).

## Decisiones del propietario (2026-11-18)

- **#348**: tope **por cliente**, mismo correo o teléfono normalizado (opción C). No hay cupo por canal.
  - Valor inicial: 3 solicitudes en 7 días.
  - Se edita en Configuración → «Reservas web».
- **#355**
  - «Habilitar todo lo necesario para configurar cualquier servidor de correo, todos los tipos posibles y parametrizados», desde Configuración.
  - Revisión cada **15 minutos**.
  - La nota registra el **buzón**, no a la persona que respondió.

## Pendiente

| Ítem | Estado | Qué falta |
|---|---|---|
| #352 (cuenta administradora nominada) | In Progress | El propietario la crea en Plataforma → Usuarios con rol Administrador y el correo de Google entregado por canal privado; la persona entra con Google y enrola el doble factor. El correo no se escribe en el repo (Ley 21.719). |
| #381 (front sin textos técnicos, panel con gráficas y UI/UX) | Listo | Reemplazo de JSON crudo por resumen elegante, ocultamiento de claves internas, selectores de usuario, eliminación de textos de desarrollo y panel con gráficas visuales y fórmulas en lenguaje claro (#381). |
| #358 (stock leyendo la factura, compartido con la cafetería) | Todo (épica) | Fuera de esta ronda. |
| Catálogo de productos | Operativo, vacío | La administración crea los productos en «Productos y stock»; mientras no existan, recepción y caja no pueden asentar cargos (la administración puede usar concepto libre). |
| Avisos por WhatsApp | Apagado | Requiere una plantilla aprobada por Meta y las variables `AVISO_WHATSAPP_*`. |
| Buzones de correo | Sin configurar | Cargar en Configuración → «Correo» los buzones de reservas y comercial, y opcionalmente el de envío de avisos. Guía: `docs/operacion/correo.md`. |
| `test_operacion_mantenedor::test_ca_hab_03` | Intermitente | Falló en la suite completa antes del cierre; no se reprodujo en las dos últimas corridas completas (566 passed). Si reaparece, revisar el orden de las pruebas. |

## Variables nuevas del servicio (Railway)

| Variable | Para qué | Estado |
|---|---|---|
| `CORREO_CLAVE_CIFRADO` | Clave Fernet que cifra las claves de los buzones (#355). | Creada el 2026-11-18. Si se rota, hay que reingresar las claves de los buzones. |
| `AVISO_CORREO_DESTINO`, `SMTP_HOST`, `SMTP_PUERTO`, `SMTP_USUARIO`, `SMTP_CLAVE`, `SMTP_REMITENTE` | Avisos por SMTP desde variables (#353). | Opcionales: el buzón de envío configurado en la plataforma los reemplaza. |
| `AVISO_WHATSAPP_DESTINO`, `WHATSAPP_ACCESS_TOKEN`, `AVISO_WHATSAPP_PLANTILLA`, `AVISO_WHATSAPP_IDIOMA` | Avisos por WhatsApp (#353). | Sin configurar. |
| `AVISOS_INTERVALO_SEGUNDOS` | Ciclo de reintentos de avisos. | Valor por defecto. |
| `LEADS_VENTANA_NUEVO_DIAS` | Ventana de lead «nuevo»: inicial 30, entre 1 y 365 (#354). | Valor por defecto. |
| `TAREAS_DE_FONDO` | `0` apaga los hilos periódicos (reintentos de avisos y revisión de correo). | Valor por defecto (encendidos fuera de Vercel). |
