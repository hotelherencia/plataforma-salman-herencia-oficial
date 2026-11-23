"""E2E por rol contra el servicio real (proceso uvicorn + PostgreSQL aislado). No imprime credenciales.

Uso (base local aislada, nunca producción):
  python3 e2e/e2e_roles.py .env
El .env (ignorado por git) define ADMIN_USUARIO/ADMIN_CLAVE y E2E_<ROL>_USUARIO/_CLAVE para los 6 roles."""
import os, sys, uuid
from datetime import date, timedelta
import httpx

def cargar(path):
    for l in open(path):
        l = l.strip()
        if l and not l.startswith("#") and "=" in l:
            k, v = l.split("=", 1); os.environ.setdefault(k, v)
cargar(sys.argv[1])
BASE = os.environ.get("E2E_BASE", "http://127.0.0.1:8765")
ROLES = ["administrador", "admin_hotel", "admin_plataforma", "recepcion", "caja", "aseo"]
res = []
def chk(nombre, ok, detalle=""):
    res.append(ok); print(("PASS " if ok else "FAIL ") + nombre + ("" if ok else f"  -> {detalle}"))
def h(): return {"Idempotency-Key": uuid.uuid4().hex}
def cli(): return httpx.Client(base_url=BASE, timeout=30)
def login(u, c):
    cl = cli(); r = cl.post("/sesion", json={"usuario": u, "clave": c}); return cl, r

adm, r = login(os.environ["ADMIN_USUARIO"], os.environ["ADMIN_CLAVE"])
chk("login admin inicial", r.status_code == 200, r.status_code)
s = {}
for rol in ROLES:
    u, c = os.environ[f"E2E_{rol.upper()}_USUARIO"], os.environ[f"E2E_{rol.upper()}_CLAVE"]
    r = adm.post("/usuarios", json={"nombre": u, "rol": rol, "clave": c}, headers=h())
    chk(f"crear usuario rol {rol}", r.status_code == 201, f"{r.status_code} {r.text[:120]}")
    cl, r = login(u, c)
    chk(f"login rol {rol}", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
    s[rol] = cl
    me = cl.get("/sesion")
    chk(f"sesión {rol} devuelve el rol", me.status_code == 200 and me.json().get("rol") == rol, me.text[:100])

A, REC, CAJ, ASE, AH, AP = s["administrador"], s["recepcion"], s["caja"], s["aseo"], s["admin_hotel"], s["admin_plataforma"]
# habitación de prueba (tipo + lote)
r = A.post("/hotel/tipos", json={"tipo_id": "doble", "nombre": "Doble", "capacidad_base": 2, "precio_clp": 40000}, headers=h())
chk("admin crea tipo de habitación", r.status_code in (200, 201), f"{r.status_code} {r.text[:150]}")
r = A.post("/hotel/habitaciones/lote", json={"tipo_id": "doble", "cantidad": 2, "prefijo": "E2E-", "desde_numero": 1, "digitos": 2}, headers=h())
chk("admin crea habitaciones (lote)", r.status_code in (200, 201), f"{r.status_code} {r.text[:150]}")
hab = "E2E-01"

# Corte 1: incidencias, tareas, atención
r = ASE.post("/hotel/incidencias", json={"habitacion_id": hab, "descripcion": "Llave de agua gotea", "gravedad": "media"}, headers=h())
chk("aseo reporta incidencia", r.status_code == 200, f"{r.status_code} {r.text[:150]}")
inc = r.json().get("incidencia_id")
r = REC.get("/hotel/indicadores"); chk("recepción ve panel con 'Lo que necesita atención'", r.status_code == 200 and "atencion" in r.json(), r.status_code)
chk("incidencia aparece en atención", any(i["id"] == inc for i in r.json()["atencion"]["incidencias_abiertas"]) if r.status_code == 200 else False)
r = REC.post("/hotel/tareas", json={"titulo": "Revisar extintores", "area": "general", "prioridad": "normal", "subtareas": [{"texto": "Piso 1"}]}, headers=h())
chk("recepción crea tarea con subtarea", r.status_code == 200, f"{r.status_code} {r.text[:150]}")
r = ASE.post("/hotel/tareas", json={"titulo": "No debería", "area": "general", "prioridad": "normal"}, headers=h())
chk("aseo NO crea tareas (403)", r.status_code == 403, r.status_code)
r = A.post(f"/hotel/incidencias/{inc}/cierre", json={"nota": "Reparada"}, headers=h())
chk("admin cierra incidencia", r.status_code == 200, f"{r.status_code} {r.text[:150]}")

# Comunicados
r = A.post("/hotel/comunicados", json={"titulo": "Turno especial", "cuerpo": "Mañana entrada 8:00", "roles": ["aseo"]}, headers=h())
chk("admin publica comunicado para aseo", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
cid = r.json().get("comunicado_id")
chk("aseo ve 1 sin leer", ASE.get("/hotel/comunicados").json().get("sin_leer") == 1)
chk("caja no lo ve", CAJ.get("/hotel/comunicados").json().get("comunicados") == [])
chk("aseo confirma lectura", ASE.post(f"/hotel/comunicados/{cid}/lectura", headers=h()).status_code == 200)
l = A.get(f"/hotel/comunicados/{cid}/lecturas").json()
chk("admin ve quién leyó", [x["usuario"] for x in l["leyeron"]] == [os.environ["E2E_ASEO_USUARIO"]], l)

# Turnos
f = (date.today() + timedelta(days=1)).isoformat()
r = A.post("/hotel/turnos", json={"fecha": f, "area": "aseo", "usuario": os.environ["E2E_ASEO_USUARIO"], "hora_inicio": "08:00", "hora_fin": "16:00"}, headers=h())
chk("admin arma turno", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
tid = r.json().get("turno_id")
r = ASE.post(f"/hotel/turnos/{tid}/cambio", json={"propuesto": os.environ["E2E_RECEPCION_USUARIO"], "motivo": "Trámite personal"}, headers=h())
chk("aseo pide cambio de turno", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
cam = r.json().get("cambio_id")
chk("aseo no ve la bandeja de cambios (403)", ASE.get("/hotel/turnos/cambios").status_code == 403)
chk("admin aprueba cambio", A.post(f"/hotel/turnos/cambios/{cam}/resolucion", json={"aprobar": True}, headers=h()).status_code == 200)
dias = REC.get("/hotel/turnos").json()["dias"]
chk("el turno pasó a recepción", any(t["usuario"] == os.environ["E2E_RECEPCION_USUARIO"] for d in dias for t in d["turnos"]))

# Biblioteca y sugerencias
r = A.post("/hotel/biblioteca", json={"titulo": "Manual de aseo", "categoria": "manual", "contenido": "1. Ventilar"}, headers=h())
chk("admin publica manual", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
chk("aseo lee la biblioteca", len(ASE.get("/hotel/biblioteca").json()["documentos"]) == 1)
r = ASE.post("/hotel/sugerencias", json={"texto": "Faltan guantes"}, headers=h())
chk("aseo envía sugerencia", r.status_code == 200, r.status_code)
sug = r.json().get("sugerencia_id")
chk("admin atiende sugerencia", A.post(f"/hotel/sugerencias/{sug}/atencion", json={"respuesta": "Se compran"}, headers=h()).status_code == 200)

# Activos y mantención
r = REC.post("/hotel/activos", json={"habitacion_id": hab, "nombre": "Split", "categoria": "climatizacion"}, headers=h())
chk("recepción registra activo", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
aid = r.json().get("activo_id")
r = REC.post(f"/hotel/activos/{aid}/plan", json={"descripcion": "Limpiar filtros", "cada_dias": 90, "proxima": date.today().isoformat()}, headers=h())
chk("recepción programa mantención", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
pid = r.json().get("plan_id")
chk("aseo ve mantención por vencer", len(ASE.get("/hotel/mantenciones").json()["mantenciones"]) == 1)
chk("aseo la marca hecha", ASE.post(f"/hotel/mantenciones/{pid}/realizada", json={"nota": "ok"}, headers=h()).status_code == 200)

# Contable / reportes por rol
hoy = date.today()
for rol, cl, esperado in (("caja", CAJ, 200), ("recepcion", REC, 403), ("aseo", ASE, 403), ("admin_hotel", AH, 200)):
    r = cl.get("/hotel/contabilidad/cuadratura-diaria")
    chk(f"cuadratura diaria como {rol} → {esperado}", r.status_code == esperado, r.status_code)
chk("admin: cierre mensual (lectura)", A.get(f"/hotel/contabilidad/cierre-mensual?anio={hoy.year}&mes={hoy.month}").status_code == 200)
chk("admin: indicadores ejecutivos", A.get("/hotel/contabilidad/indicadores-ejecutivos").status_code == 200)
chk("admin: cuentas por cobrar", A.get("/hotel/contabilidad/cuentas-por-cobrar").status_code == 200)
chk("admin: tributario/F29 borrador", A.get(f"/hotel/contabilidad/tributario?anio={hoy.year}&mes={hoy.month}").status_code == 200)
chk("admin: cuentas por pagar", A.get("/hotel/productos/cuentas-por-pagar").status_code == 200)
chk("panel semanal por defecto (7 noches)", A.get("/hotel/indicadores").json()["periodo"]["noches"] == 7)
# Usuarios: solo administración de plataforma
r = REC.post("/usuarios", json={"nombre": "intruso", "rol": "caja", "clave": "clave-intruso-1"}, headers=h())
chk("recepción no crea usuarios (403)", r.status_code == 403, r.status_code)
chk("admin_plataforma lista usuarios", AP.get("/usuarios").status_code == 200)

print(f"\n{sum(res)}/{len(res)} verificaciones OK")
sys.exit(0 if all(res) else 1)
