import re

import requests
from bs4 import BeautifulSoup


def limpiar_precio(valor):
    """Convierte un precio como '$756' o '$1.990' en número."""
    valor = valor.replace("$", "")
    valor = valor.replace(".", "")
    valor = valor.replace(" ", "")

    return int(valor)


def obtener_producto(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    respuesta = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    respuesta.raise_for_status()

    soup = BeautifulSoup(respuesta.text, "html.parser")
    print("\n--- ELEMENTOS CON PARACETAMOL ---")

    for elemento in soup.find_all(string=re.compile("Paracetamol", re.IGNORECASE)):
        print("TAG:", elemento.parent.name)
        print("TEXTO:", elemento.strip())

    texto = soup.get_text(" ", strip=True)

    # Nombre del producto
    nombre = soup.title.get_text(strip=True) if soup.title else ""

    # Laboratorio
    laboratorio = ""

    if "PHARMARIS" in texto:
        laboratorio = ""

    patron_laboratorio = re.search(
        r"Home.*?([A-ZÁÉÍÓÚÑ]{3,})\s+"
        r"Paracetamol",
        texto
    )

    if patron_laboratorio:
        laboratorio = patron_laboratorio.group(1)

    # Precio de oferta
    precio = None

    coincidencia_precio = re.search(
        r"\$(\d+(?:\.\d{3})*)\s*\(Oferta\)",
        texto
    )

    if coincidencia_precio:
        precio = limpiar_precio(coincidencia_precio.group(1))

    # Precio normal
    precio_normal = None

    coincidencia_normal = re.search(
        r"\$(\d+(?:\.\d{3})*)\s*\(Normal\)",
        texto
    )

    if coincidencia_normal:
        precio_normal = limpiar_precio(coincidencia_normal.group(1))

    # Disponibilidad
    disponible = "Agregar a la bolsa" in texto

    producto = {
        "nombre": nombre,
        "laboratorio": laboratorio,
        "precio": precio,
        "precio_normal": precio_normal,
        "disponible": disponible,
        "url": url
    }

    return producto


if __name__ == "__main__":
    url = "https://beta.cruzverde.cl/paracetamol-500-mg-16-comprimidos/272241.html"

    producto = obtener_producto(url)

    print("\n--- PRODUCTO EXTRAÍDO ---")
    print("Nombre:", producto["nombre"])
    print("Laboratorio:", producto["laboratorio"])
    print("Precio:", producto["precio"])
    print("Precio normal:", producto["precio_normal"])
    print("Disponible:", producto["disponible"])
    print("URL:", producto["url"])