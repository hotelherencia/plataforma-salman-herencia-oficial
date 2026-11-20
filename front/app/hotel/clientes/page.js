'use client'

import { Fragment, useEffect, useState } from 'react'
import { api, mensajeDeError, MarcoHotel, useSesion, Campo } from '../../../lib/api'
import { gestionaClientes } from '../../../lib/roles'
import FormularioEdicion from '../_componentes/formulario-edicion'

/** Clientes (un RUT es una sola persona o empresa). Recepción, caja o administración del hotel buscan
 *  y corrigen la ficha: nombre, tipo, RUT, giro, dirección, comuna, correo y si sigue activo. Las
 *  imputaciones y movimientos ya asentados apuntan por id, así que corregir la ficha no los altera.
 *  Nada se borra: un cliente que ya no se usa se desactiva. */
export default function Clientes() {
  const sesion = useSesion()
  const [lista, setLista] = useState(null)
  const [truncado, setTruncado] = useState(false)
  const [texto, setTexto] = useState('')
  const [error, setError] = useState('')
  const [editando, setEditando] = useState(null)
  const [aviso, setAviso] = useState('')

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
          <Campo etiqueta="Buscar por nombre, RUT o correo" value={texto} onChange={(e) => setTexto(e.target.value)} />
          <button type="submit" className="boton-primario">Buscar</button>
        </form>
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
                  <th>Nombre</th><th>RUT</th><th>Tipo</th><th>Giro</th><th>Comuna</th><th>Correo</th><th>Estado</th><th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((c) => (
                  <Fragment key={c.id}>
                    <tr>
                      <td>{c.nombre}</td>
                      <td>{c.rut}</td>
                      <td>{c.tipo === 'persona' ? 'Persona' : 'Empresa'}</td>
                      <td>{c.giro ?? '—'}</td>
                      <td>{c.comuna ?? '—'}</td>
                      <td>{c.correo ?? '—'}</td>
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
                        <td colSpan={8}>
                          <FormularioEdicion
                            ruta={`/hotel/clientes/${c.id}`}
                            inicial={c}
                            campos={[
                              { nombre: 'nombre', etiqueta: 'Nombre o razón social', requerido: true },
                              { nombre: 'rut', etiqueta: 'RUT', requerido: true },
                              { nombre: 'tipo', etiqueta: 'Tipo', tipo: 'select', opciones: [['empresa', 'Empresa'], ['persona', 'Persona']] },
                              { nombre: 'giro', etiqueta: 'Giro' },
                              { nombre: 'direccion', etiqueta: 'Dirección' },
                              { nombre: 'comuna', etiqueta: 'Comuna' },
                              { nombre: 'correo', etiqueta: 'Correo', tipo: 'email' },
                              { nombre: 'activo', etiqueta: 'Activo', tipo: 'checkbox' },
                            ]}
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
