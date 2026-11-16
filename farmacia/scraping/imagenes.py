
import json
from io import BytesIO
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, UnidentifiedImageError


def buscar_imagen_json(datos):
    if isinstance(datos, list):
        for elemento in datos:
            resultado = buscar_imagen_json(elemento)
            if resultado:
                return resultado

    elif isinstance(datos, dict):
        tipo = datos.get("@type")

        if tipo == "Product" or (
            isinstance(tipo, list) and "Product" in tipo
        ):
            imagen = datos.get("image")

            if isinstance(imagen, str):
                return imagen

            if isinstance(imagen, list) and imagen:
                primera = imagen[0]

                if isinstance(primera, str):
                    return primera

                if isinstance(primera, dict):
                    return primera.get("url")

            if isinstance(imagen, dict):
                return imagen.get("url")

        for valor in datos.values():
            resultado = buscar_imagen_json(valor)
            if resultado:
                return resultado

    return None


def extraer_url_imagen(soup, url_base):
    """Extrae la URL de la imagen principal del producto."""

    # 1. JSON-LD
    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):
        try:
            datos = json.loads(script.get_text())
            resultado = buscar_imagen_json(datos)

            if resultado:
                return urljoin(url_base, resultado)

        except (ValueError, TypeError):
            continue

    # 2. Open Graph
    for selector in [
        'meta[property="og:image"]',
        'meta[name="twitter:image"]',
    ]:
        etiqueta = soup.select_one(selector)

        if etiqueta and etiqueta.get("content"):
            return urljoin(url_base, etiqueta["content"])

    # 3. Imágenes de la ficha del producto
    selectores = [
        "main img",
        "[class*='product'] img",
        "img[itemprop='image']",
    ]

    for selector in selectores:
        for imagen in soup.select(selector):
            src = (
                imagen.get("src")
                or imagen.get("data-src")
                or imagen.get("data-original")
                or imagen.get("data-lazy-src")
            )

            if not src:
                continue

            src = src.strip()

            if src.startswith("data:"):
                continue

            if any(
                palabra in src.lower()
                for palabra in ["logo", "icon", "banner", "placeholder"]
            ):
                continue

            return urljoin(url_base, src)

    return None


def descargar_imagen_webp(url):
    """Descarga una imagen y la convierte a WEBP."""

    if not url:
        return None

    try:
        respuesta = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
            stream=True,
        )

        respuesta.raise_for_status()

        if not respuesta.headers.get(
            "Content-Type", ""
        ).startswith("image/"):
            return None

        contenido = bytearray()

        for fragmento in respuesta.iter_content(65536):
            contenido.extend(fragmento)

            if len(contenido) > 5 * 1024 * 1024:
                return None

        imagen = Image.open(BytesIO(contenido))
        imagen = ImageOps.exif_transpose(imagen)
        imagen.thumbnail((800, 800), Image.Resampling.LANCZOS)

        if imagen.mode not in ("RGB", "RGBA"):
            imagen = imagen.convert("RGB")

        salida = BytesIO()

        imagen.save(
            salida,
            format="WEBP",
            quality=78,
            method=6,
        )

        return salida.getvalue()

    except (
        requests.RequestException,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        return None

def guardar_imagen_producto(url, producto):
    from farmacia.models import ImagenProducto

    if not url:
        return False

    filtros = (
        {"medicamento_id": producto.medicamento_id}
        if producto.medicamento_id
        else {"producto_id": producto.id}
    )

    if ImagenProducto.objects.filter(**filtros).exists():
        return False

    contenido = descargar_imagen_webp(url)

    if not contenido:
        return False

    try:
        ImagenProducto.objects.create(
            **filtros,
            imagen=contenido,
            formato="WEBP"
        )
        return True
    except Exception as error:
        print(f"Error guardando imagen del producto {producto.id}: {error}")
        return False