# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Publicaciones y publicidad controlada

  @INT-006 @TC-INT-006-P
  Escenario: TC-INT-006-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Contenido aprobado se pública y guarda ID externo.
    Entonces Sin aprobación no pública contenido ni activa gasto

  @INT-006 @TC-INT-006-N
  Escenario: TC-INT-006-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Agente intenta publicar oferta o activar anuncio sin permiso.
    Entonces Bloqueo y solicitud de aprobación; cero gasto externo.

  @SOC-014 @TC-SOC-014-P
  Escenario: TC-SOC-014-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Campaña aprobada opera dentro de límite y período.
    Entonces Sin autorización no se activa gasto; aumentar presupuesto requiere nueva aprobación aplicable.

  @SOC-014 @TC-SOC-014-N
  Escenario: TC-SOC-014-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Modelo aumenta presupuesto para mejorar conversion por iniciativa.
    Entonces 403 y solicitud pendiente; no gasto extra.

  @SOC-015 @TC-SOC-015-P
  Escenario: TC-SOC-015-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Pieza aprobada pública y guarda referencia externa.
    Entonces Formato no admitido queda pendiente o se exporta para publicación manual, nunca figura publicado.

  @SOC-015 @TC-SOC-015-N
  Escenario: TC-SOC-015-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Proveedor rechaza formato pero interfaz muestra publicada.
    Entonces Estado FAILED/MANUAL y alerta, sin evidencia ficticia.
