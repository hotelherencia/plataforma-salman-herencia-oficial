# Suite E2E de la plataforma V1

Revisión ejecutable de los flujos declarados e integrados en V1 (módulo
hotel + rutas de acceso/cuenta), en local, con navegador real (Chromium) y
datos 100 % sintéticos. Lee `capturas/e2e-AAAA-MM-DD/INFORME.md` para la
matriz de aceptación y su evidencia.

## Requisitos

- Backend en `127.0.0.1:8080`: base **sintética y desechable** (p. ej.
  `plataforma_e2e`), `ADMIN_USUARIO`/`ADMIN_CLAVE` en el entorno,
  `ORIGEN_FRONT=http://127.0.0.1:3000`, migraciones aplicadas al arrancar.
- Front en `127.0.0.1:3000`: `npm run build && npm run start` en `front/`
  con `API_BASE_URL=http://127.0.0.1:8080` (siempre el build de producción;
  en `next dev` un proxy que corte el WebSocket HMR deja la app sin
  hidratar, ver «Operación continua» en `docs/arquitectura/h7-despliegue.md`).

## Correr la suite

```bash
cd e2e
npm install     # solo la primera vez
npm run e2e
```

Salida: un `✓/✗` por flujo, el resumen `N/N APROBADOS, 0 FALLIDOS` y
`e2e-resultados.json` (misma carpeta).

## Re-ejecución y datos

La suite es **re-ejecutable sin resetear la base**: siembra usuarios y
habitaciones con identificadores únicos por corrida (`RUN`) y todas las
mutaciones llevan claves de idempotencia únicas por corrida. Las corridas
anteriores dejan filas en la base sintética; no interfieren.

## Artefactos

- `e2e-resultados.json`: se **regenera en cada corrida**. Es la evidencia
  machine-readable de la aceptación: se versiona **junto con** el INFORME.md
  de la misma fecha tras cada revisión formal, y fuera de eso puede ignorarse
  el diff. Si un diff aparece en un commit de otro tema, es ruido: regenerar
  con una corrida completa o restaurarlo.
- `capturas/e2e-AAAA-MM-DD/*.png`: evidencia visual numerada en el orden de
  los casos; la ruta queda registrada en cada corrida que llama a `evidencia`.
