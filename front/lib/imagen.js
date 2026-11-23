// Foto ligera para incidencias (#415): se reduce en el móvil antes de subirla.
// El tope del cuerpo HTTP es 256 KB, así que la imagen final debe pesar ≤ 180 KB.
export const MAX_BYTES_FOTO = 180_000

/** Escala que lleva (ancho × alto) a que el lado mayor no pase de `maximo`; nunca amplía. */
export function escalaMaxima(ancho, alto, maximo = 1280) {
  const mayor = Math.max(ancho, alto)
  return mayor > maximo ? maximo / mayor : 1
}

/** Bytes que ocupa un base64 sin el prefijo `data:`. */
export function bytesDeBase64(base64) {
  const limpio = String(base64 || '').replace(/=+$/, '')
  return Math.floor((limpio.length * 3) / 4)
}

/** Reduce un File de imagen a JPEG ≤ MAX_BYTES_FOTO y lo devuelve en base64 (sin prefijo). */
export async function fotoLigera(archivo) {
  const bitmap = await createImageBitmap(archivo)
  let lado = 1280
  for (let intento = 0; intento < 6; intento += 1) {
    const escala = escalaMaxima(bitmap.width, bitmap.height, lado)
    const lienzo = document.createElement('canvas')
    lienzo.width = Math.max(1, Math.round(bitmap.width * escala))
    lienzo.height = Math.max(1, Math.round(bitmap.height * escala))
    lienzo.getContext('2d').drawImage(bitmap, 0, 0, lienzo.width, lienzo.height)
    const base64 = lienzo.toDataURL('image/jpeg', 0.7).split(',')[1]
    if (bytesDeBase64(base64) <= MAX_BYTES_FOTO) return base64
    lado = Math.round(lado * 0.75)
  }
  throw new Error('No se pudo reducir la foto lo suficiente.')
}
