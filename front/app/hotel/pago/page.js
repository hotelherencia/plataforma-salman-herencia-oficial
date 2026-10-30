'use client'

import { useState } from 'react'
import { api, MarcoHotel, SalidaJson, Campo, CampoSelect, useClaveOperacion } from '../../../lib/api'

export default function Pago() {
  const [campos, setCampos] = useState({
    reserva_id: '',
    monto_clp: '100000',
    clave: 'cobro-web-1',
    modo: 'manual',
  })
  const [salida, setSalida] = useState(null)
  const [error, setError] = useState('')
  const [aviso503, setAviso503] = useState(false)
  const [clave, renovarClave] = useClaveOperacion()

  async function cobrar(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    setAviso503(false)
    try {
      const r = await api(`/hotel/reservas/${campos.reserva_id}/pagos`, {
        metodo: 'POST',
        claveIdempotencia: clave,
        cuerpo: { monto_clp: Number(campos.monto_clp), clave: campos.clave, modo: campos.modo },
      })
      if (r.estado === 503) setAviso503(true)
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else {
        setSalida(r.datos)
        renovarClave()
      }
    } catch {
      setError('La API no está disponible')
    }
  }

  return (
    <MarcoHotel titulo="Pago">
      <section className="tarjeta">
        <form className="formulario" onSubmit={cobrar}>
          <Campo etiqueta="Reserva" value={campos.reserva_id} onChange={(e) => setCampos({ ...campos, reserva_id: e.target.value })} />
          <Campo etiqueta="Monto (CLP)" type="number" value={campos.monto_clp} onChange={(e) => setCampos({ ...campos, monto_clp: e.target.value })} />
          <Campo etiqueta="Clave del cobro" value={campos.clave} onChange={(e) => setCampos({ ...campos, clave: e.target.value })} />
          <CampoSelect etiqueta="Modo" value={campos.modo} onChange={(e) => setCampos({ ...campos, modo: e.target.value })}>
            <option value="manual">Manual de caja (efectivo/transferencia)</option>
            <option value="pasarela">Pasarela (no configurada)</option>
          </CampoSelect>
          <button type="submit" className="boton-primario">Registrar pago</button>
        </form>
      </section>
      <p className="nota-clave">Clave de idempotencia (reintenta con la misma para no duplicar): <code>{clave}</code></p>
      <button onClick={() => { setSalida(null); setError(''); setAviso503(false); renovarClave() }} className="boton-secundario">Nueva operación</button>
      {aviso503 && <p role="alert" className="alerta">La pasarela no está configurada: nada quedó marcado como cobrado.</p>}
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
