'use client'

import { Fragment, useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, useSesion, useClaveOperacion, alRechazar, Campo } from '../../../lib/api'
import { gestionaClientes } from '../../../lib/roles'
import { rutValido } from '../../../lib/contabilidad'
import FormularioEdicion from '../_componentes/formulario-edicion'
import { BotonExportar } from '../_componentes/boton-exportar'

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

/** Clientes (un RUT es una sola persona o empresa). Recepción, caja o administración del hotel crean,
 *  buscan (por nombre, RUT, teléfono o correo) y corrigen la ficha. Las imputaciones y movimientos ya
 *  asentados apuntan por id, así que corregir la ficha no los altera. Nada se borra: se desactiva. */
export default function Clientes() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [truncado, setTruncado] = useState(false)
  const [texto, setTexto] = useState('')
  const [error, setError] = useState('')
  const [creando, setCreando] = useState(false)
  const [editando, setEditando] = useState(null)
  const [aviso, setAviso] = useState('')
  const [claveAlta, renovarClaveAlta] = useClaveOperacion()

  const rol = sesion.fase === 'ok' ? sesion.usuario.rol : null
  const puede = gestionaClientes(rol)

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
          <button type="button" className="boton-secundario" aria-expanded={creando}
            onClick={() => { setCreando((v) => !v); setAviso('') }}>
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
          <div className="tabla-contenedor" tabIndex={0} role="region" aria-label="Clientes (desliza para ver todas las columnas)">
            <table className="tabla">
              <thead>
                <tr>
                  <th>Nombre</th><th>RUT</th><th>Tipo</th><th>Teléfono</th><th>Correo</th><th>Giro</th><th>Comuna</th><th>Estado</th><th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((c) => (
                  <Fragment key={c.id}>
                    <tr>
                      <td>{c.nombre}</td>
                      <td>{c.rut}</td>
                      <td>{c.tipo === 'persona' ? 'Persona' : 'Empresa'}</td>
                      <td>{c.telefono ?? '—'}</td>
                      <td>{c.correo ?? '—'}</td>
                      <td>{c.giro ?? '—'}</td>
                      <td>{c.comuna ?? '—'}</td>
                      <td>{c.activo ? 'activo' : 'inactivo'}</td>
                      <td>
                        <button type="button" className="boton-fantasma" aria-expanded={editando === c.id}
                          onClick={() => setEditando(editando === c.id ? null : c.id)}>
                          Editar
                        </button>
                      </td>
                    </tr>
                    {editando === c.id && (
                      <tr>
                        <td colSpan={9}>
                          <FormularioEdicion
                            ruta={`/hotel/clientes/${c.id}`}
                            inicial={c}
                            campos={CAMPOS_CLIENTE}
                            alGuardar={() => { setEditando(null); setAviso('Cliente actualizado.'); cargar(texto.trim()) }}
                            alCancelar={() => setEditando(null)}
                          />
                          <p className="nota-clave">Corregir la ficha no cambia pagos ni imputaciones ya asentados.</p>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
      {truncado && <p className="nota-clave">Se muestran los primeros resultados: afina la búsqueda.</p>}
    </MarcoHotel>
  )
}
