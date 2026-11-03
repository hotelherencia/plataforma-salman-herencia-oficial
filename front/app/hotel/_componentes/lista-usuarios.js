'use client'

/**
 * Capa del módulo Hotel — gestión de usuarios (pura, sin fetch): recibe solo
 * props y dibuja la respuesta de GET /usuarios tal cual la envía la API. La
 * API jamás devuelve clave_hash; aquí solo se listan id, nombre, rol y activo
 * para que el administrador descubra el id antes de revocar, dar de baja o
 * cambiar la clave. Presentación en el mismo lenguaje que lista-reservas.
 */

export function ListaUsuarios({ usuarios, total, alElegir }) {
  return (
    <>
      <p className="reservas-total">{total} usuario(s)</p>
      <ul className="reservas-lista" role="table">
        <li className="usuario-encabezado" role="row">
          <span role="columnheader">Usuario</span>
          <span role="columnheader">Nombre</span>
          <span role="columnheader">Rol</span>
          <span role="columnheader">Estado</span>
          <span role="columnheader"></span>
        </li>
        {usuarios.map((u) => (
          <FilaUsuario key={u.id} usuario={u} alElegir={alElegir} />
        ))}
      </ul>
    </>
  )
}

export function FilaUsuario({ usuario, alElegir }) {
  return (
    <li className="usuario-fila" role="row">
      <span role="cell" className="reserva-id">{usuario.id}</span>
      <span role="cell" className="reserva-huesped">{usuario.nombre}</span>
      <span role="cell" className="reserva-celda">{usuario.rol}</span>
      <span role="cell" className={`reserva-estado ${usuario.activo ? 'estado-confirmada' : 'estado-cancelada'}`}>
        {usuario.activo ? 'activo' : 'inactivo'}
      </span>
      <span role="cell" className="usuario-accion">
        <button type="button" className="boton-fantasma" onClick={() => alElegir(usuario.id)}>
          Usar id
        </button>
      </span>
    </li>
  )
}

export function UsuariosVacios() {
  return (
    <div className="oferta-vacia">
      <p className="oferta-vacia-titulo">No hay usuarios para mostrar</p>
      <p className="oferta-vacia-texto">La empresa todavía no tiene usuarios dados de alta.</p>
    </div>
  )
}
