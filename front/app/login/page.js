'use client'

import PantallaAcceso from './pantalla.jsx'

export default function Login() {
  return <PantallaAcceso despues={() => { window.location.href = '/' }} />
}
