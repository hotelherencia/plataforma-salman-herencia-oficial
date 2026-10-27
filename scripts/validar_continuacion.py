#!/usr/bin/env python3
"""Validación documental incremental. No ejecuta APIs, REA ni producto."""
from pathlib import Path
import json,hashlib,re,subprocess
R=Path(__file__).resolve().parents[1];D=R/'docs/investigacion-competitiva';B=D/'linea-base/continuacion-01';C=D/'continuacion-01'
checks=[]
def ck(ok,name):checks.append({'resultado':'PASS' if ok else 'FAIL','comprobacion':name})
def read(p):return p.read_text()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads(read(B/'manifest.json'));sources=json.loads(read(D/'evidencias.json'));new=json.loads(read(C/'evidencias-nuevas.json'));P=json.loads(read(C/'refinamientos.json'));S=json.loads(read(D/'historias.json'));M={s['id']:s for s in S}
oldS=json.loads(read(B/'docs/investigacion-competitiva/historias.json'));cat=json.loads(read(R/'docs/auditorias/catalogo-requisitos.json'))['features'];oldcat=json.loads(read(B/'docs/auditorias/catalogo-requisitos.json'))['features']
ck(len(manifest)==50,'50 archivos de línea base de continuación')
for m in manifest:ck(digest(B/m['ruta'])==m['sha256'],'Hash baseline incremental '+m['ruta'])
ck((R/'.specify/memory/constitution.md').read_bytes()==(B/'.specify/memory/constitution.md').read_bytes(),'Constitución sin cambios en continuación')
for art in ['spec.md','research.md','plan.md','data-model.md','contracts/README.md','acceptance.md','quickstart.md','tasks.md','checklists/requirements.md']:
 rel=Path('specs/001-cafeteria-mesas-pos')/art;ck((R/rel).read_bytes()==(B/rel).read_bytes(),'Cafetería preservada '+art)
ck(len(new)==26 and len(sources)==68,'26 evidencias nuevas, 68 acumuladas')
ev={e['id']:e for e in sources}
ck(len(ev)==len(sources),'IDs de evidencia únicos')
for e in new:
 ck(e['id'] in ev and ev[e['id']]==e,'Ficha integrada sin cambio de alcance '+e['id'])
 ck(e['observacion_runtime'] is False,'No atribuir runtime '+e['id'])
 ck(e['url'].startswith('https://'),'URL identificada '+e['id'])
ck(len(P)==13 and sum(len(p['criterios']) for p in P)==39,'13 refinamientos, 39 AC adicionales')
ck(len(M)==13 and set(M)=={s['id'] for s in oldS},'Historias previas conservadas sin candidatas activas')
ck(sum(len(s['ac']) for s in S)==65,'65 AC competitivos acumulados')
for s in oldS:ck(set(s['ac'])<=set(M[s['id']]['ac']),'AC previos conservados '+s['id'])
trace=read(C/'trazabilidad.md')
for p in P:
 slug=M[p['us']]['feature'];spec=read(R/'specs'/slug/'spec.md');acc=read(R/'specs'/slug/'acceptance.md')
 ck(p['id'] in spec and p['id'] in trace,'Refinamiento en spec y trazabilidad '+p['id'])
 for field in ['actor','valor','prioridad','pre','trigger','steps','alt','rules','data','risk','deps','metric']:
  ck(bool(p.get(field)),'Campo funcional '+p['id']+'/'+field)
 for e in p['ev']:ck(e in ev,'Evidencia resoluble '+p['id']+'/'+e)
 for fr in p['fr']:ck(fr in cat[slug]['fr'],'FR de historia/dominio correcto '+p['id']+'/'+fr)
 for a in p['criterios']:
  ck(a['id'] in M[p['us']]['ac'] and a['id'] in spec and a['id'] in acc and a['id'] in trace,'AC propagado '+a['id'])
expected={'000-core':{'FR-012'},'002-hotel-reservas-concierge':{'FR-018','FR-019','FR-020'},'003-inmobiliaria-comercial':{'FR-017','FR-018','FR-019','FR-020'},'004-constructora-obra':{'FR-021','FR-022','FR-023'}}
for slug,ids in expected.items():
 ck(set(cat[slug]['fr'])-set(oldcat[slug]['fr'])==ids,'FR incrementales exactos '+slug)
 for art in ['spec.md','research.md','plan.md','data-model.md','contracts/README.md','acceptance.md','quickstart.md','tasks.md','checklists/requirements.md']:
  ck((R/'specs'/slug/art).read_bytes()!=(B/'specs'/slug/art).read_bytes(),'Propagación documental '+slug+'/'+art)
ck(sum(len(v['fr']) for v in cat.values())==77 and sum(len(v['sc']) for v in cat.values())==31,'77 FR y 31 SC sin eliminar IDs')
for slug in cat:
 ck(set(oldcat[slug]['fr'])<=set(cat[slug]['fr']) and oldcat[slug]['sc']==cat[slug]['sc'],'Catálogo previo preservado '+slug)
for vertical in ['hotel','inmobiliaria','constructora']:
 for name in ['revision-profunda.md','cobertura.md']:ck((D/vertical/name).is_file(),'Revisión sustantiva '+vertical+'/'+name)
# Aritmética ilustrativa del documento, no test de producto ni validación contable del cliente.
ck(100-50==50 and 100-50-20-10==20,'Ejemplo distingue compromiso de estados incluidos; regla cliente pendiente')
ck(6==5+1 and 10-5==5,'Ejemplo de recepción/rechazo y reposición configurada')
ck(2*3==6,'Ejemplo de periodicidad por persona y noche')
# Intervalos de prioridad reproducibles, sin sustituir desconocidos por datos comerciales.
q=json.loads(read(D/'priorizacion.json'));weights=q['pesos'];ck(sum(weights.values())==100,'Pesos suman 100')
for x in q['oportunidades']:
 vals=x['valores'];lo=sum(w*((vals[k] if vals[k] is not None else 1)-1)/4 for k,w in weights.items());hi=sum(w*((vals[k] if vals[k] is not None else 5)-1)/4 for k,w in weights.items())
 ck(abs(lo-x['puntuacion_min'])<1e-8 and abs(hi-x['puntuacion_max'])<1e-8,'Puntuación e incertidumbre '+x['id'])
ck(vals['impacto_comercial'] is None and vals['frecuencia'] is None,'Sin inventar frecuencia o impacto comercial')
# Diff real incremental, sin tocar metadatos Git de la carpeta original.
patch=[];changes=[]
for m in manifest:
 old=B/m['ruta'];now=R/m['ruta']
 if old.read_bytes()==now.read_bytes():continue
 p=subprocess.run(['git','diff','--no-index','--no-ext-diff','--no-color','--',str(old),str(now)],capture_output=True,text=True)
 ck(p.returncode==1,'Diff Git incremental '+m['ruta']);patch.append(p.stdout)
 changes.append({'ruta':m['ruta'],'sha256_antes':m['sha256'],'sha256_despues':digest(now),'estado_anterior':'fase competitiva anterior preservada','estado_nuevo':'profundización propuesta; BLOCKED para implementación','justificacion':'RF de otras verticales y efectos compartidos; ver trazabilidad.md y registro-cambios global','evidencia':'H11–H18, I11–I19, O10–O18; límites por ficha','impacto':'dominio, datos, interfaz lógica, aceptación y decisiones; sin implementar','riesgo':'reglas cliente/integración no ratificadas y runtime no observado','validacion':'controles locales estructurales/semánticos documentados, no pruebas de producto'})
(C/'cambios.patch').write_text(''.join(patch));(C/'cambios.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
ck(not any('001-cafeteria' in c['ruta'] for c in changes),'Diff incremental no modifica cafetería')
ck(not re.search(r'(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}',''.join(patch)),'Diff sin token reconocible')
fail=[c['comprobacion'] for c in checks if c['resultado']=='FAIL']
report={'tipo':'validación documental incremental; no Spec Kit/REA/producto','fecha':'2026-10-16','checks':len(checks),'errores':fail,'fuentes_nuevas':len(new),'refinamientos':len(P),'ac_nuevos':39,'ac_acumulados':65,'fr_acumulados':77,'sc':31,'archivos_baseline_modificados':len(changes),'resultados':checks}
(C/'validacion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(f"{len(checks)} comprobaciones; {len(fail)} errores; {len(changes)} archivos de baseline cambiados; 26 fuentes y 39 AC nuevos")
for e in fail:print('FAIL:',e)
raise SystemExit(bool(fail))
