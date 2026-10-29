'use client'

import { useState } from 'react'
import { api, MarcoHotel, SalidaJson, Campo, CampoSelect } from '../../../lib/api'

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
  const [clave, setClave] = useState('')

  async function cobrar(e) {
    e.preventDefault()
    setError('')
    setSalida(null)
    setAviso503(false)
    const nuevaClave = crypto.randomUUID()
    setClave(nuevaClave)
    try {
      const r = await api(`/hotel/reservas/${campos.reserva_id}/pagos`, {
        metodo: 'POST',
        claveIdempotencia: nuevaClave,
        cuerpo: { monto_clp: Number(campos.monto_clp), clave: campos.clave, modo: campos.modo },
      })
      if (r.estado === 503) setAviso503(true)
      if (r.estado >= 400) setError(JSON.stringify(r.datos))
      else setSalida(r.datos)
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
      {clave && <p className="nota-clave">Clave de idempotencia: <code>{clave}</code></p>}
      {aviso503 && <p role="alert" className="alerta">La pasarela no está configurada: nada quedó marcado como cobrado.</p>}
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />
    </MarcoHotel>
  )
}
