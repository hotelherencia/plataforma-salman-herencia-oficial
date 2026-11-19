'use client'

import { useEffect, useRef, useState } from 'react'
import { api, mensajeDeError } from '../../../lib/api'
import {
  fechaCorta, insigniasEstadia, mensajeVacio, noches, pesos, rotuloLista, textoBuscable,
} from '../../../lib/estadias'
import css from './operacion.module.css'

const TONO = { exito: css.chipExito, aviso: css.chipAviso, error: css.chipError, info: css.chipInfo, neutro: '' }

export function Insignias({ estadia }) {
  return (
    <span className={css.chips}>
      {insigniasEstadia(estadia).map((i) => (
        <span key={i.texto} className={`${css.chip} ${TONO[i.tono] || ''}`}>{i.texto}</span>
      ))}
    </span>
  )
}

/**
 * Buscador único de huéspedes (2026-11-19) para Salida, Caja y Llegada:
 * nombre, habitación, documento o código. Sin texto muestra la lista del día
 * de la pantalla. Los resultados son tarjetas seleccionables.
 */
export function BuscadorEstadias({ alcance, alElegir, elegidaId, autoFocus = false }) {
  const [texto, setTexto] = useState('')
  const [estado, setEstado] = useState({ fase: 'cargando', resultados: [], listaDelDia: true, hayMas: false, aviso: '' })
  const primero = useRef(null)

  useEffect(() => {
    const t = texto.trim()
    if (!textoBuscable(t)) {
      setEstado((e) => ({ ...e, fase: 'corto', aviso: 'Escribe al menos 2 letras, o el número de habitación.' }))
      return undefined
    }
    let cancelado = false
    const temporizador = setTimeout(async () => {
      setEstado((e) => ({ ...e, fase: 'cargando' }))
      try {
        const q = new URLSearchParams({ alcance })
        if (t) q.set('q', t)
        const r = await api(`/hotel/estadias/busqueda?${q}`)
        if (cancelado) return
        if (r.estado === 200) {
          setEstado({ fase: 'ok', resultados: r.datos.resultados, listaDelDia: r.datos.lista_del_dia, hayMas: r.datos.hay_mas, aviso: '' })
        } else {
          setEstado({ fase: 'error', resultados: [], listaDelDia: !t, hayMas: false, aviso: mensajeDeError(r.datos, r.estado) })
        }
      } catch {
        if (!cancelado) setEstado({ fase: 'error', resultados: [], listaDelDia: !t, hayMas: false, aviso: 'No se pudo conectar con el servidor. Intenta nuevamente en unos minutos.' })
      }
    }, t ? 280 : 0)
    return () => {
      cancelado = true
      clearTimeout(temporizador)
    }
  }, [texto, alcance])

  function alEnviar(e) {
    e.preventDefault()
    if (estado.fase === 'ok' && estado.resultados.length === 1) alElegir(estado.resultados[0])
    else primero.current?.focus()
  }

  const { resultados } = estado
  return (
    <div className={css.buscador} data-buscador-estadias={alcance}>
      <form className={css.busquedaFila} role="search" onSubmit={alEnviar}>
        <label className="campo">
          <span className="campo-etiqueta">Buscar huésped</span>
          <input
            className="entrada"
            type="search"
            value={texto}
            autoFocus={autoFocus}
            autoComplete="off"
            enterKeyHint="search"
            placeholder="Nombre, habitación, documento o código de reserva"
            onChange={(e) => setTexto(e.target.value)}
          />
        </label>
      </form>
      <p className={css.rotuloLista} role="status" aria-live="polite">
        {estado.fase === 'cargando' ? 'Buscando…'
          : estado.fase === 'corto' ? estado.aviso
            : estado.fase === 'error' ? '' : rotuloLista(alcance, estado.listaDelDia, resultados.length)}
      </p>
      {estado.fase === 'error' && <p className="alerta" role="alert">{estado.aviso}</p>}
      {estado.fase === 'ok' && resultados.length === 0 && (
        <p className="estado estado-vacio">{mensajeVacio(alcance, estado.listaDelDia)}</p>
      )}
      {resultados.length > 0 && estado.fase !== 'corto' && (
        <ul className={css.resultados} aria-label="Huéspedes encontrados">
          {resultados.map((r, i) => (
            <li key={r.reserva_id}>
              <button
                type="button"
                ref={i === 0 ? primero : undefined}
                className={css.resultado}
                aria-pressed={elegidaId === r.reserva_id}
                data-reserva={r.reserva_id}
                onClick={() => alElegir(r)}
              >
                <span className={css.resultadoNombre}>{r.huesped_nombre}</span>
                <span className={css.resultadoLinea}>
                  Habitación <strong>{r.habitacion_id}</strong>{r.tipo_habitacion ? ` · ${r.tipo_habitacion}` : ''}
                </span>
                <span className={css.resultadoLinea}>
                  Llegada {fechaCorta(r.inicio)} · Salida {fechaCorta(r.fin)} · {noches(r.noches)}
                </span>
                {r.huesped_documento && <span className={css.resultadoLinea}>Documento {r.huesped_documento}</span>}
                <Insignias estadia={r} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {estado.hayMas && estado.fase === 'ok' && (
        <p className={css.ayuda}>Hay más coincidencias: agrega el apellido o el número de habitación para acotar.</p>
      )}
    </div>
  )
}

/** Ficha de la estadía elegida, con la cuenta al día. */
export function FichaEstadia({ detalle, alCambiar, children }) {
  if (!detalle) return null
  const { cuenta } = detalle
  const saldo = cuenta.saldo_clp
  return (
    <section className={css.ficha} aria-label="Huésped elegido" data-ficha-estadia={detalle.reserva_id}>
      <div className={css.fichaCabecera}>
        <div>
          <p className={css.fichaNombre}>{detalle.huesped_nombre}</p>
          <p className={css.ayuda}>
            Habitación <strong>{detalle.habitacion_id}</strong>{detalle.tipo_habitacion ? ` · ${detalle.tipo_habitacion}` : ''} ·
            Llegada {fechaCorta(detalle.inicio)} · Salida {fechaCorta(detalle.fin)} · {noches(detalle.noches)} · Reserva {detalle.reserva_id}
          </p>
        </div>
        {alCambiar && (
          <button type="button" className="boton-fantasma" onClick={alCambiar}>Cambiar huésped</button>
        )}
      </div>
      <dl className={css.cifras}>
        <div className={css.cifra}><dt>Total de la cuenta</dt><dd>{pesos(cuenta.cargos_netos_clp)}</dd></div>
        <div className={css.cifra}><dt>Pagado</dt><dd>{pesos(cuenta.pagado_clp)}</dd></div>
        <div className={`${css.cifra} ${saldo > 0 ? css.cifraDestacada : saldo === 0 ? css.cifraOk : ''}`}>
          <dt>{saldo < 0 ? 'A favor del huésped' : 'Saldo pendiente'}</dt>
          <dd data-saldo={saldo}>{pesos(Math.abs(saldo))}</dd>
        </div>
      </dl>
      {children}
    </section>
  )
}

export { css as estilosOperacion }
