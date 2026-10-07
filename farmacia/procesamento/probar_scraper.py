from farmacia.scraping.ahumada import obtener_producto as obtener_ahumada
from farmacia.scraping.cruz_verde import obtener_producto as obtener_cruz_verde
from farmacia.scraping.salcobrand import obtener_producto as obtener_salcobrand
from farmacia.scraping.dr_simi import obtener_producto as obtener_dr_simi

from farmacia.procesamento.normalizar import normalizar_producto


def probar_farmacia(nombre_farmacia, funcion_scraper, url):

    print("\n" + "=" * 50)
    print(f"FARMACIA: {nombre_farmacia}")
    print("=" * 50)

    try:
        producto = funcion_scraper(url)

        print("\n--- SCRAPER ---")

        for campo, valor in producto.items():
            print(f"{campo}: {valor}")

        producto_normalizado = normalizar_producto(
            producto,
            nombre_farmacia
        )

        print("\n--- NORMALIZADO ---")

        for campo, valor in producto_normalizado.items():
            print(f"{campo}: {valor}")

    except Exception as error:
        print(f"\nERROR: {error}")


if __name__ == "__main__":

    probar_farmacia(
        "Farmacias Ahumada",
        obtener_ahumada,
        "https://www.farmaciasahumada.cl/paracetamol-500-mg-x-16-comprimidos-84574.html"
    )

    probar_farmacia(
        "Cruz Verde",
        obtener_cruz_verde,
        "https://beta.cruzverde.cl/paracetamol-500-mg-16-comprimidos/272241.html"
    )

    probar_farmacia(
        "Salcobrand",
        obtener_salcobrand,
        "https://salcobrand.cl/products/paracetamol-b-500-mg-16-comprimidos?current_store_id=1&default_sku=432432&taxon_id=12976"
    )

    probar_farmacia(
        "Dr. Simi",
        obtener_dr_simi,
        "https://www.drsimi.cl/paracetamol-500-mg-16-comprimidos/p"
    )