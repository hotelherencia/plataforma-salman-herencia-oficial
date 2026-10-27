# language: es
# Especificación de escenarios; steps no implementados, pruebas NO_EJECUTADAS.
Caracteristica: Mensajeria oficial WhatsApp/Instagram/Messenger

  @SOC-007 @TC-SOC-007-P
  Escenario: TC-SOC-007-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Respuesta libre dentro de ventana o plantilla válida fuera de ella.
    Entonces Un mensaje fuera de ventana sin plantilla permitida se bloquea y queda explicacion; no se reintenta como spam.

  @SOC-007 @TC-SOC-007-N
  Escenario: TC-SOC-007-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Fuera de ventana se intenta enviar texto libre promocional.
    Entonces BLOCKED con motivo, sin reintentos para evadir restriccion.

  @SOC-008 @TC-SOC-008-P
  Escenario: TC-SOC-008-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Mensaje entrante inicia hilo y respuesta permitida se entrega.
    Entonces Una revocacion de acceso suspende sólo el conector afectado y alerta; no simula mensajes enviados.

  @SOC-008 @TC-SOC-008-N
  Escenario: TC-SOC-008-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando API rechaza permiso y app afirma mensaje enviado.
    Entonces Estado FAILED/DEGRADED, alerta y alternativa humana.

  @SOC-011 @TC-SOC-011-P
  Escenario: TC-SOC-011-P
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Diez reenvios del mismo mensaje crean un mensaje y una oportunidad.
    Entonces Repetir mensaje diez veces crea un mensaje y una oportunidad; firma inválida no crea nada.

  @SOC-011 @TC-SOC-011-N
  Escenario: TC-SOC-011-N
    Dado un entorno aislado con datos sintéticos y un actor con alcance declarado
    Cuando Firma inválida o misma ID con contenido alterado.
    Entonces 401 o cuarentena de integridad; sin creacion de objetos comerciales.
