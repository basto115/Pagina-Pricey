import json
import re
import requests
from bs4 import BeautifulSoup


def limpiar_precio(valor):
    """Convierte un precio chileno a entero."""
    if valor is None:
        return None

    valor = re.sub(r"[^\d]", "", str(valor))
    return int(valor) if valor else None


def obtener_producto(url):
    headers = {"User-Agent": "Mozilla/5.0"}

    respuesta = requests.get(url, headers=headers, timeout=20)
    respuesta.raise_for_status()

    soup = BeautifulSoup(respuesta.text, "html.parser")

    titulo = soup.find("h1")
    nombre = titulo.get_text(" ", strip=True) if titulo else ""

    precio = None
    precio_normal = None
    sku = ""
    disponible = False
    laboratorio = ""
    principio_activo = ""
    presentacion = ""

    # Leer los datos estructurados del producto.
    for script in soup.find_all(
        "script", type="application/ld+json"
    ):
        try:
            datos = json.loads(script.get_text(strip=True))
        except (json.JSONDecodeError, TypeError):
            continue

        elementos = datos if isinstance(datos, list) else [datos]

        for elemento in elementos:
            if not isinstance(elemento, dict):
                continue

            if elemento.get("@type") != "Product":
                continue

            nombre = elemento.get("name") or nombre
            sku = str(elemento.get("sku") or elemento.get("mpn") or "")

            oferta = elemento.get("offers", {})
            if isinstance(oferta, list):
                oferta = oferta[0] if oferta else {}

            if isinstance(oferta, dict):
                precio = limpiar_precio(oferta.get("price"))
                disponibilidad = str(
                    oferta.get("availability", "")
                ).lower()

                disponible = (
                    disponibilidad.endswith("/instock")
                    or disponibilidad.endswith("#instock")
                )

            marca = elemento.get("brand", {})
            if isinstance(marca, dict):
                laboratorio = marca.get("name", "")

            if precio is not None:
                break

        if precio is not None:
            break

    return {
        "nombre": nombre,
        "principio_activo": principio_activo,
        "precio": precio,
        "precio_normal": precio_normal,
        "disponible": disponible,
        "sku": sku,
        "laboratorio": laboratorio,
        "presentacion": presentacion,
        "url": url,
    }


if __name__ == "__main__":
    url = (
        "https://www.farmaciasahumada.cl/"
        "reflexan-10-mg-x-20-comprimidos-recubiertos-6.html"
    )

    print(obtener_producto(url))
