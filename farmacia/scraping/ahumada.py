
import json
import re
import requests
from bs4 import BeautifulSoup


def limpiar_precio(valor):
    """Convierte precios como '$1.309' en 1309."""
    if valor is None:
        return None

    valor = str(valor).strip()
    valor = valor.replace("$", "").replace(" ", "")
    valor = valor.replace(".", "").replace(",", "")

    try:
        return int(valor)
    except (ValueError, TypeError):
        return None


def obtener_producto(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    respuesta = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print("Código HTTP:", respuesta.status_code)
    respuesta.raise_for_status()

    soup = BeautifulSoup(
        respuesta.text,
        "html.parser"
    )

    texto = soup.get_text(" ", strip=True)

    # ---------------------------------
    # DATOS ESTRUCTURADOS DEL PRODUCTO
    # ---------------------------------

    datos_producto = None

    def buscar_productos(datos):
        """Busca objetos Product dentro del JSON-LD."""
        if isinstance(datos, list):
            for elemento in datos:
                resultado = buscar_productos(elemento)
                if resultado:
                    return resultado

        elif isinstance(datos, dict):
            tipo = datos.get("@type", [])

            if isinstance(tipo, str):
                tipo = [tipo]

            if "Product" in tipo:
                return datos

            # Algunos sitios agrupan datos dentro de @graph.
            if "@graph" in datos:
                resultado = buscar_productos(datos["@graph"])
                if resultado:
                    return resultado

        return None

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):
        contenido = script.string or script.get_text()

        try:
            datos = json.loads(contenido)
            datos_producto = buscar_productos(datos)

            if datos_producto:
                break

        except (json.JSONDecodeError, TypeError):
            continue

    # ---------------------------------
    # NOMBRE
    # ---------------------------------

    nombre = ""

    if datos_producto:
        nombre = datos_producto.get("name", "") or ""

    if not nombre:
        titulo = soup.find("h1")

        if titulo:
            nombre = titulo.get_text(" ", strip=True)

    if not nombre and soup.title:
        nombre = soup.title.get_text(" ", strip=True)

    # ---------------------------------
    # PRECIO Y DISPONIBILIDAD
    # ---------------------------------

    precio = None
    precio_normal = None
    disponible = False
    sku = ""

    if datos_producto:
        sku = str(
            datos_producto.get("sku")
            or datos_producto.get("mpn")
            or ""
        )

        ofertas = datos_producto.get("offers", [])

        if isinstance(ofertas, dict):
            ofertas = [ofertas]

        # Utilizamos una oferta que tenga un precio válido.
        for oferta in ofertas:
            if not isinstance(oferta, dict):
                continue

            moneda = oferta.get("priceCurrency")

            if moneda and moneda != "CLP":
                continue

            valor = oferta.get("price")

            if valor is None:
                precio_especificacion = oferta.get(
                    "priceSpecification", {}
                )

                if isinstance(precio_especificacion, dict):
                    valor = precio_especificacion.get("price")

            if valor is not None:
                try:
                    precio = int(float(str(valor).replace(",", ".")))
                except (ValueError, TypeError):
                    precio = None

            if precio is not None and precio > 0:
                disponibilidad = str(
                    oferta.get("availability", "")
                ).lower()

                disponible = (
                    "instock" in disponibilidad
                    or "limitedavailability" in disponibilidad
                )
                break

            precio = None

    # ---------------------------------
    # PRINCIPIO ACTIVO
    # ---------------------------------

    principio_activo = ""

    coincidencia_activo = re.search(
        r"Principio Activo\s*:?\s*"
        r"([A-Za-zÁÉÍÓÚÑáéíóúñ ,\-]+?)"
        r"(?=Registro Sanitario|$)",
        texto,
        re.IGNORECASE
    )

    if coincidencia_activo:
        principio_activo = (
            coincidencia_activo.group(1).strip()
        )

    # ---------------------------------
    # RESULTADO
    # ---------------------------------

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
        "reflexan-10-mg-x-20-comprimidos-recubiertos-6.html"
    )

    producto = obtener_producto(url)

    print("\n--- PRODUCTO EXTRAÍDO ---")

    for clave, valor in producto.items():
        print(f"{clave}: {valor}")
