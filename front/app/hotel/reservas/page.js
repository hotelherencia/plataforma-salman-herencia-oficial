'use client'

import { useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, Campo, CampoSelect, useSesion } from '../../../lib/api'
import { ListaReservas, ReservasVacias } from '../_componentes/lista-reservas'
import { BotonExportar } from '../_componentes/boton-exportar'
import { fechaChile } from '../_componentes/lista-reservas'
import Subnav from '../_componentes/subnav'
import { SUBNAV_RESERVAS } from '../../../lib/menu-hotel'

export default function Reservas() {
  const sesion = useSesion()
  const [filtros, setFiltros] = useState({ desde: '', hasta: '', fecha: '', estado: '', texto: '', habitacion_id: '' })
  const [resultado, setResultado] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState('')

  async function buscar(e) {
    if (e) e.preventDefault()
    setError('')
    setCargando(true)
    const params = new URLSearchParams()
    for (const campo of ['desde', 'hasta', 'fecha', 'estado', 'texto', 'habitacion_id']) {
      if (filtros[campo]) params.set(campo, filtros[campo].trim())
    }
    try {
      const r = await api(`/hotel/reservas?${params}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else setResultado(r.datos)
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    } finally {
      setCargando(false)
    }
  }

  // Al entrar se listan las reservas de la empresa (sin filtros): la página
  // nace con datos; el formulario solo acota lo que ya se ve.
  useEffect(() => {
    if (sesion.fase === 'ok') buscar(null)
  }, [sesion.fase])

  return (
    <MarcoHotel titulo="Buscar reservas">
      <Subnav items={SUBNAV_RESERVAS} />
      <section className="tarjeta">
        <form className="formulario" onSubmit={buscar}>
          <Campo etiqueta="Periodo desde" type="date" value={filtros.desde} onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })} />
          <Campo etiqueta="Periodo hasta (sin incluir)" type="date" value={filtros.hasta} onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })} />
          <Campo etiqueta="Fecha (la noche contiene ese día)" type="date" value={filtros.fecha} onChange={(e) => setFiltros({ ...filtros, fecha: e.target.value })} />
          <Campo etiqueta="Habitación (exacta)" value={filtros.habitacion_id} onChange={(e) => setFiltros({ ...filtros, habitacion_id: e.target.value })} />
          <CampoSelect etiqueta="Estado" value={filtros.estado} onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}>
            <option value="">Todos los estados</option>
            <option value="confirmada">Confirmada</option>
            <option value="en_estadia">En estadía</option>
            <option value="finalizada">Finalizada</option>
            <option value="cancelada">Cancelada</option>
          </CampoSelect>
          <Campo etiqueta="Texto (id, huésped, documento o habitación)" value={filtros.texto} onChange={(e) => setFiltros({ ...filtros, texto: e.target.value })} />
          <button type="submit" className="boton-primario">Buscar</button>
        </form>
        <p className="nota-clave">
          Periodo: lista las reservas que tienen al menos una noche entre «desde» y «hasta». Los filtros se combinan con Y.
          Abre una reserva para ver su cuenta (cargos, pagos y saldo).
        </p>
      </section>
      {error && <p role="alert" className="alerta">{error}</p>}
      {cargando && <p className="estado" role="status" aria-busy="true">Buscando…</p>}
      {resultado &&
        (resultado.reservas.length === 0 ? (
          <ReservasVacias />
        ) : (
          <>
          <div className="acciones-fila" style={{ marginBottom: '0.75rem' }}>
            <BotonExportar
              titulo="Reservas"
              filtros={[filtros.desde && `desde ${filtros.desde}`, filtros.hasta && `hasta ${filtros.hasta}`, filtros.estado && `estado ${filtros.estado}`, filtros.habitacion_id && `hab ${filtros.habitacion_id}`, filtros.texto && `texto ${filtros.texto}`].filter(Boolean).join(', ')}
              columnas={['Reserva', 'Huésped', 'Documento', 'Habitación', 'Llegada', 'Salida', 'Estado', 'Tarifa noche CLP']}
              filas={resultado.reservas.map((r) => [r.reserva_id, r.huesped_nombre, r.huesped_documento || '', r.habitacion_id, fechaChile(r.inicio), fechaChile(r.fin), r.estado, r.tarifa_noche_aceptada_clp])}
              nombreArchivo="herencia-reservas.csv"
            />
          </div>
          <ListaReservas reservas={resultado.reservas} total={resultado.total} alActualizar={() => buscar(null)} />
          </>
        ))}
    </MarcoHotel>
  )
}
