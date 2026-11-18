// Documento del huésped (#367): misma regla que servicio/documento.py, en el
// front para avisar antes de enviar. Módulo puro (node --test).

export function digitoVerificador(cuerpo) {
  let suma = 0
  let factor = 2
  for (const d of String(cuerpo).split('').reverse()) {
    suma += Number(d) * factor
    factor = factor === 7 ? 2 : factor + 1
  }
  const resto = 11 - (suma % 11)
  return resto === 11 ? '0' : resto === 10 ? 'K' : String(resto)
}

/** { ok, valor, error }: valor normalizado (12.345.678-5 o pasaporte en mayúsculas). */
export function validarDocumento(tipo, numero) {
  const texto = (numero || '').trim()
  if (!texto) return { ok: false, error: 'El documento es obligatorio.' }
  if (tipo === 'rut') {
    const limpio = texto.replace(/[.\s-]/g, '').toUpperCase()
    if (!/^\d{7,8}[0-9K]$/.test(limpio)) return { ok: false, error: 'RUT inválido: usa el formato 12.345.678-5.' }
    const cuerpo = limpio.slice(0, -1)
    const dv = limpio.slice(-1)
    if (digitoVerificador(cuerpo) !== dv) return { ok: false, error: 'RUT inválido: el dígito verificador no corresponde.' }
    return { ok: true, valor: `${Number(cuerpo).toLocaleString('es-CL')}-${dv}` }
  }
  if (tipo === 'pasaporte') {
    const limpio = texto.replace(/\s/g, '').toUpperCase()
    if (!/^[A-Z0-9]{6,12}$/.test(limpio)) return { ok: false, error: 'Pasaporte inválido: de 6 a 12 letras o números.' }
    return { ok: true, valor: limpio }
  }
  return { ok: false, error: 'Elige el tipo de documento.' }
}
