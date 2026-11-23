import { redirect } from 'next/navigation'

/** /hotel no es una pantalla: lleva al Panel (el acceso pide sesión si hace falta). */
export default function IndiceHotel() {
  redirect('/hotel/panel')
}
