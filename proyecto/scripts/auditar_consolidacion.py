#!/usr/bin/env python3
"""Inventario SHA-256 y examen redactado de secretos, incluidos blobs históricos."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OUT = ROOT / 'docs/auditoria'
GIT = ['git', '-c', 'core.preloadIndex=false', '-c', 'core.fscache=false']

def git(*args):
    return subprocess.check_output(GIT + list(args), cwd=REPO)

def main():
    OUT.mkdir(exist_ok=True)
    known = []
    env = REPO / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                value = value.strip().strip('\"\'')
                if any(x in key.upper() for x in ('TOKEN', 'SECRET', 'PASSWORD', 'PAT')) and len(value) >= 16:
                    known.append(value.encode())
    patterns = [rb'gh[pousr]_[A-Za-z0-9]{30,}', rb'github_pat_[A-Za-z0-9_]{40,}',
                rb'AKIA[0-9A-Z]{16}', rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    findings = []
    def scan(data, location):
        if any(value in data for value in known) or any(re.search(p, data) for p in patterns):
            findings.append({'ubicacion': location, 'detalle': 'Posible secreto; valor omitido'})
    records = []
    for path in sorted(REPO.rglob('*')):
        rel = path.relative_to(REPO)
        if any(p in {'.git', '.cache', '__pycache__', 'rea'} for p in rel.parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if path.name == '.env' or path.name.startswith('.env.') and path.name != '.env.example':
            records.append({'ruta': rel.as_posix(), 'clase': 'REFERENCE', 'motivo': 'Secreto local excluido; contenido y hash omitidos'})
            continue
        data = path.read_bytes()
        scan(data, rel.as_posix())
        if path.parent == OUT and path.name in {'inventario-consolidacion.json', 'seguridad-consolidacion.json'}:
            records.append({'ruta': rel.as_posix(), 'clase': 'GENERATED', 'motivo': 'Informe de esta ejecución; se omite hash autorreferencial'})
            continue
        parts = set(rel.parts)
        if 'linea-base' in parts:
            kind, reason = 'ARCHIVE', 'Baseline inmutable requerida por validadores'
        elif 'originales' in parts or len(rel.parts) == 1 and path.suffix in {'.md', '.docx'}:
            kind, reason = 'REFERENCE', 'Fuente primaria; equivalencia semántica completa no acreditada'
        elif path.suffix in {'.diff', '.patch', '.log', '.drawio', '.dbml', '.mmd'} or path.name in {'arbol.txt', 'validacion-local.json', 'validacion_arquitectura.json'} or path.parent.name == 'sql' and 'pruebas' in parts:
            kind, reason = 'GENERATED', 'Salida reproducible o evidencia histórica identificada'
        elif 'specs' in parts or '.specify' in parts or 'scripts' in parts or path.name == 'README.md':
            kind, reason = 'CANONICAL', 'Especificación activa, configuración o verificador'
        else:
            kind, reason = 'REFERENCE', 'Contexto o artefacto preservado; autoridad según README'
        records.append({'ruta': rel.as_posix(), 'sha256': hashlib.sha256(data).hexdigest(), 'clase': kind, 'motivo': reason})
    objects = git('rev-list', '--objects', '--all').decode().splitlines()
    blobs = 0
    object_ids = [entry.split(' ', 1)[0] for entry in objects]
    batch = subprocess.run(GIT + ['cat-file', '--batch'], cwd=REPO,
                           input=('\n'.join(object_ids) + '\n').encode(),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    cursor = 0
    for oid in object_ids:
        end = batch.index(b'\n', cursor)
        header = batch[cursor:end].split()
        size = int(header[2])
        cursor = end + 1
        data = batch[cursor:cursor + size]
        cursor += size + 1
        if header[1] == b'blob':
            scan(data, 'git:' + oid)
            blobs += 1
    tracked = git('ls-files', '-z').decode().split('\0')
    sensitive = [p for p in tracked if p and (Path(p).name == '.env' or Path(p).name.startswith('.env.') and Path(p).name != '.env.example')]
    groups = {}
    for item in records:
        if 'sha256' in item:
            groups.setdefault(item['sha256'], []).append(item['ruta'])
    duplicates = [{'sha256': h, 'rutas': paths} for h, paths in groups.items() if len(paths) > 1]
    (OUT / 'inventario-consolidacion.json').write_text(json.dumps({'archivos': records, 'duplicados_exactos': duplicates}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    report = {'blobs_historicos_examinados': blobs, 'archivos_actuales': len(records), 'hallazgos': findings,
              'env_versionados': sensitive, 'limite': 'Patrones de credenciales y coincidencia con secretos locales; no garantiza detección universal.'}
    (OUT / 'seguridad-consolidacion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'archivos': len(records), 'grupos_iguales': len(duplicates), 'blobs': blobs, 'hallazgos': len(findings), 'env_versionados': len(sensitive)}))
    return int(bool(findings or sensitive))

if __name__ == '__main__':
    raise SystemExit(main())
