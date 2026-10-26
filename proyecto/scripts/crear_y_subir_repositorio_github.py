#!/usr/bin/env python3
"""
Script de creación y publicación segura del repositorio en GitHub.
Utiliza GITHUB_TOKEN_CLASIC de .env sin exponer el token en logs.
"""
import os
import subprocess
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent
ENV_FILE = ROOT / ".env"

if not ENV_FILE.is_file():
    print(f"Error: No se encontró el archivo .env en {ROOT}")
    sys.exit(1)

token = ""
for line in ENV_FILE.read_text().splitlines():
    line = line.strip()
    if line.startswith("GITHUB_TOKEN_CLASIC="):
        token = line.split("=", 1)[1].strip().strip('"').strip("'")
        break

if not token:
    print("Error: No se encontró GITHUB_TOKEN_CLASIC en .env")
    sys.exit(1)

# Configurar entorno con GH_TOKEN
env = os.environ.copy()
env["GH_TOKEN"] = token

# 1. Comprobar usuario
res_user = subprocess.run(["gh", "api", "user", "--jq", ".login"], env=env, capture_output=True, text=True)
if res_user.returncode != 0:
    print("Error de autenticación con GitHub:", res_user.stderr.strip())
    sys.exit(1)

username = res_user.stdout.strip()
repo_name = "plataforma-salman"
full_repo = f"{username}/{repo_name}"
print(f"Usuario autenticado en GitHub: {username}")
print(f"Repositorio objetivo: {full_repo} (Privado)")

# 2. Verificar si el repositorio ya existe en GitHub
check_repo = subprocess.run(["gh", "repo", "view", full_repo], env=env, capture_output=True, text=True)

if check_repo.returncode != 0:
    print(f"Creando repositorio privado '{full_repo}' en GitHub...")
    create_proc = subprocess.run(
        ["gh", "repo", "create", full_repo, "--private", "--description", "Plataforma Salman: Especificaciones SDD, Modelos Visuales y Arquitectura de Datos Multi-tenant"],
        env=env,
        capture_output=True,
        text=True,
        cwd=ROOT
    )
    if create_proc.returncode != 0:
        print("Error al crear el repositorio:", create_proc.stderr.strip())
        sys.exit(1)
    print(f"Repositorio creado exitosamente: https://github.com/{full_repo}")
else:
    print(f"El repositorio '{full_repo}' ya existe en GitHub.")

# 3. Configurar remoto git si no existe
remote_url = f"https://x-access-token:{token}@github.com/{full_repo}.git"
safe_remote_url = f"https://github.com/{full_repo}.git"

remotes = subprocess.run(["git", "remote"], capture_output=True, text=True, cwd=ROOT).stdout.splitlines()
if "origin" in remotes:
    subprocess.run(["git", "remote", "set-url", "origin", safe_remote_url], cwd=ROOT, check=True)
else:
    subprocess.run(["git", "remote", "add", "origin", safe_remote_url], cwd=ROOT, check=True)

print("Remoto 'origin' configurado hacia:", safe_remote_url)

# 4. Empujar las ramas usando el helper con token
branches = ["main", "docs/consolidacion-sdd", "docs/consolidacion-definitiva"]
for br in branches:
    print(f"Subiendo rama '{br}'...")
    push_proc = subprocess.run(
        ["git", "push", "-u", remote_url, br],
        capture_output=True,
        text=True,
        cwd=ROOT
    )
    if push_proc.returncode != 0:
        print(f"Error al subir rama '{br}':", push_proc.stderr.strip().replace(token, "***TOKEN***"))
        sys.exit(1)
    print(f"Rama '{br}' subida con éxito.")

# 5. Establecer docs/consolidacion-definitiva como rama por defecto
print("Configurando 'docs/consolidacion-definitiva' como rama por defecto...")
edit_proc = subprocess.run(
    ["gh", "repo", "edit", full_repo, "--default-branch", "docs/consolidacion-definitiva"],
    env=env,
    capture_output=True,
    text=True,
    cwd=ROOT
)
if edit_proc.returncode == 0:
    print("Rama por defecto configurada exitosamente.")
else:
    print("Aviso al configurar rama por defecto:", edit_proc.stderr.strip())

# 6. Comprobar estado final en GitHub
view_proc = subprocess.run(
    ["gh", "repo", "view", full_repo, "--json", "name,visibility,url,defaultBranchRef"],
    env=env,
    capture_output=True,
    text=True,
    cwd=ROOT
)
if view_proc.returncode == 0:
    info = json.loads(view_proc.stdout)
    print("\nResumen final del repositorio:")
    print("  Nombre:", info.get("name"))
    print("  Visibilidad:", info.get("visibility"))
    print("  URL:", info.get("url"))
    print("  Rama Principal:", info.get("defaultBranchRef", {}).get("name"))

print("\nOperación completada con éxito.")
