#!/usr/bin/env python3
"""Validación documental local; no reemplaza Spec Kit ni pruebas de producto."""
from pathlib import Path
import hashlib, json, re, difflib
ROOT=Path(__file__).resolve().parents[1]
errors=[];checks=[]
def check(ok,message):
 checks.append({'resultado':'PASS' if ok else 'FAIL','comprobacion':message})
 if not ok:errors.append(message)
manifest=json.loads((ROOT/'docs/auditorias/originales-sha256.json').read_text())
for source in manifest:
 for p in [ROOT/'docs/originales'/source['ruta']]:
  check(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==source['sha256'],f'Hash original {p.relative_to(ROOT.parent)}')
features=json.loads((ROOT/'docs/auditorias/catalogo-requisitos.json').read_text())['features']
required=['spec.md','plan.md','research.md','data-model.md','quickstart.md','tasks.md','acceptance.md','contracts/README.md','checklists/requirements.md']
trace=(ROOT/'docs/auditorias/trazabilidad.md').read_text()
for slug,ids in features.items():
 folder=ROOT/'specs'/slug
 for name in required:
  p=folder/name;check(p.is_file() and len(p.read_text().strip())>150,f'Contenido {slug}/{name}')
 spec=(folder/'spec.md').read_text();accept=(folder/'acceptance.md').read_text()
 check('**BLOCKED**' in spec,f'Bloqueos visibles {slug}')
 actual=re.findall(r'^\| (FR-\d+) \|',spec,re.M)
 check(sorted(actual)==sorted(ids['fr']) and len(actual)==len(set(actual)),f'IDs FR exactos y únicos {slug}')
 actualsc=re.findall(r'^\| (SC-\d+) \|',spec,re.M)
 check(sorted(actualsc)==sorted(ids['sc']),f'IDs SC preservados {slug}')
 for fr in ids['fr']:
  check(bool(re.search(r'^\| AT-\d+ \| '+fr+r' \|',accept,re.M)),f'Prueba propuesta {slug}/{fr}')
  check(f'| {slug} | {fr} |' in trace,f'Origen trazado {slug}/{fr}')
 for sc in ids['sc']:
  check(f'| {sc} |' in accept,f'Criterio medible propuesto {slug}/{sc}')
for folder,_,files in __import__('os').walk(ROOT):
 for filename in files:
  p=Path(folder)/filename
  if p.suffix!='.md' or 'originales' in p.parts or 'linea-base' in p.parts:continue
  text=p.read_text()
  for match in re.finditer(r'(?<!!)\[[^\]]+\]\(([^)]+)\)',text):
   target=match.group(1).strip('<>')
   if target.startswith(('https://','http://','mailto:','#')):continue
   target=target.split('#')[0]
   check((p.parent/target).exists(),f'Enlace local {p.relative_to(ROOT)} → {target}')
check(len([p for p in ROOT.rglob('constitution.md') if 'linea-base' not in p.parts and 'Análisis' not in p.parts])==1,'Una única constitución activa; baseline archivada y Análisis/ excluidos')
check(set(p.name for p in (ROOT/'specs').iterdir() if p.is_dir())==set(features),'Cinco features esperadas')
# Grafo interno consumidor -> proveedor. La relación opcional también debe ser acíclica.
edges={'000-core':[],'001-cafeteria-mesas-pos':['000-core'],'002-hotel-reservas-concierge':['000-core','001-cafeteria-mesas-pos'],'003-inmobiliaria-comercial':['000-core'],'004-constructora-obra':['000-core','003-inmobiliaria-comercial']}
def acyclic(node,stack):
 if node in stack:return False
 return all(acyclic(child,stack|{node}) for child in edges[node])
check(all(acyclic(n,set()) for n in edges),'Dependencias internas propuestas sin ciclos')
check(not any(p.suffix in {'.py','.js','.ts','.sql','.tsx'} for d in ['core','verticales'] for p in (ROOT/d).rglob('*')),'Sin código funcional en core/verticales')
report={'tipo':'validación documental local; no Spec Kit','fecha':'2026-10-16','checks':len(checks),'errores':errors,'resultados':checks,'fr':sum(len(x['fr']) for x in features.values()),'sc':sum(len(x['sc']) for x in features.values())}
(ROOT/'docs/auditorias/validacion-local.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
# Diff auditable por fuente respecto de la spec derivada, incluidos traslados de alcance.
for marker,slug,label in [('01 Caf','001-cafeteria-mesas-pos','cafeteria'),('02 Hotel','002-hotel-reservas-concierge','hotel'),('03 Inm','003-inmobiliaria-comercial','inmobiliaria')]:
 original=next(x for x in manifest if marker in x['ruta'])
 old=(ROOT/'docs/originales'/original['ruta']).read_text().splitlines(True)
 new=(ROOT/'specs'/slug/'spec.md').read_text().splitlines(True)
 diff=''.join(difflib.unified_diff(old,new,fromfile=original['ruta'],tofile=f'specs/{slug}/spec.md'))
 (ROOT/f'docs/auditorias/cambios-{label}.diff').write_text(diff)
# Árbol de archivos reales; archivos excluidos son solo metadatos del SO.
paths=sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file())
(ROOT/'docs/auditorias/arbol.txt').write_text('plataforma-salman/\n'+'\n'.join('  '+p for p in paths)+'\n')
print(f"{len(checks)} comprobaciones; {len(errors)} errores; {report['fr']} FR; {report['sc']} SC")
for error in errors:print('FAIL:',error)
raise SystemExit(1 if errors else 0)
