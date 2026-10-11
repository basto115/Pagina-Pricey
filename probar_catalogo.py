import json
import requests
from bs4 import BeautifulSoup

url = "https://www.farmaciasahumada.cl/reflexan-10-mg-x-20-comprimidos-recubiertos-6.html"

respuesta = requests.get(
    url,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)

print("Codigo HTTP:", respuesta.status_code)
soup = BeautifulSoup(respuesta.content, "html.parser")

encontrado = False

for script in soup.find_all("script", type="application/ld+json"):
    try:
        datos = json.loads(script.string or script.get_text())

        elementos = datos if isinstance(datos, list) else [datos]

        for elemento in elementos:
            if not isinstance(elemento, dict):
                continue

            tipo = elemento.get("@type", "")

            if tipo == "Product" or (
                isinstance(tipo, list) and "Product" in tipo
            ):
                encontrado = True
                print("\nPRODUCTO ESTRUCTURADO:")
                print(json.dumps(elemento, indent=2, ensure_ascii=False))

            if tipo == "ProductGroup":
                encontrado = True
                print("\nGRUPO DE PRODUCTOS:")
                print(json.dumps(elemento, indent=2, ensure_ascii=False))

    except (json.JSONDecodeError, TypeError):
        continue

if not encontrado:
    print("No se encontro Product/ProductGroup en JSON-LD.")

print("\nElementos HTML con atributos relacionados con precios:")

for etiqueta in soup.find_all(
    attrs={"class": lambda valor: valor and "price" in str(valor).lower()}
)[:15]:
    print(
        "Etiqueta:", etiqueta.name,
        "| Clase:", etiqueta.get("class"),
        "| Texto:", etiqueta.get_text(" ", strip=True)[:250]
    )
