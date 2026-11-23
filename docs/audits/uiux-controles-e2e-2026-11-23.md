# Auditoría UI/UX, Geometría de Controles y E2E Accesibilidad (WCAG 2.1/2.2 AA)

- **Fecha:** 2026-11-23
- **Rama:** `fix/uiux-controles-alineacion` (worktree limpio sobre `origin/main` `2795a23`)
- **Alcance:** `front/` de la plataforma Hotel Herencia (10 rutas interactivas clave) + landing `~/herencia-git/landinpage` (`index.html`).
- **Herramientas de verificación:**
  - Playwright + Chromium headless sobre `next start` con API interceptada con datos sintéticos (12–17 filas por tabla/listado, sin producción ni `.env`).
  - `axe-core` (`wcag2a`, `wcag2aa`, `wcag21aa`) en viewports móvil y escritorio.
  - Suite unitaria Node 24 (`node --test tests/*.test.mjs`) y build de producción (`npx next build`).

---

## 1. Resumen ejecutivo

| Indicador | Antes | Después |
|---|---:|---:|
| Máx. botones repetidos por vista (12–17 filas) | 24 a 90+ (`Editar`, `Convertir`, `Rechazar`, `Cambiar precio`, `Ajustar stock`, `Anotar`, `Reversar`) | **0 botones repetidos en filas** (`<= 1` barra contextual única por listado) |
| Desborde horizontal (`scrollWidth > innerWidth`) en 4 viewports | `18 px` en `768×1024` (`/hotel/caja?pestana=cuenta`) | **0 px** en **44 / 44** combinaciones ruta × viewport |
| Desalineación vertical en `.formulario` / `.filtros` (escritorio `1366×768`) | Botones desalineados en `.filtros` (`/hotel/clientes`) y 7.ª columna desbordando grilla de 6 en `/hotel/reservas` | **0 desalineaciones** (`|bottom_A - bottom_B| <= 2.5 px`) |
| Contraste WCAG AA (`axe-core` críticas/serias) | 3 fallos serios (`estado-en_estadia`: `4.14:1` < `4.5:1`) | **0 violaciones críticas o serias** en todas las rutas |
| Errores de runtime en carga parcial | Crash en `turnos.js` / `aseo/page.js` si `sesion.usuario` o `datos.dias` no estaban definidos | **0 errores de runtime** (guards defensivos) |
| Pruebas unitarias (`node --test`) | 157 / 157 | **161 / 161** (4 tests nuevos de invariantes UI/UX) |
| Build Next.js (`npx next build`) | 34 / 34 rutas | **34 / 34 rutas** sin errores ni advertencias |

---

## 2. Hallazgos y correcciones por ruta (Antes vs. Después)

| Ruta | Botones/controles repetidos **ANTES** (con N filas) | Solución aplicada **DESPUÉS** | Controles de acción visibles simultáneos (N=12–17) | Otros ajustes funcionales / UX |
|---|---|---|---|---|
| `/hotel/reservas` | `Editar` + `Ficha` en cada fila (`2N = 24`) + desfase entre grilla de 6 columnas y 7 hijos | `SelectorFila` + `BarraContextual` única (`Ver ficha y cuenta`, `Editar huésped`) + grilla exacta de 7 columnas (`3rem` + 6 datos) | **0** en filas · **1** barra contextual | Combo `Estado` en castellano legible (`Todos los estados`, `Confirmada`, `En estadía`, `Finalizada`, `Cancelada`); contraste AA en `.estado-en_estadia` (`#8a4b2f` sobre `#f6e4d8` ≥ `5.6:1`) |
| `/hotel/leads` | `Editar`, `Vincular`, `Historial`, `input Nota`, `Contactado`, `Cerrar` por fila (`5–6N = 60–72`) | `SelectorFila` + `BarraContextual` única + paneles únicos de edición, vínculo e historial debajo de la barra | **0** en filas · **1** barra contextual | Fechas Llegada/Salida formateadas a `dd/mm/aaaa` (`fechaATexto`); exportación alineada en grilla `.formulario` |
| `/hotel/solicitudes` | `Editar`, `Convertir en reserva`, `input Motivo`, `Rechazar` por fila (`4N = 48`) | `SelectorFila` + `BarraContextual` única (`Editar`, `Convertir en reserva`, campo motivo + `Rechazar`) | **0** en filas · **1** barra contextual | Botón exportar alineado dentro de `.filtros` |
| `/hotel/clientes` (+ CxC) | `Editar` + `Crédito` × N clientes (`24`) + `Registrar abono` × M cuentas (`10`) | `SelectorFila` + `BarraContextual` única en Clientes (`Editar ficha`, `Política de crédito`) y en CxC (`Ver reserva`, `Registrar abono`) | **0** en filas · **1** barra por tabla | `.filtros` con `align-items: flex-end` alinea exactamente campo buscar y botones; estado capitalizado (`Activo`/`Inactivo`) |
| `/hotel/habitaciones` | `Ficha`, `Completar limpieza`, `Abrir/Cerrar mantenimiento` × 17 filas (hasta `51`) | `SelectorFila` + `BarraContextual` única (`Abrir ficha`, `Completar limpieza`, `Abrir/Cerrar mantenimiento`) | **0** en filas · **1** barra contextual | `nombreTipo(h.tipo)` (elimina códigos crudos como `matrimonial_mas_1`); fechas de mantenimiento en `dd/mm/aaaa` |
| `/hotel/productos` | `input Nuevo precio`, `Cambiar precio`, `Activar/Desactivar`, `input Ajuste`, `input Motivo`, `Ajustar stock` × 15 productos (`90`) | Tabla de catálogo con `SelectorFila` + `BarraContextual` única y formularios únicos de precio y stock | **0** en filas · **1** barra contextual | `inputMode="numeric"` automático en campos de precio y stock |
| `/hotel/aseo` | `Empezar limpieza`, `Limpia`, `input Observación`, `Anotar`, `Verificar`, `Rechazar` × 17 habitaciones (`50–85`) | Tarjetas seleccionables (`SelectorFila`) + `BarraContextual` única con todas las acciones de la habitación elegida | **0** en tarjetas · **1** barra contextual | `fechaHora(...)` en última limpieza; estados capitalizados (`Sucia`, `Limpia`, `En limpieza`); guard defensivo en `turnos.js` y `aseo/page.js` |
| `/hotel/caja` (`Libro contable` y `Movimientos`) | `Cobrar` y `Reversar` repetidos por fila (`12–24`) | `SelectorFila` + `BarraContextual` única en `movimientos-contables.js` y `caja-contable.js` | **0** en filas · **1** barra contextual | Corregido desborde horizontal de `18 px` en `768×1024` permitiendo envoltura segura de botones en columnas estrechas y `grid-column: 1 / -1` en `textarea` |
| `/reservar` | Ya agrupaba por tipo de habitación (`agruparOferta`) y mostraba política única (`politicaUnica`) | Validación geométrica, `inputMode="numeric"` en `Personas` y controles de `44 px` | **0** botones repetidos | Error en línea accesible (`aria-invalid` + `aria-describedby`) y foco automático verificados |
| `/hotel/panel` y `/hotel/agente` | `<select>` con valores crudos (`matrimonial_mas_1`, `landing`, `(todos)`) | Etiquetas en castellano legible (`Todos los tipos`, `nombreTipo(t)`, `Manual (recepción)`, `Sitio web`, `Correo electrónico`, `WhatsApp`) | N/A | Sin ítems nuevos en `front/lib/menu-hotel.js` |
| Landing (`hotelherencia.cl`) | Revisión E2E en 4 viewports (`index.html`) | Sin desbordes, sin botones repetidos y `0` violaciones `axe-core` WCAG AA | **1** botón por acción | Validado en `360×740`, `390×844`, `768×1024` y `1366×768` |

---

## 3. Mediciones E2E automatizadas por viewport (`front/tests/auditoria_uiux_e2e.py`)

Todas las mediciones se ejecutaron sobre Chromium real (`next start` + servidor HTTP local para landing):

| Ruta | `360×740` (overflow / axe) | `390×844` (overflow) | `768×1024` (overflow) | `1366×768` (overflow / desalin. / clic fila → barra / axe) | Máx. botón visible repetido |
|---|---|---|---|---|---|
| `/hotel/reservas` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / **OK** (`12` radios) / `0` | `Abrir calendario` ×3 (filtros de fecha) |
| `/hotel/leads` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / **OK** (`12` radios) / `0` | `Abrir calendario` ×2 (filtros de fecha) |
| `/hotel/solicitudes` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / **OK** (`12` radios) / `0` | `Todas` ×1 |
| `/hotel/clientes` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / **OK** (`22` radios) / `0` | `Buscar` ×1 |
| `/hotel/habitaciones` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / **OK** (`17` radios) / `0` | `Dar de alta` ×1 |
| `/hotel/productos` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / **OK** (`15` radios) / `0` | `Catálogo` ×1 |
| `/hotel/aseo` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / **OK** (`17` radios) / `0` | `Enviar sugerencia` ×1 |
| `/hotel/caja?pestana=cuenta` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / **OK** (`12` radios) / `0` | `Abrir calendario` ×2 |
| `/hotel/caja?pestana=movimientos` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / **OK** (`12` radios) / `0` | `Abrir calendario` ×2 |
| `/reservar` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / N/A / `0` | `Abrir calendario` ×2 |
| `landinpage/index.html` | `0 px` / `0` | `0 px` | `0 px` | `0 px` / `0` / N/A / `0` | `×1` |

**Resultado global E2E:** `44 / 44` comprobaciones aprobadas (`fallos_count: 0`).

---

## 4. Cómo re-ejecutar la auditoría

```bash
# 1. Pruebas unitarias y build (Node 24)
cd front
node --test tests/*.test.mjs
npx next build

# 2. Auditoría E2E geométrica + WCAG AA (Playwright + axe-core)
npx next start -p 3111 &
UIUX_BASE_URL=http://127.0.0.1:3111 python tests/auditoria_uiux_e2e.py
```
