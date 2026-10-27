# Grupo Salman / Hotel Herencia
## Especificaciones funcionales y técnicas V1.0
**Destinatarios: equipo de Mikhail y Cristóbal. Propietario funcional: Ricardo Salman. Fecha:25 de octubre de 2026.**

Estado: ESPECIFICACIONES DESARROLLADAS PARA REVISIÓN. No es otro prompt ni una aplicación implementada. La construcción con IA/agentes y SDD fue acordada; no estan aprobados automáticamente stack,proveedores,precios,políticas,datos reales ni producción.

## Lectura y uso
1. Leer Documento_Maestro_Herencia_V1_0.docx y maestro/M01..M24.md. El Word es vista legible del maestro; el ZIP contiene el detalle contractual completo.
2. Revisar sdd/constitucion.md, sdd/ADR-001-stack-propuesto.md, registros/decisiones.csv y registros/acoplamientos_resueltos.csv.
3. Consultar cada carpeta specs/NNN-...: spec,plan,tasks,data-model,research,contracts,acceptance,quickstart,checklist,traceability,status. Son documentos desarrollados con reglas/casos; no semillas ni tareas ejecutadas.
4. Usar modelos,contratos,reglas,ux,seguridad,pruebas y operación como anexos normativos. La trazabilidad relaciona 153 requisitos con 505 tareas propuestas y 306 casos, mas 48 escenarios transversales; estos últimos se superponen y no son porcentajes de cobertura.
5. Acordar responsables y validar decisiones bloqueantes,adaptar al Spec Kit instalado y autorizar un paquete. No entregar todos los archivos a un agente con permiso irrestricto de producción.

## Contenido
24 capitulos maestros;23 paquetesSDD;153 requisitos originales preservados y desarrollados;109 entidades y 1409 campos incluyendo comunes;53 pantallas;API propia y eventos;reglas financieras,permisos,riesgos,45 decisiones,22 relaciones de dependencia clasificadas y plan de traspaso. Las cifras indican alcance documental, no software completado.

## Lo que ya esta definido
Operaciones de hotel y núcleo multiempresa, recorridos desde redes, disponibilidad única,reserva,pago,caja,recepción,aseo,lavandería,alimentación,compras,personal,costos,conciliación,renovación y corte. Modelo/arquitectura propuestos,pruebas esperadas y tareas concretas.

## Lo que sigue pendiente de validar
Datos actuales de administradora:17 fichas,camas,tarifas,políticas,personal,recetas,inventario,contratos,activos y reservas/fondos del corte. Cuentas y proveedores,reglas tributarias/laborales/privacidad,stack y costos,version/agente Spec Kit,revisores y autorizaciones. Ninguno se relleno como hecho real. Fuentes históricas y datos sintéticos estan separados.

## Frontera del grupo
Hotel y servicios compartidos se desarrollan ahora. F22 establece interfaces para cafetería,inmobiliarias,inversiones,matriz y constructora; no inventa sus procesos completos aún no estudiados. Mantener sociedades hermanas y filiales segun evidencia actual.

## Validación de esta entrega
Ver evidencias_documentales/resultado_validacion.json. Comprueba estructura,referencias,IDs,esquemas y consistencia documental. No se han ejecutado tests de la aplicación,instaladoSpecKit,probadoAPIs reales,creado repositorio remoto ni realizado auditoría independiente. Ningun escenario de software esta marcadoPASS.

## Primer paquete de equipo
RevisarF00/F01 y D37-D45. Decidir arquitectura/identidad,entorno,repo y roles; preparar controles antes de desarrollar reserva. Luego F02/F03/F04/F05 para recorrido comercial y F06 en paralelo cuando contratos estables. F21 es transversal desde inicio; F20 puede levantar datos desde ahora,pero carga productiva necesita gates aprobados.

## Integridad
MANIFEST.json contiene huellasSHA256. Para validar documentalmente ejecutar `python scripts/validar_paquete.py` en una copia extraida. El validador no instala dependencias ni toca servicios externos. Un resultado correcto no aprueba políticas empresariales.
