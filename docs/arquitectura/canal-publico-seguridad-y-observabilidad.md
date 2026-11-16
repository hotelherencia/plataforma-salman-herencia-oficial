# Canal público: continuidad landing → /reservar, entradas y observabilidad

Fecha: 2026-11-16. Alcance: `/publico/leads`, `/publico/referencia`,
`/publico/disponibilidad`, `/publico/solicitudes` y la página `/reservar`.

## Continuidad de la consulta (sin datos personales en la URL)

1. La landing envía la consulta a su función `/api/publico/leads`, que verifica
   reCAPTCHA y la reenvía a `POST /publico/leads`. La respuesta trae
   `referencia` (opaca, 256 bits, caduca a las 72 h y se revoca al cerrar el
   lead, SOC-016).
2. La landing guarda la referencia en `localStorage` (`herencia:consulta-ref`,
   misma caducidad) y la agrega a todo enlace hacia `/reservar`.
3. `/reservar` lee `llegada`, `salida`, `personas` (canónicos; `inicio`/`fin`
   solo como alias de enlaces antiguos) y `ref`; guarda la referencia en su
   propio `localStorage`, deja la URL canónica **sin** `ref`
   (`history.replaceState`) y pide `GET /publico/referencia`. Con 200 muestra
   «Te contactaremos a <correo>» con «Editar mis datos»; con 404/422 olvida la
   referencia y pide nombre y contacto.

**Causa del fallo del 2026-11-16:** el proxy de la landing verificaba el token
de reCAPTCHA y reenviaba **el mismo** token a la plataforma, que lo verificaba
otra vez. Google acepta cada token una sola vez (`timeout-or-duplicate`), así
que la plataforma respondía 403, el lead no se guardaba, no había referencia y
la landing llevaba al visitante a `/reservar` solo con fechas. Ahora la landing
pide dos tokens (`X-Recaptcha-Token` para el proxy y
`X-Recaptcha-Token-Servicio` para la plataforma).

## Validación de entradas

| Entrada | Regla |
|---|---|
| `llegada`/`salida` (y alias) | `AAAA-MM-DD` que exista en el calendario; salida > llegada; sin pasado; ≤ 30 noches. Lo inválido se descarta con un aviso de texto fijo (nunca se refleja). |
| `personas` | Entero 1..30 (cada habitación admite como máximo `capacidad_maxima_habitacion`, hoy 3; con más, `/reservar` explica y ofrece WhatsApp). |
| `ref` / `token` | `^[A-Za-z0-9_-]{20,128}$`; búsqueda parametrizada por igualdad; 256 bits de entropía + freno por IP hacen inviable la fuerza bruta. |
| Parámetros ajenos | 422 en el servicio (`_solo_parametros`); `/reservar` los elimina de la URL. No hay parámetros `next`/`volver`: no hay redirecciones abiertas (la de la landing `/reservar` va a un host fijo). |
| Cuerpos públicos | `extra="forbid"` (campo no declarado → 422). Texto normalizado (`servicio/entrada_publica.py`): NFC, sin controles C0/C1 ni marcas bidi, espacios colapsados; correo en minúsculas; teléfono solo `+ dígitos espacios ( ) . -` y 8–15 dígitos; topes de largo sobre el texto ya limpio. El proxy de la landing aplica las mismas reglas antes de gastar reCAPTCHA. |
| Errores 422 | El manejador global ya no devuelve `input` (FastAPI reflejaba el valor recibido). |
| SQL | Todo con parámetros psycopg (`%s`). Las pruebas guardan `Robert'); DROP TABLE leads;--` y `<script>` como texto literal. |

## Freno de abuso

`FrenoDeSolicitudes` (en memoria por instancia): 6 por minuto por clave (IP,
correo, teléfono) y 30 por minuto por ruta en toda la instancia, con ámbitos
separados (`disponibilidad`, `referencia`, `leads:pre`, `leads`,
`solicitudes:pre`, `solicitudes`). No hay almacén compartido (Redis) en el
despliegue actual: con varias instancias cada una frena por su cuenta. Además,
Cloudflare limita `/api/` de la landing (10 peticiones/10 s por IP).

**Riesgo conocido:** las consultas de la landing llegan al servicio desde la
función de Vercel, así que comparten IP. Igual para `/reservar` si el último
salto de `X-Forwarded-For` es el borde de Vercel. Con mucho tráfico real el
tope por IP o el global de 30/min puede rechazar visitantes legítimos (429).
Revisar en los logs (`resultado=freno`) y, si aparece, subir el tope o
mover el freno a un almacén compartido con la IP real del visitante.

## Observabilidad

- Cada respuesta lleva `X-Request-ID`. La landing genera uno por consulta (o
  respeta uno válido entrante), lo devuelve y lo propaga a la plataforma, que
  lo usa en sus logs: la misma consulta se sigue en Vercel y en Railway.
- Una línea JSON por petición pública: `evento=publico`, `ruta` (sin query),
  `estado`, `resultado` (`ok`, `entrada_rechazada`, `freno`,
  `recaptcha_rechazado`, `no_encontrado`, `conflicto`, `no_disponible`,
  `error`), `ms`, `request_id`. Para la referencia, `evento=referencia` con
  `ref_hash` (12 caracteres de su SHA-256), nunca el token.
- La función de la landing escribe `servicio=landing-leads` con `request_id`,
  `estado`, `resultado` y `ms`; nunca cuerpo, token ni secreto.
- `GET /hotel/metricas-publicas` (solo administrador): contadores de la
  instancia por ruta y resultado.

### Dónde mirar

- **Vercel (landing):** proyecto de la landing → *Logs* → filtrar
  `landing-leads` o por `request_id`.
- **Railway (servicio):** servicio → *Deployments* → *View logs* (o
  *Observability*) → buscar `"evento": "publico"`, `"resultado": "freno"` o
  el `request_id` que devolvió la landing.
- **Vercel (plataforma):** proyecto de la plataforma → *Logs* (la API FastAPI
  de `/api/*` escribe las mismas líneas JSON).
