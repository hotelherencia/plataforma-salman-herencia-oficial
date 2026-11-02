# Dominio: entidades, estados y reglas (2026-11-02)

HECHO DOCUMENTADO. Modelo funcional tal como vive en PostgreSQL y en el
servicio. El dominio decide; la base de datos proyecta.

## Entidades principales

| Entidad | Qué es | Notas |
|---|---|---|
| Empresa | Aislamiento multi-tenant | toda operación queda atada a `empresa_id` (hoy `EMP-SINTETICA-001`) |
| Usuario | Quien opera | rol `administrador`/`recepcion`/`caja`; nombre de usuario único por empresa; TOTP opcional |
| Sesión | Acceso vigente | `sid` en cookie HttpOnly/Secure (12 h), revocable individual o por usuario |
| Habitación | Unidad vendible | doble estado (ver diagrama) + bandera de mantenimiento + tareas operativas |
| Tarifa | Precio por noche | con vigencia: sin tarifa vigente no hay oferta ni reserva |
| Reserva | Compromiso de estadía | ciclo de estados (ver diagrama); huésped con documento exigido a la entrada |
| Pago / Cargo | Movimientos de la cuenta | pagos manuales por rol autorizado; cargos en estadía (minibar etc.) |
| Auditoría | Trazabilidad | actor, acción, recurso, resultado en cada mutación |

## Ciclo de vida de la reserva

```mermaid
stateDiagram-v2
    [*] --> confirmada : POST /hotel/reservas (con cupo y tarifa vigente)
    confirmada --> en_estadia : entrada (documento + hora; habitación lista)
    confirmada --> cancelada : cancelación (dentro de plazo sin cargo; fuera: primera noche)
    en_estadia --> finalizada : salida (liquidación)
    en_estadia --> cancelada : cancelación con saldo a favor (sin reembolso automático)
    cancelada --> [*]
    finalizada --> [*]
```

## Estados de la habitación (doble dimensión)

```mermaid
stateDiagram-v2
    [*] --> disponible
    disponible --> ocupada : check-in
    ocupada --> disponible : check-out (queda sucia)
    disponible --> disponible : limpieza (sucia → limpia / inspeccionada)
    note right of disponible
        mantenimiento abierto bloquea el check-in
        aunque esté limpia; el cierre autorizado lo habilita
    end note
```

Proyección técnica: `estado_operativo` (disponible/ocupada) ×
`estado_preparacion` (limpia/sucia/inspeccionada) + bandera `mantenimiento`.

## Reglas de negocio citadas en las pruebas del dominio

- **Última unidad con cupo**: cien intentos concurrentes → máximo una
  confirmación; la oferta sin vigencia queda pendiente y escala a atención
  humana.
- **Turnover**: la limpieza completa solo cambia la preparación; las fechas de
  mantenimiento quedan intactas; unidad sucia hoy puede venderse en fecha
  futura.
- **Entrada**: exige documento y hora de llegada; la noche se asienta al
  check-in.
- **Caja**: conciliación del día con pagos y cargos; solo roles autorizados.
- **Idempotencia en todo POST de mutación** (cl `Idempotency-Key`): reintento
  seguro de red y de usuario; 409 ante clave reutilizada con cuerpo distinto.
- **Freno de fuerza bruta**: 5 fallos de login en 5 minutos bloquean al usuario
  5 minutos (en memoria de proceso).
- **Sin sistemas externos reales** (AGENTS.md): Webpay/Mercado Pago/SII/
  Booking/WhatsApp existen solo como puertos; sin adaptador responden 503
  «no configurado» y la API devuelve estado pendiente.

## Pantallas del front (mapa a operaciones)

| Pantalla | Operaciones que consume |
|---|---|
| Login | `POST /sesion`, `DELETE /sesion`, Google estado/callback |
| Oferta | `GET /hotel/oferta` |
| Reserva | `POST /hotel/reservas` |
| Reservas | `GET /hotel/reservas` (filtros fecha/estado/texto) |
| Pago | `POST /hotel/reservas/{id}/pagos` |
| Estadía | entrada, cargos, cancelación |
| Salida | `POST /hotel/reservas/{id}/salida` |
| Caja | `GET /hotel/caja?fecha` |
| Habitaciones | alta/edición (PUT), limpieza, mantenimiento |
| Usuarios | alta, cambio de clave, revocación, baja |
| Cuenta | TOTP: activar, QR, desactivar |
