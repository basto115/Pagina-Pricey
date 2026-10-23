import re

CATEGORIAS_VALIDAS = {
    "medicamentos",
    "cuidado_personal",
    "cosmeticos",
    "otros",
}


def limpiar_texto(texto):
    """Limpia espacios y normaliza texto."""
    if texto is None:
        return ""

    texto = str(texto).strip()
    texto = re.sub(r"\s+", " ", texto)

    return texto


def normalizar_nombre(nombre):
    """Normaliza el nombre del producto."""
    return limpiar_texto(nombre)


def normalizar_principio_activo(principio_activo):
    """Normaliza el principio activo."""
    principio_activo = limpiar_texto(principio_activo)

    if not principio_activo:
        return ""

    return principio_activo.capitalize()



def normalizar_precio(precio):
    """Convierte precios como '$1.490', '$ 1.490' o '1490' en 1490."""
    if precio is None:
        return None

    precio = str(precio).strip()
    digitos = re.sub(r"\D", "", precio)

    if not digitos:
        return None

    try:
        return int(digitos)
    except ValueError:
        return None
    
    precio = str(precio)
    precio = precio.replace("$", "")
    precio = precio.replace(".", "")
    precio = precio.replace(" ", "")
    precio = precio.strip()

    if not precio:
        return None

    try:
        return int(precio)
    except (ValueError, TypeError):
        return None


def normalizar_disponibilidad(disponible):
    """Convierte diferentes valores a True o False."""
    if isinstance(disponible, bool):
        return disponible

    if disponible is None:
        return False

    disponible = limpiar_texto(disponible).lower()

    valores_positivos = {
        "true",
        "1",
        "si",
        "sí",
        "disponible",
        "disponible online",
        "comprar",
        "agregar al carro",
        "agregar al carrito",
        "añadir al carro",
    }

    return disponible in valores_positivos


def normalizar_url(url):
    """Limpia la URL del producto."""
    return limpiar_texto(url)


def normalizar_categoria(categoria):
    """Valida y normaliza la categoría del producto."""
    categoria = limpiar_texto(categoria).lower()

    if categoria in CATEGORIAS_VALIDAS:
        return categoria

    return "otros" if categoria else "medicamentos"


def normalizar_producto(producto, farmacia):
    """
    Unifica los datos recibidos desde los scrapers
    y conserva los campos útiles para guardar el producto.
    """
    return {
        "nombre": normalizar_nombre(
            producto.get("nombre")
        ),
        "principio_activo": normalizar_principio_activo(
            producto.get("principio_activo")
        ),
        "precio": normalizar_precio(
            producto.get("precio")
        ),
        "precio_normal": normalizar_precio(
            producto.get("precio_normal")
        ),
        "disponible": normalizar_disponibilidad(
            producto.get("disponible")
        ),
        "url": normalizar_url(
            producto.get("url")
        ),
        "farmacia": farmacia,
        "categoria": normalizar_categoria(
            producto.get("categoria")
        ),
        "sku": limpiar_texto(
            producto.get("sku")
        ),
        "laboratorio": limpiar_texto(
            producto.get("laboratorio")
        ),
        "presentacion": limpiar_texto(
            producto.get("presentacion")
        ),
    }


if __name__ == "__main__":
    producto_prueba = {
        "nombre": "  Paracetamol 500 mg x 16 Comprimidos ",
        "principio_activo": "PARACETAMOL",
        "precio": "$1.490",
        "precio_normal": "1.990",
        "disponible": True,
        "url": "https://www.farmaciasahumada.cl/",
        "categoria": "medicamentos",
        "sku": "12345",
        "laboratorio": "Laboratorio de prueba",
        "presentacion": "16 comprimidos",
    }

    resultado = normalizar_producto(
        producto_prueba,
        "Farmacia Ahumada"
    )

    print("\nProducto normalizado:")

    for campo, valor in resultado.items():
        print(f"{campo}: {valor}")
