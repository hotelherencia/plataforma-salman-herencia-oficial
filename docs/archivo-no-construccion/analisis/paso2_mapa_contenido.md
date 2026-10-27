# Paso 2 — Mapa de contenido (entrega Kimi)

- **Agente:** Kimi · **Fecha:** 2026-10-26
- **Rol:** por instrucción del propietario ("continuar con el análisis, colaborar con Claude, iterar"), Kimi produce este Paso 2 y el Paso 3; **queda pendiente la revisión cruzada de Claude** (roles invertidos respecto al guion original; registrado en el tablero).
- **Aclaración del propietario acogida:** no son 4 módulos ni capítulos: son **24 capítulos** y **23 fichas/paquetes SDD**.

## Verificación de la aclaración (24, no 4)

| Afirmación | Resultado | Fuente | Etiqueta |
|---|---|---|---|
| El maestro declara "24 capitulos y 23 paquetes SDD desarrollados" | Confirmado | `02_texto/Documento_Word_Especificaciones_V1.txt` línea 14 (tabla de cobertura) | HECHO DOCUMENTADO |
| El Mapa del Documento Maestro lista M01–M24 (24 filas) | Confirmado | mismo archivo, líneas 40–66 | HECHO DOCUMENTADO |
| Existen 24 archivos maestro/M01.md…M24.md con SHA-256 | Confirmado | `03_inventario/inventario_Especificaciones_V1.csv` líneas 38–61 | HECHO DOCUMENTADO |
| Se encontró alguna afirmación de "4 capítulos/módulos" en las fuentes | **No** en maestro, inventarios ni registros revisados | búsqueda en fuentes | INFORMACIÓN NO VERIFICADA (no aparece) |
| Posible origen del número 4: las 4 entregas E0–E3 del Anexo A | Plausible | mismo archivo, líneas 354–379 | HIPÓTESIS |

## Tabla A — Capítulo → fuente → requisitos asociados (24 capítulos)

Fuentes por fila: `maestro/MNN.md` (bytes, SHA-256 según inventario), asignación capítulo↔requisito de `registros/requisitos_originales_preservados.csv` (columna "Capitulo maestro"), fichas de `registros/paquetes.csv`. Verificación: 153/153 requisitos tienen capítulo válido M01–M24, sin duplicados ni anomalías.

| Cap | Materia | Fuente (maestro) | #Req | Fichas SDD | Requisitos asociados (IDs preservados) | Etiqueta |
|---|---|---|---|---|---|---|
| M01 | Visión, alcance y gobierno del grupo | `maestro/M01.md` · 2927 B · sha 275e19549277 | 7 | F01;F22 | CORE-001;CORE-002;CORE-003;CORE-004;CORE-005;CORE-006;CORE-007 | HECHO DOCUMENTADO |
| M02 | Fuentes, decisiones y reglas versionadas | `maestro/M02.md` · 2766 B · sha 452ec9932d80 | 0 | — | — | HECHO DOCUMENTADO |
| M03 | Procesos, roles y autorizaciones | `maestro/M03.md` · 2655 B · sha cb4beb09595c | 0 | — | — | HECHO DOCUMENTADO |
| M04 | Oferta hotelera, tarifas y disponibilidad | `maestro/M04.md` · 2785 B · sha 9d8b40568af6 | 17 | F02;F03 | HOT-001;HOT-002;HOT-003;HOT-004;HOT-005;RES-001;RES-002;RES-003;RES-004;RES-005;RES-006;RES-007;RES-008;RES-009;RES-010;RES-011;REV-001 | HECHO DOCUMENTADO |
| M05 | Sitio público, reserva directa y pago | `maestro/M05.md` · 2596 B · sha f0446f2b6584 | 2 | F03 | SOC-003;SOC-016 | HECHO DOCUMENTADO |
| M06 | Ventas desde redes y relación con clientes | `maestro/M06.md` · 2778 B · sha ba2acd4b5f69 | 11 | F03;F14;F15;F17 | SOC-001;SOC-002;SOC-004;SOC-005;SOC-006;SOC-007;SOC-008;SOC-009;SOC-014;SOC-015;SOC-017 | HECHO DOCUMENTADO |
| M07 | Canales externos y distribución | `maestro/M07.md` · 2811 B · sha 0de402b17c22 | 1 | F13 | SOC-019 | HECHO DOCUMENTADO |
| M08 | Recepción, estadías y portal | `maestro/M08.md` · 2635 B · sha f09fbb5975a0 | 9 | F05;F18 | REC-001;REC-002;REC-003;REC-004;REC-005;GEX-001;GEX-002;GEX-003;OPS-006 | HECHO DOCUMENTADO |
| M09 | Aseo, lavandería y calidad | `maestro/M09.md` · 2572 B · sha 827a2f017af6 | 9 | F07 | OPS-001;OPS-002;OPS-003;OPS-004;OPS-005;LIN-001;LIN-002;LIN-003;LIN-004 | HECHO DOCUMENTADO |
| M10 | Desayunos, cenas, cafetería y espacios | `maestro/M10.md` · 2649 B · sha d6981abce8e7 | 6 | F08 | FNB-001;FNB-002;FNB-003;FNB-004;FNB-005;SPA-001 | HECHO DOCUMENTADO |
| M11 | Compras, proveedores y existencias | `maestro/M11.md` · 2606 B · sha 2ab8016cd8a1 | 10 | F06 | INV-001;INV-002;INV-003;INV-004;INV-005;PUR-001;PUR-002;PUR-003;PUR-004;CAP-001 | HECHO DOCUMENTADO |
| M12 | Activos, mantenimiento y renovaciones | `maestro/M12.md` · 2557 B · sha 8f241c3e082c | 7 | F09 | MNT-001;MNT-002;CAP-002;CAP-003;CAP-004;CAP-005;CAP-006 | HECHO DOCUMENTADO |
| M13 | Personal, turnos e incentivos | `maestro/M13.md` · 2635 B · sha 3a4b6186349c | 6 | F10 | HR-001;HR-002;HR-003;HR-004;HR-005;HR-006 | HECHO DOCUMENTADO |
| M14 | Finanzas, costos y contabilidad auxiliar | `maestro/M14.md` · 2794 B · sha a1e94c128a1f | 22 | F04;F11;F12 | PAY-001;PAY-002;PAY-003;PAY-004;PAY-005;PAY-006;PAY-007;PAY-008;TAX-001;TAX-002;TAX-003;FIN-001;FIN-002;FIN-003;FIN-004;FIN-005;FIN-006;FIN-007;FIN-008;FIN-009;FIN-010;FIN-011 | HECHO DOCUMENTADO |
| M15 | Indicadores, costos y planificación | `maestro/M15.md` · 2776 B · sha 4baa045b5e95 | 6 | F12 | KPI-001;KPI-002;KPI-003;SOC-012;SOC-018;REV-002 | HECHO DOCUMENTADO |
| M16 | Modelo de datos, identidad y estados | `maestro/M16.md` · 2741 B · sha 5f3511fae8ae | 0 | — | — | HECHO DOCUMENTADO |
| M17 | Arquitectura y contratos de integración | `maestro/M17.md` · 2726 B · sha ec65bfc6e0bb | 9 | F00;F03;F13;F15;F17;F19 | INT-001;INT-002;INT-003;INT-004;INT-005;INT-006;SOC-011;GOV-002;INT-007 | HECHO DOCUMENTADO |
| M18 | Pantallas, experiencia y accesibilidad | `maestro/M18.md` · 2625 B · sha eeed336e6245 | 2 | F03 | UX-001;UX-002 | HECHO DOCUMENTADO |
| M19 | Seguridad, privacidad y cumplimiento | `maestro/M19.md` · 2702 B · sha 0f0b0b791bc0 | 10 | F01;F04;F14;F21 | SEC-001;SEC-002;SEC-003;SEC-004;SEC-005;SEC-006;SOC-013;SEC-007;SEC-008;SEC-009 | HECHO DOCUMENTADO |
| M20 | Agentes, SDD y supervisión empresarial | `maestro/M20.md` · 2744 B · sha 689d96d49e43 | 8 | F00;F16;F21 | AI-001;AI-002;AI-003;AI-004;AI-005;AI-006;SOC-010;AI-007 | HECHO DOCUMENTADO |
| M21 | Pruebas, cobertura y aceptación | `maestro/M21.md` · 2627 B · sha a31ef2082485 | 4 | F00;F21 | GOV-001;QA-001;QA-002;QA-003 | HECHO DOCUMENTADO |
| M22 | Infraestructura, continuidad y soporte | `maestro/M22.md` · 2623 B · sha 1c912059f4ec | 1 | F21 | SEC-010 | HECHO DOCUMENTADO |
| M23 | Traspaso, carga inicial y apertura | `maestro/M23.md` · 2744 B · sha 69084ad01aa8 | 6 | F20 | MIG-001;MIG-002;MIG-003;MIG-004;MIG-005;MIG-006 | HECHO DOCUMENTADO |
| M24 | Plan de ejecución y entrega al equipo | `maestro/M24.md` · 2985 B · sha 5a6486e00de8 | 0 | — | — | HECHO DOCUMENTADO |

## Tabla B — Las 23 fichas/paquetes SDD

Fuentes: `registros/paquetes.csv` (V1) y `backlog/` del SDD v0.3 extraído en `01_extraccion/Herencia_SDD_V03/`. Verificación: 23 fichas F00–F22 en ambos paquetes; suma de requisitos por paquete = 153.

| Ficha | Nombre | Spec V1 (`specs/`) | Semilla v0.3 (`backlog/`) | Entrega | #Req | Decisiones | Estado | Etiqueta |
|---|---|---|---|---|---|---|---|---|
| F00 | Gobierno, arquitectura base y entorno seguro | `specs/001-gobierno-y-entorno` | `F00_gobierno-y-entorno` | E0 | 7 | D18;D37;D38;D39;D40;D42;D43;D44;D45 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F01 | Sociedades, identidad, permisos y auditoria | `specs/002-nucleo-multiempresa` | `F01_nucleo-multiempresa` | E0 | 10 | D14;D15;D16;D24;D42;D44;D45 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F02 | Habitaciones, tarifas e inventario vendible | `specs/003-oferta-y-disponibilidad` | `F02_oferta-y-disponibilidad` | E1 | 8 | D01;D02;D03;D14 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F03 | Reserva directa desde enlace social | `specs/004-reserva-directa` | `F03_reserva-directa` | E1 | 15 | D01;D02;D03;D06;D14;D19;D25;D28 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F04 | Pagos, caja y documentos tributarios | `specs/005-pagos-caja-documentos` | `F04_pagos-caja-documentos` | E1 | 12 | D03;D06;D07;D08;D14;D34 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F05 | Recepcion, estadias y auditoria nocturna | `specs/006-recepcion-estadias` | `F05_recepcion-estadias` | E1 | 6 | D01;D03;D09;D14;D36 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F06 | Compras, existencias y precios unitarios | `specs/007-compras-inventarios` | `F06_compras-inventarios` | E1 | 10 | D13;D14;D24;D31;D32 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F07 | Aseo, inspeccion y lavanderia | `specs/008-aseo-lavanderia` | `F07_aseo-lavanderia` | E1 | 9 | D09;D11;D13;D14;D17 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F08 | Desayunos, cenas y espacios compartidos | `specs/009-alimentacion-espacios` | `F08_alimentacion-espacios` | E1 | 6 | D10;D12;D23;D32 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F09 | Activos, mantenimiento y renovacion | `specs/010-activos-renovacion` | `F09_activos-renovacion` | E1 | 7 | D01;D13;D14;D24;D31;D32 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F10 | Personal, turnos e incentivos | `specs/011-personal-turnos` | `F10_personal-turnos` | E1 | 6 | D09;D14;D17;D21 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F11 | Conciliacion y auxiliares financieros | `specs/012-conciliacion-finanzas` | `F11_conciliacion-finanzas` | E1 | 8 | D08;D14;D21;D34 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F12 | Costos, presupuestos e indicadores | `specs/013-costos-indicadores` | `F12_costos-indicadores` | E1 | 9 | D18;D24;D30;D32;D34;D35 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F13 | Booking y distribucion externa | `specs/014-canales-externos` | `F13_canales-externos` | E1 | 5 | D04;D06;D19;D25 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F14 | CRM, identidad y consentimiento | `specs/015-crm-clientes` | `F14_crm-clientes` | E2 | 8 | D16;D19;D25;D26;D28;D30 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F15 | Mensajeria oficial WhatsApp/Instagram/Messenger | `specs/016-mensajeria-social` | `F15_mensajeria-social` | E2 | 3 | D19;D25;D26;D27;D28 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F16 | Asistente comercial con herramientas limitadas | `specs/017-asistente-comercial` | `F16_asistente-comercial` | E2 | 2 | D18;D28;D29;D39;D40 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F17 | Publicaciones y publicidad controlada | `specs/018-contenidos-campanas` | `F17_contenidos-campanas` | E3 | 3 | D19;D25;D26;D28;D30 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F18 | Portal, solicitudes y experiencia del huesped | `specs/019-portal-huesped` | `F18_portal-huesped` | E2 | 3 | D16;D23;D28;D33 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F19 | Conexion bancaria autorizada de lectura | `specs/020-bancos-lectura` | `F19_bancos-lectura` | E3 | 1 | D08;D16;D18 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F20 | Traspaso, migracion y apertura | `specs/021-traspaso-apertura` | `F20_traspaso-apertura` | E1 | 6 | D05;D13;D14;D15;D16;D19;D22;D24;D31;D36;D44 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F21 | Verificacion transversal y continuidad | `specs/022-calidad-continuidad` | `F21_calidad-continuidad` | TRANSVERSAL | 8 | D16;D18;D20;D22;D37;D42;D43 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |
| F22 | Contratos para modulos futuros del grupo | `specs/023-evolucion-grupo` | `F22_evolucion-grupo` | FUTURO | 1 | D15;D21;D24;D34;D35;D38 | DESARROLLADO_PARA_REVISION | HECHO DOCUMENTADO |

## Hallazgos del mapa (Paso 2)

1. **Cuatro capítulos sin requisitos asignados en el CSV:** M02 (fuentes/decisiones), M03 (procesos/roles), M16 (modelo de datos), M24 (plan de ejecución) tienen 0 requisitos en `registros/requisitos_originales_preservados.csv`. Son capítulos transversales; el texto de M24 referencia los 23 paquetes. Etiqueta: HECHO DOCUMENTADO (el 0 es conteo) + SUPUESTO (se asume cobertura intencional; confirmar con propietario).
2. **Cruce texto del maestro vs CSV de trazabilidad:** las referencias "F…" explícitas en el cuerpo de cada capítulo no siempre coinciden con las fichas asignadas en el CSV. Detalle en `paso2_verificaciones.json` (`cruce_inconsistente`). El texto usa rangos (p.ej. "F14-F17") y menciones contextuales (p.ej. M12: "la compra atraviesa F06"), mientras el CSV asigna por pertenencia. Etiqueta: HECHO DOCUMENTADO; no constituye CONTRADICCIÓN (el CSV es la trazabilidad autoritativa; el texto referencia de forma selectiva).
3. **IDs estables:** los 153 IDs preservados (prefijos AI, CAP, CORE, FIN, FNB, GEX, GOV, HOT, HR, INT, INV, KPI, LIN, MIG, MNT, OPS, PAY, PUR, QA, REC, RES, REV, SEC, SOC, SPA, TAX, UX) coinciden exactamente entre `requisitos_originales_preservados.csv` y `trazabilidad.csv` (diferencia = 0). Etiqueta: HECHO DOCUMENTADO.
4. **Prioridades:** P0=118, P1=29, P2=6 (suma 153). Todas las filas son `REQUISITO_DE_PRODUCTO_O_CONTROL_EXISTENTE`. Etiqueta: HECHO DOCUMENTADO.

## Qué queda sin verificar en este paso

- Relación padre/hijo entre requisitos (columna "Padre o relacion") no analizada.
- Fichas SDD v0.3 como specs: `backlog/` son semillas según su propio AGENTS.md; no specs aprobadas (dato, no instrucción).
- Cifras de paginación del Word (CONTRADICCIÓN MENOR del Paso 1) sin resolver.
- Contenido interno de los 24 archivos maestro/MNN.md (este mapa usa el Word + CSV; los MNN.md son la misma base según el maestro, línea 25).
