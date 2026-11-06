#!/usr/bin/env python3
"""Empaqueta la landing para publicar en el hosting de hotelherencia.cl
(#313, V1-ISSUE-25): genera un zip con los estáticos y unas instrucciones
de subida y verificación. El sitio no lleva build — se sirve tal cual.

Uso:  python3 scripts/empaquetar_landing.py
Salida: landing-dist/landing-hotelherencia-<fecha>.zip junto a INSTRUCCIONES.txt
"""
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "landing"
DESTINO = ROOT / "landing-dist"
HOY = date.today().isoformat()

INSTRUCCIONES = f"""INSTRUCCIONES DE PUBLICACIÓN — landing hotelherencia.cl (#313)
Fecha del paquete: {HOY}

1. DESCOMPRIMIR en el directorio raíz del hosting actual de hotelherencia.cl
   (el sitio que hoy sirve el Apache estático). Los archivos van tal cual:
   index.html, css/, js/. HACER UN RESPALDO del sitio actual antes de pisar.

2. CONFIGURACIÓN (ya viene apuntando a producción; js/config.js):
   - PLATAFORMA_URL: https://plataforma-salman-herencia-oficial.vercel.app
   - API_URL: la misma + /api (reenvío al backend según front/vercel.json)
   Solo tocar si el front cambia de dominio.

3. VERIFICACIÓN tras publicar (desde una ventana de incógnito):
   [ ] https://hotelherencia.cl/ carga: hero, servicios, habitaciones, FAQ.
   [ ] Elegir llegada/salida en el widget y pulsar «Consultar reserva»
       abre  https://plataforma-salman-herencia-oficial.vercel.app/reservar
       con inicio/fin/personas en la URL (nada de datos personales).
   [ ] Rango inválido (salida antes de llegada) muestra aviso y NO navega.
   [ ] El formulario de contacto (#contacto) envía y muestra «Consulta enviada».
   [ ] https://hotelherencia.cl/reservar no existe en el hosting (la reserva
       vive en el front de la plataforma): 404 del hosting está bien.

4. CERRAR la issue #313 con la fecha de verificación.

Problemas frecuentes:
- El CTA abre /reservar del MISMO dominio: revisar que js/config.js llegó
  actualizado (PLATAFORMA_URL apuntando a Vercel) y vaciar caché del hosting.
- El formulario no envía: el CORS del backend valida el ORIGEN_LANDING; el
  valor en producción debe ser https://hotelherencia.cl (Railway → variables).
"""


def main() -> None:
    DESTINO.mkdir(exist_ok=True)
    zip_path = DESTINO / f"landing-hotelherencia-{HOY}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for ruta in sorted(LANDING.rglob("*")):
            if ruta.is_file() and "__pycache__" not in ruta.parts \
                    and "test" not in ruta.parts and not ruta.name.endswith(".pyc") \
                    and ruta.name != "README.md":
                z.write(ruta, ruta.relative_to(LANDING))
        z.writestr("INSTRUCCIONES.txt", INSTRUCCIONES)
    (DESTINO / "INSTRUCCIONES.txt").write_text(INSTRUCCIONES, encoding="utf-8")
    n = len(zipfile.ZipFile(zip_path).namelist())
    print(f"paquete: {zip_path.name} ({n} archivos)")
    print(f"instrucciones: {DESTINO / 'INSTRUCCIONES.txt'}")
    print("listo para subir al hosting (hacer respaldo del sitio actual primero)")


if __name__ == "__main__":
    main()
