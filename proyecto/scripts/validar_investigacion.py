#!/usr/bin/env python3
"""Comprueba trazabilidad documental competitiva; no ejecuta plataformas ni REA."""
from pathlib import Path
import json,hashlib,re,subprocess,difflib
R=Path(__file__).resolve().parents[1];D=R/'docs/investigacion-competitiva';B=D/'linea-base'
checks=[]
def ck(ok,name):checks.append({'resultado':'PASS' if ok else 'FAIL','comprobacion':name})
manifest=json.loads((B/'manifest.json').read_text())
E=json.loads((D/'evidencias.json').read_text());ev={e['id']:e for e in E}
S=json.loads((D/'historias.json').read_text())
ck(len(ev)==len(E),'Evidencias con identificadores únicos')
ck(all(not e['observacion_runtime'] for e in E),'Sin atribución de runtime a fuentes documentales')
ck(all(e['url'].startswith('https://') for e in E),'URLs primarias explícitas HTTPS; accesibilidad en registro web separado')
ck(ev['C11']['url']=='https://fu.do/es-cl/','Referencia regional Fudo indicada por usuario')
ck(sum(1 for p in R.rglob('.env'))==0,'Sin archivo de credenciales copiado al proyecto')
for m in manifest:
 p=B/m['ruta'];ck(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'],'Baseline íntegra '+m['ruta'])
constitution='.specify/memory/constitution.md'
ck((R/constitution).read_bytes()==(B/constitution).read_bytes(),'Constitución no modificada por investigación')
ck(len(S)==13 and len(set(s['id'] for s in S))==13,'13 historias heredadas con alias únicos')
tr=(D/'trazabilidad.md').read_text()
for s in S:
 spec=(R/'specs'/s['feature']/'spec.md').read_text();accept=(R/'specs'/s['feature']/'acceptance.md').read_text()
 ck('### Historia '+s['id'] in spec,'Historia activa '+s['id'])
 ck(s['id'] in tr and s['original'] in tr,'Equivalencia y origen '+s['id'])
 for e in s['evidencias']:ck(e in ev,'Evidencia resoluble '+s['id']+' '+e)
 for ac in s['ac']:ck(ac in spec and ac in accept,'Criterio propagado '+ac)
 for fr in re.findall(r'FR-\d+',s['requisitos']):ck(bool(re.search(r'^\| '+fr+r' \|',spec,re.M)),'Requisito existente '+s['id']+' '+fr)
for slug in sorted(p.name for p in (R/'specs').iterdir() if p.is_dir()):
 old=(B/'specs'/slug/'spec.md').read_text();new=(R/'specs'/slug/'spec.md').read_text()
 oldids=set(re.findall(r'^\| (?:FR|SC)-\d+ \|',old,re.M));newids=set(re.findall(r'^\| (?:FR|SC)-\d+ \|',new,re.M))
 ck(oldids<=newids,'Ningún FR/SC heredado eliminado '+slug)
 ck('**BLOCKED**' in new,'Estado sin aprobación ficticia '+slug)
 ck('NFR-006' in new,'Procedencia e incertidumbre en '+slug)
 for art in ['spec.md','research.md','plan.md','data-model.md','contracts/README.md','quickstart.md','tasks.md','acceptance.md','checklists/requirements.md']:
  ck((B/'specs'/slug/art).read_bytes()!=(R/'specs'/slug/art).read_bytes(),'Cambio propagado '+slug+'/'+art)
# No números de token ni secretos en los cambios revisables.
for folder in [R/'specs',D]:
 for p in folder.rglob('*'):
  if not p.is_file() or p.suffix not in {'.md','.json','.patch','.diff','.py'}:continue
  ck(not bool(re.search(r'(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}',p.read_text())), 'Sin token reconocible '+str(p.relative_to(R)))
for forbidden in [R/'core',R/'verticales']:
 ck(not any(p.suffix in {'.py','.js','.ts','.tsx','.sql'} for p in forbidden.rglob('*')),'Sin código de producto '+forbidden.name)
# Evidencia revisable con git diff --no-index, sin tocar .git ni inicializar repo.
changes=[];patch=[]
for m in manifest:
 old=B/m['ruta'];new=R/m['ruta']
 if old.read_bytes()==new.read_bytes():continue
 proc=subprocess.run(['git','diff','--no-index','--no-ext-diff','--no-color','--',str(old),str(new)],capture_output=True,text=True)
 ck(proc.returncode==1,'Diff Git revisable '+m['ruta'])
 patch.append(proc.stdout)
 changes.append({'ruta':m['ruta'],'sha256_antes':m['sha256'],'sha256_despues':hashlib.sha256(new.read_bytes()).hexdigest(),'estado_anterior':'línea base conservada','estado_nuevo':'enriquecido documentalmente; BLOCKED para implementación','justificacion':'comportamientos de negocio y controles derivados de evidencia; trazabilidad por historia en trazabilidad.md','evidencia':'matriz-evidencias.md y registros US/H; detalle semántico en registro-cambios.md','impacto':'propagación SDD y modelos/contratos lógicos sin implementación','riesgo':'reglas propuestas pendientes de ratificación y runtime no observado','validacion':'comprobaciones locales, no Spec Kit ni pruebas de producto'})
(D/'cambios.patch').write_text(''.join(patch))
(D/'cambios.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
fail=[c['comprobacion'] for c in checks if c['resultado']=='FAIL']
report={'tipo':'validación local de investigación, no REA/Spec Kit','fecha':'2026-10-16','checks':len(checks),'errores':fail,'historias_enriquecidas':len(S),'criterios_nuevos':sum(len(s['ac']) for s in S),'evidencias':len(E),'archivos_baseline_modificados':len(changes),'resultados':checks}
(D/'validacion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(f"{len(checks)} comprobaciones; {len(fail)} errores; {len(S)} historias; {sum(len(s['ac']) for s in S)} AC; {len(changes)} archivos baseline modificados")
for e in fail:print('FAIL:',e)
raise SystemExit(bool(fail))
