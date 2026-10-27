"""Carga el backlog (github-projects.json) en el GitHub Project n.º 2 de hotelherencia.

Crea el repositorio si no existe, crea los campos del Project (incluido el
numérico Esfuerzo), agrega la opción de estado «Decisión humana» y carga los
150 ítems con sus campos. Esfuerzo solo en tareas hoja del hotel (plan §2).
Es idempotente: no duplica issues ya creadas.
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

OWNER = "hotelherencia"
REPO = "hotelherencia/plataforma-salman-herencia-oficial"
PROJECT_NUMBER = 2
PROJECT_ID = "PVT_kwHOFMML_M4Bo9XP"
ROOT = Path(__file__).resolve().parents[1]
ITEMS_PATH = ROOT / "backlog" / "github-projects.json"
LOG_PATH = ROOT / "backlog" / "carga-github-projects.log.json"

DECISION_HUMANA = "Decisión humana"

ESFUERZO_HOTEL = {
    "002-hotel-reservas-concierge/T001": 0,
    "002-hotel-reservas-concierge/T002": 0,
    "002-hotel-reservas-concierge/T003": 3,
    "002-hotel-reservas-concierge/T004": 3,
    "002-hotel-reservas-concierge/T005": 5,
    "002-hotel-reservas-concierge/T006": 5,
    "002-hotel-reservas-concierge/T007": 2,
    "002-hotel-reservas-concierge/T101": 0,
    "002-hotel-reservas-concierge/T102": 3,
    "002-hotel-reservas-concierge/T103": 5,
    "002-hotel-reservas-concierge/T104": 5,
    "002-hotel-reservas-concierge/T105": 2,
    "002-hotel-reservas-concierge/T201": 0,
    "002-hotel-reservas-concierge/T202": 5,
    "002-hotel-reservas-concierge/T203": 8,
    "002-hotel-reservas-concierge/T204": 5,
    "002-hotel-reservas-concierge/T205": 3,
    "002-hotel-reservas-concierge/H1/T-DEC": 2,
    "002-hotel-reservas-concierge/H1/T-DIS": 5,
    "002-hotel-reservas-concierge/H1/T-ACC": 3,
    "002-hotel-reservas-concierge/H1/T-IMP": 13,
    "002-hotel-reservas-concierge/H2/T-DEC": 2,
    "002-hotel-reservas-concierge/H2/T-DIS": 3,
    "002-hotel-reservas-concierge/H2/T-ACC": 3,
    "002-hotel-reservas-concierge/H2/T-IMP": 8,
    "002-hotel-reservas-concierge/H3/T-DEC": 2,
    "002-hotel-reservas-concierge/H3/T-DIS": 5,
    "002-hotel-reservas-concierge/H3/T-ACC": 3,
    "002-hotel-reservas-concierge/H3/T-IMP": 13,
}

ESTADO_A_STATUS = {"Hecha": "Done"}


def run(args, check=True):
    p = subprocess.run(["gh"] + args, capture_output=True, text=True, encoding="utf-8")
    if check and p.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}... falló:\n{p.stderr}")
    return p


def gql(query):
    p = run(["api", "graphql", "-f", f"query={query}"])
    data = json.loads(p.stdout)
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], ensure_ascii=False))
    return data["data"]


def es_decision_humana(item):
    return item["id"].endswith("/T003") or "decision" in item.get("etiquetas", [])


def status_para(item):
    if es_decision_humana(item):
        return DECISION_HUMANA
    return ESTADO_A_STATUS.get(item["estado"], "Todo")


def asegurar_repo():
    p = run(["repo", "view", REPO, "--json", "nameWithOwner"], check=False)
    if p.returncode == 0:
        print("repo: ya existe")
        return
    run(["repo", "create", REPO, "--public",
         "--description", "Backlog plataforma Salman Herencia (documental)"])
    print("repo: creado", REPO)


def query_fields():
    q = ('query { user(login: "%s") { projectV2(number: %d) { fields(first: 40) { nodes { '
         '__typename '
         '... on ProjectV2Field { id name dataType } '
         '... on ProjectV2SingleSelectField { id name dataType options { id name } } '
         '} } } } }' % (OWNER, PROJECT_NUMBER))
    nodo = gql(q)["user"]["projectV2"]["fields"]["nodes"]
    return {f["name"]: f for f in nodo}


def asegurar_campos(fields):
    creados = []
    if "Esfuerzo" not in fields:
        run(["project", "field-create", str(PROJECT_NUMBER), "--owner", OWNER,
             "--name", "Esfuerzo", "--data-type", "NUMBER"])
        creados.append("Esfuerzo(number)")
    if "Tipo" not in fields:
        run(["project", "field-create", str(PROJECT_NUMBER), "--owner", OWNER,
             "--name", "Tipo", "--data-type", "SINGLE_SELECT",
             "--single-select-options", "Épica,Historia,Tarea"])
        creados.append("Tipo(select)")
    if "Prioridad" not in fields:
        run(["project", "field-create", str(PROJECT_NUMBER), "--owner", OWNER,
             "--name", "Prioridad", "--data-type", "SINGLE_SELECT",
             "--single-select-options", "P1,P2,P3"])
        creados.append("Prioridad(select)")
    for nombre in ("Vertical", "Padre", "Depende de"):
        if nombre not in fields:
            run(["project", "field-create", str(PROJECT_NUMBER), "--owner", OWNER,
                 "--name", nombre, "--data-type", "TEXT"])
            creados.append(f"{nombre}(text)")
    print("campos creados:", creados or "ninguno (ya existían)")


def asegurar_opcion_decision(fields):
    q = ('query { user(login: "%s") { projectV2(number: %d) '
         '{ status: field(name: "Status") { ... on ProjectV2SingleSelectField '
         '{ id options { id name color description } } } } } }' % (OWNER, PROJECT_NUMBER))
    status = gql(q)["user"]["projectV2"]["status"]
    opciones = status["options"]
    if any(o["name"] == DECISION_HUMANA for o in opciones):
        print("status: opción ya existe")
        return
    base = next((o for o in opciones if o["name"] == "In Progress"), opciones[0])
    defs = ", ".join(
        '{id: "%s", name: "%s", color: %s, description: %s}'
        % (o["id"], o["name"], o["color"], json.dumps(o.get("description") or "", ensure_ascii=False))
        for o in opciones
    )
    defs += ', {name: "%s", color: %s, description: %s}' % (
        DECISION_HUMANA, base["color"],
        json.dumps("Pendiente de respuesta del propietario", ensure_ascii=False))
    gql('mutation { updateProjectV2Field(input: {fieldId: "%s", singleSelectOptions: [%s]}) '
        '{ projectV2Field { __typename ... on ProjectV2SingleSelectField { id } } } }'
        % (status["id"], defs))
    print("status: opción «%s» agregada" % DECISION_HUMANA)


def listar_issues(intentos=4):
    for _ in range(intentos):
        p = run(["issue", "list", "--repo", REPO, "--state", "all", "--limit", "300",
                 "--json", "title,url,id"], check=False)
        if p.returncode == 0 and p.stdout.strip():
            return {it["title"]: it for it in json.loads(p.stdout)}
        time.sleep(2)
    raise RuntimeError("no se pudo listar los issues del repo")


def crear_issues(items):
    existentes = listar_issues()
    pendientes = [i for i in items if i["title"] not in existentes]
    for n, item in enumerate(pendientes, 1):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as f:
            f.write(item["body"])
            cuerpo = f.name
        run(["issue", "create", "--repo", REPO, "--title", item["title"],
             "--body-file", cuerpo])
        if n % 25 == 0:
            print(f"issues creados: {n}/{len(pendientes)}")
    if pendientes:
        time.sleep(3)
    finales = listar_issues()
    faltan = [i["id"] for i in items if i["title"] not in finales]
    if faltan:
        raise RuntimeError("issues no visibles tras crear: %s" % faltan)
    mapa = {i["id"]: finales[i["title"]] for i in items}
    print("issues listos:", len(mapa))
    return mapa


def agregar_al_project(items, mapa):
    item_ids = {}
    for n, item in enumerate(items, 1):
        nodo = mapa[item["id"]]
        data = gql('mutation { addProjectV2ItemById(input: {projectId: "%s", contentId: "%s"}) { item { id } } }'
                   % (PROJECT_ID, nodo["id"]))
        item_ids[item["id"]] = data["addProjectV2ItemById"]["item"]["id"]
        if n % 25 == 0:
            print(f"item-add: {n}/{len(items)}")
    return item_ids


def fijar_campo(item_id_project, field_id, valor):
    if isinstance(valor, (int, float)):
        v = "number: %s" % valor
    elif isinstance(valor, str) and valor.startswith("opt:"):
        v = 'singleSelectOptionId: "%s"' % valor[4:]
    else:
        v = 'text: %s' % json.dumps(valor, ensure_ascii=False)
    gql('mutation { updateProjectV2ItemFieldValue(input: {projectId: "%s", itemId: "%s", fieldId: "%s", value: {%s}}) { clientMutationId } }'
        % (PROJECT_ID, item_id_project, field_id, v))


def fijar_campos(items, item_ids, fields):
    opt_status = {o["name"]: o["id"] for o in fields["Status"]["options"]}
    opt_tipo = {o["name"]: o["id"] for o in fields["Tipo"]["options"]}
    opt_prio = {o["name"]: o["id"] for o in fields["Prioridad"]["options"]}
    ids = {n: f["id"] for n, f in fields.items()}
    for n, item in enumerate(items, 1):
        ip = item_ids[item["id"]]
        fijar_campo(ip, ids["Status"], "opt:" + opt_status[status_para(item)])
        fijar_campo(ip, ids["Tipo"], "opt:" + opt_tipo[item["tipo"]])
        fijar_campo(ip, ids["Prioridad"], "opt:" + opt_prio[item["prioridad"]])
        fijar_campo(ip, ids["Vertical"], item["vertical"])
        if item.get("padre"):
            fijar_campo(ip, ids["Padre"], item["padre"])
        if item.get("depende_de"):
            fijar_campo(ip, ids["Depende de"], ", ".join(item["depende_de"]))
        if item["id"] in ESFUERZO_HOTEL:
            fijar_campo(ip, ids["Esfuerzo"], ESFUERZO_HOTEL[item["id"]])
        if n % 25 == 0:
            print(f"campos: {n}/{len(items)}")


def main():
    items = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    assert len(items) == 150, len(items)
    asegurar_repo()
    asegurar_campos(query_fields())
    fields = query_fields()
    asegurar_opcion_decision(fields)
    fields = query_fields()
    mapa = crear_issues(items)
    item_ids = agregar_al_project(items, mapa)
    fijar_campos(items, item_ids, fields)
    log = {
        "repo": REPO,
        "project": "%s/projects/%d" % (OWNER, PROJECT_NUMBER),
        "items": len(items),
        "decision_humana": [i["id"] for i in items if es_decision_humana(i)],
        "issues": {i["id"]: mapa[i["id"]]["url"] for i in items},
    }
    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK:", len(items), "ítems cargados. Log:", LOG_PATH)


if __name__ == "__main__":
    main()
