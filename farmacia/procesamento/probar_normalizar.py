from farmacia.scraping.ahumada import obtener_producto
from farmacia.procesamento.normalizar import normalizar_producto


if __name__ == "__main__":

    url = "https://www.farmaciasahumada.cl/paracetamol-500-mg-x-16-comprimidos-84574.html"

    producto = obtener_producto(url)

    resultado = normalizar_producto(
        producto,
        "Farmacias Ahumada"
    )

    print("\n--- SCRAPER ---")

    for campo, valor in producto.items():
        print(f"{campo}: {valor}")

    print("\n--- PRODUCTO NORMALIZADO ---")

    for campo, valor in resultado.items():
        print(f"{campo}: {valor}")