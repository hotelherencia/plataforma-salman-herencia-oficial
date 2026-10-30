"""Carga el milestone «adaptador dominio↔PostgreSQL» (ADP) en el GitHub Project n.º 2.

Lee `backlog/v1/adaptador-dominio.json` (épica + 11 historias con criterios),
crea los issues que no existan (idempotente por título), los agrega al
Project y fija Status/Tipo/Prioridad/Vertical/Padre/Depende de/Esfuerzo.
Log: `backlog/v1/carga-adaptador.log.json`.
"""
import json
import subprocess
import tempfile
import time
from pathlib import Path

OWNER = "hotelherencia"
REPO = "hotelherencia/plataforma-salman-herencia-oficial"
PROJECT_NUMBER = 2
PROJECT_ID = "PVT_kwHOFMML_M4Bo9XP"
ROOT = Path(__file__).resolve().parents[1]
ITEMS_PATH = ROOT / "backlog" / "v1" / "adaptador-dominio.json"
LOG_PATH = ROOT / "backlog" / "v1" / "carga-adaptador.log.json"

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


def status_para(item):
    return ESTADO_A_STATUS.get(item["estado"], "Todo")


def query_fields():
    q = ('query { user(login: "%s") { projectV2(number: %d) { fields(first: 40) { nodes { '
         '__typename '
         '... on ProjectV2Field { id name dataType } '
         '... on ProjectV2SingleSelectField { id name dataType options { id name } } '
         '} } } } }' % (OWNER, PROJECT_NUMBER))
    nodos = gql(q)["user"]["projectV2"]["fields"]["nodes"]
    return {f["name"]: f for f in nodos}


def listar_issues(intentos=4):
    for _ in range(intentos):
        p = run(["issue", "list", "--repo", REPO, "--state", "all", "--limit", "400",
                 "--json", "title,url,id"], check=False)
        if p.returncode == 0 and p.stdout.strip():
            return {it["title"]: it for it in json.loads(p.stdout)}
        time.sleep(2)
    raise RuntimeError("no se pudo listar los issues del repo")


def crear_issues(items):
    existentes = listar_issues()
    # idempotencia por título: no recrea los que ya existen
    pendientes = [i for i in items if i["title"] not in existentes]
    for item in pendientes:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as f:
            f.write(item["body"])
            cuerpo = f.name
        run(["issue", "create", "--repo", REPO, "--title", item["title"], "--body-file", cuerpo])
    if pendientes:
        print(f"issues creados: {len(pendientes)}; ya existían: {len(items) - len(pendientes)}")
        time.sleep(3)
    finales = listar_issues()
    faltan = [i["id"] for i in items if i["title"] not in finales]
    if faltan:
        raise RuntimeError("issues no visibles tras crear: %s" % faltan)
    return {i["id"]: finales[i["title"]] for i in items}


def agregar_al_project(items, mapa):
    item_ids = {}
    fallidos = {}
    for item in items:
        nodo = mapa[item["id"]]
        try:
            data = gql('mutation { addProjectV2ItemById(input: {projectId: "%s", contentId: "%s"}) { item { id } } }'
                       % (PROJECT_ID, nodo["id"]))
            item_ids[item["id"]] = data["addProjectV2ItemById"]["item"]["id"]
        except RuntimeError as error:
            # sin permiso de escritura en el Project: se reporta y el log
            # deja la re-ejecución como paso pendiente (el script es
            # idempotente por título de issue)
            fallidos[item["id"]] = str(error).splitlines()[-1][:200]
    if fallidos:
        print(f"aviso: {len(fallidos)} ítems sin agregar al Project (permiso):", ", ".join(fallidos))
    return item_ids, fallidos


def fijar_campo(item_id_project, field_id, valor):
    if isinstance(valor, (int, float)):
        v = "number: %s" % valor
    elif isinstance(valor, str) and valor.startswith("opt:"):
        v = 'singleSelectOptionId: "%s"' % valor[4:]
    else:
        v = "text: %s" % json.dumps(valor, ensure_ascii=False)
    gql('mutation { updateProjectV2ItemFieldValue(input: {projectId: "%s", itemId: "%s", fieldId: "%s", value: {%s}}) { clientMutationId } }'
        % (PROJECT_ID, item_id_project, field_id, v))


def fijar_campos(items, item_ids, fields):
    opt_status = {o["name"]: o["id"] for o in fields["Status"]["options"]}
    opt_tipo = {o["name"]: o["id"] for o in fields["Tipo"]["options"]}
    opt_prio = {o["name"]: o["id"] for o in fields["Prioridad"]["options"]}
    ids = {n: f["id"] for n, f in fields.items()}
    for item in items:
        ip = item_ids[item["id"]]
        fijar_campo(ip, ids["Status"], "opt:" + opt_status[status_para(item)])
        fijar_campo(ip, ids["Tipo"], "opt:" + opt_tipo[item["tipo"]])
        fijar_campo(ip, ids["Prioridad"], "opt:" + opt_prio[item["prioridad"]])
        fijar_campo(ip, ids["Vertical"], item["vertical"])
        if item.get("padre"):
            fijar_campo(ip, ids["Padre"], item["padre"])
        if item.get("depende_de"):
            fijar_campo(ip, ids["Depende de"], ", ".join(item["depende_de"]))
        if item.get("esfuerzo") is not None:
            fijar_campo(ip, ids["Esfuerzo"], item["esfuerzo"])


def main():
    items = json.loads(ITEMS_PATH.read_text(encoding="utf-8"))
    assert len(items) == 12, len(items)
    assert items[0]["tipo"] == "Épica" and items[0]["id"] == "ADP-0"
    fields = query_fields()
    mapa = crear_issues(items)
    item_ids, fallidos = agregar_al_project(items, mapa)
    if item_ids:
        fijar_campos([i for i in items if i["id"] in item_ids], item_ids, fields)
    log = {
        "repo": REPO,
        "project": "%s/projects/%d" % (OWNER, PROJECT_NUMBER),
        "milestone": "adaptador-dominio",
        "items": len(items),
        "issues": {i["id"]: mapa[i["id"]]["url"] for i in items},
        "en_project": sorted(item_ids),
        "pendiente_project": sorted(fallidos),
        "nota": "con permiso de escritura en el Project, re-ejecutar: python scripts/cargar_github_projects_adaptador.py",
    }
    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK:", len(items), "issues;", len(item_ids), "en el Project. Log:", LOG_PATH)


if __name__ == "__main__":
    main()
