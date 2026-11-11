"""Lecturas de análisis del hotel: ocupación por noche e indicadores operativos.

Definiciones gobernantes: spec-hotel-operacion-v1 §4 (indicadores) y §5
(ocupación). Solo lectura: nada se escribe. La fecha de corte (`hoy`) es la
del reloj del servidor, como en la cancelación. Un indicador sin muestra vale
None, nunca 0 (HECHO DOCUMENTADO: regla del dominio `IndicadoresDiarios`).
Los indicadores financieros (ADR, RevPAR, ingresos) no se calculan: quedan
declarados en `no_disponibles` (DECISIÓN PENDIENTE D-IND-01/02, D-ROL-01).
"""
from datetime import date, timedelta

import psycopg

from .reservas import ESTADOS_NO_VENDIBLES, ESTADOS_QUE_OCUPAN_CUPO, tarifas_por_noche

MAX_NOCHES_OCUPACION = 62
MAX_NOCHES_INDICADORES = 92
ESTADOS_CON_NOCHES = ("confirmada", "en_estadia", "finalizada")


class PeriodoInvalido(Exception):
    """422: periodo vacío, invertido o más largo que el máximo."""


def validar_periodo(desde: date, hasta: date, maximo: int) -> list[date]:
    if hasta <= desde:
        raise PeriodoInvalido("hasta debe ser mayor que desde")
    noches = (hasta - desde).days
    if noches > maximo:
        raise PeriodoInvalido(f"el periodo admite como máximo {maximo} noches")
    return [desde + timedelta(days=i) for i in range(noches)]


def _fecha_local(instante) -> date:
    # Misma zona que `date.today()` del proceso (la fecha de corte).
    return instante.astimezone().date()


def _habitaciones(
    conexion: psycopg.Connection,
    tipo: str | None,
    *,
    solo_inventario_real: bool = False,
) -> list[dict]:
    consulta = (
        "SELECT id, tipo, capacidad, estado_operativo, estado_preparacion, mantenimiento, creado_en "
        "FROM habitaciones"
    )
    parametros: list = []
    filtros: list[str] = []
    if tipo:
        filtros.append("tipo = %s")
        parametros.append(tipo)
    if solo_inventario_real:
        # HAB-01..17 únicamente (titular). Coincide con inventario_documental._RE_HAB_REAL.
        filtros.append("id ~ '^HAB-(0[1-9]|1[0-7])$'")
    if filtros:
        consulta += " WHERE " + " AND ".join(filtros)
    return [
        {
            "habitacion_id": f[0],
            "tipo": f[1],
            "capacidad": f[2],
            "estado_operativo": f[3],
            "estado_preparacion": f[4],
            "mantenimiento": f[5],
            "en_servicio": f[3] != "fuera_de_servicio",
            "registrada_el": _fecha_local(f[6]),
        }
        for f in conexion.execute(consulta + " ORDER BY id", parametros).fetchall()
    ]


def _reservas_del_periodo(
    conexion: psycopg.Connection, empresa_id: str, desde: date, hasta: date, ids_habitacion: list[str]
) -> list[dict]:
    """Reservas que tocan [desde, hasta) con su fin efectivo: una finalizada
    con liquidación anterior a `fin` (salida anticipada) ocupa hasta la fecha
    de esa liquidación."""
    filas = conexion.execute(
        "SELECT r.id, r.habitacion_id, r.inicio, r.fin, r.estado, r.huesped_nombre, l.creado_en "
        "FROM reservas r LEFT JOIN liquidaciones l ON l.reserva_id = r.id "
        "WHERE r.empresa_id = %s AND r.inicio < %s AND r.fin > %s AND r.habitacion_id = ANY(%s) "
        "ORDER BY r.inicio, r.id",
        (empresa_id, hasta, desde, ids_habitacion),
    ).fetchall()
    reservas = []
    for f in filas:
        fin_efectivo = f[3]
        if f[4] == "finalizada" and f[6] is not None:
            fin_efectivo = min(f[3], _fecha_local(f[6]))
        reservas.append(
            {
                "reserva_id": f[0],
                "habitacion_id": f[1],
                "inicio": f[2],
                "fin": f[3],
                "fin_efectivo": fin_efectivo,
                "estado": f[4],
                "huesped_nombre": f[5],
            }
        )
    return reservas


def _contiene(reserva: dict, noche: date) -> bool:
    return reserva["inicio"] <= noche < reserva["fin_efectivo"]


def _motivo_no_vendible(habitacion: dict) -> str | None:
    if habitacion["mantenimiento"]:
        return "mantenimiento"
    if habitacion["estado_operativo"] in ESTADOS_NO_VENDIBLES:
        return habitacion["estado_operativo"]
    return None


def ocupacion(
    conexion: psycopg.Connection,
    empresa_id: str,
    desde: date,
    hasta: date,
    hoy: date,
    *,
    solo_inventario_real: bool = False,
) -> dict:
    """Estado de cada (habitación, noche) según spec-hotel-operacion-v1 §5."""
    noches = validar_periodo(desde, hasta, MAX_NOCHES_OCUPACION)
    habitaciones = _habitaciones(conexion, None, solo_inventario_real=solo_inventario_real)
    reservas = _reservas_del_periodo(conexion, empresa_id, desde, hasta, [h["habitacion_id"] for h in habitaciones])
    tarifas = tarifas_por_noche(conexion, desde, hasta)
    resumen = {n: {"fecha": n.isoformat(), "disponibles": 0, "ocupadas_cupo": 0, "no_vendibles": 0} for n in noches}
    salida = []
    for h in habitaciones:
        propias = [r for r in reservas if r["habitacion_id"] == h["habitacion_id"]]
        motivo = _motivo_no_vendible(h)
        celdas = []
        for noche in noches:
            celda: dict = {"fecha": noche.isoformat()}
            vigente = next(
                (r for r in propias if r["estado"] in ESTADOS_QUE_OCUPAN_CUPO and _contiene(r, noche)), None
            )
            finalizada = next((r for r in propias if r["estado"] == "finalizada" and _contiene(r, noche)), None)
            if vigente:
                celda.update(estado=vigente["estado"], reserva_id=vigente["reserva_id"])
                resumen[noche]["ocupadas_cupo"] += 1
            elif noche < hoy:
                if finalizada:
                    celda.update(estado="finalizada", reserva_id=finalizada["reserva_id"])
                else:
                    celda["estado"] = "sin_ocupar"
            elif motivo:
                celda.update(estado="no_vendible", motivo=motivo)
                resumen[noche]["no_vendibles"] += 1
            elif (h["habitacion_id"], noche) not in tarifas:
                celda["estado"] = "sin_tarifa"
            else:
                celda.update(estado="disponible", tarifa_noche_clp=tarifas[(h["habitacion_id"], noche)])
                resumen[noche]["disponibles"] += 1
            celdas.append(celda)
        salida.append(
            {
                "habitacion_id": h["habitacion_id"],
                "tipo": h["tipo"],
                "capacidad": h["capacidad"],
                "estado_operativo": h["estado_operativo"],
                "estado_preparacion": h["estado_preparacion"],
                "mantenimiento": h["mantenimiento"],
                "en_servicio": h["en_servicio"],
                "noches": celdas,
                "reservas": [
                    {
                        "reserva_id": r["reserva_id"],
                        "inicio": r["inicio"].isoformat(),
                        "fin": r["fin"].isoformat(),
                        "estado": r["estado"],
                        "huesped_nombre": r["huesped_nombre"],
                    }
                    for r in propias
                ],
            }
        )
    return {
        "fecha_corte": hoy.isoformat(),
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "noches": len(noches)},
        "noches": [n.isoformat() for n in noches],
        "habitaciones": salida,
        "resumen": list(resumen.values()),
    }


def _indicador(valor, unidad: str, formula: str, fuente: str, limitaciones: str = "") -> dict:
    return {"valor": valor, "unidad": unidad, "formula": formula, "fuente": fuente, "limitaciones": limitaciones}


def _conteo_reservas(ids: list[str], unidad_formula: str, fuente: str = "reservas") -> dict:
    return {**_indicador(len(ids), "reservas", unidad_formula, fuente), "reservas": ids}


NO_DISPONIBLES = [
    {
        "indicador": "ADR y RevPAR",
        "motivo": "requieren el reconocimiento de ingreso por noche; el precio noche a noche quedó resuelto "
                  "(#305, 2026-11-06) pero la fórmula de ingreso reconocido sigue sin decidir (D-IND-02).",
    },
    {"indicador": "ingresos por canal", "motivo": "el modelo no registra canal de origen (dominio)."},
    {
        "indicador": "pagos del periodo",
        "motivo": "DECISIÓN PENDIENTE D-IND-02; los pagos del día están en Caja (caja y administrador), sin conciliar.",
    },
    {"indicador": "no-show", "motivo": "V1 no tiene ese estado; ver llegadas_vencidas."},
]


def indicadores(
    conexion: psycopg.Connection, empresa_id: str, desde: date, hasta: date, hoy: date,
    tipo: str | None = None, incluir_financiero: bool = False,
    *,
    solo_inventario_real: bool = False,
) -> dict:
    """Panel operativo (spec-hotel-operacion-v1 §4). El indicador financiero
    `ingresos_periodo_clp` se incluye solo cuando `incluir_financiero`
    (D-ROL-01 RATIFICADA 2026-11-06, #297 opción a: solo administrador)."""
    noches = validar_periodo(desde, hasta, MAX_NOCHES_INDICADORES)
    habitaciones = _habitaciones(conexion, tipo, solo_inventario_real=solo_inventario_real)
    ids = [h["habitacion_id"] for h in habitaciones]

    # --- Situación de hoy (§4.2) ---
    def reservas_donde(condicion: str, *parametros) -> list[str]:
        return [
            f[0]
            for f in conexion.execute(
                f"SELECT id FROM reservas WHERE empresa_id = %s AND habitacion_id = ANY(%s) AND {condicion} "
                "ORDER BY inicio, id",
                (empresa_id, ids, *parametros),
            ).fetchall()
        ]

    (limpiezas,) = conexion.execute(
        "SELECT count(*) FROM tareas_operativas WHERE tipo = 'limpieza' AND estado = 'pendiente' "
        "AND habitacion_id = ANY(%s)",
        (ids,),
    ).fetchone()
    contar = lambda predicado: sum(1 for h in habitaciones if predicado(h))  # noqa: E731
    hab = "habitaciones (estado actual)"
    situacion = {
        "llegadas_hoy": _conteo_reservas(reservas_donde("estado = 'confirmada' AND inicio = %s", hoy),
                                         "reservas confirmada con inicio = hoy"),
        "llegadas_vencidas": {
            **_conteo_reservas(reservas_donde("estado = 'confirmada' AND inicio < %s", hoy),
                               "reservas confirmada con inicio < hoy"),
            "limitaciones": "no hicieron check-in; V1 no tiene estado no-show",
        },
        "salidas_hoy": _conteo_reservas(reservas_donde("estado = 'en_estadia' AND fin = %s", hoy),
                                        "reservas en_estadia con fin = hoy"),
        "salidas_vencidas": _conteo_reservas(reservas_donde("estado = 'en_estadia' AND fin < %s", hoy),
                                             "reservas en_estadia con fin < hoy"),
        "en_casa": _conteo_reservas(reservas_donde("estado = 'en_estadia'"), "reservas en_estadia"),
        "habitaciones_total": _indicador(len(habitaciones), "unidades", "habitaciones registradas", hab),
        "habitaciones_ocupadas": _indicador(contar(lambda h: h["estado_operativo"] == "ocupada"), "unidades",
                                            "estado_operativo = ocupada", hab),
        "habitaciones_vendibles": _indicador(contar(lambda h: _motivo_no_vendible(h) is None), "unidades",
                                             "sin mantenimiento y fuera de bloqueada/fuera_de_servicio", hab),
        "habitaciones_sucias": _indicador(contar(lambda h: h["estado_preparacion"] == "sucia"), "unidades",
                                          "estado_preparacion = sucia", hab),
        "limpiezas_pendientes": _indicador(limpiezas, "tareas", "tareas de limpieza pendientes",
                                           "tareas_operativas"),
        "en_mantenimiento": _indicador(contar(lambda h: h["mantenimiento"]), "unidades", "mantenimiento = true", hab),
        "fuera_de_servicio": _indicador(contar(lambda h: h["estado_operativo"] == "fuera_de_servicio"), "unidades",
                                        "estado_operativo = fuera_de_servicio", hab),
    }

    # --- Indicadores del periodo (§4.3) ---
    reservas = _reservas_del_periodo(conexion, empresa_id, desde, hasta, ids)
    serie = []
    unidades_total = unidades_pasadas = ocupadas_total = reservadas_total = 0
    for noche in noches:
        con_noche = [r for r in reservas if r["estado"] in ESTADOS_CON_NOCHES and _contiene(r, noche)]
        # Una habitación cuenta en la noche si ya estaba registrada o si tiene
        # una noche de reserva en ella (no hay ratio por encima de 1).
        # D-OCU-02 (#299, DECISIÓN 2026-11-06): las fuera_de_servicio no entran
        # al denominador de ocupación (limitación: V1 no guarda historial de
        # estados; se excluye por estado actual).
        activas = {h["habitacion_id"] for h in habitaciones
                   if h["registrada_el"] <= noche and h["estado_operativo"] != "fuera_de_servicio"}
        activas |= {r["habitacion_id"] for r in con_noche}
        reservadas = len({r["habitacion_id"] for r in con_noche})
        ocupadas_estadias = None
        if noche <= hoy:
            ocupadas_estadias = len({r["habitacion_id"] for r in con_noche if r["estado"] in ("en_estadia", "finalizada")})
            unidades_pasadas += len(activas)
            ocupadas_total += ocupadas_estadias
        unidades_total += len(activas)
        reservadas_total += reservadas
        serie.append({"fecha": noche.isoformat(), "unidades": len(activas), "ocupadas_estadias": ocupadas_estadias,
                      "reservadas": reservadas})

    canceladas = [r for r in reservas if r["estado"] == "cancelada"]
    noches_canceladas = sum(
        len([n for n in noches if r["inicio"] <= n < r["fin"]]) for r in canceladas
    )
    registradas: dict[str, int] = {}
    for f in conexion.execute(
        "SELECT estado, creado_en FROM reservas WHERE empresa_id = %s AND habitacion_id = ANY(%s)",
        (empresa_id, ids),
    ).fetchall():
        if desde <= _fecha_local(f[1]) < hasta:
            registradas[f[0]] = registradas.get(f[0], 0) + 1

    fuente_noches = "reservas (rango) y liquidaciones (salida anticipada)"
    periodo = {
        "unidades_noche": _indicador(
            unidades_total, "unidades-noche",
            "Σ por noche de habitaciones registradas a esa fecha (o con noche de reserva en ella)",
            "habitaciones.creado_en",
            "una habitación retirada sigue contando (fórmula del dominio; D-IND-03)"),
        "noches_ocupadas": _indicador(
            ocupadas_total, "noches",
            "noches con fecha ≤ hoy de reservas en_estadia o finalizada", fuente_noches,
            "solo estadías reales; las noches futuras no cuentan"),
        "ocupacion": _indicador(
            ocupadas_total / unidades_pasadas if unidades_pasadas else None, "proporción 0–1",
            "noches_ocupadas / unidades-noche de las noches con fecha ≤ hoy", fuente_noches,
            "null si el periodo es todo futuro; noche de estadía = noche vendida del dominio (SUPUESTO: V1 no "
            "asienta cargos por noche)"),
        "noches_reservadas": _indicador(
            reservadas_total, "noches",
            "noches del periodo de reservas confirmada, en_estadia o finalizada", fuente_noches,
            "incluye confirmadas pasadas sin check-in"),
        "ocupacion_reservada": _indicador(
            reservadas_total / unidades_total if unidades_total else None, "proporción 0–1",
            "noches_reservadas / unidades_noche", fuente_noches,
            "ocupación comprometida (prospectiva), no realizada"),
        "reservas_canceladas": {
            **_indicador(len(canceladas), "reservas", "reservas cancelada cuyo rango toca el periodo", "reservas",
                         "se mide por fecha de estadía; la fecha de cancelación no está en reservas"),
            "noches": noches_canceladas,
            "reservas": [r["reserva_id"] for r in canceladas],
        },
        "reservas_registradas": {
            **_indicador(sum(registradas.values()), "reservas",
                         "reservas creadas dentro del periodo, por estado actual", "reservas.creado_en"),
            "por_estado": registradas,
        },
    }
    if incluir_financiero:
        # D-IND-01/#297 (DECISIÓN 2026-11-06): ingresos del periodo = pagos
        # confirmados por fecha de pago (lo cobrado, no lo reservado).
        (ingresos,) = conexion.execute(
            "SELECT COALESCE(SUM(p.monto_clp), 0) FROM pagos p JOIN reservas r ON r.id = p.reserva_id "
            "WHERE r.empresa_id = %s AND p.estado = 'confirmado' "
            "AND p.creado_en::date >= %s AND p.creado_en::date < %s",
            (empresa_id, desde, hasta),
        ).fetchone()
        periodo["ingresos_periodo_clp"] = _indicador(
            ingresos, "CLP", "pagos confirmados por fecha de pago dentro del periodo",
            "pagos (join reservas)", "lo cobrado, no lo reservado; fuente veraz")
    return {
        "fecha_corte": hoy.isoformat(),
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "noches": len(noches)},
        "filtros": {"tipo": tipo},
        "hoy": situacion,
        "periodo_indicadores": periodo,
        "serie": serie,
        "no_disponibles": NO_DISPONIBLES,
    }
