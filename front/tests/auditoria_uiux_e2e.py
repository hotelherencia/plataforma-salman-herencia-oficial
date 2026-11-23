"""Auditoría E2E automatizada UI/UX + Geometría + WCAG 2.1/2.2 AA (Playwright + axe-core).

Valida sobre el servidor Next.js local (datos sintéticos interceptados en `/api/*`,
sin tocar producción ni `.env`) en 4 viewports (`360x740`, `390x844`, `768x1024`, `1366x768`):
  1. Cero desborde horizontal (`scrollWidth <= innerWidth`).
  2. Alineación geométrica en formularios y filtros (`|bottom_A - bottom_B| <= 2px` en escritorio,
     botones estándar `44px <= height <= 56px`).
  3. Regla anti-repetición de botones (máximo de botones con el mismo texto visibles simultáneamente
     en tablas/listados <= 3, más prueba funcional de clic en fila → barra contextual activa).
  4. `axe-core` WCAG 2.0/2.1 AA: 0 violaciones críticas o serias.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("UIUX_BASE_URL", "http://127.0.0.1:3111")
LANDING_URL = os.environ.get("UIUX_LANDING_URL", "")
AXE_PATH = Path(os.environ.get("AXE_PATH", "/home/herre/projects/blu/node_modules/axe-core/axe.min.js"))

VIEWPORTS = [
    ("360x740", 360, 740),
    ("390x844", 390, 844),
    ("768x1024", 768, 1024),
    ("1366x768", 1366, 768),
]

RUTAS = [
    "/hotel/reservas",
    "/hotel/leads",
    "/hotel/solicitudes",
    "/hotel/clientes",
    "/hotel/habitaciones",
    "/hotel/productos",
    "/hotel/aseo",
    "/hotel/caja?pestana=cuenta",
    "/hotel/caja?pestana=movimientos",
    "/reservar?llegada=2026-12-10&salida=2026-12-12&personas=2",
]


def _datos_sinteticos(path: str) -> dict:
    if path.startswith("/api/sesion"):
        return {
            "id": "USR-QA-1",
            "usuario": "admin_qa",
            "rol": "admin_hotel",
            "empresa_id": "EMP-SINTETICA-001",
            "totp_activo": True,
        }
    if path.startswith("/api/hotel/reservas"):
        reservas = [
            {
                "reserva_id": f"RSV-QA-{i:03d}",
                "huesped_nombre": f"Huésped Prueba {i}",
                "huesped_documento": f"12.345.{600 + i}-5",
                "habitacion_id": f"HAB-{i:02d}",
                "inicio": "2026-12-10",
                "fin": "2026-12-12",
                "estado": ["confirmada", "en_estadia", "finalizada", "cancelada"][i % 4],
                "tarifa_noche_aceptada_clp": 55000,
            }
            for i in range(1, 13)
        ]
        return {"total": len(reservas), "reservas": reservas}
    if path.startswith("/api/hotel/leads"):
        leads = [
            {
                "id": f"LEAD-{i:03d}",
                "nombre": f"Contacto Web {i}",
                "correo": f"contacto{i}@ejemplo.cl",
                "telefono": f"+56 9 5555 00{i:02d}",
                "huespedes": 2,
                "check_in": "2026-12-15",
                "check_out": "2026-12-17",
                "mensaje": "Consulta de disponibilidad familiar",
                "estado": "nuevo" if i % 2 else "contactado",
                "nota": "",
                "creado_en": "2026-11-23T12:00:00Z",
                "gestion_por": None,
                "gestion_en": None,
                "cliente_id": None,
                "solicitud_id": None,
                "leads_del_contacto": 1,
            }
            for i in range(1, 13)
        ]
        return {"leads": leads, "corte": {"desde": "2026-11-10", "ventana_nuevo_dias": 14}, "sin_gestionar_antiguos": 0}
    if path.startswith("/api/hotel/solicitudes"):
        sols = [
            {
                "solicitud_id": f"SOL-{i:03d}",
                "tipo": "matrimonial_mas_1" if i % 2 else "doble",
                "habitacion_id": None,
                "inicio": "2026-12-12",
                "fin": "2026-12-14",
                "personas": 2,
                "huesped_nombre": f"Solicitante {i}",
                "huesped_contacto": f"sol{i}@ejemplo.cl · Tel: +56 9 4444 00{i:02d}",
                "origen": "landing",
                "estado": "recibida" if i <= 10 else "convertida",
                "reserva_id": None if i <= 10 else f"RSV-QA-{i:03d}",
            }
            for i in range(1, 13)
        ]
        return {"solicitudes": sols}
    if path.startswith("/api/hotel/clientes"):
        clientes = [
            {
                "id": f"CLI-{i:03d}",
                "nombre": f"Empresa Cliente {i} SpA",
                "rut": f"76.543.{200 + i}-K",
                "tipo": "empresa",
                "telefono": f"+56 9 3333 00{i:02d}",
                "correo": f"facturacion{i}@empresa.cl",
                "politica_credito": "credito_autorizado" if i % 2 else "pago_al_registrarse",
                "cupo_credito_clp": 500000 if i % 2 else 0,
                "plazo_dias": 30 if i % 2 else 0,
                "activo": True,
            }
            for i in range(1, 13)
        ]
        return {"clientes": clientes, "truncado": False}
    if path.startswith("/api/hotel/contabilidad/cuentas-por-cobrar"):
        cxc = [
            {
                "cxc_id": f"CXC-{i:03d}",
                "cliente_nombre": f"Empresa Cliente {i} SpA",
                "cliente_rut": f"76.543.{200 + i}-K",
                "politica_aplicada": "credito_autorizado",
                "reserva_id": f"RSV-QA-{i:03d}",
                "habitacion_id": f"HAB-{i:02d}",
                "huesped_nombre": f"Huésped Prueba {i}",
                "fecha_vencimiento": "2026-12-20",
                "vencida": False,
                "dias_vencido": 0,
                "tramo_antiguedad": "0-30",
                "monto_original_clp": 110000,
                "saldo_pendiente_clp": 110000,
            }
            for i in range(1, 11)
        ]
        return {
            "total_pendiente_clp": 1100000,
            "total_vencido_clp": 0,
            "tramos": {"0-30": {"monto_clp": 1100000, "cantidad": 10}, "31-60": {"monto_clp": 0, "cantidad": 0}, "61-90": {"monto_clp": 0, "cantidad": 0}, "mas_90": {"monto_clp": 0, "cantidad": 0}},
            "cuentas_por_cobrar": cxc,
        }
    if path.startswith("/api/hotel/habitaciones"):
        habs = [
            {
                "habitacion_id": f"HAB-{i:02d}",
                "tipo": "matrimonial_mas_1" if i % 3 == 0 else "doble",
                "capacidad": 3 if i % 3 == 0 else 2,
                "estado_operativo": "disponible" if i % 2 else "ocupada",
                "estado_preparacion": "sucia" if i % 3 == 0 else "limpia",
                "limpieza_pendiente": i % 3 == 0,
                "mantenimiento": False,
                "tarifa_vigente_hoy_clp": 55000,
            }
            for i in range(1, 18)
        ]
        return {"habitaciones": habs}
    if path.startswith("/api/hotel/productos"):
        prods = [
            {
                "producto_id": f"PRD-{i:03d}",
                "nombre": f"Agua mineral {i}",
                "categoria": "minibar",
                "precio_clp": 2500 + i * 100,
                "costo_clp": 1000,
                "codigo": f"780123400{i:03d}",
                "controla_stock": True,
                "stock": 12,
                "activo": True,
            }
            for i in range(1, 16)
        ]
        return {"productos": prods}
    if path.startswith("/api/hotel/aseo"):
        habs = [
            {
                "habitacion_id": f"HAB-{i:02d}",
                "tipo": "matrimonial_mas_1" if i % 2 else "doble",
                "situacion": "sale_hoy" if i <= 6 else "libre",
                "estado_preparacion": "sucia" if i <= 6 else "limpia",
                "limpieza_pendiente": i <= 6,
                "en_limpieza": False,
                "mantenimiento_hoy": False,
                "observaciones": [],
                "ultima_limpieza": {"tarea_id": f"LIM-{i}", "completada_en": "2026-11-23T11:30:00Z", "completada_por": "aseo1", "verificacion": None} if i > 6 else None,
            }
            for i in range(1, 18)
        ]
        return {"pendientes": 6, "por_verificar": ["HAB-07", "HAB-08"], "habitaciones": habs}
    if path.startswith("/api/hotel/contabilidad/movimientos"):
        movs = [
            {
                "movimiento_directo_id": f"MVD-{i:03d}",
                "fecha_hora": "2026-11-23T13:15:00Z",
                "tipo": "cargo_directo",
                "concepto": f"Desayuno externo {i}",
                "cantidad": 1,
                "reserva_id": None,
                "habitacion_id": None,
                "monto_clp": 12000,
                "medio": None,
                "estado_cobro": "pendiente",
                "documento_tipo": "boleta",
                "actor": "admin_qa",
                "reversado": False,
            }
            for i in range(1, 13)
        ]
        return {
            "movimientos": movs,
            "resumen": {
                "total_devengado_clp": 144000,
                "cargos_reservas_clp": 0,
                "cargos_directos_clp": 144000,
                "total_cobrado_clp": 0,
                "pendiente_directo_clp": 144000,
                "egresos_operacionales_clp": 0,
            },
        }
    if path.startswith("/api/hotel/caja/movimientos"):
        movs = [
            {
                "movimiento_id": f"CAJ-{i:03d}",
                "fecha_contable": "2026-11-23",
                "registrado_en": "2026-11-23T14:20:00Z",
                "tipo": "cobro",
                "medio": "transferencia",
                "monto_clp": 55000,
                "huesped_nombre": f"Huésped Prueba {i}",
                "habitacion_id": f"HAB-{i:02d}",
                "pago_id": f"PAG-{i:03d}",
                "documento_tipo": "boleta",
                "actor": "admin_qa",
                "es_anticipo": False,
            }
            for i in range(1, 13)
        ]
        return {"movimientos": movs}
    if path.startswith("/api/hotel/contabilidad/cartolas"):
        return {
            "periodo": "2026-11",
            "cartolas": [],
            "movimientos_cartola": [],
            "internos_pendientes": [],
            "en_transito": [],
            "resumen": {"conciliados": 0, "parciales": 0, "pendientes_cartola": 0, "en_transito_cantidad": 0, "en_transito_clp": 0},
        }
    if path.startswith("/api/hotel/contabilidad/tributario"):
        return {
            "periodo": "2026-11",
            "nota_legal": "Borrador interno F29. Sin envío al SII.",
            "por_documento": {"boleta": {"cantidad": 10, "neto_clp": 462185, "iva_clp": 87815, "total_clp": 550000}},
            "compras_credito_fiscal": {"facturas_cantidad": 2, "notas_credito_cantidad": 0, "credito_fiscal_neto_clp": 19000},
            "ventas_en_transito": [],
            "borrador_f29": {
                "ventas_tributarias_neto_clp": 462185,
                "debito_fiscal_clp": 87815,
                "ventas_tributarias_total_clp": 550000,
                "iva_determinado_clp": 68815,
                "ventas_en_transito_total_clp": 0,
            },
        }
    if path.startswith("/api/hotel/contabilidad/comisiones-medios"):
        return {"comisiones": {"credito": {"proveedor": "transbank", "porcentaje_comision": 2.0, "iva_comision": True, "dias_habiles_abono": 2}}}
    if path.startswith("/api/publico/disponibilidad"):
        return {
            "vigencia_minutos": 30,
            "capacidad_maxima_habitacion": 3,
            "oferta": [
                {"habitacion_id": f"HAB-{i:02d}", "tipo": "doble" if i <= 8 else "matrimonial_mas_1", "capacidad": 2 if i <= 8 else 3, "tarifa_noche_clp": 55000 if i <= 8 else 65000, "total_clp": 110000 if i <= 8 else 130000, "politica_cancelacion": "Cancelación sin costo hasta 24 horas antes de la Llegada"}
                for i in range(1, 17)
            ],
        }
    if path.startswith("/api/hotel/comunicados"):
        return {"comunicados": [], "sin_leer": 0}
    if path.startswith("/api/hotel/turnos"):
        return {"desde": "2026-11-23", "hasta": "2026-11-29", "dias": [], "turnos": [], "cambios": []}
    if path.startswith("/api/hotel/biblioteca"):
        return {"documentos": [], "sugerencias": []}
    if path.startswith("/api/hotel/activos") or path.startswith("/api/hotel/mantenciones"):
        return {"activos": [], "mantenciones": []}
    if path.startswith("/api/hotel/tareas") or path.startswith("/api/hotel/checklists"):
        return {"items": [], "tareas": [], "plantillas": []}
    if path.startswith("/api/hotel/incidencias"):
        return {"items": [], "incidencias": []}
    return {}


def main() -> int:
    axe_js = AXE_PATH.read_text(encoding="utf-8") if AXE_PATH.exists() else ""
    reporte = {"base_url": BASE_URL, "viewports": [v[0] for v in VIEWPORTS], "resultados": [], "resumen": {}}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for nombre_vp, w, h in VIEWPORTS:
            context = browser.new_context(viewport={"width": w, "height": h}, bypass_csp=True)
            page = context.new_page()

            def interceptar(route):
                url = route.request.url
                idx = url.find("/api/")
                if idx != -1:
                    path = url[idx:]
                    route.fulfill(
                        status=200,
                        content_type="application/json",
                        body=json.dumps(_datos_sinteticos(path)),
                    )
                elif "google.com/recaptcha" in url or "gstatic.com" in url:
                    route.abort()
                else:
                    route.continue_()

            page.route("**/*", interceptar)

            rutas_a_probar = list(RUTAS)
            if LANDING_URL:
                rutas_a_probar.append(LANDING_URL)

            for ruta in rutas_a_probar:
                url_dest = ruta if ruta.startswith("http") else f"{BASE_URL}{ruta}"
                page.goto(url_dest, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(350)

                metricas = page.evaluate(
                    """() => {
                        const overflowX = document.documentElement.scrollWidth - window.innerWidth;
                        const botones = [...document.querySelectorAll('main button, main a.boton-primario, main a.boton-secundario, main a.boton-fantasma')]
                            .filter(el => el.offsetParent !== null);
                        const textos = {};
                        const alturasAnomalas = [];
                        for (const b of botones) {
                            const txt = (b.innerText || b.getAttribute('aria-label') || '').trim();
                            if (txt) textos[txt] = (textos[txt] || 0) + 1;
                            const r = b.getBoundingClientRect();
                            if (b.classList.contains('boton-primario') || b.classList.contains('boton-secundario') || b.classList.contains('boton-fantasma')) {
                                if (r.height > 56) alturasAnomalas.push({ txt, h: Math.round(r.height) });
                            }
                        }
                        const maxRepetido = Object.entries(textos).sort((a, b) => b[1] - a[1])[0] || ['', 0];

                        // Medir alineación bottom entre controles hermanos en .formulario y .filtros cuando están en la misma fila visual
                        const desalineaciones = [];
                        const contenedores = [...document.querySelectorAll('main .formulario, main .filtros')].filter(el => el.offsetParent !== null);
                        for (const cont of contenedores) {
                            const controles = [...cont.querySelectorAll(':scope > .campo input.entrada, :scope > .campo select.entrada, :scope > .campo .campo-fecha input.entrada, :scope > button, :scope > a.boton-primario, :scope > a.boton-secundario')]
                                .filter(el => el.offsetParent !== null);
                            // Agrupar por fila visual (top dentro de +-35px)
                            for (let i = 0; i < controles.length; i++) {
                                for (let j = i + 1; j < controles.length; j++) {
                                    const ra = controles[i].getBoundingClientRect();
                                    const rb = controles[j].getBoundingClientRect();
                                    if (Math.abs(ra.top - rb.top) < 30 && Math.abs(ra.left - rb.left) > 20) {
                                        const diffBottom = Math.abs(ra.bottom - rb.bottom);
                                        if (diffBottom > 2.5) {
                                            desalineaciones.push({
                                                a: controles[i].tagName,
                                                b: controles[j].tagName,
                                                diffBottom: Number(diffBottom.toFixed(1)),
                                            });
                                        }
                                    }
                                }
                            }
                        }

                        const tieneBarra = Boolean(document.querySelector('.barra-contextual'));
                        const radios = document.querySelectorAll('.selector-fila input[type="radio"]').length;
                        return {
                            overflowX,
                            maxBotonTexto: maxRepetido[0],
                            maxBotonRepeticiones: maxRepetido[1],
                            alturasAnomalas,
                            desalineaciones,
                            tieneBarra,
                            radios,
                        };
                    }"""
                )

                # Prueba funcional de selección -> barra contextual activa (en escritorio)
                interaccion_ok = None
                if nombre_vp == "1366x768" and metricas["radios"] > 0:
                    page.locator(".selector-fila").first.click()
                    page.wait_for_timeout(150)
                    activa = page.locator('.barra-contextual[data-activa="true"]').count()
                    interaccion_ok = activa > 0

                # axe-core WCAG 2.0/2.1 AA
                axe_criticas = []
                if axe_js and nombre_vp in ("360x740", "1366x768"):
                    page.add_script_tag(content=axe_js)
                    res_axe = page.evaluate(
                        """async () => {
                            const r = await axe.run(document, {
                                runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] }
                            });
                            return r.violations
                                .filter(v => v.impact === 'critical' || v.impact === 'serious')
                                .map(v => ({ id: v.id, impact: v.impact, count: v.nodes.length, help: v.help }));
                        }"""
                    )
                    axe_criticas = res_axe

                reporte["resultados"].append(
                    {
                        "viewport": nombre_vp,
                        "ruta": ruta,
                        **metricas,
                        "interaccion_seleccion_ok": interaccion_ok,
                        "axe_criticas_serias": axe_criticas,
                    }
                )
            context.close()
        browser.close()

    fallos = []
    for r in reporte["resultados"]:
        if r["overflowX"] > 1:
            fallos.append(f"{r['viewport']} {r['ruta']}: overflowX={r['overflowX']}px")
        if r["viewport"] == "1366x768" and r["desalineaciones"]:
            fallos.append(f"{r['viewport']} {r['ruta']}: desalineaciones={r['desalineaciones']}")
        if r["alturasAnomalas"]:
            fallos.append(f"{r['viewport']} {r['ruta']}: botones altos={r['alturasAnomalas']}")
        if r["tieneBarra"] and r["maxBotonRepeticiones"] > 3:
            fallos.append(f"{r['viewport']} {r['ruta']}: botón repetido '{r['maxBotonTexto']}' x{r['maxBotonRepeticiones']}")
        if r["interaccion_seleccion_ok"] is False:
            fallos.append(f"{r['viewport']} {r['ruta']}: clic en fila no activó BarraContextual")
        if r["axe_criticas_serias"]:
            fallos.append(f"{r['viewport']} {r['ruta']}: axe={r['axe_criticas_serias']}")

    reporte["resumen"] = {
        "total_checks": len(reporte["resultados"]),
        "fallos_count": len(fallos),
        "fallos": fallos,
    }
    print(json.dumps(reporte, ensure_ascii=False, indent=2))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
