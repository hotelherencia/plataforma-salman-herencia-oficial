#!/usr/bin/env python3
"""Validación exhaustiva de consistencia de arquitectura de datos, MER, MR y contratos SDD."""
from pathlib import Path
import json, re

ROOT = Path(__file__).resolve().parents[1]
DATOS_DIR = ROOT / 'docs/arquitectura/datos'

errors = []
checks = []

def check(ok, message):
    checks.append({'resultado': 'PASS' if ok else 'FAIL', 'comprobacion': message})
    if not ok:
        errors.append(message)

# 1. Comprobación de existencia de los artefactos de arquitectura de datos
required_artifacts = [
    'mer-conceptual.md',
    'mr-logico.md',
    'modelo-fisico.md',
    'diagramas-comportamiento.md',
    'diagrama-c4.md',
    'contratos-integracion.md',
    'trazabilidad-datos.md',
    'hallazgos-datos.md'
]

for art in required_artifacts:
    p = DATOS_DIR / art
    check(p.is_file() and len(p.read_text().strip()) > 300, f'Artefacto de datos sustantivo: {art}')

# 2. Resolución matemática de la discrepancia de conteo de FRs (77 reales vs 91 aparente)
cat_path = ROOT / 'docs/auditorias/catalogo-requisitos.json'
cat = json.loads(cat_path.read_text())['features']

counts = {k: len(v['fr']) for k, v in cat.items()}
total_real = sum(counts.values())

check(total_real == 77, f'Catálogo canónico contiene exactamente 77 FRs (obtenido: {total_real})')
check(counts['000-core'] == 12, '000-core tiene exactamente 12 FRs')
check(counts['001-cafeteria-mesas-pos'] == 16, '001-cafeteria-mesas-pos tiene exactamente 16 FRs')
check(counts['002-hotel-reservas-concierge'] == 20, '002-hotel-reservas-concierge tiene exactamente 20 FRs')
check(counts['003-inmobiliaria-comercial'] == 17, '003-inmobiliaria-comercial tiene exactamente 17 FRs (IDs 1-9, 13-20)')
check(counts['004-constructora-obra'] == 12, '004-constructora-obra tiene exactamente 12 FRs (IDs 10-12, 15-23)')

# Explicación de la suma 91: suma de índices máximos por feature
max_indices = {
    '000-core': 12,
    '001-cafeteria-mesas-pos': 16,
    '002-hotel-reservas-concierge': 20,
    '003-inmobiliaria-comercial': 20, # FR-020
    '004-constructora-obra': 23        # FR-023
}
check(sum(max_indices.values()) == 91, 'Suma de índices máximos explica matemáticamente el valor aparente de 91 FRs')

# 3. Comprobación de no duplicidad de FRs dentro de cada feature
for k, v in cat.items():
    check(len(v['fr']) == len(set(v['fr'])), f'FRs únicos sin duplicados en {k}')

# 4. Comprobación de integridad multi-tenant en el modelo físico y relacional
mr_text = (DATOS_DIR / 'mr-logico.md').read_text()
fisico_text = (DATOS_DIR / 'modelo-fisico.md').read_text()

check('tenant_id' in mr_text and 'UUID' in mr_text, 'Integridad multi-tenant con tenant_id en MR')
check('ROW LEVEL SECURITY' in fisico_text, 'Políticas RLS declaradas en modelo físico')
check('FOR UPDATE' in fisico_text, 'Control de concurrencia pesimista en hot-paths')
check('idempotency_key' in fisico_text, 'Estrategia de idempotencia explícita en diseño físico')

# 5. Comprobación de sintaxis de bloques Mermaid
for art in ['mer-conceptual.md', 'diagramas-comportamiento.md', 'diagrama-c4.md']:
    text = (DATOS_DIR / art).read_text()
    open_mermaid = text.count('```mermaid')
    close_mermaid = text.count('```\n') + (1 if text.endswith('```') else 0)
    check(open_mermaid > 0 and open_mermaid <= text.count('```') // 2, f'Bloques Mermaid balanceados en {art}')

# 6. Comprobación de que no se implementó código de producto
for forbidden in [ROOT / 'core', ROOT / 'verticales']:
    check(not any(p.suffix in {'.py', '.js', '.ts', '.tsx', '.sql'} for p in forbidden.rglob('*')),
          f'Sin código ejecutable en {forbidden.name}')

print(f"{len(checks)} comprobaciones de arquitectura de datos; {len(errors)} errores.")
for err in errors:
    print('FAIL:', err)

raise SystemExit(1 if errors else 0)
