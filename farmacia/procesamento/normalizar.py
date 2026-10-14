
import re
import unicodedata


def limpiar_texto(texto):
    """Limpia espacios y convierte el valor a texto."""
    if texto is None:
        return ""

    texto = str(texto).strip()
    return re.sub(r"\s+", " ", texto)


def normalizar_nombre(nombre):
    return limpiar_texto(nombre)


def normalizar_principio_activo(principio_activo):
    principio_activo = limpiar_texto(principio_activo)

    if not principio_activo:
        return ""

    return principio_activo.capitalize()


def normalizar_precio(precio):
    """
    Convierte precios como '$1.490', '1.490' y '1490' en 1490.
    Devuelve None si el valor está vacío o tiene un formato ambiguo.
    """
    if precio is None or isinstance(precio, bool):
        return None

    precio = limpiar_texto(precio)

    if not precio:
        return None

    precio = precio.replace("$", "").replace(" ", "")

    # Los precios chilenos pueden usar puntos como separadores de miles.
    if not re.fullmatch(r"\d{1,3}(?:\.\d{3})+|\d+", precio):
        return None

    precio = precio.replace(".", "")

    try:
        valor = int(precio)
    except ValueError:
        return None

    return valor if valor > 0 else None


def normalizar_disponibilidad(disponible):
    """Distingue disponibilidad confirmada de información desconocida."""
    if isinstance(disponible, bool):
        return disponible

    if disponible is None:
        return None

    texto = limpiar_texto(disponible).lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caracter for caracter in texto
        if not unicodedata.combining(caracter)
    )

    valores_positivos = {
        "true",
        "1",
        "si",
        "disponible",
        "disponible online",
        "in stock",
        "instock",
    }

    valores_negativos = {
        "false",
        "0",
        "no disponible",
        "agotado",
        "sin stock",
        "out of stock",
        "outofstock",
    }

    if texto in valores_positivos:
        return True

    if texto in valores_negativos:
        return False

    return None


def normalizar_url(url):
    return limpiar_texto(url)


def normalizar_producto(producto, farmacia):
    """Unifica los campos de los scrapers de las cuatro farmacias."""
    return {
        "nombre": normalizar_nombre(producto.get("nombre")),
        "principio_activo": normalizar_principio_activo(
            producto.get("principio_activo")
        ),
        "precio": normalizar_precio(producto.get("precio")),
        "precio_normal": normalizar_precio(
            producto.get("precio_normal")
        ),
        "disponible": normalizar_disponibilidad(
            producto.get("disponible")
        ),
        "url": normalizar_url(producto.get("url")),
        "farmacia": limpiar_texto(farmacia),
        "presentacion": limpiar_texto(producto.get("presentacion")),
        "laboratorio": limpiar_texto(producto.get("laboratorio")),
        "sku": limpiar_texto(producto.get("sku")),
    }


if __name__ == "__main__":
    producto_prueba = {
        "nombre": "  Paracetamol 500 mg x 16 Comprimidos ",
        "principio_activo": "PARACETAMOL",
        "precio": "$1.490",
        "precio_normal": "1.990",
        "disponible": True,
        "url": " https://www.farmaciasahumada.cl/ ",
        "presentacion": "16 comprimidos",
        "laboratorio": "Laboratorio de prueba",
        "sku": "12345",
    }

    resultado = normalizar_producto(
        producto_prueba,
        "Farmacias Ahumada",
    )

    print("\nProducto normalizado:")
    for campo, valor in resultado.items():
        print(f"{campo}: {valor}")
