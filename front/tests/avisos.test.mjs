import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import {
  aQuienLlega, cuerpoPreferencias, estadoEnvio, filasDesdeApi, leerCorreos, nombreCanal, textoCanal,
} from '../lib/avisos.js'

const API = [
  { tipo: 'solicitud_recibida', nombre: 'Nueva solicitud de reserva', descripcion: 'd', activo: true, destinatarios: ['a@hotel.cl'] },
  { tipo: 'pago_registrado', nombre: 'Pago registrado', descripcion: 'd', activo: false, destinatarios: [] },
]

describe('Configuración → Avisos', () => {
  it('lee correos separados por coma, espacio o salto de línea, sin repetir', () => {
    assert.deepEqual(leerCorreos(' A@Hotel.cl, b@hotel.cl;\na@hotel.cl  '), { correos: ['a@hotel.cl', 'b@hotel.cl'], invalidos: [] })
    assert.deepEqual(leerCorreos('a@hotel.cl, malo').invalidos, ['malo'])
    assert.deepEqual(leerCorreos(''), { correos: [], invalidos: [] })
  })

  it('arma el cuerpo de la API y valida en castellano', () => {
    const filas = filasDesdeApi(API)
    assert.equal(filas[0].texto, 'a@hotel.cl')
    assert.deepEqual(cuerpoPreferencias(filas).cuerpo, {
      preferencias: [
        { tipo: 'solicitud_recibida', activo: true, destinatarios: ['a@hotel.cl'] },
        { tipo: 'pago_registrado', activo: false, destinatarios: [] },
      ],
    })
    const mala = cuerpoPreferencias([{ ...filas[0], texto: 'x@' }])
    assert.equal(mala.error, 'Nueva solicitud de reserva: «x@» no parece un correo.')
    const muchos = cuerpoPreferencias([{ ...filas[0], texto: Array.from({ length: 11 }, (_, i) => `p${i}@h.cl`).join(',') }])
    assert.match(muchos.error, /máximo 10 destinatarios/)
  })

  it('explica a quién llega cada aviso', () => {
    const [sol, pago] = filasDesdeApi(API)
    assert.equal(aQuienLlega(sol, ['d@hotel.cl']), 'Llega a a@hotel.cl.')
    assert.equal(aQuienLlega(pago, ['d@hotel.cl']), 'Apagado: no se envía.')
    assert.match(aQuienLlega({ ...pago, activo: true }, ['d@hotel.cl']), /correo por defecto \(d@hotel\.cl\)/)
    assert.match(aQuienLlega({ ...pago, activo: true }, []), /Sin destinatarios/)
  })

  it('muestra estados y canales en castellano simple', () => {
    assert.deepEqual(estadoEnvio('enviado'), ['Enviado', 'estado-confirmada'])
    assert.equal(estadoEnvio('reintentando')[0], 'Reintentando')
    assert.equal(estadoEnvio('fallido')[0], 'Falló')
    assert.equal(estadoEnvio('omitido')[0], 'No enviado')
    assert.equal(nombreCanal('whatsapp'), 'WhatsApp')
    assert.match(textoCanal({ origen: 'ninguno' }), /pestaña Correo/)
    assert.equal(textoCanal({ origen: 'buzon', etiqueta: 'avisos', remitente: 'r@hotel.cl' }), 'Los avisos salen desde el buzón «avisos» (r@hotel.cl).')
  })

  it('la pestaña vive dentro de Configuración, sin JSON crudo y con formato chileno', () => {
    const src = readFileSync(new URL('../app/hotel/_componentes/ajustes-avisos.js', import.meta.url), 'utf8')
    const pagina = readFileSync(new URL('../app/hotel/configuracion/page.js', import.meta.url), 'utf8')
    assert.match(pagina, /seccion === 'avisos' && <AjustesAvisos \/>/)
    assert.doesNotMatch(src, /JSON\.stringify|SalidaJson|<pre/)
    assert.match(src, /fechaHora/)
    assert.match(src, /Enviar correo de prueba/)
  })
})
