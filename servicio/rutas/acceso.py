"""Rutas de acceso: sesión, Google OIDC, 2FA TOTP y gestión de usuarios.

Extraídas de `aplicacion.py` (ARC-A01, #334). Comportamiento idéntico: el
estado que antes capturaban las closures (freno, estados OAuth, config) se
lee de `request.app.state`.
"""
import json
import secrets
import time

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from .. import google_oidc, idempotencia, seguridad, totp, totp_qr
from . import comun
from .modelos import ClaveActualIn, ClaveIn, CodigoTotpIn, Credenciales, UsuarioIn

router = APIRouter()

# --- Login con Google (OAuth 2.0 / OIDC): adaptador opcional (spec-api-v1).
# DECISIÓN 2026-10-29: sustituye al par usuario/clave + TOTP para la
# identidad vinculada; no lleva freno de fuerza bruta ni aprovisionamiento.


@router.post("/sesion")
def abrir_sesion(
    credenciales: Credenciales,
    response: Response,
    request: Request,
    conexion=Depends(comun.conexion),
) -> dict:
    ip = request.client.host if request.client else "desconocida"
    freno: seguridad.FrenoDeLogins = request.app.state.freno_logins
    if freno.bloqueado(ip, credenciales.usuario, time.time()) or \
            freno.bloqueado_usuario(credenciales.usuario, time.time()):
        raise HTTPException(status_code=429, detail="demasiados intentos; espera unos minutos")
    auth = seguridad.autenticar(conexion, credenciales.usuario, credenciales.clave)
    if auth is None:
        freno.registrar_fallo(ip, credenciales.usuario, time.time())
        freno.registrar_fallo_usuario(credenciales.usuario, time.time())
        seguridad.auditar(conexion, credenciales.usuario, "login", "/sesion", "rechazado")
        conexion.commit()
        raise HTTPException(status_code=401, detail="credenciales inválidas")
    usuario_id, empresa_id, rol, totp_activado = auth
    config = request.app.state.configuracion
    if totp_activado:
        secreto = seguridad.secreto_totp(conexion, usuario_id)
        if not credenciales.totp:
            seguridad.auditar(conexion, credenciales.usuario, "login", "/sesion", "falta codigo 2fa")
            conexion.commit()
            raise HTTPException(status_code=401, detail="codigo_totp_requerido")
        if secreto is None or not totp.verificar(secreto, credenciales.totp):
            freno.registrar_fallo(ip, credenciales.usuario, time.time())
            freno.registrar_fallo_usuario(credenciales.usuario, time.time())
            seguridad.auditar(conexion, credenciales.usuario, "login", "/sesion", "2fa rechazado")
            conexion.commit()
            raise HTTPException(status_code=401, detail="código 2FA inválido")
    # SEC-A03 (#328): los contadores se reinician solo al completar TODA
    # la autenticación. Hacerlo con la clave correcta (antes del TOTP)
    # borraba los fallos en cada intento y dejaba el segundo factor sin
    # freno de fuerza bruta (auditoría de jefatura 2026-11-03, SEC-A03).
    freno.reiniciar(ip, credenciales.usuario)
    freno.reiniciar_usuario(credenciales.usuario)
    sid = seguridad.crear_sesion(
        conexion, usuario_id, empresa_id,
        horas_vigencia=config.session_horas if config else 12,
    )
    seguridad.auditar(conexion, credenciales.usuario, "login", "/sesion", "ok")
    conexion.commit()
    comun.fijar_cookie_sesion(response, request, sid)
    return {
        "usuario": credenciales.usuario,
        "rol": rol,
        "empresa_id": empresa_id,
        "totp_activado": totp_activado,
    }


@router.delete("/sesion")
def cerrar_sesion(request: Request, response: Response, conexion=Depends(comun.conexion)) -> dict:
    sid = request.cookies.get(comun.NOMBRE_COOKIE_SESION)
    if not sid:
        raise HTTPException(status_code=401, detail="sin sesión")
    sesion = seguridad.obtener_sesion_activa(conexion, sid)
    if sesion is None:
        raise HTTPException(status_code=401, detail="sesión inválida o vencida")
    seguridad.revocar_sesion(conexion, sid)
    conexion.commit()
    comun.borrar_cookie_sesion(response, request)
    return {"estado": "cerrada"}


@router.get("/sesion")
def ver_sesion(sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion), conexion=Depends(comun.conexion)) -> dict:
    (totp_activado,) = conexion.execute(
        "SELECT totp_activado FROM usuarios WHERE id = %s", (sesion.usuario_id,)
    ).fetchone()
    return {
        "id": sesion.usuario_id,
        "usuario": sesion.nombre,
        "rol": sesion.rol,
        "empresa_id": sesion.empresa_id,
        "totp_activado": totp_activado,
    }


@router.get("/auth/google/estado")
def estado_login_google(request: Request) -> dict:
    return {"configurado": google_oidc.configurado(request.app.state.configuracion)}


@router.get("/auth/google")
def iniciar_login_google(request: Request) -> Response:
    config = request.app.state.configuracion
    if not google_oidc.configurado(config):
        raise HTTPException(status_code=503, detail="no configurado")
    # SEC-A05 (#330): la transacción queda atada a una cookie HttpOnly de
    # vida corta; el callback exige que la cookie coincida con el state.
    tx = secrets.token_urlsafe(16)
    estado = request.app.state.estados_oauth.nuevo(tx=tx)
    url = google_oidc.url_de_consentimiento(config.google_client_id, estado, config.google_redirect_uri)
    respuesta = RedirectResponse(url, status_code=302)
    segura = config.cookie_segura if config else False
    respuesta.set_cookie(
        comun.NOMBRE_COOKIE_OAUTH_TX,
        tx,
        max_age=google_oidc.VIDA_ESTADO_SEG,
        httponly=True,
        secure=segura,
        samesite="none" if segura else "lax",
        path="/auth",
    )
    return respuesta


@router.get("/auth/google/callback")
def callback_login_google(
    request: Request,
    state: str | None = None,
    code: str | None = None,
    error: str | None = None,
    conexion=Depends(comun.conexion),
) -> Response:
    config = request.app.state.configuracion
    if not google_oidc.configurado(config):
        raise HTTPException(status_code=503, detail="no configurado")
    front = config.front_url
    if error is not None:
        destino = RedirectResponse(f"{front}/login?error=acceso_denegado", status_code=302)
        comun.borrar_cookie_oauth_tx(destino, request)
        return destino
    # El state se consume en todo intento (tomar lo extrae siempre): un
    # rechazo por cookie ausente o distinta no deja el state reutilizable.
    tx = request.cookies.get(comun.NOMBRE_COOKIE_OAUTH_TX)
    if state is None or not request.app.state.estados_oauth.tomar(state, tx=tx):
        raise HTTPException(status_code=400, detail="state inválido o expirado")
    if code is None:
        raise HTTPException(status_code=400, detail="falta el código de autorización")
    try:
        tokens = google_oidc.intercambiar_codigo(
            code, config.google_client_id, config.google_client_secret, config.google_redirect_uri
        )
        claims = google_oidc.verificar_id_token(tokens["id_token"], config.google_client_id)
    except (google_oidc.ErrorGoogleOidc, KeyError) as fallo:
        raise HTTPException(status_code=502, detail="fallo al validar la identidad con Google") from fallo
    email = claims["email"]
    usuario = seguridad.buscar_usuario_por_email(conexion, email)
    if usuario is None:
        seguridad.auditar(conexion, email, "login", "/auth/google/callback", "sin vinculo")
        conexion.commit()
        destino = RedirectResponse(f"{front}/login?error=cuenta_sin_vinculo", status_code=302)
        comun.borrar_cookie_oauth_tx(destino, request)
        return destino
    usuario_id, empresa_id, _rol, nombre = usuario
    sid = seguridad.crear_sesion(
        conexion, usuario_id, empresa_id,
        horas_vigencia=config.session_horas,
    )
    seguridad.auditar(conexion, nombre, "login", "/auth/google/callback", "ok")
    conexion.commit()
    destino = RedirectResponse(front, status_code=302)
    comun.fijar_cookie_sesion(destino, request, sid)
    comun.borrar_cookie_oauth_tx(destino, request)
    return destino


@router.post("/cuenta/2fa")
def iniciar_2fa(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
    cuerpo: ClaveActualIn | None = Body(default=None),
) -> dict:
    """Genera el secreto TOTP pendiente: el factor activo queda intacto
    hasta confirmar. SEC-A02 (#327): con 2FA ya activo (reenrolamiento)
    exige la clave actual — una sesión capturada no puede reemplazar el
    autenticador."""
    (activo,) = conexion.execute(
        "SELECT totp_activado FROM usuarios WHERE id = %s", (sesion.usuario_id,)
    ).fetchone()
    if activo:
        if cuerpo is None or not seguridad.reautenticar_clave(conexion, sesion.usuario_id, cuerpo.clave):
            seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa", "reauth rechazada")
            conexion.commit()
            raise HTTPException(status_code=401, detail="se requiere la clave actual para reemplazar el autenticador")
    secreto = seguridad.iniciar_alta_totp(conexion, sesion.usuario_id)
    seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa", "alta iniciada")
    conexion.commit()
    return {
        "secreto": secreto,
        "uri": totp.uri_de_alta(secreto, sesion.nombre),
    }


@router.post("/cuenta/2fa/activar")
def activar_2fa(
    cuerpo: CodigoTotpIn,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    secreto = seguridad.secreto_totp_pendiente(conexion, sesion.usuario_id)
    if secreto is None:
        raise HTTPException(status_code=400, detail="no hay alta de 2FA en curso")
    if not totp.verificar(secreto, cuerpo.codigo):
        seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa/activar", "rechazado")
        conexion.commit()
        raise HTTPException(status_code=400, detail="código 2FA inválido")
    seguridad.activar_totp(conexion, sesion.usuario_id)
    seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa/activar", "activado")
    conexion.commit()
    return {"estado": "activado"}


@router.get("/cuenta/2fa/qr")
def qr_2fa(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> Response:
    """QR (SVG) del secreto PENDIENTE: escaneable por Google Authenticator.

    SEC-A02 (#327): el secreto activo nunca se expone; el QR sirve solo
    durante el alta en curso."""
    secreto = seguridad.secreto_totp_pendiente(conexion, sesion.usuario_id)
    if secreto is None:
        raise HTTPException(status_code=400, detail="no hay alta de 2FA en curso; iníciala con POST /cuenta/2fa")
    svg = totp_qr.uri_a_svg(totp.uri_de_alta(secreto, sesion.nombre))
    return Response(content=svg, media_type="image/svg+xml")


@router.delete("/cuenta/2fa")
def desactivar_2fa(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
    cuerpo: ClaveActualIn | None = Body(default=None),
) -> dict:
    """SEC-A02 (#327): desactivar exige la clave actual (reautenticación):
    una sesión capturada no puede eliminar el segundo factor."""
    if cuerpo is None or not seguridad.reautenticar_clave(conexion, sesion.usuario_id, cuerpo.clave):
        seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa", "reauth rechazada")
        conexion.commit()
        raise HTTPException(status_code=401, detail="clave de confirmación inválida")
    seguridad.desactivar_totp(conexion, sesion.usuario_id)
    seguridad.auditar(conexion, sesion.nombre, "2fa", "/cuenta/2fa", "desactivado")
    conexion.commit()
    return {"estado": "desactivado"}


@router.get("/usuarios")
def listar_usuarios(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_admin(sesion)
    return {"usuarios": seguridad.listar_usuarios(conexion, sesion.empresa_id)}


@router.post("/usuarios")
def alta_usuario(
    usuario: UsuarioIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = json.loads(usuario.model_dump_json())

    def operacion() -> tuple[int, dict]:
        existe = conexion.execute(
            "SELECT 1 FROM usuarios WHERE empresa_id = %s AND nombre = %s",
            (sesion.empresa_id, usuario.nombre),
        ).fetchone()
        if existe is not None:
            return 409, {"detail": "nombre de usuario ya existe en la empresa"}
        usuario_id = seguridad.crear_usuario(
            conexion, sesion.empresa_id, usuario.nombre, usuario.rol, usuario.clave
        )
        seguridad.auditar(conexion, sesion.nombre, "usuario", usuario_id, "creado")
        return 201, {"id": usuario_id, "nombre": usuario.nombre, "rol": usuario.rol, "activo": True}

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)


@router.post("/usuarios/{usuario_id}/clave")
def cambiar_clave_usuario(
    usuario_id: str,
    cuerpo_clave: ClaveIn,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    if sesion.rol != "administrador" and sesion.usuario_id != usuario_id:
        raise HTTPException(status_code=403, detail="acceso denegado")
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"usuario_id": usuario_id, **json.loads(cuerpo_clave.model_dump_json())}

    def operacion() -> tuple[int, dict]:
        seguridad.buscar_usuario_en_empresa(conexion, sesion.empresa_id, usuario_id)
        seguridad.cambiar_clave(conexion, usuario_id, cuerpo_clave.clave)
        conservar = sesion.sid if sesion.usuario_id == usuario_id else None
        revocadas = seguridad.revocar_sesiones_de_usuario(
            conexion, usuario_id, conservar_sid=conservar
        )
        seguridad.auditar(
            conexion, sesion.nombre, "usuario-clave", usuario_id, f"cambiada; {revocadas} sesiones"
        )
        return 200, {
            "id": usuario_id,
            "estado": "clave actualizada",
            "sesiones_revocadas": revocadas,
        }

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)


@router.post("/usuarios/{usuario_id}/revocacion")
def revocar_usuario(
    usuario_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin(sesion)
    if usuario_id == sesion.usuario_id:
        raise HTTPException(status_code=409, detail="para cerrar tu sesión usa DELETE /sesion")
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"usuario_id": usuario_id, "operacion": "revocacion"}

    def operacion() -> tuple[int, dict]:
        seguridad.buscar_usuario_en_empresa(conexion, sesion.empresa_id, usuario_id)
        revocadas = seguridad.revocar_sesiones_de_usuario(conexion, usuario_id)
        seguridad.auditar(conexion, sesion.nombre, "usuario-revocacion", usuario_id, f"{revocadas} sesiones")
        return 200, {"id": usuario_id, "sesiones_revocadas": revocadas}

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)


@router.post("/usuarios/{usuario_id}/baja")
def baja_usuario(
    usuario_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin(sesion)
    if usuario_id == sesion.usuario_id:
        raise HTTPException(status_code=409, detail="no puedes darte de baja a ti mismo")
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    cuerpo = {"usuario_id": usuario_id, "operacion": "baja"}

    def operacion() -> tuple[int, dict]:
        _id, _nombre, rol, activo = seguridad.buscar_usuario_en_empresa(
            conexion, sesion.empresa_id, usuario_id
        )
        if not activo:
            return 409, {"detail": "el usuario ya está de baja"}
        if rol == "administrador" and seguridad.contar_administradores_activos(
            conexion, sesion.empresa_id
        ) <= 1:
            return 409, {"detail": "no se puede dar de baja al último administrador activo"}
        seguridad.dar_de_baja(conexion, usuario_id)
        seguridad.auditar(conexion, sesion.nombre, "usuario-baja", usuario_id, "de baja")
        return 200, {"id": usuario_id, "activo": False}

    try:
        codigo, cuerpo_respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo_respuesta)
