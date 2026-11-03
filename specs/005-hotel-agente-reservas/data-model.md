# Modelo de datos — Agente de reservas

PROPUESTO (2026-11-03). Todas las tablas llevan `empresa_id` y se filtran
por la empresa de la sesión.

| Tabla | Campos | Reglas |
|---|---|---|
| `consultas_agente` | `id` (CON-…), `empresa_id`, `canal_origen` (`manual`, `landing`, `correo`, `whatsapp`), `texto_redactado`, `recibida_en`, `registrada_por`, `estado` (`pendiente`, `procesada`, `escalada`), `motivo` | El texto original sin redactar no se guarda. `pendiente` cuando el modelo no está configurado |
| `borradores_agente` | `id` (BOR-…), `consulta_id`, `plantilla`, `campos` (jsonb, copiados del resultado de la herramienta), `texto_compuesto`, `oferta_emitida_en`, `vigente_hasta`, `estado` (`pendiente_aprobacion`, `aprobado`, `editado`, `descartado`, `escalado`, `enviado`, `pendiente_envio`), `aprobado_por`, `aprobado_en`, `version` | La transición solo es válida desde `pendiente_aprobacion`. La edición guarda el texto de recepción y marca `editado`; las cifras siguen siendo las de la herramienta |
| `trazas_agente` | `id`, `consulta_id`, `turno`, `herramienta`, `argumentos` (jsonb), `resultado` (jsonb resumido), `decision`, `verificacion` (`ok`/`rechazo:<motivo>`), `version_prompt`, `version_politica`, `modelo` (nombre del adaptador o `guionado`), `creada_en` | Solo agrega filas, no se actualiza. Sin datos personales sin redactar |
| `politica_agente` | `empresa_id` (PK), `nivel` (`N0`, `N1` o `N2`; por defecto `N0`), `horario`, `max_noches`, `max_personas`, `tope_mensual_clp`, `actualizada_por`, `actualizada_en` | Solo el administrador la cambia. Subir de nivel exige registrar la referencia a la evaluación SC-003 |

Rol nuevo: `agente` en `usuarios` (sin clave utilizable ni TOTP, `activo`
siempre). Ninguna sesión web puede emitirse para ese usuario (prueba
`test_agente_no_inicia_sesion`).
