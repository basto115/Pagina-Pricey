import re
import json
import requests
from bs4 import BeautifulSoup


def limpiar_precio(valor):
    """Convierte un precio como '$1.990' en número."""
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

    texto = soup.get_text(" ", strip=True)

    # -------------------------
    # Nombre del producto
    # -------------------------

    nombre = ""

    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    datos_producto = None

    for script in scripts:
        try:
            datos = json.loads(script.get_text())

            if datos.get("@type") == "Product":
                datos_producto = datos
                break

        except json.JSONDecodeError:
            continue

    if datos_producto:
        nombre = datos_producto.get("name", "")

    # Si no se encuentra en JSON-LD, usamos el título
    if not nombre and soup.title:
        nombre = soup.title.get_text(strip=True)

    # -------------------------
    # Laboratorio
    # -------------------------

    laboratorio = ""

    if datos_producto:
        marca = datos_producto.get("brand")

        if isinstance(marca, dict):
            laboratorio = marca.get("name", "")

    # -------------------------
    # Precio
    # -------------------------

    precio = None

    if datos_producto:
        offers = datos_producto.get("offers", {})

        if "lowPrice" in offers:
            precio = offers["lowPrice"]

    # Si no se encuentra en JSON-LD, buscamos en el texto
    if precio is None:

        coincidencia_precio = re.search(
            r"\$\s*(\d+(?:\.\d{3})*)",
            texto
        )

        if coincidencia_precio:
            precio = limpiar_precio(
                coincidencia_precio.group(1)
            )

    # -------------------------
    # Disponibilidad
    # -------------------------

    disponible = False

    if datos_producto:
        offers = datos_producto.get("offers", {})

        oferta = offers.get("offers", [])

        if oferta:
            disponibilidad = oferta[0].get(
                "availability",
                ""
            )

            disponible = "InStock" in disponibilidad

    # Si no se encuentra en JSON-LD
    if not disponible:
        disponible = "En Stock" in texto

    # -------------------------
    # Producto final
    # -------------------------

    producto = {
        "nombre": nombre,
        "laboratorio": laboratorio,
        "precio": precio,
        "precio_normal": None,
        "disponible": disponible,
        "url": url
    }

    return producto


if __name__ == "__main__":

    url = "https://www.drsimi.cl/paracetamol-500-mg-16-comprimidos/p"

    producto = obtener_producto(url)

    print("\n--- PRODUCTO EXTRAÍDO ---")
    print("Nombre:", producto["nombre"])
    print("Laboratorio:", producto["laboratorio"])
    print("Precio:", producto["precio"])
    print("Precio normal:", producto["precio_normal"])
    print("Disponible:", producto["disponible"])
    print("URL:", producto["url"])