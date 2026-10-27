#!/usr/bin/env python3
"""Punto de entrada documental; no ejecuta ni regenera bases de datos."""
from pathlib import Path
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUITES = [
    ('documental', 'validar_documentacion.py'),
    ('semantica_investigacion', 'validar_investigacion.py'),
    ('semantica_continuacion', 'validar_continuacion.py'),
    ('modelos_datos', 'validar_modelo_datos.py'),
    ('estructura_visual_y_evidencia_historica', 'validar_arquitectura_visual_ejecutable.py'),
]

def main():
    results = []
    for category, name in SUITES:
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / name)],
                                cwd=ROOT, env={**os.environ, 'PYTHONUTF8': '1'})
        results.append({'categoria': category, 'script': name, 'codigo': result.returncode})
    report = {'suites': results, 'postgresql_actual': 'NO EJECUTADO',
              'revision_visual_actual': 'NO EJECUTADA',
              'alcance': 'XML y logs históricos no prueban ejecución SQL actual ni revisión visual.'}
    (ROOT / 'docs/auditoria/validacion-consolidada.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return int(any(r['codigo'] for r in results))

if __name__ == '__main__':
    raise SystemExit(main())
