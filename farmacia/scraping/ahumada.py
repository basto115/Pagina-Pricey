import re
import requests
from bs4 import BeautifulSoup
import json

def limpiar_precio(valor):
    """Convierte precios como '$1.309' en 1309."""

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

    print(
        "Código HTTP:",
        respuesta.status_code
    )

    respuesta.raise_for_status()

    soup = BeautifulSoup(
        respuesta.text,
        "html.parser"
    )

    texto = soup.get_text(
        " ",
        strip=True
    )

    # -----------------------------
    # NOMBRE
    # -----------------------------

    nombre = ""

    titulo = soup.find("h1")

    if titulo:

        nombre = titulo.get_text(
            " ",
            strip=True
        )

    if not nombre and soup.title:

        nombre = soup.title.get_text(
            " ",
            strip=True
        )

    # PRECIO Y DATOS ESTRUCTURADOS
    precio = None
    precio_normal = None
    sku = ""
    disponible = False

    def buscar_producto_json(datos):
        if isinstance(datos, list):
            for elemento in datos:
                resultado = buscar_producto_json(elemento)
                if resultado:
                    return resultado

        elif isinstance(datos, dict):
            tipo = datos.get("@type")

            if tipo == "Product" or (
                isinstance(tipo, list) and "Product" in tipo
            ):
                ofertas = datos.get("offers", {})

                if isinstance(ofertas, list):
                    ofertas = ofertas[0] if ofertas else {}

                if isinstance(ofertas, dict) and ofertas.get("price"):
                    return datos, ofertas

            for valor in datos.values():
                resultado = buscar_producto_json(valor)
                if resultado:
                    return resultado

        return None

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):
        try:
            contenido = json.loads(
                script.string or script.get_text()
            )

            resultado = buscar_producto_json(contenido)

            if resultado:
                producto_json, oferta = resultado

                precio = limpiar_precio(oferta["price"])
                sku = str(
                    producto_json.get("sku")
                    or producto_json.get("mpn")
                    or ""
                )

                disponibilidad = str(
                    oferta.get("availability", "")
                )

                disponible = (
                    "instock" in disponibilidad.lower()
                    and "outofstock" not in disponibilidad.lower()
                )

                break

        except (json.JSONDecodeError, ValueError, TypeError):
            continue

    # -----------------------------
    # PRINCIPIO ACTIVO
    # -----------------------------

    principio_activo = ""

    coincidencia_activo = re.search(
        r"Principio Activo\s*:?\s*"
        r"([A-Za-zÁÉÍÓÚÑáéíóúñ ]+?)"
        r"(?:Registro Sanitario|$)",
        texto,
        re.IGNORECASE
    )

    if coincidencia_activo:

        principio_activo = (
            coincidencia_activo
            .group(1)
            .strip()
        )

    # -----------------------------
    # DISPONIBILIDAD
    # -----------------------------

    disponible = False

    palabras_disponibilidad = [
        "Agregar al carrito",
        "Agregar al Carrito",
        "Comprar"
    ]

    for palabra in palabras_disponibilidad:

        if palabra.lower() in texto.lower():

            disponible = True
            break

    # -----------------------------
    # RESULTADO
    # -----------------------------

    producto = {

        "nombre": nombre,

        "principio_activo": principio_activo,

        "precio": precio,

        "precio_normal": precio_normal,

        "disponible": disponible,

        "sku": sku,

        "laboratorio": "",

        "presentacion": "",

        "url": url
    }

    return producto


if __name__ == "__main__":

    url = (
        "https://www.farmaciasahumada.cl/"
        "paracetamol-500-mg-x-16-comprimidos-84574.html"
    )

    producto = obtener_producto(url)

    print("\n--- PRODUCTO EXTRAÍDO ---")

    for clave, valor in producto.items():
        print(f"{clave}: {valor}")