"""Configuración → Avisos (2026-11-19): qué eventos avisan por correo, a
quién, últimos envíos y correo de prueba. Solo administración del hotel."""
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .. import avisos, idempotencia, seguridad
from . import comun

router = APIRouter()


def _despachador(request: Request):
    return getattr(request.app.state, "avisos", None)


def _canal(request: Request, conexion) -> dict:
    """Desde dónde sale el correo, sin secretos: buzón de la plataforma,
    SMTP de variables o ninguno."""
    despachador = _despachador(request)
    canal = despachador.canal_correo(conexion) if despachador else None
    if isinstance(canal, avisos.CanalBuzon):
        b = canal.buzon
        return {"origen": "buzon", "etiqueta": b.etiqueta, "proveedor": b.proveedor,
                "remitente": b.parametros.get("remitente") or b.parametros.get("usuario"),
                "destino_defecto": b.parametros.get("destino")}
    if isinstance(canal, avisos.CanalCorreo):
        return {"origen": "entorno", "etiqueta": "Servidor SMTP del servicio", "proveedor": "smtp",
                "remitente": canal.remitente, "destino_defecto": canal.destino}
    if canal is not None:
        return {"origen": "otro", "etiqueta": canal.nombre, "proveedor": None, "remitente": None, "destino_defecto": None}
    return {"origen": "ninguno", "etiqueta": None, "proveedor": None, "remitente": None, "destino_defecto": None}


def _defecto(request: Request, canal: dict) -> list[str]:
    despachador = _despachador(request)
    return (avisos.correos_desde_texto(canal.get("destino_defecto"))
            or (list(despachador.destinos_defecto) if despachador else []))


@router.get("/hotel/avisos/configuracion")
def ver_configuracion(
    request: Request,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_admin_hotel(sesion)
    canal = _canal(request, conexion)
    return {
        "preferencias": list(avisos.preferencias(conexion, sesion.empresa_id).values()),
        "destinatarios_defecto": _defecto(request, canal),
        "canal": canal,
        "envios": avisos.ultimos_envios(conexion, sesion.empresa_id, 20),
        "max_destinatarios": avisos.MAX_DESTINATARIOS,
        "hora_resumen": f"{avisos.HORA_RESUMEN:02d}:00",
    }


@router.put("/hotel/avisos/preferencias")
def guardar_preferencias(
    cuerpo: dict = Body(...),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)

    def operacion() -> tuple[int, dict]:
        try:
            return 200, avisos.guardar_preferencias(conexion, sesion.empresa_id, cuerpo, sesion.nombre)
        except avisos.PreferenciaInvalida as error:
            return 422, {"detail": error.detalle}

    try:
        codigo, respuesta = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, {"avisos": cuerpo}, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=respuesta)


@router.post("/hotel/avisos/prueba")
def enviar_prueba(
    request: Request,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Manda ahora un correo de prueba a todos quienes reciben algún aviso
    encendido (su lista propia o, si no tiene, el correo por defecto)."""
    comun.exigir_admin_hotel(sesion)
    despachador = _despachador(request)
    if despachador is None:
        return JSONResponse(status_code=200, content={"ok": False, "detalle": "Los avisos no están disponibles en este servicio."})
    defecto = _defecto(request, _canal(request, conexion))
    destinos: list[str] = []
    for p in avisos.preferencias(conexion, sesion.empresa_id).values():
        if p["activo"]:  # a quien recibiría ese aviso: su lista o el correo por defecto
            destinos += [d for d in (p["destinatarios"] or defecto) if d not in destinos]
    if not destinos:
        return JSONResponse(status_code=200, content={
            "ok": False, "detalle": "No hay destinatarios: agrega al menos un correo en algún aviso."})
    conexion.rollback()  # la prueba abre su propia conexión
    resultado = despachador.enviar_prueba(sesion.empresa_id, destinos)
    seguridad.auditar(conexion, sesion.nombre, "avisos_prueba", sesion.empresa_id, "ok" if resultado["ok"] else "falla")
    conexion.commit()
    return JSONResponse(status_code=200, content=resultado)
