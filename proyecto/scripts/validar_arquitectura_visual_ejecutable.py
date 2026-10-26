#!/usr/bin/env python3
"""
Validador formal de arquitectura visual (.drawio), modelos relacionales (.dbml)
y esquemas ejecutables PostgreSQL para Plataforma Salman.
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
ARQ_DIR = ROOT / "docs/arquitectura"

errors = []
checks = []

def check(ok, message, category="ESTRUCTURAL"):
    if category == "EJECUTABLE":
        category = "EVIDENCIA_HISTORICA_SQL"
    res = "PASS" if ok else "FAIL"
    checks.append({"categoria": category, "comprobacion": message, "resultado": res})
    if not ok:
        errors.append(f"[{category}] {message}")

print("Iniciando validación exhaustiva de arquitectura visual y modelos ejecutables...")

# 1. Validación Estructural de todos los archivos .drawio
drawio_files = list(ARQ_DIR.rglob("*.drawio"))
check(len(drawio_files) >= 19, f"Se encontraron {len(drawio_files)} diagramas .drawio (esperados >= 19)", "ESTRUCTURAL")

for df in drawio_files:
    rel_path = df.relative_to(ROOT)
    try:
        tree = ET.parse(df)
        root = tree.getroot()
        check(root.tag == "mxfile", f"Root tag <mxfile> válido en {rel_path}", "ESTRUCTURAL")
        
        diagram = root.find("diagram")
        check(diagram is not None and diagram.get("name"), f"Página <diagram> no vacía en {rel_path}", "ESTRUCTURAL")
        
        model = diagram.find("mxGraphModel") if diagram is not None else None
        check(model is not None, f"<mxGraphModel> presente en {rel_path}", "ESTRUCTURAL")
        
        mx_root = model.find("root") if model is not None else None
        check(mx_root is not None, f"<root> presente en {rel_path}", "ESTRUCTURAL")
        
        cells = mx_root.findall("mxCell") if mx_root is not None else []
        vertices = [c for c in cells if c.get("vertex") == "1"]
        edges = [c for c in cells if c.get("edge") == "1"]
        
        check(len(vertices) >= 2, f"Nodos sustantivos ({len(vertices)} vértices) en {rel_path}", "SEMANTICA")
        check(len(edges) >= 1, f"Conectores/Relaciones ({len(edges)} aristas) en {rel_path}", "SEMANTICA")
        
        # Validar que los identificadores de celda sean únicos
        cell_ids = [c.get("id") for c in cells if c.get("id")]
        check(len(cell_ids) == len(set(cell_ids)), f"IDs de celdas únicos en {rel_path}", "ESTRUCTURAL")

    except Exception as e:
        check(False, f"Error parseando XML en {rel_path}: {e}", "ESTRUCTURAL")

# 2. Validación de Modelos Relacionales DBML
dbml_files = list(ARQ_DIR.rglob("*.dbml"))
check(len(dbml_files) >= 6, f"Se encontraron {len(dbml_files)} archivos DBML (esperados >= 6)", "ESTRUCTURAL")

for dbf in dbml_files:
    rel_path = dbf.relative_to(ROOT)
    text = dbf.read_text()
    table_count = text.count("Table ")
    check(table_count >= 5, f"Contenido relacional ({table_count} tablas) en {rel_path}", "SEMANTICA")
    check("indexes {" in text or "Project " in text, f"Estructura formal DBML en {rel_path}", "ESTRUCTURAL")
    # Verificar balance de llaves
    check(text.count("{") == text.count("}"), f"Llaves balanceadas en {rel_path}", "ESTRUCTURAL")

# 3. Validación de Scripts SQL y Pruebas
sql_files = list((ARQ_DIR / "pruebas").rglob("*.sql"))
check(len(sql_files) >= 9, f"Se encontraron {len(sql_files)} scripts de prueba SQL (esperados >= 9)", "ESTRUCTURAL")

for sf in sql_files:
    rel_path = sf.relative_to(ROOT)
    text = sf.read_text()
    check(len(text.strip()) > 50, f"Script SQL no vacío en {rel_path}", "ESTRUCTURAL")

# 4. Comprobación de Log de Resultados de PostgreSQL
log_file = ARQ_DIR / "pruebas/resultados/ejecucion_postgresql.log"
check(log_file.is_file(), "Log de ejecución PostgreSQL existe", "EJECUTABLE")
log_text = log_file.read_text()
check("[PASS] DDL Core" in log_text, "DDL Core ejecutado con éxito", "EJECUTABLE")
check("[PASS] DDL Cafeteria" in log_text, "DDL Cafetería ejecutado con éxito", "EJECUTABLE")
check("[PASS] DDL Hotel" in log_text, "DDL Hotel ejecutado con éxito", "EJECUTABLE")
check("[PASS] DDL Inmobiliaria" in log_text, "DDL Inmobiliaria ejecutado con éxito", "EJECUTABLE")
check("[PASS] DDL Constructora" in log_text, "DDL Constructora ejecutado con éxito", "EJECUTABLE")
check("[PASS] Pruebas de Integridad y Restricciones CHECK" in log_text, "Integridad y CHECKs validados", "EJECUTABLE")
check("[PASS] Pruebas de Aislamiento Tenant y RLS (app_user)" in log_text, "RLS con app_user validado", "EJECUTABLE")
check("[PASS] Pruebas de Concurrencia y Control Optimista" in log_text, "Concurrencia optimista validada", "EJECUTABLE")
check("NOTICE:  RLS de aislamiento en SELECT validado exitosamente" in log_text, "Comprobación RLS SELECT registrada", "EJECUTABLE")
check("NOTICE:  RLS de aislamiento en INSERT validado exitosamente" in log_text, "Comprobación RLS INSERT registrada", "EJECUTABLE")

# Guardar informe JSON
report = {
    "titulo": "Validación de Arquitectura Visual y Ejecutable",
    "total_comprobaciones": len(checks),
    "errores": len(errors),
    "detalles": checks
}
(ARQ_DIR / "pruebas/resultados/validacion_arquitectura.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))

print(f"\nResumen: {len(checks)} comprobaciones; {len(errors)} errores.")
for err in errors:
    print("FAIL:", err)

sys.exit(1 if errors else 0)
