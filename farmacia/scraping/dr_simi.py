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

def extraer_presentacion(nombre):
    nombre = nombre.lower()

    concentraciones = re.findall(
        r"\d+(?:[.,]\d+)?\s*(?:mg/ml|mcg/ml|mg|mcg|g)\b",
        nombre
    )

    formas = [
        "comprimidos recubiertos",
        "comprimidos",
        "cápsulas blandas",
        "cápsulas",
        "capsulas",
        "jarabe",
        "suspensión oral",
        "suspension oral",
        "solución oral",
        "solucion oral",
        "gotas",
        "crema",
        "gel",
        "ampollas",
        "sobres"
    ]

    forma = next(
        (f for f in formas if f in nombre),
        ""
    )

    cantidad = re.search(
        r"\b(\d+)\s*(comprimidos|cápsulas|capsulas|sobres|ampollas|ml)\b",
        nombre
    )

    partes = []

    partes.extend(concentraciones)

    if forma and not (
        cantidad and forma in cantidad.group(2)
    ):
        partes.append(forma)

    if cantidad:
        partes.append(
            cantidad.group(1) + " " + cantidad.group(2)
        )

    return " ".join(partes)


def extraer_principio_activo(nombre):
    nombre = nombre.strip()

    coincidencia = re.search(
        r"\b\d+(?:[.,]\d+)?\s*(?:mg/ml|mcg/ml|mg|mcg|g)\b",
        nombre,
        flags=re.IGNORECASE
    )

    if not coincidencia:
        return ""

    texto = nombre[:coincidencia.start()].strip()
    palabras = texto.split()

    if len(palabras) <= 1:
        return texto

    # Quitar marca comercial inicial y su posible concentración
    # numérica, por ejemplo: "Alix 2,5".
    texto = re.sub(
        r"^[^\s]+\s+\d+(?:[.,]\d+)?\s+",
        "",
        texto
    )

    if texto == nombre[:coincidencia.start()].strip():
        texto = " ".join(palabras[1:])

    return texto.strip()

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
        offers = datos_producto.get("offers", {})

        if isinstance(offers, dict):
            ofertas_internas = offers.get("offers", [])

            if isinstance(ofertas_internas, dict):
                ofertas_internas = [ofertas_internas]

            disponibilidad = offers.get("availability", "")

            if "InStock" in disponibilidad:
                disponible = True

            for oferta in ofertas_internas:
                disponibilidad = oferta.get("availability", "")

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
        "principio_activo": extraer_principio_activo(nombre),
        "laboratorio": laboratorio,
        "presentacion": extraer_presentacion(nombre),
        "sku": datos_producto.get("sku", "") if datos_producto else "",
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
    
