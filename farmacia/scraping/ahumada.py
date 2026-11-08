import re
import requests
from bs4 import BeautifulSoup
import json

def limpiar_precio(valor):
    """Convierte precios como '$1.309' en 1309."""

    valor = str(valor)

    valor = valor.replace("$", "")
    valor = valor.replace(".", "")
    valor = valor.replace(" ", "")
    valor = valor.strip()

    return int(valor)

def obtener_texto_seccion(soup, nombre_seccion):
    etiquetas = ["h2", "h3", "h4", "h5", "dt", "strong", "b", "span"]

    for elemento in soup.find_all(etiquetas):
        titulo = elemento.get_text(" ", strip=True)
        titulo = titulo.replace("■", "").strip().rstrip(":").strip()

        if titulo.lower() != nombre_seccion.lower():
            continue

        # Buscar el contenido en el siguiente elemento hermano.
        siguiente = elemento.find_next_sibling()

        if siguiente:
            texto = siguiente.get_text(" ", strip=True)
            if texto and texto.lower() != titulo.lower():
                return texto

        # Buscar el contenido en el siguiente hermano del contenedor.
        if elemento.parent:
            siguiente = elemento.parent.find_next_sibling()

            if siguiente:
                texto = siguiente.get_text(" ", strip=True)
                if texto:
                    return texto

    return ""

def extraer_dato_ficha(texto, etiqueta):
    etiquetas_siguientes = (
        r"Principio\s+Activo|"
        r"Registro\s+Sanitario|"
        r"Laboratorio|"
        r"Marca|"
        r"Concentraci[oó]n|"
        r"Forma\s+Farmac[eé]utica|"
        r"Mostrar\s+M[aá]s|"
        r"Informaci[oó]n\s+Para|"
        r"Ficha\s+T[eé]cnica"
    )

    patron = (
        rf"{re.escape(etiqueta)}\s+(.+?)"
        rf"(?=\s+(?:{etiquetas_siguientes})\b|$)"
    )

    coincidencia = re.search(
        patron,
        texto,
        re.IGNORECASE
    )

    return coincidencia.group(1).strip() if coincidencia else ""


def obtener_producto(url):

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    respuesta = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    print(
        "Código HTTP:",
        respuesta.status_code
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
    
    for termino in [
        "Principio Activo",
        "TOPIRAMATO",
        "Galenicum",
        "Forma Farmaceutica",
        "Comprimidos Recubiertos"
    ]:
        posicion = texto.lower().find(termino.lower())
        print(f"{termino}: posición={posicion}")

        if posicion >= 0:
            print(texto[max(0, posicion - 80):posicion + 200])
    
    print("\n========== COMPROBACIÓN HTML ==========")

    for termino in ["Principio Activo", "TOPIRAMATO", "Galenicum Health Chi"]:
        posicion = texto.lower().find(termino.lower())

        print(f"\n{termino}: posición={posicion}")

        if posicion >= 0:
            print(texto[max(0, posicion - 50):posicion + 150])
    
    
    # -----------------------------
    # INFORMACIÓN DEL MEDICAMENTO
    # -----------------------------

    seccion_activos = obtener_texto_seccion(
        soup,
        "Principios Activos"
    )

    seccion_presentacion = obtener_texto_seccion(
        soup,
        "Presentación"
    )

    seccion_laboratorio = obtener_texto_seccion(
        soup,
        "Laboratorio"
    )

    seccion_caracteristicas = obtener_texto_seccion(
        soup,
        "Características"
    )
    
    print("\n========== DEBUG SECCIONES ==========")
    print("Activos:", repr(seccion_activos))
    print("Presentación:", repr(seccion_presentacion))
    print("Laboratorio:", repr(seccion_laboratorio))

    # PRINCIPIO ACTIVO
    principio_activo = (
        seccion_activos.strip()
        or extraer_dato_ficha(texto, "Principio Activo")
    )


    # LABORATORIO
    laboratorio = (
        seccion_laboratorio.strip()
        or extraer_dato_ficha(texto, "Laboratorio")
    )

    # PRESENTACIÓN
    presentacion = (
        seccion_presentacion.strip()
        or extraer_dato_ficha(texto, "Forma Farmaceutica")
    )

    # BIOEQUIVALENCIA
    es_bioequivalente = bool(
        re.search(
            r"bioequivalente\s*\(b\)",
            seccion_caracteristicas,
            re.IGNORECASE
        )
    )

    # -----------------------------
    # NOMBRE
    # -----------------------------

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

    # PRECIO Y DATOS ESTRUCTURADOS
    precio = None
    precio_normal = None
    sku = ""
    disponible = False

    def buscar_producto_json(datos):
        if isinstance(datos, list):
            for elemento in datos:
                resultado = buscar_producto_json(elemento)
                if resultado:
                    return resultado

        elif isinstance(datos, dict):
            tipo = datos.get("@type")

            if tipo == "Product" or (
                isinstance(tipo, list) and "Product" in tipo
            ):
                ofertas = datos.get("offers", {})

                if isinstance(ofertas, list):
                    ofertas = ofertas[0] if ofertas else {}

                if isinstance(ofertas, dict) and ofertas.get("price"):
                    return datos, ofertas

            for valor in datos.values():
                resultado = buscar_producto_json(valor)
                if resultado:
                    return resultado

        return None

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):
        try:
            contenido = json.loads(
                script.string or script.get_text()
            )

            resultado = buscar_producto_json(contenido)

            if resultado:
                producto_json, oferta = resultado

                precio = limpiar_precio(oferta["price"])
                sku = str(
                    producto_json.get("sku")
                    or producto_json.get("mpn")
                    or ""
                )

                disponibilidad = str(
                    oferta.get("availability", "")
                )

                disponible = (
                    "instock" in disponibilidad.lower()
                    and "outofstock" not in disponibilidad.lower()
                )

                break

        except (json.JSONDecodeError, ValueError, TypeError):
            continue




    # -----------------------------
    # DISPONIBILIDAD
    # -----------------------------

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

    # -----------------------------
    # RESULTADO
    # -----------------------------

    producto = {

        "nombre": nombre,

        "principio_activo": principio_activo,

        "precio": precio,

        "precio_normal": precio_normal,

        "disponible": disponible,

        "sku": sku,

        "laboratorio": laboratorio,

        "presentacion": presentacion,

        "url": url,
        
        "es_bioequivalente": es_bioequivalente,
    }

    return producto


if __name__ == "__main__":

    url = (
        "https://www.farmaciasahumada.cl/"
        "topivitae-50-mg-x-28-comprimidos-recubiertos-83170.html"
    )

    producto = obtener_producto(url)

    print("\n--- PRODUCTO EXTRAÍDO ---")

    for clave, valor in producto.items():
        print(f"{clave}: {valor}")