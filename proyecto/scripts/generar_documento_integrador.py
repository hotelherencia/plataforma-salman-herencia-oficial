# Genera el documento Word integrador del paquete de presentacion al holding.
# Uso: python3 scripts/generar_documento_integrador.py
# Requiere: python-docx. Lee las imagenes PNG de docs/presentacion-holding/diagramas/
# (generadas desde los .mmd equivalentes, ver README de esa carpeta).

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

BASE = Path(__file__).resolve().parent.parent
CARPETA = BASE / "docs" / "presentacion-holding"
DIAGRAMAS = CARPETA / "diagramas"
SALIDA = CARPETA / "05-documento-integrador.docx"
ANCHO_IMAGEN = Inches(6.2)


def en_palabras_simples(doc, texto):
    p = doc.add_paragraph()
    r = p.add_run("En palabras simples: ")
    r.bold = True
    p.add_run(texto).italic = True


def con_imagen(doc, nombre):
    doc.add_picture(str(DIAGRAMAS / nombre), width=ANCHO_IMAGEN)
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def con_tabla(doc, cabeceras, filas):
    tabla = doc.add_table(rows=1, cols=len(cabeceras))
    tabla.style = "Table Grid"
    for i, h in enumerate(cabeceras):
        celda = tabla.rows[0].cells[i]
        celda.text = h
        celda.paragraphs[0].runs[0].bold = True
    for fila in filas:
        celdas = tabla.add_row().cells
        for i, valor in enumerate(fila):
            celdas[i].text = valor
    doc.add_paragraph()


def main():
    doc = Document()
    doc.core_properties.title = "Plataforma Salman - Documento Integrador de la Propuesta"
    doc.core_properties.author = "Comite de revision independiente"

    # Portada
    titulo = doc.add_paragraph()
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = titulo.add_run("Plataforma Salman\nDe los silos a la plataforma del grupo")
    r.bold = True
    r.font.size = Pt(24)
    subt = doc.add_paragraph()
    subt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subt.add_run(
        "Documento integrador de la evaluacion y la propuesta de decision\n"
        "Paquete de presentacion al holding · 19-10-2026\n"
        "Clasificacion: PROPUESTA DE COMITE (material de apoyo, no modifica requisitos)"
    ).font.size = Pt(12)
    doc.add_paragraph(
        "Este documento reune en un solo archivo la evaluacion independiente de la propuesta de "
        "plataforma del grupo Salman: el problema, la evidencia de mercado, el dictamen y las "
        "cinco decisiones que requieren la sesion de direccion. Cada concepto tecnico va "
        "acompanado de un diagrama y de su explicacion en lenguaje simple."
    )
    doc.add_page_break()

    # 1. Problema
    doc.add_heading("1. El problema de hoy", level=1)
    doc.add_paragraph(
        "El holding opera varios negocios (hotel, cafeteria, inmobiliaria, constructora y farmacia), "
        "cada uno con herramientas aisladas. Ese fue el motivo original del proyecto: obtener "
        "decisiones de grupo y una vision integral del cliente."
    )
    con_imagen(doc, "d01-silos-hoy.png")
    en_palabras_simples(
        doc,
        "cada negocio vive en su isla. Nadie del grupo puede responder \"cuanto facturamos en "
        "conjunto este mes\" sin armar planillas a mano. Ese era el problema que este proyecto "
        "debia resolver.",
    )

    # 2. Estado del proyecto
    doc.add_heading("2. Que existe hoy en el proyecto", level=1)
    doc.add_paragraph(
        "Hay un diseno detallado y auditado: 77 requisitos funcionales, 31 criterios de aceptacion, "
        "4 verticales especificadas, 6 decisiones de arquitectura y una constitucion. Todo propuesto; "
        "nada ratificado con firma, y sin lineas de codigo."
    )
    con_imagen(doc, "d02-documento-vs-codigo.png")
    en_palabras_simples(
        doc,
        "hay los planos de una casa muy completos, pero nadie ha aprobado los planos y no se ha "
        "movido un solo ladrillo. Ademas hay mas de 30 preguntas sobre el propio negocio que solo "
        "el grupo puede responder y que siguen abiertas.",
    )

    # 3. Mercado
    doc.add_heading("3. El mercado en tres datos", level=1)
    con_tabla(
        doc,
        ["Dato (verificable)", "Que significa para el holding"],
        [
            [
                "Toast (lider mundial): 164.000 locales y US$195.000 millones procesados en 2025; "
                "sin entrada a LATAM (earnings Q4-2025, feb-2026).",
                "El modelo ganador (software + pagos + agentes) no ha llegado; hay tiempo, no mucho.",
            ],
            [
                "Toteat (Chile) levanto US$7,4 millones para IA y expansion (sep-2025); Fudo supera "
                "25.000 clientes activos (ago-2026).",
                "Los competidores locales crecen y agregan inteligencia artificial; cada mes de "
                "espera es mercado que se asienta.",
            ],
            [
                "Ningun proveedor cubre la plataforma multi-vertical de un grupo familiar en LATAM "
                "(verificacion del comite, oct-2026); ventana estimada de 24 a 48 meses.",
                "El terreno que el grupo podria ocupar esta libre hoy.",
            ],
            [
                "Ley 21.719 de proteccion de datos: vigencia plena el 1-dic-2026, multas de hasta "
                "4% de ingresos anuales.",
                "Los datos de clientes deben gobernarse bien desde el diseno; tambien es una "
                "ventaja frente a competidores descuidados.",
            ],
        ],
    )

    # 4. Oportunidad
    doc.add_heading("4. La oportunidad: el terreno esta libre", level=1)
    con_imagen(doc, "d03-terreno-libre.png")
    en_palabras_simples(
        doc,
        "cada proveedor fuerte hace una sola cosa: los de restaurantes no hacen hoteles, los de "
        "hoteles no hacen farmacias. Nadie hace \"el sistema del grupo\". Ese hueco es exactamente "
        "lo que el holding necesita para si mismo y lo que despues podria vender a otros grupos "
        "familiares.",
    )

    # 5. Hallazgo central
    doc.add_heading("5. El hallazgo central: un candado que nadie decidio poner", level=1)
    doc.add_paragraph(
        "El diseno actual prohibe que el sistema reconozca al mismo cliente en dos negocios del "
        "grupo, por principio constitucional, sin que exista registro de una evaluacion de "
        "alternativas. La ley chilena nueva no lo prohibe: permite compartir datos entre empresas "
        "del mismo grupo con el consentimiento expreso del cliente."
    )
    con_imagen(doc, "d04-cliente-transversal.png")
    en_palabras_simples(
        doc,
        "la propuesta del comite es guardar la llave en vez de soldar la puerta: el reconocimiento "
        "de cliente comun viene apagado por defecto y cada negocio lo activa solo con el permiso "
        "del cliente, como un checkbox. Si el dia de manana la direccion pregunta \"por que el "
        "sistema no sabe quien es nuestro cliente comun?\", la respuesta no puede ser \"un papel "
        "sin firmar lo prohibio\".",
    )

    # 6. Escenarios
    doc.add_heading("6. Los tres escenarios a 36 meses", level=1)
    con_imagen(doc, "d05-escenarios.png")
    doc.add_paragraph(
        "Gatillos observables en los primeros 90 dias: constitucion firmada con fecha, stack "
        "tecnologico elegido, inventario operativo entregado por el grupo y primer commit del nucleo."
    )
    en_palabras_simples(
        doc,
        "el escenario malo no depende de la tecnologia, depende de una firma. Si en 90 dias no hay "
        "constitucion aprobada, ya estamos en el escenario rojo, y se puede saber sin esperar "
        "tres anos.",
    )

    # 7. Dictamen
    doc.add_heading("7. Dictamen del comite: MODIFICAR", level=1)
    doc.add_paragraph(
        "Ni continuar tal cual (mata la tesis del holding) ni abandonar (la oportunidad existe y "
        "esta libre). Cinco modificaciones obligatorias:"
    )
    con_tabla(
        doc,
        ["#", "Modificacion", "Por que"],
        [
            ["1", "Cliente transversal por consentimiento, apagado por defecto",
             "Mantiene la tesis del holding sin riesgo legal"],
            ["2", "Una vertical primero (cafeteria u hotel); las demas congeladas",
             "Asi crecieron Toast, Fudo, Cloudbeds y Mews"],
            ["3", "Agentes por politica: autonomos sin dinero, aprobacion humana con dinero, "
                  "regla fija en documentos tributarios",
             "La gobernanza es producto que se cobra, no un freno"],
            ["4", "Farmacia: decision explicita con fecha",
             "Su regulacion abierta da una ventana de 24 a 36 meses"],
            ["5", "Ratificar constitucion y decisiones de arquitectura con fecha limite",
             "Sin firma, todo lo demas es papel"],
        ],
    )

    # 8. Cinco decisiones
    doc.add_heading("8. Las cinco decisiones que no pueden esperar", level=1)
    con_tabla(
        doc,
        ["#", "Decision", "Costo de postergarla 6 meses"],
        [
            ["1", "Ratificar constitucion y decisiones de arquitectura", "Nada avanza sin esto"],
            ["2", "Cliente transversal: consentimiento o prohibicion",
             "Unificar identidades despues cuesta 10 a 50 veces mas"],
            ["3", "Stack tecnologico (lenguaje, base de datos, hosting)",
             "No se puede contratar ni escribir codigo"],
            ["4", "Primera vertical y destino del software actual",
             "Es la definicion del producto; el mercado no espera"],
            ["5", "Farmacia: dentro o fuera del alcance",
             "La ventana regulatoria se cierra sola"],
        ],
    )
    en_palabras_simples(
        doc,
        "estas cinco son baratas hoy (son decisiones de una reunion) y caras despues (son obras de "
        "demolicion). Por eso se deciden en la sesion, una por una: firma, rechazo con fecha, o "
        "aplazamiento con fecha.",
    )

    # 9. Agente gobernado
    doc.add_heading("9. Como trabajaria un agente con gobernanza", level=1)
    doc.add_paragraph(
        "Los agentes de inteligencia artificial del proyecto operan con limites por tipo de tarea, "
        "no con una regla unica:"
    )
    con_imagen(doc, "d06-agente-gobernado.png")
    en_palabras_simples(
        doc,
        "el agente es como un encargado con tarjeta limitada. Para tareas sin plata trabaja solo; "
        "para gastar pide permiso por telefono, y el permiso sirve una sola vez y por el monto "
        "exacto; para boletas y facturas no decide nunca, porque ahi manda la regla fija y un "
        "error le cuesta multa al grupo. Esto es lo que el lider mundial (Toast) ya vende en "
        "Estados Unidos a US$699 al mes.",
    )

    # 10. Lo que no se propone
    doc.add_heading("10. Lo que NO se esta proponiendo", level=1)
    for item in [
        "Escribir codigo de inmediato: primero se firma el diseno; la fase sigue siendo documental.",
        "Compartir datos de clientes sin permiso: el reconocimiento viene apagado por defecto.",
        "Reemplazar de golpe los sistemas actuales: la convivencia se decide con datos del grupo.",
        "Prometer las cuatro verticales: se implementa una y las demas quedan como opciones evaluadas.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    # 11. Agenda
    doc.add_heading("11. La sesion de decision", level=1)
    con_imagen(doc, "d07-agenda-sesion.png")
    doc.add_paragraph(
        "Regla de cierre: cada decision termina en firmada, rechazada con fecha, o diferida con "
        "fecha. \"Lo pensamos\" sin fecha equivale a no, y activa el escenario pesimista. El acta "
        "se firma al terminar la sesion (plantilla en 04-acta-decision.md)."
    )

    # Cierre
    doc.add_heading("Fuentes y estado del documento", level=1)
    doc.add_paragraph(
        "Fuentes de mercado con fecha: Toast (earnings Q4-2025, feb-2026), LatamList (sep-2025), "
        "Startupeable (ago-2026), verificacion directa del comite (oct-2026), normativa chilena "
        "Ley 21.719 y Ley 20.727 (SII). Lo no verificable se declara como tal en el informe "
        "completo del comite. Documento elaborado por el comite de revision independiente "
        "(arquitectura multi-tenant, analista de mercado LATAM, evaluador esceptico)."
    )

    doc.save(SALIDA)
    print(f"OK: {SALIDA} ({SALIDA.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
