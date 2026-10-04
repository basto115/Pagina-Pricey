import re
import requests
from bs4 import BeautifulSoup

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

    print("Código HTTP:", respuesta.status_code)

    respuesta.raise_for_status()

    html = respuesta.text

    soup = BeautifulSoup(
        html,
        "html.parser"
    )
    
    texto = soup.get_text(
        " ",
        strip=True
    )
    
    # Nombre del producto
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

    # Precios del producto principal
    precios = []

    for elemento in soup.find_all(string=re.compile(r"\$")):

        texto_precio = elemento.strip()

        coincidencia = re.search(
            r"\$(\d+(?:\.\d{3})*)",
            texto_precio
        )

        if coincidencia:
            valor = limpiar_precio(
                coincidencia.group(1)
            )

            # Ignorar el precio del banner de despacho gratis
            if valor == 34990:
                continue

            if valor not in precios:
                precios.append(valor)

    # Los primeros dos precios restantes corresponden al producto
    precio = precios[0] if len(precios) > 0 else None
    precio_normal = precios[1] if len(precios) > 1 else None

    # Principio activo
    principio_activo = ""

    coincidencia_activo = re.search(
        r"Principio Activo\s*:?\s*([A-Za-zÁÉÍÓÚÑáéíóúñ ]+?)(?:Registro Sanitario|$)",
        texto,
        re.IGNORECASE
    )

    if coincidencia_activo:
        principio_activo = coincidencia_activo.group(1).strip()

    # Disponibilidad
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

    producto = {
        "nombre": nombre,
        "principio_activo": principio_activo,
        "precio": precio,
        "precio_normal": precio_normal,
        "disponible": disponible,
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
    print("Nombre:", producto["nombre"])
    print("Principio activo:", producto["principio_activo"])
    print("Precio:", producto["precio"])
    print("Precio normal:", producto["precio_normal"])
    print("Disponible:", producto["disponible"])
    print("URL:", producto["url"])