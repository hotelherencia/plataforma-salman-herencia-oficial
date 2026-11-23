'use client'

import { useEffect, useState } from 'react'
import { api, clp, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, Campo, CampoSelect } from '../../../lib/api'
import { esAdminHotel, gestionaClientes } from '../../../lib/roles'
import { rutValido } from '../../../lib/contabilidad'
import FormularioEdicion from '../_componentes/formulario-edicion'
import { BarraContextual, SelectorFila } from '../_componentes/barra-contextual'
import { BotonExportar } from '../_componentes/boton-exportar'
import CuentasPorCobrar, { ETIQUETA_POLITICA } from '../_componentes/cuentas-por-cobrar'
import ConveniosPanel from '../_componentes/convenios-panel'

function validarRutCampo(v) {
  const texto = String(v ?? '').trim()
  if (!texto) return 'RUT es obligatorio.'
  if (!rutValido(texto)) return 'RUT inválido: revisa el formato y el dígito verificador.'
  return undefined
}

const CAMPOS_CLIENTE = [
  { nombre: 'nombre', etiqueta: 'Nombre o razón social', requerido: true },
  { nombre: 'rut', etiqueta: 'RUT', requerido: true, placeholder: '12.345.678-5', validar: validarRutCampo },
  { nombre: 'tipo', etiqueta: 'Tipo', tipo: 'select', opciones: [['empresa', 'Empresa'], ['persona', 'Persona']] },
  { nombre: 'telefono', etiqueta: 'Teléfono', tipo: 'tel', placeholder: '+56 9 1234 5678' },
  { nombre: 'correo', etiqueta: 'Correo', tipo: 'email' },
  { nombre: 'giro', etiqueta: 'Giro' },
  { nombre: 'direccion', etiqueta: 'Dirección' },
  { nombre: 'comuna', etiqueta: 'Comuna' },
  { nombre: 'activo', etiqueta: 'Activo', tipo: 'checkbox' },
]

/** Clientes: selección de cliente activo + barra contextual única (sin repetir
 *  botones de editar/crédito en cada fila). */
export default function Clientes() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [truncado, setTruncado] = useState(false)
  const [texto, setTexto] = useState('')
  const [error, setError] = useState('')
  const [creando, setCreando] = useState(false)
  const [seleccionadoId, setSeleccionadoId] = useState(null)
  const [panelActivo, setPanelActivo] = useState(null) // 'editar' | 'credito' | null
  const [formCredito, setFormCredito] = useState({
    politica_credito: 'pago_al_registrarse',
    cupo_credito_clp: '0',
    plazo_dias: '0',
    garantia_tarjeta_marca: '',
    garantia_tarjeta_ultimos4: '',
  })
  const [aviso, setAviso] = useState('')
  const [claveAlta, renovarClaveAlta] = useClaveOperacion()

  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puede = gestionaClientes(rol)
  const esAdmin = esAdminHotel(rol)
  const puedeVerCxc = esAdmin || rol === 'caja'

  const activo = (lista || []).find((c) => c.id === seleccionadoId) || null

  function elegirCliente(c) {
    setSeleccionadoId(c.id)
    setPanelActivo(null)
    setError('')
  }

  function alternarCredito(c) {
    if (panelActivo === 'credito') {
      setPanelActivo(null)
      return
    }
    setPanelActivo('credito')
    setFormCredito({
      politica_credito: c.politica_credito || 'pago_al_registrarse',
      cupo_credito_clp: String(c.cupo_credito_clp || 0),
      plazo_dias: String(c.plazo_dias || 0),
      garantia_tarjeta_marca: c.garantia_tarjeta_marca || '',
      garantia_tarjeta_ultimos4: c.garantia_tarjeta_ultimos4 || '',
    })
  }

  async function guardarCredito(e, clienteId) {
    e.preventDefault()
    setError('')
    setAviso('')
    try {
      const r = await api(`/hotel/clientes/${encodeURIComponent(clienteId)}/credito`, {
        metodo: 'PUT',
        claveIdempotencia: `cred-${clienteId}-${crypto.randomUUID().slice(0, 8)}`,
        cuerpo: {
          politica_credito: formCredito.politica_credito,
          cupo_credito_clp: Math.max(0, Number(formCredito.cupo_credito_clp) || 0),
          plazo_dias: Math.max(0, Number(formCredito.plazo_dias) || 0),
          garantia_tarjeta_marca: formCredito.garantia_tarjeta_marca.trim() || null,
          garantia_tarjeta_ultimos4: formCredito.garantia_tarjeta_ultimos4.trim() || null,
        },
      })
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else {
        setPanelActivo(null)
        setAviso('Política de crédito actualizada.')
        cargar(texto.trim())
      }
    } catch {
      setError('No se pudo conectar con el servidor.')
    }
  }

  async function cargar(q) {
    setError('')
    try {
      const r = await api(`/hotel/clientes${q ? `?q=${encodeURIComponent(q)}` : ''}`)
      if (r.estado >= 400) setError(mensajeDeError(r.datos, r.estado))
      else { setLista(r.datos.clientes); setTruncado(Boolean(r.datos.truncado)) }
    } catch {
      setError('No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.')
    }
  }

  useEffect(() => {
    if (puede) cargar('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [puede])

  if (sesion.fase === 'ok' && !puede) {
    return (
      <MarcoHotel titulo="Clientes">
        <p className="estado">Los clientes son solo para recepción, caja o la administración del hotel.</p>
      </MarcoHotel>
    )
  }

  return (
    <MarcoHotel titulo="Clientes">
      <section className="tarjeta">
        <form className="filtros" onSubmit={(e) => { e.preventDefault(); setAviso(''); cargar(texto.trim()) }}>
          <Campo etiqueta="Buscar por nombre, RUT, teléfono o correo" value={texto} onChange={(e) => setTexto(e.target.value)} />
          <button type="submit" className="boton-primario">Buscar</button>
          <button
            type="button"
            className="boton-secundario"
            aria-expanded={creando}
            onClick={() => { setCreando((v) => !v); setAviso('') }}
          >
            {creando ? 'Cerrar alta' : 'Nuevo cliente'}
          </button>
          {lista && lista.length > 0 && (
            <BotonExportar
              titulo="Clientes"
              filtros={texto.trim() ? `búsqueda: ${texto.trim()}` : 'todos'}
              columnas={['Nombre o razón social', 'RUT', 'Tipo', 'Teléfono', 'Correo', 'Giro', 'Dirección', 'Comuna', 'Activo']}
              filas={lista.map((c) => [c.nombre, c.rut, c.tipo, c.telefono || '', c.correo || '', c.giro || '', c.direccion || '', c.comuna || '', c.activo])}
              nombreArchivo="herencia-clientes.csv"
            />
          )}
        </form>
        {creando && (
          <div style={{ marginTop: '1rem' }}>
            <h2 className="subtitulo">Alta manual de cliente</h2>
            <FormularioEdicion
              ruta="/hotel/clientes"
              metodo="POST"
              claveIdempotencia={claveAlta}
              etiquetaGuardar="Crear cliente"
              tituloAria="Alta manual de cliente"
              inicial={{ tipo: 'empresa', activo: true }}
              campos={CAMPOS_CLIENTE}
              alErrorEstado={(estado) => alRechazar(estado, renovarClaveAlta)}
              alGuardar={() => {
                setCreando(false)
                renovarClaveAlta()
                setAviso('Cliente creado correctamente.')
                cargar(texto.trim())
              }}
              alCancelar={() => setCreando(false)}
            />
          </div>
        )}
      </section>

      {error && <p role="alert" className="alerta">{error}</p>}
      {aviso && <p role="status" className="aviso-ok">{aviso}</p>}

      {lista && (
        lista.length === 0 ? (
          <p className="estado">No hay clientes que coincidan.</p>
        ) : (
          <>
            <BarraContextual
              titulo="Acciones de cliente"
              seleccionado={Boolean(activo)}
              resumen={activo ? `${activo.nombre} · ${activo.rut}` : ''}
              detalle={activo ? `${activo.tipo === 'persona' ? 'Persona' : 'Empresa'} · ${ETIQUETA_POLITICA[activo.politica_credito] || 'Pago al registrarse'}` : ''}
              placeholder="Selecciona un cliente de la tabla para editar su ficha o configurar su política de crédito."
              alLimpiar={() => { setSeleccionadoId(null); setPanelActivo(null) }}
            >
              {activo && (
                <>
                  <button
                    type="button"
                    className="boton-secundario"
                    aria-expanded={panelActivo === 'editar'}
                    onClick={() => setPanelActivo(panelActivo === 'editar' ? null : 'editar')}
                  >
                    {panelActivo === 'editar' ? 'Cerrar edición' : 'Editar ficha'}
                  </button>
                  {esAdmin && (
                    <button
                      type="button"
                      className="boton-secundario"
                      aria-expanded={panelActivo === 'credito'}
                      onClick={() => alternarCredito(activo)}
                    >
                      {panelActivo === 'credito' ? 'Cerrar crédito' : 'Política de crédito'}
                    </button>
                  )}
                </>
              )}
            </BarraContextual>

            {activo && panelActivo === 'editar' && (
              <div style={{ marginBottom: '0.75rem' }}>
                <FormularioEdicion
                  key={activo.id}
                  ruta={`/hotel/clientes/${activo.id}`}
                  tituloAria={`Editar ficha de ${activo.nombre}`}
                  inicial={activo}
                  campos={CAMPOS_CLIENTE}
                  alGuardar={() => { setPanelActivo(null); setAviso('Cliente actualizado.'); cargar(texto.trim()) }}
                  alCancelar={() => setPanelActivo(null)}
                />
                <p className="nota-clave">Corregir la ficha no cambia pagos ni imputaciones ya asentados.</p>
              </div>
            )}

            {activo && esAdmin && panelActivo === 'credito' && (
              <section className="tarjeta" aria-label="Política de crédito">
                <form className="formulario" onSubmit={(e) => guardarCredito(e, activo.id)}>
                  <CampoSelect
                    etiqueta="Política de crédito"
                    value={formCredito.politica_credito}
                    onChange={(e) => setFormCredito({ ...formCredito, politica_credito: e.target.value })}
                  >
                    <option value="pago_al_registrarse">Pago al registrarse</option>
                    <option value="credito_autorizado">Crédito autorizado</option>
                    <option value="garantia_salida">Garantía con tarjeta cobrada a la Salida</option>
                  </CampoSelect>
                  {formCredito.politica_credito === 'credito_autorizado' && (
                    <>
                      <Campo
                        etiqueta="Límite de crédito (CLP)"
                        type="number"
                        min="1"
                        value={formCredito.cupo_credito_clp}
                        onChange={(e) => setFormCredito({ ...formCredito, cupo_credito_clp: e.target.value })}
                      />
                      <Campo
                        etiqueta="Plazo en días"
                        type="number"
                        min="0"
                        max="365"
                        value={formCredito.plazo_dias}
                        onChange={(e) => setFormCredito({ ...formCredito, plazo_dias: e.target.value })}
                      />
                    </>
                  )}
                  {formCredito.politica_credito === 'garantia_salida' && (
                    <>
                      <Campo
                        etiqueta="Marca tarjeta (sin número completo)"
                        value={formCredito.garantia_tarjeta_marca}
                        placeholder="Ej.: Visa / Mastercard"
                        onChange={(e) => setFormCredito({ ...formCredito, garantia_tarjeta_marca: e.target.value })}
                      />
                      <Campo
                        etiqueta="Últimos 4 dígitos (nunca CVV)"
                        inputMode="numeric"
                        maxLength={4}
                        value={formCredito.garantia_tarjeta_ultimos4}
                        placeholder="1234"
                        onChange={(e) => setFormCredito({ ...formCredito, garantia_tarjeta_ultimos4: e.target.value })}
                      />
                    </>
                  )}
                  <div className="acciones-fila">
                    <button type="submit" className="boton-primario">Guardar política de crédito</button>
                    <button type="button" className="boton-fantasma" onClick={() => setPanelActivo(null)}>Cancelar</button>
                  </div>
                </form>
              </section>
            )}

            <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Clientes (desliza para ver todas las columnas)">
              <table className="tabla">
                <thead>
                  <tr>
                    <th className="celda-selector"><span className="sr-only">Elegir</span></th>
                    <th>Nombre</th>
                    <th>RUT</th>
                    <th>Tipo</th>
                    <th>Teléfono</th>
                    <th>Correo</th>
                    <th>Crédito</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {lista.map((c) => {
                    const elegida = activo?.id === c.id
                    return (
                      <tr
                        key={c.id}
                        className="fila-seleccionable"
                        data-seleccionada={elegida ? 'true' : 'false'}
                        onClick={() => elegirCliente(c)}
                      >
                        <td className="celda-selector">
                          <SelectorFila
                            nombreGrupo="cliente-activo"
                            elegido={elegida}
                            etiqueta={`Seleccionar cliente ${c.nombre}`}
                            alElegir={() => elegirCliente(c)}
                          />
                        </td>
                        <td>{c.nombre}</td>
                        <td>{c.rut}</td>
                        <td>{c.tipo === 'persona' ? 'Persona' : 'Empresa'}</td>
                        <td>{c.telefono ?? '—'}</td>
                        <td>{c.correo ?? '—'}</td>
                        <td>
                          {ETIQUETA_POLITICA[c.politica_credito] || 'Pago al registrarse'}
                          {c.politica_credito === 'credito_autorizado' && (
                            <div className="nota-clave">Cupo {clp(c.cupo_credito_clp)} · {c.plazo_dias} d</div>
                          )}
                        </td>
                        <td>{c.activo ? 'Activo' : 'Inactivo'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </>
        )
      )}
      {truncado && <p className="nota-clave">Se muestran los primeros resultados: afina la búsqueda.</p>}
      <CuentasPorCobrar puedeCobrar={puedeVerCxc} />
      <ConveniosPanel esAdmin={esAdmin} clientes={lista || []} />
    </MarcoHotel>
  )
}
