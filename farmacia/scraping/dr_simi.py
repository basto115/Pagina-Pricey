import re
import json
import time
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://www.drsimi.cl"


def limpiar_precio(valor):
    """Convierte un precio como '$1.990' en número."""
    if valor is None:
        return None

    valor = str(valor)
    valor = valor.replace("$", "")
    valor = valor.replace(".", "")
    valor = valor.replace(" ", "")
    valor = valor.strip()

    try:
        return int(valor)
    except ValueError:
        return None


def obtener_datos_json_ld(soup):
    """
    Busca los datos del producto dentro de JSON-LD.
    """
    scripts = soup.find_all(
        "script",
        type="application/ld+json"
    )

    for script in scripts:
        try:
            datos = json.loads(script.get_text())

            # Puede venir como lista
            if isinstance(datos, list):
                for item in datos:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item

            # Puede venir como diccionario
            if isinstance(datos, dict):
                if datos.get("@type") == "Product":
                    return datos

                # Algunas páginas utilizan @graph
                graph = datos.get("@graph", [])

                for item in graph:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item

        except (json.JSONDecodeError, TypeError):
            continue

    return None


def obtener_producto(url):
    """
    Entra a la página individual de un producto
    y extrae su información.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/155.0.0.0 Safari/537.36"
        )
    }

    respuesta = requests.get(
        url,
        headers=headers,
        timeout=15
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

    # ---------------------------------
    # JSON-LD
    # ---------------------------------

    datos_producto = obtener_datos_json_ld(soup)

    # ---------------------------------
    # Nombre
    # ---------------------------------

    nombre = ""

    if datos_producto:
        nombre = datos_producto.get(
            "name",
            ""
        )

    if not nombre and soup.title:
        nombre = soup.title.get_text(
            strip=True
        )

    # ---------------------------------
    # Laboratorio / Marca
    # ---------------------------------

    laboratorio = ""

    if datos_producto:

        marca = datos_producto.get(
            "brand"
        )

        if isinstance(marca, dict):
            laboratorio = marca.get(
                "name",
                ""
            )

        elif isinstance(marca, str):
            laboratorio = marca

    # ---------------------------------
    # Precio
    # ---------------------------------

    precio = None
    precio_normal = None

    if datos_producto:

        offers = datos_producto.get(
            "offers",
            {}
        )

        # Puede ser diccionario
        if isinstance(offers, dict):

            precio = offers.get(
                "price"
            )

            if precio is None:
                precio = offers.get(
                    "lowPrice"
                )

        # Puede ser lista
        elif isinstance(offers, list):

            if offers:

                primera_oferta = offers[0]

                precio = primera_oferta.get(
                    "price"
                )

    # Convertir precio
    if precio is not None:
        try:
            precio = int(float(precio))
        except (ValueError, TypeError):
            precio = limpiar_precio(precio)

    # ---------------------------------
    # Precio desde texto
    # ---------------------------------

    if precio is None:

        precios = re.findall(
            r"\$\s*([\d.]+)",
            texto
        )

        if precios:
            precio = limpiar_precio(
                precios[-1]
            )

    # ---------------------------------
    # Disponibilidad
    # ---------------------------------

    disponible = False

    if datos_producto:

        offers = datos_producto.get(
            "offers",
            {}
        )

        if isinstance(offers, dict):

            disponibilidad = offers.get(
                "availability",
                ""
            )

            if "InStock" in disponibilidad:
                disponible = True

        elif isinstance(offers, list):

            for oferta in offers:

                disponibilidad = oferta.get(
                    "availability",
                    ""
                )

                if "InStock" in disponibilidad:
                    disponible = True
                    break

    # ---------------------------------
    # Disponibilidad desde texto
    # ---------------------------------

    if not disponible:

        texto_minuscula = texto.lower()

        if (
            "en stock" in texto_minuscula
            or "disponible" in texto_minuscula
        ):
            disponible = True

    # ---------------------------------
    # Producto final
    # ---------------------------------

    producto = {
        "nombre": nombre,
        "principio_activo": "",
        "laboratorio": laboratorio,
        "precio": precio,
        "precio_normal": precio_normal,
        "disponible": disponible,
        "url": url
    }

    return producto


def obtener_urls_productos(pagina=1):
    """
    Obtiene las URLs de los productos
    desde una página del catálogo de medicamentos.
    """

    if pagina == 1:
        url = f"{BASE_URL}/medicamentos"
    else:
        url = f"{BASE_URL}/medicamentos?page={pagina}"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/155.0.0.0 Safari/537.36"
        )
    }

    respuesta = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    respuesta.raise_for_status()

    soup = BeautifulSoup(
        respuesta.text,
        "html.parser"
    )

    urls = set()

    for enlace in soup.find_all("a", href=True):

        href = enlace["href"]

        # Convertimos URL relativa en absoluta
        url_producto = urljoin(
            BASE_URL,
            href
        )

        # Los productos de Dr. Simi terminan en /p
        if url_producto.endswith("/p"):

            urls.add(
                url_producto
            )

    return list(urls)


def obtener_productos(paginas=1):
    """
    Recorre una o varias páginas del catálogo
    y obtiene todos los productos encontrados.
    """

    productos = []

    urls_vistas = set()

    for pagina in range(1, paginas + 1):

        print(
            f"\n========== PÁGINA {pagina} =========="
        )

        try:

            urls = obtener_urls_productos(
                pagina
            )

            print(
                f"Productos encontrados: {len(urls)}"
            )

        except Exception as e:

            print(
                f"Error obteniendo página {pagina}: {e}"
            )

            continue

        for numero, url in enumerate(
            urls,
            start=1
        ):

            if url in urls_vistas:
                continue

            urls_vistas.add(url)

            try:

                producto = obtener_producto(
                    url
                )

                productos.append(
                    producto
                )

                print(
                    f"[{numero}/{len(urls)}] "
                    f"{producto['nombre']} "
                    f"- ${producto['precio']}"
                )

            except Exception as e:

                print(
                    f"Error obteniendo {url}: {e}"
                )

            # Esperamos un poco para no hacer
            # demasiadas solicitudes seguidas
            time.sleep(0.5)

    return productos


if __name__ == "__main__":

    productos = obtener_productos(
        paginas=1
    )

    print("\n")
    print("==============================")
    print("PRODUCTOS EXTRAÍDOS")
    print("==============================")

    for producto in productos:

        print("\n------------------------------")

        print(
            "Nombre:",
            producto["nombre"]
        )

        print(
            "Laboratorio:",
            producto["laboratorio"]
        )

        print(
            "Precio:",
            producto["precio"]
        )

        print(
            "Disponible:",
            producto["disponible"]
        )

        print(
            "URL:",
            producto["url"]
        )

    print("\n")
    print(
        f"TOTAL PRODUCTOS: {len(productos)}"
    )