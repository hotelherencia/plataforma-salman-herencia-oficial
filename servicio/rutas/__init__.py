"""Rutas HTTP por dominio (ARC-A01, #334: split de aplicacion.py).

- `comun`: dependencias y auxiliares compartidos (conexión, sesión, cookies,
  exigencias de rol, clave de idempotencia).
- `modelos`: esquemas pydantic de entrada HTTP.
- `acceso`: sesión, Google OIDC, 2FA TOTP y gestión de usuarios.
- `hotel`, `publico`, `agente`: operación del hotel, canal público y agente.
"""
