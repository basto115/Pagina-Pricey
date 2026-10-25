
import re
from playwright.sync_api import sync_playwright


def limpiar_precio(valor):
    """Convierte un precio chileno en un número entero."""
    if valor is None:
        return None

    digitos = re.sub(r"\D", "", str(valor))
    return int(digitos) if digitos else None


def obtener_producto(url):
    """Obtiene el nombre y los precios del producto en Cruz Verde."""

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)

        pagina = navegador.new_page(
            locale="es-CL",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        try:
            pagina.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            pagina.locator("h1").first.wait_for(timeout=20000)
            pagina.wait_for_timeout(3000)

            nombre = pagina.locator("h1").first.inner_text().strip()
            texto = pagina.locator("body").inner_text()

            precio = None
            precio_normal = None

            # Limitar la búsqueda a la sección anterior a
            # "Beneficios y Usos", donde aparece el producto principal.
            texto_producto = texto.split(
                "Beneficios y Usos",
                1,
            )[0]

            # Buscar la última aparición del nombre del producto
            # para evitar precios de productos patrocinados anteriores.
            posicion = texto_producto.rfind(nombre)

            if posicion != -1:
                texto_producto = texto_producto[
                    posicion + len(nombre):
                ]

                # Precio normal seguido del precio de oferta y descuento.
                coincidencia_oferta = re.search(
                    r"\$\s*([\d.]+)\s*\n\s*"
                    r"\$\s*([\d.]+)\s*\n\s*-?\d+\s*%",
                    texto_producto,
                )

                if coincidencia_oferta:
                    precio_normal = limpiar_precio(
                        coincidencia_oferta.group(1)
                    )
                    precio = limpiar_precio(
                        coincidencia_oferta.group(2)
                    )
                else:
                    # Si no hay oferta, tomar el primer precio
                    # encontrado después del nombre del producto.
                    coincidencia_precio = re.search(
                        r"\$\s*([\d.]+)",
                        texto_producto,
                    )

                    if coincidencia_precio:
                        precio = limpiar_precio(
                            coincidencia_precio.group(1)
                        )

            # Comprobar disponibilidad.
            disponible = bool(
                re.search(
                    r"Stock\s+Disponible|Agregar a la bolsa",
                    texto,
                    re.IGNORECASE,
                )
            )

            return {
                "nombre": nombre,
                "principio_activo": "",
                "precio": precio,
                "precio_normal": precio_normal,
                "disponible": disponible,
                "sku": "",
                "laboratorio": "",
                "presentacion": "",
                "url": url,
            }

        finally:
            navegador.close()


if __name__ == "__main__":
    url = (
        "https://www.cruzverde.cl/"
        "xumadol-paracetamol-1000-mg-20-comprimidos/"
        "266145.html"
    )

    print(obtener_producto(url))
