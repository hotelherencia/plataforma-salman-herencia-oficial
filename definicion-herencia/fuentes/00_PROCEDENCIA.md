# Procedencia y vigencia

Base primaria: decisiones del usuario en la conversacion y paquete Prompt Maestro SDD V0.3, archivo Herencia_SDD_V03.zip. Se preservan 153 filas originales, 44 decisiones previas y 48 escenarios críticos. Se agrega D45 como propuesta técnica para completar el plan, no como decisión aprobada. El organigrama 2018 y planillas2019/2020 se utilizan mediante hallazgos sanitizados; no se reafirman porcentajes, precios, tasas o dotacion como actuales. Esta ejecución no reaudito las 255 hojas originales ni ejecuta operación del hotel.

Los datos del propietario confirmados incluyen 17 habitaciones, desayuno, recepción 24 h, hotel y cafetería en Herencia SpA y reinicio el 1 enero 2027. Falta catastro actual y información de la administradora. Mikhail y Cristóbal son destinatarios del paquete; sus facultades y responsabilidades concretas no se presumen.

Los archivos originales con huéspedes, trabajadores y operaciones privadas no se incluyen para evitar que se incorporen al repositorio. Las fuentes públicas se revisaron para orientar decisiones; las condiciones pueden cambiar. Toda conexión, compra y activación real requiere su cuenta, autorización y prueba.

## Referencias
**[S01] GitHub Spec Kit - flujo SDD.** https://github.github.com/spec-kit/quickstart.html
Uso: Proceso, integración de agente y selección explícita de funcionalidad; fijar release/commit en D37. No instalado.

**[S02] Node.js - versiones soportadas.** https://nodejs.org/en/about/previous-releases
Uso: Se propone linea 24 LTS; parche y soporte deben verificarse y fijarse en F00.

**[S03] Next.js - linea 16.** https://nextjs.org/blog/next-16
Uso: Propuesta técnica, no compromiso con parche inicial. Actualizaciones de seguridad antes de instalar.

**[S04] WhatsApp Business Messaging Policy.** https://whatsappbusiness.com/policy/
Uso: Permiso, ventana de 24 h, plantillas, bajas y escalamiento. Revalidar antes de activación.

**[S05] Instagram Messaging API con Instagram Login.** https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/messaging-api.md/
Uso: Cuenta profesional, permisos y conversacion iniciada por usuario; otras rutas tienen requisitos distintos.

**[S06] Booking Connectivity.** https://connect.booking.com/
Uso: Propiedad individual debe usar proveedor habilitado; disponibilidad de admision sujeta a condiciones. No hay acceso contratado.

**[S07] Transbank Webpay Plus.** https://transbankdevelopers.cl/documentacion/webpay-plus
Uso: Referencia para retorno, confirmacion/consulta servidor y validación de monto/orden. No proveedor elegido.

**[S08] PostgreSQL17 - Row Security.** https://www.postgresql.org/docs/17/ddl-rowsecurity.html
Uso: RLS como defensa adicional; rol propietario/bypass puede evadirla; permisos de aplicación siguen necesarios.

**[S09] BCN - Ley 21719.** https://www.bcn.cl/leychile/N?f=2026-12-01&i=1209272
Uso: Entrada en vigencia 1 diciembre 2026; revisión jurídica del tratamiento antes de operar.

**[S10] Direccion del Trabajo - ORD253/21.** https://www.dt.gob.cl/legislacion/1624/w3-article-129189.html
Uso: Jornada general 42 h desde 26 abril 2026; confirmar régimen y contratos concretos.

**[S11] SII - exención alojamiento a turistas extranjeros.** https://www.sii.cl/preguntas_frecuentes/impuestos_mensuales/001_130_2328.htm
Uso: Condiciones no se deducen sólo de nacionalidad. Requiere aprobación del contador y antecedentes.

**[S12] W3C WCAG2.2.** https://www.w3.org/TR/WCAG22/
Uso: Objetivo propuestoAA y pruebas automaticas/manuales; no certificacion obtenida.

**[S13] OWASP ASVS.** https://asvs.owasp.org/
Uso: Referencia ASVS5.0 para mapa de controles; seleccionar verificaciones aplicables con evidencia.

**[S14] OpenAPI3.1.1.** https://spec.openapis.org/oas/v3.1.1.html
Uso: Versión deliberadamente seleccionada para contratos propios; no afirmacion de última versión.

**[S15] GitHub Spec Kit - plantilla tareas.** https://raw.githubusercontent.com/github/spec-kit/main/templates/tasks-template.md
Uso: Pruebas deben exigirse expresamente; el proyecto las vuelve obligatorias.

**[S16] GitHub Spec Kit - converge.** https://raw.githubusercontent.com/github/spec-kit/main/templates/commands/converge.md
Uso: Convergencia contrasta spec/plan/tasks y artefactos; no equivale a aprobación de producción.

**[S17] Meta Instagram Login.** https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login.md/
Uso: No mezclar requisito de página Facebook de otra ruta con Instagram Login; anuncios no cubiertos por login de mensajes.

**[S18] PostgreSQL17 - aislamiento de transacciones.** https://www.postgresql.org/docs/17/transaction-iso.html
Uso: Bloqueos, restricciones y reintentos transaccionales para invariantes.
