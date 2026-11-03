# Contrato — rutas del agente (propuesta de enmienda a spec-api-v1)

PROPUESTO (2026-11-03). Todas exigen sesión de recepción o administrador
(401 sin sesión, 403 con otro rol o con otra empresa). Las mutaciones llevan
`Idempotency-Key`. Los errores son legibles, como en el resto de la API.

| Método y ruta | Rol | Cuerpo | Respuestas |
|---|---|---|---|
| `POST /hotel/agente/consultas` | recepción, admin | `{canal_origen, texto}` (texto de 1 a 4000 caracteres) | 201 `{consulta, borrador?}` con borrador `pendiente_aprobacion` o `escalado`; 503 `{"detail":"modelo no configurado","estado":"pendiente"}` con la consulta guardada; 400 validación |
| `GET /hotel/agente/consultas?estado=` | recepción, admin | — | 200 lista sin texto completo |
| `GET /hotel/agente/consultas/{id}` | recepción, admin | — | 200 consulta, borradores y traza resumida; 404 |
| `POST /hotel/agente/borradores/{id}/aprobacion` | recepción, admin | `{texto_editado?}` | 200 `aprobado`/`editado`; 409 «la oferta cambió» con borrador nuevo; 409 «ya resuelto» |
| `POST /hotel/agente/borradores/{id}/descarte` | recepción, admin | `{motivo}` | 200; 409 «ya resuelto» |
| `GET /hotel/agente/politica` / `PUT` | admin (PUT) | `{nivel, horario, max_noches, max_personas, tope_mensual_clp, evaluacion_ref?}` | 200; 409 si se sube de nivel sin `evaluacion_ref`; 403 recepción en PUT |

## Herramientas internas (no son HTTP)

| Herramienta | Argumentos (validados) | Resultado | Escribe |
|---|---|---|---|
| `consultar_disponibilidad` | `inicio`, `fin` (fechas, futuro, fin mayor que inicio), `personas` (1 a 30), noches ≤ `max_noches` | la salida de `reservas.oferta` tal cual | no |
| `proponer_borrador` | `plantilla` ∈ {cotizacion, sin_disponibilidad, pedir_dato, escalar}, `campos` (referencias a ítems de la oferta del mismo turno, no valores), `saludo` (≤ 280 caracteres, sin dígitos) | borrador compuesto por el servidor | sí (borrador) |
| `crear_solicitud` (solo N2) | `oferta_item_ref`, `nombre`, contacto según D-PUB-01 | operación de v1-issue-22 con clave `agente:<consulta>:<turno>` | sí |

Una herramienta inexistente o con argumentos inválidos produce rechazo y
escala la consulta. El modelo nunca envía `empresa_id`, rol, tarifa ni total.
