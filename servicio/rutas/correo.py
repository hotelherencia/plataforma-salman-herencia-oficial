"""Servidores de correo desde Configuración (#355)."""
from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from .. import ajustes, correo, idempotencia, seguridad
from . import comun

router = APIRouter()


def _catalogo() -> dict:
    return {
        "propositos": list(correo.PROPOSITOS),
        "proveedores": {k: list(v) for k, v in correo.PROVEEDORES.items()},
        "autenticaciones": {k: list(v) for k, v in correo.AUTENTICACIONES.items()},
        "parametros": {k: list(v) for k, v in correo.PARAMETROS.items()},
        "secretos": {k: list(v) for k, v in correo.SECRETOS.items()},
        "seguridades": list(correo.SEGURIDADES),
    }


@router.get("/hotel/correo/buzones")
def listar_buzones(
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    comun.exigir_admin_hotel(sesion)
    return {
        "buzones": correo.listar(conexion, sesion.empresa_id),
        "cifrado_disponible": correo.cifrado_disponible(),
        "revision": ajustes.leer(conexion, sesion.empresa_id, "revision_correo"),
        "catalogo": _catalogo(),
    }


def _operar(conexion, sesion, clave, cuerpo_hash: dict, accion) -> JSONResponse:
    def operacion() -> tuple[int, dict]:
        try:
            return accion()
        except correo.CorreoInvalido as error:
            return 422, {"detail": error.detalle}
        except correo.CifradoNoConfigurado as error:
            return 409, {"detail": str(error)}

    try:
        codigo, cuerpo = idempotencia.ejecutar(conexion, sesion.empresa_id, clave, cuerpo_hash, operacion)
    except idempotencia.ConflictoIdempotencia as error:
        raise HTTPException(status_code=409, detail=str(error))
    conexion.commit()
    return JSONResponse(status_code=codigo, content=cuerpo)


def _huella(cuerpo: dict) -> dict:
    """La huella idempotente no guarda secretos en claro."""
    import hashlib
    import json

    secretos = cuerpo.get("secretos") or {}
    return {**{k: v for k, v in cuerpo.items() if k != "secretos"},
            "secretos": hashlib.sha256(json.dumps(secretos, sort_keys=True).encode()).hexdigest()}


@router.post("/hotel/correo/buzones")
def crear_buzon(
    cuerpo: dict = Body(...),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    return _operar(conexion, sesion, clave, _huella(cuerpo),
                   lambda: (201, correo.guardar(conexion, sesion.empresa_id, None, cuerpo, sesion.nombre)))


@router.put("/hotel/correo/buzones/{buzon_id}")
def editar_buzon(
    buzon_id: str,
    cuerpo: dict = Body(...),
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)
    return _operar(conexion, sesion, clave, {"buzon_id": buzon_id, **_huella(cuerpo)},
                   lambda: (200, correo.guardar(conexion, sesion.empresa_id, buzon_id, cuerpo, sesion.nombre)))


@router.delete("/hotel/correo/buzones/{buzon_id}")
def eliminar_buzon(
    buzon_id: str,
    idempotency_key: str | None = Header(default=None),
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    comun.exigir_admin_hotel(sesion)
    clave = comun.clave_idempotencia_o_400(idempotency_key)

    def accion():
        correo.eliminar(conexion, sesion.empresa_id, buzon_id, sesion.nombre)
        return 200, {"buzon_id": buzon_id, "eliminado": True}

    return _operar(conexion, sesion, clave, {"eliminar": buzon_id}, accion)


@router.post("/hotel/correo/buzones/{buzon_id}/prueba")
def probar_buzon(
    buzon_id: str,
    request: Request,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> JSONResponse:
    """Prueba la conexión con lo guardado: lee enviados de 7 días (solo
    cuenta) o manda un correo de prueba al destino de avisos."""
    comun.exigir_admin_hotel(sesion)
    fabrica = getattr(request.app.state, "correo_fabrica", None)
    try:
        fila = correo._fila(conexion, sesion.empresa_id, buzon_id)
        buzon = (fabrica or correo.buzon_desde_fila)(fila)
        resultado = buzon.probar()
    except correo.CorreoInvalido as error:
        return JSONResponse(status_code=422 if error.detalle == "buzón inexistente" else 200,
                            content={"ok": False, "detalle": error.detalle})
    except correo.CifradoNoConfigurado as error:
        return JSONResponse(status_code=409, content={"detail": str(error)})
    except Exception as error:  # noqa: BLE001 (red, credenciales, proveedor)
        resultado = {"ok": False, "detalle": f"{type(error).__name__}: {error}"[:300]}
    seguridad.auditar(conexion, sesion.nombre, "buzon_correo", buzon_id, "prueba:" + ("ok" if resultado["ok"] else "falla"))
    conexion.commit()
    return JSONResponse(status_code=200, content=resultado)


@router.post("/hotel/correo/revision")
def revisar_ahora(
    request: Request,
    sesion: seguridad.SesionActiva = Depends(comun.requerir_sesion),
    conexion=Depends(comun.conexion),
) -> dict:
    """«Revisar ahora»: misma revisión que el ciclo de 15 minutos."""
    comun.exigir_admin_hotel(sesion)
    resultado = correo.revisar(conexion, sesion.empresa_id, getattr(request.app.state, "correo_fabrica", None))
    seguridad.auditar(conexion, sesion.nombre, "revision_correo", sesion.empresa_id,
                      f"{resultado['leads_contactados']} contactado(s)")
    conexion.commit()
    return resultado
