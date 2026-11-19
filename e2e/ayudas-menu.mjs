/**
 * Navegación del menú 1A.3 para las suites E2E existentes.
 * Oferta / Nueva reserva / Buscar reservas viven en el subnav de Reservas;
 * Solicitudes / Leads bajo «Solicitudes y leads»; Caja / Pago bajo «Caja y pagos»;
 * la antigua «Tipos, habitaciones y precios» es la pestaña Tipos de Configuración.
 */
export function opcionesNavegador() {
  return { executablePath: process.env.CHROME_PATH || '/usr/bin/google-chrome' }
}

const BAJO_RESERVAS = new Set(['Oferta', 'Nueva reserva', 'Buscar reservas'])
const BAJO_BANDEJAS = new Set(['Solicitudes', 'Leads'])
const BAJO_CAJA = new Set(['Caja del día', 'Registrar pago', 'Caja', 'Pago'])
const TIPOS = new Set([
  'Tipos habitaciones y precios',
  'Tipos, habitaciones y precios',
  'Tipos y habitaciones',
])

export async function irDesdeMenu(page, enlace, ruta, front) {
  const base = front || process.env.FRONT_URL || 'http://127.0.0.1:3013'
  await page.goto(`${base}/`)
  await page.waitForTimeout(800)
  await page.locator('aside.barra').getByRole('link', { name: 'Hotel', exact: true }).click()
  await page.waitForURL(/\/hotel\//, { timeout: 10000 })
  await page.waitForTimeout(400)

  const barra = page.locator('aside.barra')
  if (BAJO_RESERVAS.has(enlace)) {
    await barra.getByRole('link', { name: 'Reservas', exact: true }).click()
    await page.waitForTimeout(500)
    await page.locator('.subnav').getByRole('link', { name: enlace, exact: true }).click()
  } else if (BAJO_BANDEJAS.has(enlace)) {
    await barra.getByRole('link', { name: 'Solicitudes y leads', exact: true }).click()
    await page.waitForTimeout(500)
    await page.locator('.subnav').getByRole('link', { name: enlace, exact: true }).click()
  } else if (BAJO_CAJA.has(enlace)) {
    await barra.getByRole('link', { name: 'Caja y pagos', exact: true }).click()
    await page.waitForTimeout(500)
    const nombre = (enlace === 'Caja' || enlace === 'Caja del día') ? 'Caja' : enlace === 'Pago' ? 'Registrar pago' : enlace
    await page.locator('.subnav').getByRole('link', { name: nombre, exact: true }).click()
  } else if (TIPOS.has(enlace) || ruta === '/hotel/tipos') {
    await barra.getByRole('link', { name: 'Configuración', exact: true }).click()
    await page.waitForTimeout(500)
    const tab = page.locator('.subnav').getByRole('link', { name: 'Tipos y habitaciones' })
    if (await tab.count()) await tab.click()
  } else {
    await barra.getByRole('link', { name: enlace, exact: true }).click()
  }
  await page.waitForTimeout(800)
  if (!ruta) return
  const url = page.url()
  const ok = url.includes(ruta) || (ruta === '/hotel/tipos' && url.includes('/hotel/configuracion'))
  if (!ok) throw new Error(`el menú llevó a ${url}, se esperaba ${ruta}`)
}
