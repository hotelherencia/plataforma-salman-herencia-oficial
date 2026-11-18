# Correo: buzones configurables (#355)

Se configura en **Configuración → «Correo»**. Lo hace la administración del hotel. Hay dos usos:

| Uso | Para qué | Proveedores |
|---|---|---|
| Leer enviados | Si el hotel ya le escribió a un lead `nuevo`, ese lead pasa solo a `contactado`. | IMAP, API de Gmail, Microsoft Graph |
| Enviar avisos | Avisa de cada solicitud de reserva (#353). Si está activo, reemplaza al SMTP de variables. | SMTP, API de Gmail, Microsoft Graph |

Solo se leen **destinatarios y fecha** de los enviados, nunca el asunto ni el cuerpo:

- IMAP pide `BODY.PEEK[HEADER.FIELDS (DATE TO CC BCC)]`.
- Gmail usa `format=metadata` con el alcance `gmail.metadata`.
- Graph usa `$select` sobre los destinatarios.

## Requisito único en Railway

`CORREO_CLAVE_CIFRADO` es la clave Fernet con que se cifran las claves de los buzones. Se genera con este comando:

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Si se cambia, las claves ya guardadas dejan de poder leerse y hay que volver a ingresarlas en cada buzón.

## Recetas por proveedor

- **Gmail o Google Workspace (IMAP/SMTP)**
  - Elige «Gmail / Google Workspace» en «Proveedor conocido».
  - Autenticación por **clave de aplicación**: requiere la verificación en dos pasos y se crea en myaccount.google.com → Seguridad.
  - También sirve OAuth2, con client ID, client secret y refresh token.
- **Google Workspace (API de Gmail)**
  - Crea una cuenta de servicio con delegación de dominio.
  - En la consola de administración, autoriza su client ID con estos alcances:
    - `https://www.googleapis.com/auth/gmail.metadata` para lectura.
    - `https://www.googleapis.com/auth/gmail.send` para el envío.
  - Pega el JSON de la cuenta de servicio y el correo del buzón.
- **Microsoft 365 (Graph)**
  - Registra una aplicación en Entra ID con permiso de aplicación `Mail.ReadBasic.All` (lectura) o `Mail.Send` (envío), y da el consentimiento de administrador.
  - Ingresa el tenant ID, el client ID, el client secret y el correo del buzón.
- **Outlook o Microsoft 365 (IMAP/SMTP)**: usa el preset «Outlook / Microsoft 365». Microsoft 365 suele exigir OAuth2 (XOAUTH2).
- **Yahoo, Zoho e iCloud**: usa el preset correspondiente con una clave de aplicación.
- **Hosting (cPanel o Plesk)**
  - El servidor suele ser `mail.<dominio>`, con puerto 993 (IMAP) o 465 (SMTP) sobre SSL.
  - El usuario es la casilla completa.

Después de guardar, usa **«Probar conexión»**:

- En un buzón de lectura cuenta los enviados de los últimos 7 días.
- En el de avisos manda un correo de prueba.

**«Revisar ahora»** corre la revisión de inmediato, sin esperar el ciclo.
