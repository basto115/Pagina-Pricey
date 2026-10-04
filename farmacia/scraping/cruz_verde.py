import re
import requests
from bs4 import BeautifulSoup


def limpiar_precio(valor):
    """Convierte un precio como '$1.399' en número entero."""

    valor = str(valor)

    valor = valor.replace("$", "")
    valor = valor.replace(".", "")
    valor = valor.replace(" ", "")
    valor = valor.strip()

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

    texto = soup.get_text(" ", strip=True)



    nombre = ""

    titulo = soup.find("h1")

    if titulo:
        nombre = titulo.get_text(" ", strip=True)

    # Si no encuentra h1, usamos el título de la página
    if not nombre and soup.title:
        nombre = soup.title.get_text(" ", strip=True)



    precio = None

    coincidencia_precio = re.search(
        r"\$(\d+(?:\.\d{3})*)\s*\(Oferta\)",
        texto
    )

    if coincidencia_precio:
        precio = limpiar_precio(
            coincidencia_precio.group(1)
        )



    precio_normal = None

    coincidencia_normal = re.search(
        r"\$(\d+(?:\.\d{3})*)\s*\(Normal\)",
        texto
    )

    if coincidencia_normal:
        precio_normal = limpiar_precio(
            coincidencia_normal.group(1)
        )



    principio_activo = ""

    coincidencia_activo = re.search(
        r"Principio Activo:\s*(.*?)\s*/",
        texto,
        re.IGNORECASE
    )

    if coincidencia_activo:
        principio_activo = coincidencia_activo.group(1).strip()



    sku = ""

    coincidencia_sku = re.search(
        r"(?:SKU|sku|mpn)[\s:]*([0-9]+)",
        texto
    )

    if coincidencia_sku:
        sku = coincidencia_sku.group(1)



    disponible = False

    palabras_disponibilidad = [
        "Agregar a la bolsa",
        "Agregar al carro",
        "Agregar al carrito",
        "Comprar"
    ]

    for palabra in palabras_disponibilidad:
        if palabra.lower() in texto.lower():
            disponible = True
            break



    producto = {
        "nombre": nombre,
        "principio_activo": principio_activo,
        "precio": precio,
        "precio_normal": precio_normal,
        "sku": sku,
        "disponible": disponible,
        "url": url
    }

    return producto


if __name__ == "__main__":

    url = (
        "https://beta.cruzverde.cl/"
        "paracetamol-500-mg-16-comprimidos/"
        "272241.html"
    )

    producto = obtener_producto(url)

    print("\n--- PRODUCTO EXTRAÍDO ---")
    print("Nombre:", producto["nombre"])
    print("Principio activo:", producto["principio_activo"])
    print("Precio oferta:", producto["precio"])
    print("Precio normal:", producto["precio_normal"])
    print("SKU:", producto["sku"])
    print("Disponible:", producto["disponible"])
    print("URL:", producto["url"])