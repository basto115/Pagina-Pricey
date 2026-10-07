import re 
import requests
from bs4 import BeautifulSoup

def limpiar_precio(valor):
    """Convierte un precio como '$1.399' en número entero."""
    
    valor = str(valor)
    
    valor = valor.replace("$", "")
    valor = valor.replace(".", "")
    valor = valor.replace("", "")
    valor = valor.strip()
    
    return int(valor)

def obtener_producto(url):
    headers = {
        "User-agent": "Mozilla/5.0"
    }
    
    respuesta = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    respuesta.raise_for_status()
    
    soup = BeautifulSoup(respuesta.text, "html.parser")
    
    texto = soup.get_text(" ", strip=True)
    
    #nombre del producto
    nombre = ""
    
    titulo = soup.find("h1")
    
    if titulo:
        nombre = titulo.get_text(" ", strip=True)
        
    #si no encuentra h1, usamos el titulo de la pagina
    if not nombre and soup.title:
        nombre = soup.title.get_text(" ", strip=True)
        
    # el precio
    precio = None
    
    coincidencia_precio = re.search(
        r"\$(\d+(?:\.\d{3})*)\s*Precio Farmacia",
        texto
    )
    
    if coincidencia_precio:
        precio = limpiar_precio(
            coincidencia_precio.group(1)
        )
        
    # el precio pero en internet
    precio_internet = None
    
    coincidencia_internet = re.search(
        r"\$(\d+(?:\.\d{3})*)\s*Precio Internet",
        texto
    )
    
    if coincidencia_internet:
        precio_internet = limpiar_precio(
            coincidencia_internet.group(1)
        )

    #principio activo
    principio_activo = ""
    
    coincidencia_activo = re.search(
        r"Principio Activo:\s*(.*?)\s*/",
        texto
    )
    
    if coincidencia_activo:
        principio_activo = coincidencia_activo.group(1).strip()
        
    #sku
    
    sku = ""
    
    coincidencia_sku = re.search(
        r"SKU:\s*(\d+)",
        texto
    ) 
    
    if coincidencia_sku:
        sku = coincidencia_sku.group(1)
        
    #disponibilidad
    disponibilidad = False
    
    palabras_disponibilidad = [
        "Agregar al carro",
        "Agregar al carrito",
        "Comprar",
        "Añadir al carro"
    ]
    
    for palabra in palabras_disponibilidad:
        if palabra.lower() in texto.lower():
            disponible = True
            break
        
    producto = {
        "nombre": nombre,
        "principio_activo": principio_activo,
        "precio": precio,
        "precio_normal": None,
        "disponible": disponible,
        "url": url
    }
    
    return producto

if __name__ == "__main__":
    
    url = (
        "https://salcobrand.cl/products/"
        "paracetamol-b-500-mg-16-comprimidos"
        "?current_store_id=1"
        "&default_sku=432432"
        "&taxon_id=12976"
    )
    
    producto = obtener_producto(url)
    
    print("\n--- PRODUCTO EXTRAÍDO ---")
    print("Nombre:", producto["nombre"])
    print("Principio activo:", producto["principio_activo"])
    print("Precio farmacia:", producto["precio"])
    print("Precio Internet:", producto["precio_internet"])
    print("SKU:", producto["sku"])
    print("Disponible:", producto["disponible"])
    print("URL:", producto["url"])