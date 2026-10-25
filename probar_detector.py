
import os
import re
import django
import pytesseract
from PIL import Image

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from farmacia.models import Medicamento

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def normalizar(texto):
    """Normaliza texto para facilitar las comparaciones."""
    texto = texto.casefold().replace(",", ".")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def detectar_medicamentos(texto):
    resultados = []
    lineas = [
        normalizar(linea)
        for linea in texto.splitlines()
        if len(linea.strip()) >= 3
    ]

    medicamentos = list(
        Medicamento.objects.prefetch_related("productos__precios").all()
    )

    def tiene_precios(medicamento):
        return any(
            producto.precios.exists()
            for producto in medicamento.productos.all()
        )

    for i, linea in enumerate(lineas):
        contexto = linea
        if i + 1 < len(lineas):
            contexto += " " + lineas[i + 1]

        coincidencias = []

        # Primero buscamos el nombre completo del producto.
        for medicamento in medicamentos:
            nombre = normalizar(medicamento.nombre)

            if nombre and nombre in contexto:
                coincidencias.append(medicamento)

        if coincidencias:
            for medicamento in coincidencias:
                if not any(
                    r["medicamento"].id == medicamento.id
                    for r in resultados
                ):
                    resultados.append({
                        "medicamento": medicamento,
                        "tipo": "Nombre del producto reconocido",
                        "tiene_precios": tiene_precios(medicamento),
                        "confirmacion": False,
                    })
            continue

        # Si no hay nombre completo, buscamos el principio activo.
        principios_detectados = {
            normalizar(m.principio_activo)
            for m in medicamentos
            if m.principio_activo
            and re.search(
                rf"(?<!\w){re.escape(normalizar(m.principio_activo))}(?!\w)",
                linea
            )
        }

        for principio in principios_detectados:
            alternativas = [
                m for m in medicamentos
                if (
                    normalizar(m.principio_activo or "") == principio
                    or principio in normalizar(m.nombre)
                )
            ]

            for medicamento in alternativas:
                if not any(
                    r["medicamento"].id == medicamento.id
                    for r in resultados
                ):
                    resultados.append({
                        "medicamento": medicamento,
                        "tipo": "Coincidencia por principio activo",
                        "tiene_precios": tiene_precios(medicamento),
                        "confirmacion": True,
                    })

    # Los que tienen precios aparecen primero.
    resultados.sort(
        key=lambda r: not r["tiene_precios"]
    )

    return resultados

def probar_detector():
    pruebas = {
        "Nombre y concentración en una línea": """
            Paracetamol 500 mg 16 Comprimidos
        """,
        "Nombre y concentración en líneas separadas": """
            Paracetamol
            500 mg
        """,
        "Solo principio activo": """
            PARACETAMOL
        """,
        "Medicamento fuera del catálogo": """
            Ibuprofeno 400 mg
        """,
        "Texto sin medicamentos": """
            Receta médica
            Tomar según indicación
        """,
    }

    for nombre_prueba, texto in pruebas.items():
        resultados = detectar_medicamentos(texto)

        print(f"\n=== {nombre_prueba} ===")

        if not resultados:
            print("No se encontraron coincidencias.")
            continue

        for resultado in resultados:
            medicamento = resultado["medicamento"]
            print(f"- {medicamento.nombre}")
            print(f"  Tipo: {resultado['tipo']}")
            print(
                "  Tiene precios registrados:",
                "Sí" if resultado["tiene_precios"] else "No"
            )

            if resultado["confirmacion"]:
                print("  Revisar presentación antes de continuar.")


if __name__ == "__main__":
    probar_detector()
