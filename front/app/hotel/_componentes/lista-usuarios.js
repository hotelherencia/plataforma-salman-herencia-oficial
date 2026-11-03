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
      <ul className="reservas-lista">
        <li className="usuario-encabezado" aria-hidden="true">
          <span>Usuario</span>
          <span>Nombre</span>
          <span>Rol</span>
          <span>Estado</span>
          <span></span>
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
    <li className="usuario-fila">
      <span className="reserva-id">{usuario.id}</span>
      <span className="reserva-huesped">{usuario.nombre}</span>
      <span className="reserva-celda">{usuario.rol}</span>
      <span className={`reserva-estado ${usuario.activo ? 'estado-confirmada' : 'estado-cancelada'}`}>
        {usuario.activo ? 'activo' : 'inactivo'}
      </span>
      <span className="usuario-accion">
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
