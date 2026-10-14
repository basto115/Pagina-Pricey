import json
import re

import requests
from bs4 import BeautifulSoup


def limpiar_precio(valor):
    """Convierte un texto de precio a entero. Devuelve None si no es válido."""
    if valor is None:
        return None

    texto = str(valor).strip()
    texto = re.sub(r"[^\d,\.]", "", texto)

    if not texto:
        return None

    # Los precios de productos chilenos suelen expresarse en pesos enteros.
    # Si hay separadores de miles, se eliminan.
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", "")
    elif "." in texto:
        partes = texto.split(".")
        if len(partes) > 1 and len(partes[-1]) == 3:
            texto = "".join(partes)

    try:
        precio = int(float(texto))
    except (ValueError, TypeError, OverflowError):
        return None

    return precio if precio > 0 else None


def obtener_producto(url):
    """Obtiene los datos de un producto desde Farmacias Ahumada."""

    encabezados = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
    }

    try:
        respuesta = requests.get(
            url,
            headers=encabezados,
            timeout=20,
        )
        respuesta.raise_for_status()
    except requests.RequestException as error:
        print(f"Error al consultar Farmacias Ahumada: {error}")
        return None

    sopa = BeautifulSoup(respuesta.text, "html.parser")

    nombre = ""
    sku = ""
    precio = None
    precio_normal = None
    disponible = None
    principio_activo = ""
    laboratorio = ""
    presentacion = ""

    # Buscar datos estructurados JSON-LD de tipo Product.
    datos_producto = None

    for script in sopa.find_all(
        "script",
        type="application/ld+json",
    ):
        contenido = script.string or script.get_text(strip=True)

        if not contenido:
            continue

        try:
            datos_json = json.loads(contenido)
        except (json.JSONDecodeError, TypeError):
            continue

        elementos = (
            datos_json
            if isinstance(datos_json, list)
            else [datos_json]
        )

        pendientes = list(elementos)

        while pendientes:
            elemento = pendientes.pop(0)

            if not isinstance(elemento, dict):
                continue

            grafo = elemento.get("@graph")
            if isinstance(grafo, list):
                pendientes.extend(grafo)

            tipo = elemento.get("@type", [])
            if isinstance(tipo, str):
                tipo = [tipo]

            if any(
                str(t).lower() == "product"
                for t in tipo
            ):
                datos_producto = elemento
                break

        if datos_producto:
            break

    # Nombre y otros datos del producto.
    if datos_producto:
        nombre = str(
            datos_producto.get("name") or ""
        ).strip()

        sku = str(
            datos_producto.get("sku")
            or datos_producto.get("mpn")
            or ""
        ).strip()

        marca = datos_producto.get("brand")
        if isinstance(marca, dict):
            laboratorio = str(
                marca.get("name") or ""
            ).strip()
        elif isinstance(marca, str):
            laboratorio = marca.strip()

        descripcion = str(
            datos_producto.get("description") or ""
        ).strip()

        if descripcion:
            coincidencia = re.search(
                r"(?:principio activo|composición|composicion)"
                r"\s*:\s*([^.;]+)",
                descripcion,
                re.IGNORECASE,
            )
            if coincidencia:
                principio_activo = coincidencia.group(1).strip()

        # PRECIO Y DISPONIBILIDAD.
        ofertas = datos_producto.get("offers", [])

        if isinstance(ofertas, dict):
            ofertas = [ofertas]

        for oferta in ofertas:
            if not isinstance(oferta, dict):
                continue

            moneda = oferta.get("priceCurrency")

            if moneda and str(moneda).upper() != "CLP":
                continue

            valor = oferta.get("price")

            if valor is None:
                especificacion = oferta.get(
                    "priceSpecification", {}
                )

                if isinstance(especificacion, dict):
                    valor = especificacion.get("price")

            precio_candidato = limpiar_precio(valor)

            if precio_candidato is None:
                continue

            precio = precio_candidato

            disponibilidad = str(
                oferta.get("availability") or ""
            ).lower()

            if (
                "instock" in disponibilidad
                or "limitedavailability" in disponibilidad
            ):
                disponible = True
            elif (
                "outofstock" in disponibilidad
                or "soldout" in disponibilidad
                or "discontinued" in disponibilidad
            ):
                disponible = False
            else:
                disponible = None

            # Si hay una oferta válida, se utiliza.
            break

    # Si el JSON-LD no incluye el nombre, intentar obtenerlo del HTML.
    if not nombre:
        encabezado = sopa.find("h1")
        if encabezado:
            nombre = encabezado.get_text(" ", strip=True)

    if not nombre:
        etiqueta_titulo = sopa.find("title")
        if etiqueta_titulo:
            nombre = etiqueta_titulo.get_text(" ", strip=True)

    # Intentar recuperar información adicional del texto visible.
    texto_pagina = sopa.get_text(" ", strip=True)

    if not principio_activo:
        coincidencia = re.search(
            r"(?:principio activo|composición|composicion)"
            r"\s*:?\s*([^.;|]+)",
            texto_pagina,
            re.IGNORECASE,
        )
        if coincidencia:
            principio_activo = coincidencia.group(1).strip()

    if not presentacion and nombre:
        coincidencia = re.search(
            r"\b\d+(?:[.,]\d+)?\s*"
            r"(?:mg|g|ml|l|mcg|µg| unidades| comprimidos| cápsulas| capsulas)"
            r"\b.*",
            nombre,
            re.IGNORECASE,
        )
        if coincidencia:
            presentacion = coincidencia.group(0).strip()

    # Si el precio no apareció en JSON-LD, intentar localizarlo
    # en algunos atributos habituales del HTML.
    if precio is None:
        selectores_precio = [
            "[itemprop='price']",
            "[data-price]",
            ".price",
            ".sales",
            ".product-price",
        ]

        for selector in selectores_precio:
            elemento = sopa.select_one(selector)

            if not elemento:
                continue

            valor = (
                elemento.get("content")
                or elemento.get("data-price")
                or elemento.get_text(" ", strip=True)
            )

            precio_candidato = limpiar_precio(valor)

            if precio_candidato is not None:
                precio = precio_candidato
                break

    # No inventar disponibilidad ni precio normal si no se encontraron.
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
