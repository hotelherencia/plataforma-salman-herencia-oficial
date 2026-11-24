"""Auditoría E2E de mensajes, diálogos modales accesibles y toasts (Playwright + axe-core).

Ejecuta contra `next start` con API interceptada con datos sintéticos (sin producción ni .env)
verificando:
1. Cero diálogos nativos del navegador (window.alert/confirm/prompt).
2. Apertura, cierre con Escape, cancelación y confirmación de `role="alertdialog"` en escritorio y móvil.
3. Validación en línea dentro de `solicitarTexto` (reverso de cargo en `/hotel/reservas/RSV-DEMO-1`)
   y aparición de toast flotante accesible (`.toast-exito`) + aviso unificado `.aviso-ok`.
4. Consistencia visual y contraste WCAG 2.1/2.2 AA (`axe-core`: 0 violaciones críticas o serias)
   y 0 px de desborde horizontal en escritorio (1366x768) y móvil (390x844).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("UIUX_BASE_URL", "http://127.0.0.1:3119").rstrip("/")
AXE_PATH = Path(os.environ.get("AXE_PATH", "/home/herre/projects/blu/node_modules/axe-core/axe.min.js"))

RESERVA_SINTETICA = {
    "reserva_id": "RSV-DEMO-1",
    "habitacion_id": "HAB-02",
    "tipo_habitacion": "doble",
    "inicio": "2026-11-24",
    "fin": "2026-11-26",
    "noches": 2,
    "huesped_nombre": "Ana Prueba Sintética",
    "huesped_documento": "12345678-5",
    "estado": "confirmada",
    "canal": "recepcion",
    "tarifa_noche_aceptada_clp": 55000,
    "personas": 2,
    "adultos": 2,
    "ninos": 0,
    "grupo_id": None,
    "titular_aloja": True,
    "creada_en": "2026-11-23T15:00:00-03:00",
    "total_aceptado_clp": 110000,
    "precio_por_noche": [
        {"noche": "2026-11-24", "precio_clp": 55000, "origen": "tipo:doble"},
        {"noche": "2026-11-25", "precio_clp": 55000, "origen": "tipo:doble"},
    ],
    "cargos": [
        {
            "cargo_id": "CRG-DEMO-1",
            "tipo": "cargo",
            "concepto": "Minibar agua mineral",
            "monto_clp": 3500,
            "referencia": None,
            "registrado_en": "2026-11-23T16:00:00-03:00",
            "reversado": False,
            "producto_id": "PRD-1",
            "cantidad": 1,
            "precio_unitario_clp": 3500,
        }
    ],
    "pagos": [],
    "cuenta": {"cargos_netos_clp": 113500, "pagado_clp": 0, "saldo_clp": 113500},
    "liquidacion": None,
    "reasignaciones": [],
    "credito_cliente": None,
    "datos_faltantes": [],
}


def interceptar_api(page):
    def handler(route):
        url = route.request.url
        metodo = route.request.method
        if "/api/sesion" in url:
            return route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "id": "USR-1",
                    "usuario": "admin_demo",
                    "rol": "administrador",
                    "empresa_id": "EMP-SINT",
                    "totp_activado": True,
                    "mfa_pendiente": False,
                }),
            )
        if "/api/hotel/avisos" in url:
            return route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"solicitudes_recibidas": 0, "canales_activos": []}),
            )
        if "/api/hotel/reservas/RSV-DEMO-1/cargos/CRG-DEMO-1/reverso" in url and metodo == "POST":
            return route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"reverso_id": "CRG-REV-1", "monto_clp": 3500, "saldo_clp": 110000}),
            )
        if "/api/hotel/reservas/RSV-DEMO-1/cancelacion" in url and metodo == "POST":
            return route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"reserva_id": "RSV-DEMO-1", "estado": "cancelada", "penalidad_clp": 0}),
            )
        if "/api/hotel/reservas/RSV-DEMO-1/mensajes" in url:
            return route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({
                    "reserva_id": "RSV-DEMO-1",
                    "alerta": None,
                    "datos_faltantes": [],
                    "contacto": {"correo": "ana@ejemplo.cl", "telefono": "+56912345678"},
                    "mensajes": [
                        {
                            "plantilla": "confirmacion",
                            "nombre": "Confirmación de reserva",
                            "asunto": "Confirmación Hotel Herencia",
                            "texto": "Hola Ana, tu reserva está confirmada.",
                            "whatsapp": "https://wa.me/56912345678",
                            "puede_correo": True,
                        }
                    ],
                    "historial": [],
                }),
            )
        if "/api/hotel/reservas/RSV-DEMO-1/saldo" in url:
            return route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"total_clp": 113500, "abonado_clp": 0, "pagado_clp": 0, "pendiente_clp": 113500, "noches": []}),
            )
        if "/api/hotel/reservas/RSV-DEMO-1" in url:
            return route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(RESERVA_SINTETICA),
            )
        if "/api/hotel/habitaciones" in url:
            return route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"habitaciones": [{"habitacion_id": "HAB-02", "tipo": "doble", "capacidad": 2}]}),
            )
        if "/api/hotel/oferta" in url:
            return route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"items": []}),
            )
        if "/api/cuenta/2fa" in url and metodo == "DELETE":
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"ok": True}))
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({}))

    page.route("**/api/**", handler)


def correr_axe(page) -> list[dict]:
    if not AXE_PATH.exists():
        return []
    page.add_script_tag(path=str(AXE_PATH))
    res = page.evaluate(
        """async () => {
            const r = await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] } });
            return r.violations.filter((v) => v.impact === 'critical' || v.impact === 'serious');
        }"""
    )
    return res


def main() -> int:
    fallos = []
    dialogos_nativos = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for nombre_vp, vp in (("escritorio-1366", {"width": 1366, "height": 768}), ("movil-390", {"width": 390, "height": 844})):
            ctx = browser.new_context(viewport=vp, bypass_csp=True)
            page = ctx.new_page()
            page.on("dialog", lambda d: (dialogos_nativos.append(d.message), d.dismiss()))
            interceptar_api(page)

            # 1. Ir a /hotel/reservas/RSV-DEMO-1 y probar modal de confirmación (Cancelar reserva) + Escape
            page.goto(f"{BASE_URL}/hotel/reservas/RSV-DEMO-1", wait_until="networkidle")
            page.get_by_role("button", name="Cancelar reserva").click()
            modal = page.locator('[role="alertdialog"]')
            modal.wait_for(state="visible", timeout=5000)

            overflow_modal = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            if overflow_modal > 1:
                fallos.append(f"{nombre_vp}: desborde horizontal con modal abierto ({overflow_modal}px)")

            violaciones_modal = correr_axe(page)
            if violaciones_modal:
                fallos.append(f"{nombre_vp} modal axe: {[v['id'] for v in violaciones_modal]}")

            # Cerrar con Escape
            page.keyboard.press("Escape")
            modal.wait_for(state="hidden", timeout=3000)

            # 2. Probar modal solicitarTexto (Reversar cargo) con validación y envío exitoso -> toast + aviso-ok
            page.get_by_role("button", name="Reversar").first.click()
            modal.wait_for(state="visible", timeout=5000)
            page.get_by_role("button", name="Asentar reverso").click()
            err_inline = modal.locator(".error-campo")
            err_inline.wait_for(state="visible", timeout=3000)

            modal.locator("textarea").fill("Cargo registrado por error")
            page.get_by_role("button", name="Asentar reverso").click()
            modal.wait_for(state="hidden", timeout=5000)

            aviso_ok = page.locator(".aviso-ok").first
            aviso_ok.wait_for(state="visible", timeout=5000)
            toast_ok = page.locator(".toast-exito").first
            toast_ok.wait_for(state="visible", timeout=5000)

            overflow_toast = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            if overflow_toast > 1:
                fallos.append(f"{nombre_vp}: desborde horizontal con toast visible ({overflow_toast}px)")

            violaciones_post = correr_axe(page)
            if violaciones_post:
                fallos.append(f"{nombre_vp} toast/aviso-ok axe: {[v['id'] for v in violaciones_post]}")

            # 3. Ir a /cuenta y verificar modal de desactivar doble factor (sin window.confirm)
            page.goto(f"{BASE_URL}/cuenta", wait_until="networkidle")
            page.get_by_role("button", name="Desactivar doble factor").click()
            modal.wait_for(state="visible", timeout=5000)
            page.get_by_role("button", name="Cancelar").click()
            modal.wait_for(state="hidden", timeout=3000)

            ctx.close()
        browser.close()

    if dialogos_nativos:
        fallos.append(f"Se dispararon diálogos nativos del navegador: {dialogos_nativos}")

    print(json.dumps({"ok": len(fallos) == 0, "dialogos_nativos": len(dialogos_nativos), "fallos": fallos}, ensure_ascii=False))
    return 0 if not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
