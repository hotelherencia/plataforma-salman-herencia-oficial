'use client'

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  api, mensajeDeError, MarcoHotel, Campo, CampoSelect, useClaveOperacion, useSesion, clp, alRechazar, SalidaJson,
} from '../../../lib/api'
import { tasaTexto } from '../../../lib/iva'
import { PESTANAS_CONFIGURACION } from '../../../lib/menu-hotel'
import MantenedorTiposPrecios from '../_componentes/mantenedor-tipos-precios'
import AjustesReservasWeb from '../_componentes/ajustes-reservas-web'
import AjustesCorreo from '../_componentes/ajustes-correo'

const ETIQUETA_CONF = {
  confirmado: 'Confirmado',
  pendiente_confirmar: 'Pendiente de confirmar',
  no_definido: 'No definido',
}

function BadgeConfirmacion({ valor }) {
  if (!valor || valor === 'confirmado') return null
  return (
    <span className={`politica-badge politica-badge-${valor === 'pendiente_confirmar' ? 'pendiente' : 'indefinido'}`}>
      {ETIQUETA_CONF[valor] || valor}
    </span>
  )
}

function SelectConfirmacion({ valor, onChange, id }) {
  return (
    <CampoSelect id={id} etiqueta="Estado de confirmación" value={valor || 'no_definido'} onChange={(e) => onChange(e.target.value)}>
      <option value="confirmado">Confirmado</option>
      <option value="pendiente_confirmar">Pendiente de confirmar</option>
      <option value="no_definido">No definido</option>
    </CampoSelect>
  )
}

function ConfiguracionHotel() {
  const sesion = useSesion()
  const router = useRouter()
  const params = useSearchParams()
  const seccion = PESTANAS_CONFIGURACION.some(([id]) => id === params.get('seccion')) ? params.get('seccion') : 'tipos'

  function irA(id) {
    router.replace(`/hotel/configuracion?seccion=${id}`, { scroll: false })
  }

  return (
    <MarcoHotel titulo="Configuración del hotel">
      <p className="nota-clave">
        Aquí se define cómo opera <strong>Hotel Herencia</strong>: tipos de habitación, precios (IVA incluido),
        políticas de Llegada y Salida, y las preguntas frecuentes que ve el huésped. Un solo lugar, para no
        duplicar información.
      </p>
      <nav className="subnav subnav-config" aria-label="Secciones de la configuración">
        {PESTANAS_CONFIGURACION.map(([id, nombre]) => (
          <Link
            key={id}
            href={`/hotel/configuracion?seccion=${id}`}
            onClick={(e) => { e.preventDefault(); irA(id) }}
            aria-current={seccion === id ? 'page' : undefined}
            className={seccion === id ? 'subnav-enlace activo' : 'subnav-enlace'}
          >
            {nombre}
          </Link>
        ))}
      </nav>
      {(seccion === 'tipos' || seccion === 'precios') && (
        <MantenedorTiposPrecios seccion={seccion} sinMarco />
      )}
      {(seccion === 'politicas' || seccion === 'faq') && (
        <EditorPoliticas sesion={sesion} seccion={seccion} />
      )}
      {seccion === 'reservas_web' && <AjustesReservasWeb />}
      {seccion === 'correo' && <AjustesCorreo />}
    </MarcoHotel>
  )
}

function EditorPoliticas({ sesion, seccion }) {
  const [doc, setDoc] = useState(null)
  const [cuerpo, setCuerpo] = useState(null)
  const [error, setError] = useState('')
  const [salida, setSalida] = useState(null)
  const [clave, renovar] = useClaveOperacion()

  const cargar = useCallback(async () => {
    try {
      const r = await api('/hotel/politicas')
      if (r.estado === 200) {
        setDoc(r.datos)
        setCuerpo(JSON.parse(JSON.stringify(r.datos.cuerpo)))
        setError('')
      } else {
        setError(mensajeDeError(r.datos, r.estado))
      }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }, [])

  useEffect(() => {
    if (sesion.fase === 'ok') cargar()
  }, [sesion.fase, cargar])

  const puedeEditar = Boolean(doc?.puede_editar)

  async function guardar(e) {
    e.preventDefault()
    setError('')
    try {
      const r = await api('/hotel/politicas', {
        metodo: 'PUT', cuerpo: { cuerpo }, claveIdempotencia: clave,
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        return
      }
      setSalida(r.datos)
      setDoc(r.datos)
      setCuerpo(JSON.parse(JSON.stringify(r.datos.cuerpo)))
      renovar()
    } catch (err) {
      alRechazar(err, setError)
    }
  }

  function setRuta(ruta, valor) {
    setCuerpo((prev) => {
      const next = JSON.parse(JSON.stringify(prev))
      const partes = ruta.split('.')
      let nodo = next
      for (let i = 0; i < partes.length - 1; i += 1) nodo = nodo[partes[i]]
      nodo[partes[partes.length - 1]] = valor
      return next
    })
  }

  if (!cuerpo) return <p className="estado" role="status" aria-busy="true">Cargando políticas…</p>

  return (
    <>
      {doc?.pendientes?.length > 0 && (
        <p className="politica-aviso-pendientes" role="note">
          Hay {doc.pendientes.length} dato{doc.pendientes.length === 1 ? '' : 's'} pendiente
          {doc.pendientes.length === 1 ? '' : 's'} de confirmar o aún no definido
          {doc.pendientes.length === 1 ? '' : 's'}. Aparecen resaltados para que el administrador del hotel los revise.
          No se publican como hechos confirmados.
        </p>
      )}
      {error && <p role="alert" className="alerta">{error}</p>}
      <SalidaJson datos={salida} />

      {seccion === 'politicas' && (
        <div className="politicas-layout">
          <form className="tarjeta politicas-formulario" onSubmit={guardar}>
            <Horarios cuerpo={cuerpo} setRuta={setRuta} puedeEditar={puedeEditar} />
            <Cancelacion cuerpo={cuerpo} setRuta={setRuta} puedeEditar={puedeEditar} />
            <BloqueDeposito cuerpo={cuerpo} setRuta={setRuta} puedeEditar={puedeEditar} />
            <BloquesVarios cuerpo={cuerpo} setRuta={setRuta} puedeEditar={puedeEditar} />
            <Registro cuerpo={cuerpo} setCuerpo={setCuerpo} puedeEditar={puedeEditar} />
            {puedeEditar ? (
              <p className="acciones">
                <button type="submit" className="boton-principal">Guardar políticas</button>
              </p>
            ) : (
              <p className="tipos-solo-lectura" role="note">Solo lectura: las políticas las edita la administración del hotel.</p>
            )}
          </form>
          <aside className="politicas-lado">
            <VistaHuesped cuerpo={cuerpo} texto={doc.texto_cancelacion} />
            <CalculadoraPolitica tasa={Number(doc.iva?.porcentaje ?? 19)} />
          </aside>
        </div>
      )}

      {seccion === 'faq' && (
        <EditorFaq
          cuerpo={cuerpo}
          setCuerpo={setCuerpo}
          puedeEditar={puedeEditar}
          onGuardar={guardar}
        />
      )}
    </>
  )
}

function Horarios({ cuerpo, setRuta, puedeEditar }) {
  const l = cuerpo.llegada_salida || {}
  const ant = l.llegada_anticipada || {}
  const tar = l.salida_tardia || {}
  const ro = !puedeEditar
  return (
    <fieldset className={l.confirmacion !== 'confirmado' ? 'politica-bloque pendiente' : 'politica-bloque'}>
      <legend>Llegada y Salida <BadgeConfirmacion valor={l.confirmacion} /></legend>
      {l.nota_confirmacion && <p className="nota">{l.nota_confirmacion}</p>}
      <div className="politicas-fila">
        <Campo id="hora-llegada" etiqueta="Hora de llegada (desde)" type="time" value={l.hora_llegada_desde || ''} disabled={ro} onChange={(e) => setRuta('llegada_salida.hora_llegada_desde', e.target.value || null)} />
        <Campo id="hora-salida" etiqueta="Hora de salida (hasta)" type="time" value={l.hora_salida_hasta || ''} disabled={ro} onChange={(e) => setRuta('llegada_salida.hora_salida_hasta', e.target.value || null)} />
        <SelectConfirmacion id="conf-horarios" valor={l.confirmacion} onChange={(v) => setRuta('llegada_salida.confirmacion', v)} />
      </div>
      <h3>Llegada anticipada</h3>
      <RecargoEditable prefijo="llegada_salida.llegada_anticipada" bloque={ant} setRuta={setRuta} ro={ro} />
      <h3>Salida tardía</h3>
      <RecargoEditable prefijo="llegada_salida.salida_tardia" bloque={tar} setRuta={setRuta} ro={ro} />
    </fieldset>
  )
}

function RecargoEditable({ prefijo, bloque, setRuta, ro }) {
  const recargo = bloque.recargo || { modo: 'monto_clp', valor: '', por: 'hora' }
  return (
    <div className={bloque.confirmacion !== 'confirmado' ? 'politica-subbloque pendiente' : 'politica-subbloque'}>
      <div className="politicas-fila">
        <CampoSelect id={`${prefijo}-perm`} etiqueta="¿Permitida?" value={bloque.permitida === true ? 'si' : bloque.permitida === false ? 'no' : ''} disabled={ro} onChange={(e) => setRuta(`${prefijo}.permitida`, e.target.value === '' ? null : e.target.value === 'si')}>
          <option value="">Sin definir</option>
          <option value="si">Sí</option>
          <option value="no">No</option>
        </CampoSelect>
        <Campo id={`${prefijo}-limite`} etiqueta="Hora límite (opcional)" type="time" value={bloque.hora_limite || ''} disabled={ro} onChange={(e) => setRuta(`${prefijo}.hora_limite`, e.target.value || null)} />
        <CampoSelect id={`${prefijo}-modo`} etiqueta="Recargo" value={recargo.modo || 'monto_clp'} disabled={ro} onChange={(e) => setRuta(`${prefijo}.recargo`, { ...recargo, modo: e.target.value })}>
          <option value="monto_clp">Monto en CLP (IVA incluido)</option>
          <option value="porcentaje_noche">Porcentaje de la noche</option>
        </CampoSelect>
        <Campo id={`${prefijo}-valor`} etiqueta={recargo.modo === 'porcentaje_noche' ? 'Porcentaje' : 'Monto CLP'} type="number" min="0" value={recargo.valor ?? ''} disabled={ro} onChange={(e) => setRuta(`${prefijo}.recargo`, { ...recargo, valor: e.target.value === '' ? 0 : Number(e.target.value) })} />
        <CampoSelect id={`${prefijo}-por`} etiqueta="Se cobra por" value={recargo.por || 'hora'} disabled={ro} onChange={(e) => setRuta(`${prefijo}.recargo`, { ...recargo, por: e.target.value })}>
          <option value="hora">Hora</option>
          <option value="noche">Noche</option>
          <option value="estadia">Estadía</option>
        </CampoSelect>
        <SelectConfirmacion id={`${prefijo}-conf`} valor={bloque.confirmacion} onChange={(v) => setRuta(`${prefijo}.confirmacion`, v)} />
      </div>
    </div>
  )
}

function Cancelacion({ cuerpo, setRuta, puedeEditar }) {
  const c = cuerpo.cancelacion || {}
  const ns = cuerpo.no_show || {}
  const ro = !puedeEditar
  return (
    <>
      <fieldset className={c.confirmacion !== 'confirmado' ? 'politica-bloque pendiente' : 'politica-bloque'}>
        <legend>Cancelación <BadgeConfirmacion valor={c.confirmacion} /></legend>
        {c.nota_confirmacion && <p className="nota">{c.nota_confirmacion}</p>}
        <div className="politicas-fila">
          <Campo id="horas-gratis" etiqueta="Horas de antelación sin cargo" type="number" min="0" value={c.horas_antelacion_gratis ?? ''} disabled={ro} onChange={(e) => setRuta('cancelacion.horas_antelacion_gratis', e.target.value === '' ? null : Number(e.target.value))} />
          <CampoSelect id="penalidad" etiqueta="Penalidad después" value={c.penalidad_tipo || ''} disabled={ro} onChange={(e) => setRuta('cancelacion.penalidad_tipo', e.target.value || null)}>
            <option value="">Sin definir</option>
            <option value="primera_noche">Primera noche</option>
            <option value="porcentaje">Porcentaje</option>
            <option value="monto">Monto fijo (CLP)</option>
          </CampoSelect>
          {(c.penalidad_tipo === 'porcentaje' || c.penalidad_tipo === 'monto') && (
            <Campo id="penalidad-valor" etiqueta={c.penalidad_tipo === 'porcentaje' ? 'Porcentaje' : 'Monto CLP'} type="number" min="0" value={c.penalidad_valor ?? ''} disabled={ro} onChange={(e) => setRuta('cancelacion.penalidad_valor', e.target.value === '' ? null : Number(e.target.value))} />
          )}
          <SelectConfirmacion id="conf-cancel" valor={c.confirmacion} onChange={(v) => setRuta('cancelacion.confirmacion', v)} />
        </div>
        <Campo id="texto-cancel" etiqueta="Texto visible para el huésped" value={c.texto_visible || ''} disabled={ro} onChange={(e) => setRuta('cancelacion.texto_visible', e.target.value || null)} />
      </fieldset>
      <fieldset className={ns.confirmacion !== 'confirmado' ? 'politica-bloque pendiente' : 'politica-bloque'}>
        <legend>No-show <BadgeConfirmacion valor={ns.confirmacion} /></legend>
        {ns.nota_confirmacion && <p className="nota">{ns.nota_confirmacion}</p>}
        <div className="politicas-fila">
          <CampoSelect id="ns-tipo" etiqueta="Penalidad" value={ns.penalidad_tipo || ''} disabled={ro} onChange={(e) => setRuta('no_show.penalidad_tipo', e.target.value || null)}>
            <option value="">Sin definir</option>
            <option value="primera_noche">Primera noche</option>
            <option value="porcentaje">Porcentaje</option>
            <option value="monto">Monto fijo (CLP)</option>
          </CampoSelect>
          <SelectConfirmacion id="conf-ns" valor={ns.confirmacion} onChange={(v) => setRuta('no_show.confirmacion', v)} />
        </div>
        <Campo id="texto-ns" etiqueta="Texto visible (opcional)" value={ns.texto_visible || ''} disabled={ro} onChange={(e) => setRuta('no_show.texto_visible', e.target.value || null)} />
      </fieldset>
    </>
  )
}

function BloqueDeposito({ cuerpo, setRuta, puedeEditar }) {
  const d = cuerpo.deposito || {}
  const m = cuerpo.minimo_noches || {}
  const ro = !puedeEditar
  return (
    <>
      <fieldset className="politica-bloque">
        <legend>Depósito o garantía <BadgeConfirmacion valor={d.confirmacion} /></legend>
        {d.nota && <p className="nota">{d.nota}</p>}
        <div className="politicas-fila">
          <CampoSelect id="dep-exigido" etiqueta="¿Se exige abono previo?" value={d.exigido === true ? 'si' : d.exigido === false ? 'no' : ''} disabled={ro} onChange={(e) => setRuta('deposito.exigido', e.target.value === '' ? null : e.target.value === 'si')}>
            <option value="">Sin definir</option>
            <option value="si">Sí</option>
            <option value="no">No</option>
          </CampoSelect>
          <Campo id="dep-deleg" etiqueta="% en delegaciones (excepción)" type="number" min="0" max="100" value={d.excepcion_delegaciones_porcentaje ?? ''} disabled={ro} onChange={(e) => setRuta('deposito.excepcion_delegaciones_porcentaje', e.target.value === '' ? null : Number(e.target.value))} />
          <SelectConfirmacion id="conf-dep" valor={d.confirmacion} onChange={(v) => setRuta('deposito.confirmacion', v)} />
        </div>
      </fieldset>
      <fieldset className={m.confirmacion !== 'confirmado' ? 'politica-bloque pendiente' : 'politica-bloque'}>
        <legend>Mínimo de noches <BadgeConfirmacion valor={m.confirmacion} /></legend>
        {m.nota_confirmacion && <p className="nota">{m.nota_confirmacion}</p>}
        <div className="politicas-fila">
          <Campo id="min-noches" etiqueta="Noches mínimas (opcional)" type="number" min="1" value={m.noches ?? ''} disabled={ro} onChange={(e) => setRuta('minimo_noches.noches', e.target.value === '' ? null : Number(e.target.value))} />
          <SelectConfirmacion id="conf-min" valor={m.confirmacion} onChange={(v) => setRuta('minimo_noches.confirmacion', v)} />
        </div>
      </fieldset>
    </>
  )
}

function BloquesVarios({ cuerpo, setRuta, puedeEditar }) {
  const n = cuerpo.ninos_cama || {}
  const mas = cuerpo.mascotas || {}
  const des = cuerpo.desayuno || {}
  const est = cuerpo.estacionamiento || {}
  const pag = cuerpo.medios_pago || {}
  const ro = !puedeEditar
  return (
    <>
      <fieldset className={n.confirmacion !== 'confirmado' ? 'politica-bloque pendiente' : 'politica-bloque'}>
        <legend>Niños y cama adicional <BadgeConfirmacion valor={n.confirmacion} /></legend>
        {n.nota_confirmacion && <p className="nota">{n.nota_confirmacion}</p>}
        <div className="politicas-fila">
          <Campo id="edad-nino" etiqueta="Edad de niño hasta (años)" type="number" min="0" value={n.edad_nino_hasta ?? ''} disabled={ro} onChange={(e) => setRuta('ninos_cama.edad_nino_hasta', e.target.value === '' ? null : Number(e.target.value))} />
          <CampoSelect id="cama-perm" etiqueta="¿Cama adicional?" value={n.cama_adicional_permitida === true ? 'si' : n.cama_adicional_permitida === false ? 'no' : ''} disabled={ro} onChange={(e) => setRuta('ninos_cama.cama_adicional_permitida', e.target.value === '' ? null : e.target.value === 'si')}>
            <option value="">Sin definir</option>
            <option value="si">Sí</option>
            <option value="no">No</option>
          </CampoSelect>
          <SelectConfirmacion id="conf-ninos" valor={n.confirmacion} onChange={(v) => setRuta('ninos_cama.confirmacion', v)} />
        </div>
      </fieldset>
      <fieldset className={mas.confirmacion !== 'confirmado' ? 'politica-bloque pendiente' : 'politica-bloque'}>
        <legend>Mascotas <BadgeConfirmacion valor={mas.confirmacion} /></legend>
        {mas.nota_confirmacion && <p className="nota">{mas.nota_confirmacion}</p>}
        <div className="politicas-fila">
          <CampoSelect id="mas-si" etiqueta="¿Se aceptan?" value={mas.se_aceptan === true ? 'si' : mas.se_aceptan === false ? 'no' : ''} disabled={ro} onChange={(e) => setRuta('mascotas.se_aceptan', e.target.value === '' ? null : e.target.value === 'si')}>
            <option value="">Sin definir</option>
            <option value="si">Sí</option>
            <option value="no">No</option>
          </CampoSelect>
          <SelectConfirmacion id="conf-mas" valor={mas.confirmacion} onChange={(v) => setRuta('mascotas.confirmacion', v)} />
        </div>
      </fieldset>
      <fieldset className="politica-bloque">
        <legend>Desayuno <BadgeConfirmacion valor={des.confirmacion} /></legend>
        {des.nota && <p className="nota">{des.nota}</p>}
        <div className="politicas-fila">
          <CampoSelect id="des-inc" etiqueta="¿Incluido?" value={des.incluido === true ? 'si' : des.incluido === false ? 'no' : ''} disabled={ro} onChange={(e) => setRuta('desayuno.incluido', e.target.value === '' ? null : e.target.value === 'si')}>
            <option value="">Sin definir</option>
            <option value="si">Sí</option>
            <option value="no">No</option>
          </CampoSelect>
          <Campo id="des-tipo" etiqueta="Tipo" value={des.tipo || ''} disabled={ro} onChange={(e) => setRuta('desayuno.tipo', e.target.value || null)} />
          <Campo id="des-desde" etiqueta="Horario desde" type="time" value={des.horario_desde || ''} disabled={ro} onChange={(e) => setRuta('desayuno.horario_desde', e.target.value || null)} />
          <Campo id="des-hasta" etiqueta="Horario hasta" type="time" value={des.horario_hasta || ''} disabled={ro} onChange={(e) => setRuta('desayuno.horario_hasta', e.target.value || null)} />
        </div>
      </fieldset>
      <fieldset className={est.confirmacion !== 'confirmado' ? 'politica-bloque pendiente' : 'politica-bloque'}>
        <legend>Estacionamiento <BadgeConfirmacion valor={est.confirmacion} /></legend>
        {est.nota_confirmacion && <p className="nota">{est.nota_confirmacion}</p>}
        <div className="politicas-fila">
          <CampoSelect id="est-disp" etiqueta="¿Disponible?" value={est.disponible === true ? 'si' : est.disponible === false ? 'no' : ''} disabled={ro} onChange={(e) => setRuta('estacionamiento.disponible', e.target.value === '' ? null : e.target.value === 'si')}>
            <option value="">Sin definir</option>
            <option value="si">Sí</option>
            <option value="no">No</option>
          </CampoSelect>
          <CampoSelect id="est-costo" etiqueta="¿Tiene costo?" value={est.con_costo === true ? 'si' : est.con_costo === false ? 'no' : ''} disabled={ro} onChange={(e) => setRuta('estacionamiento.con_costo', e.target.value === '' ? null : e.target.value === 'si')}>
            <option value="">Sin definir</option>
            <option value="si">Sí</option>
            <option value="no">No</option>
          </CampoSelect>
          <SelectConfirmacion id="conf-est" valor={est.confirmacion} onChange={(v) => setRuta('estacionamiento.confirmacion', v)} />
        </div>
      </fieldset>
      <fieldset className="politica-bloque">
        <legend>Medios de pago <BadgeConfirmacion valor={pag.confirmacion} /></legend>
        <Campo id="medios" etiqueta="Medios (separados por coma)" value={(pag.medios || []).join(', ')} disabled={ro} onChange={(e) => setRuta('medios_pago.medios', e.target.value.split(',').map((s) => s.trim()).filter(Boolean))} />
      </fieldset>
    </>
  )
}

function Registro({ cuerpo, setCuerpo, puedeEditar }) {
  const ro = !puedeEditar
  const llegada = cuerpo.registro_llegada || { datos: [], pasos: [] }
  const salida = cuerpo.registro_salida || { pasos: [] }

  function setPaso(cual, i, texto) {
    setCuerpo((prev) => {
      const next = JSON.parse(JSON.stringify(prev))
      next[cual].pasos[i].texto = texto
      return next
    })
  }
  function addPaso(cual) {
    setCuerpo((prev) => {
      const next = JSON.parse(JSON.stringify(prev))
      const pasos = next[cual].pasos || []
      pasos.push({ orden: pasos.length + 1, texto: '' })
      next[cual].pasos = pasos
      return next
    })
  }
  function setDato(i, campo, valor) {
    setCuerpo((prev) => {
      const next = JSON.parse(JSON.stringify(prev))
      next.registro_llegada.datos[i][campo] = valor
      return next
    })
  }

  return (
    <>
      <fieldset className="politica-bloque">
        <legend>Registro de Llegada</legend>
        {llegada.nota && <p className="nota">{llegada.nota}</p>}
        <h3>Datos que se piden</h3>
        <ul className="politicas-lista">
          {(llegada.datos || []).map((dato, i) => (
            <li key={dato.clave || i}>
              <strong>{dato.etiqueta}</strong>
              {dato.exigido ? ' (obligatorio)' : ' (opcional)'}
              {' · '}
              <label>
                <input type="checkbox" checked={Boolean(dato.publico)} disabled={ro} onChange={(e) => setDato(i, 'publico', e.target.checked)} />
                {' '}Visible para el huésped
              </label>
              <BadgeConfirmacion valor={dato.confirmacion} />
              {dato.nota && <p className="nota">{dato.nota}</p>}
            </li>
          ))}
        </ul>
        <h3>Pasos</h3>
        {(llegada.pasos || []).map((paso, i) => (
          <Campo key={`l-${paso.orden}`} id={`paso-l-${i}`} etiqueta={`Paso ${paso.orden}`} value={paso.texto} disabled={ro} onChange={(e) => setPaso('registro_llegada', i, e.target.value)} />
        ))}
        {puedeEditar && <button type="button" className="boton-secundario" onClick={() => addPaso('registro_llegada')}>Agregar paso de llegada</button>}
      </fieldset>
      <fieldset className="politica-bloque">
        <legend>Registro de Salida</legend>
        {salida.nota && <p className="nota">{salida.nota}</p>}
        {(salida.pasos || []).map((paso, i) => (
          <Campo key={`s-${paso.orden}`} id={`paso-s-${i}`} etiqueta={`Paso ${paso.orden}`} value={paso.texto} disabled={ro} onChange={(e) => setPaso('registro_salida', i, e.target.value)} />
        ))}
        {puedeEditar && <button type="button" className="boton-secundario" onClick={() => addPaso('registro_salida')}>Agregar paso de salida</button>}
      </fieldset>
    </>
  )
}

function VistaHuesped({ cuerpo, texto }) {
  const l = cuerpo.llegada_salida || {}
  const des = cuerpo.desayuno || {}
  const est = cuerpo.estacionamiento || {}
  const pag = cuerpo.medios_pago || {}
  return (
    <section className="tarjeta vista-huesped">
      <h2>Vista previa para el huésped</h2>
      <p className="nota">Así se verían los datos públicos. Lo pendiente no se afirma como hecho.</p>
      <dl>
        <div>
          <dt>Llegada</dt>
          <dd>
            {l.hora_llegada_desde ? `desde las ${l.hora_llegada_desde}` : 'Por confirmar'}
            <BadgeConfirmacion valor={l.confirmacion} />
          </dd>
        </div>
        <div>
          <dt>Salida</dt>
          <dd>{l.hora_salida_hasta ? `hasta las ${l.hora_salida_hasta}` : 'Por confirmar'}</dd>
        </div>
        <div>
          <dt>Cancelación</dt>
          <dd>
            {texto || 'Se confirma en recepción'}
            <BadgeConfirmacion valor={cuerpo.cancelacion?.confirmacion} />
          </dd>
        </div>
        <div>
          <dt>Desayuno</dt>
          <dd>{des.incluido ? `Incluido${des.tipo ? ` (${des.tipo})` : ''}` : 'Por confirmar'}</dd>
        </div>
        <div>
          <dt>Estacionamiento</dt>
          <dd>
            {est.disponible ? 'Disponible' : est.disponible === false ? 'No disponible' : 'Por confirmar'}
            {est.con_costo == null && est.disponible ? ' (no está confirmado si tiene costo)' : ''}
            <BadgeConfirmacion valor={est.confirmacion} />
          </dd>
        </div>
        <div>
          <dt>Medios de pago</dt>
          <dd>{(pag.medios || []).join(', ') || 'Por confirmar'}</dd>
        </div>
      </dl>
    </section>
  )
}

function CalculadoraPolitica({ tasa }) {
  const hoy = useMemo(() => {
    const d = new Date()
    const iso = (n) => {
      const x = new Date(d)
      x.setDate(x.getDate() + n)
      return x.toISOString().slice(0, 10)
    }
    return { inicio: iso(3), fin: iso(5) }
  }, [])
  const [form, setForm] = useState({
    inicio: hoy.inicio, fin: hoy.fin, hora_llegada: '11:00', hora_salida: '14:00', precio_noche_clp: '55000',
  })
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState('')

  async function calcular(e) {
    e.preventDefault()
    setError('')
    try {
      const r = await api('/hotel/politicas/simulacion', {
        metodo: 'POST',
        cuerpo: {
          inicio: form.inicio,
          fin: form.fin,
          hora_llegada: form.hora_llegada || null,
          hora_salida: form.hora_salida || null,
          precio_noche_clp: Number(form.precio_noche_clp),
        },
      })
      if (r.estado >= 400) {
        setError(mensajeDeError(r.datos, r.estado))
        setResultado(null)
        return
      }
      setResultado(r.datos)
    } catch {
      setError('No se pudo calcular')
    }
  }

  const s = resultado?.simulacion
  const d = s?.desglose

  return (
    <section className="tarjeta calculadora-politica">
      <h2>Calculadora de ejemplo</h2>
      <p className="nota">Fechas y horas de Llegada/Salida → total con recargos e IVA ({tasaTexto(tasa)} %).</p>
      <form onSubmit={calcular} className="politicas-fila">
        <Campo id="sim-inicio" etiqueta="Llegada (fecha)" type="date" value={form.inicio} onChange={(e) => setForm({ ...form, inicio: e.target.value })} />
        <Campo id="sim-fin" etiqueta="Salida (fecha)" type="date" value={form.fin} onChange={(e) => setForm({ ...form, fin: e.target.value })} />
        <Campo id="sim-hl" etiqueta="Hora de llegada" type="time" value={form.hora_llegada} onChange={(e) => setForm({ ...form, hora_llegada: e.target.value })} />
        <Campo id="sim-hs" etiqueta="Hora de salida" type="time" value={form.hora_salida} onChange={(e) => setForm({ ...form, hora_salida: e.target.value })} />
        <Campo id="sim-precio" etiqueta="Precio por noche de ejemplo (IVA incl.)" type="number" min="1" value={form.precio_noche_clp} onChange={(e) => setForm({ ...form, precio_noche_clp: e.target.value })} />
        <p className="acciones"><button type="submit" className="boton-principal">Calcular</button></p>
      </form>
      {error && <p role="alert" className="alerta">{error}</p>}
      {s && (
        <dl className="tipos-totales">
          <div><dt>Noches</dt><dd>{resultado.noches}</dd></div>
          <div><dt>Alojamiento</dt><dd>{clp(s.subtotal_noches_clp)}</dd></div>
          {(s.recargos || []).map((r) => (
            <div key={r.concepto}><dt>{r.detalle}</dt><dd>{clp(r.monto_clp)}</dd></div>
          ))}
          <div><dt>Total (IVA incl.)</dt><dd>{clp(s.total_clp)}</dd></div>
          {d && (
            <>
              <div><dt>Neto</dt><dd>{clp(d.neto)}</dd></div>
              <div><dt>IVA</dt><dd>{clp(d.iva)}</dd></div>
            </>
          )}
        </dl>
      )}
    </section>
  )
}

function EditorFaq({ cuerpo, setCuerpo, puedeEditar, onGuardar }) {
  const faq = cuerpo.faq || []
  function setItem(i, campo, valor) {
    setCuerpo((prev) => {
      const next = JSON.parse(JSON.stringify(prev))
      next.faq[i][campo] = valor
      return next
    })
  }
  function agregar() {
    setCuerpo((prev) => {
      const next = JSON.parse(JSON.stringify(prev))
      const n = (next.faq || []).length + 1
      next.faq = [...(next.faq || []), {
        id: `FAQ-${String(n).padStart(2, '0')}`,
        pregunta: '',
        respuesta: '',
        publica: true,
        confirmacion: 'confirmado',
      }]
      return next
    })
  }
  function quitar(i) {
    setCuerpo((prev) => {
      const next = JSON.parse(JSON.stringify(prev))
      next.faq.splice(i, 1)
      return next
    })
  }
  return (
    <form className="tarjeta" onSubmit={onGuardar}>
      <p className="nota">Preguntas y respuestas editables. Las públicas aparecen en la vista del huésped y las usa el agente.</p>
      {faq.map((item, i) => (
        <fieldset key={item.id || i} className={item.confirmacion !== 'confirmado' ? 'politica-bloque pendiente' : 'politica-bloque'}>
          <legend>{item.id || `FAQ ${i + 1}`} <BadgeConfirmacion valor={item.confirmacion} /></legend>
          <Campo id={`faq-p-${i}`} etiqueta="Pregunta" value={item.pregunta} disabled={!puedeEditar} onChange={(e) => setItem(i, 'pregunta', e.target.value)} />
          <label className="campo" htmlFor={`faq-r-${i}`}>
            <span>Respuesta</span>
            <textarea id={`faq-r-${i}`} rows="3" value={item.respuesta} disabled={!puedeEditar} onChange={(e) => setItem(i, 'respuesta', e.target.value)} />
          </label>
          <div className="politicas-fila">
            <label>
              <input type="checkbox" checked={Boolean(item.publica)} disabled={!puedeEditar} onChange={(e) => setItem(i, 'publica', e.target.checked)} />
              {' '}Pública
            </label>
            <SelectConfirmacion id={`faq-c-${i}`} valor={item.confirmacion} onChange={(v) => setItem(i, 'confirmacion', v)} />
            {puedeEditar && <button type="button" className="boton-secundario" onClick={() => quitar(i)}>Quitar</button>}
          </div>
        </fieldset>
      ))}
      {puedeEditar && (
        <p className="acciones">
          <button type="button" className="boton-secundario" onClick={agregar}>Agregar pregunta</button>
          <button type="submit" className="boton-principal">Guardar preguntas frecuentes</button>
        </p>
      )}
    </form>
  )
}


export default function PaginaConfiguracion() {
  return (
    <Suspense fallback={<p className="estado" role="status" aria-busy="true">Cargando configuración…</p>}>
      <ConfiguracionHotel />
    </Suspense>
  )
}
