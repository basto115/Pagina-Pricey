
import re
import time
import requests
from urllib.parse import urlparse
from xml.etree import ElementTree

from django.core.management.base import BaseCommand
from django.db import transaction

from farmacia.procesamento.guardar_productos import guardar_producto
from farmacia.scraping.ahumada import obtener_producto as obtener_ahumada
from farmacia.scraping.cruz_verde import obtener_producto as obtener_cruz_verde
from farmacia.scraping.salcobrand import obtener_producto as obtener_salcobrand
from farmacia.scraping.dr_simi import obtener_producto as obtener_dr_simi


SITEMAPS = {
    "Ahumada": [
        "https://www.farmaciasahumada.cl/sitemap_0-product.xml"
    ],
    "Cruz Verde": [
        "https://www.cruzverde.cl/sitemap_index.xml"
    ],
    "Salcobrand": [
        "https://salcobrand.cl/sitemap2.xml"
    ],
    "Dr. Simi": [
        "https://www.drsimi.cl/sitemap/product-0.xml"
    ],
}

SCRAPERS = {
    "Ahumada": obtener_ahumada,
    "Cruz Verde": obtener_cruz_verde,
    "Salcobrand": obtener_salcobrand,
    "Dr. Simi": obtener_dr_simi,
}


def detectar_categoria(nombre, principio_activo=""):
    texto = f"{nombre} {principio_activo}".lower()

    palabras_cosmeticos = [
        "maquillaje", "labial", "máscara de pestañas",
        "mascara de pestanas", "base de maquillaje",
        "delineador", "rubor", "corrector", "serum",
        "sérum", "crema facial", "agua micelar",
        "contorno de ojos", "perfume",
    ]

    palabras_cuidado = [
        "shampoo", "champú", "acondicionador", "desodorante",
        "jabón", "jabon", "pasta dental", "cepillo dental",
        "toalla higiénica", "pañal", "pañales",
        "protector solar", "agua termal", "crema corporal",
        "higiene",
    ]

    palabras_medicamento = [
        "comprimido", "comprimidos", "cápsula", "capsula",
        "jarabe", "solución oral", "solucion oral",
        "antibiótico", "antibiotico", "analgésico",
        "analgesico", "mg", "mcg",
    ]

    if any(p in texto for p in palabras_cosmeticos):
        return "cosmeticos"

    if any(p in texto for p in palabras_cuidado):
        return "cuidado_personal"

    if principio_activo or any(p in texto for p in palabras_medicamento):
        return "medicamentos"

    return "otros"


def obtener_urls_sitemap(url, farmacia, visitados=None, profundidad=0):
    if visitados is None:
        visitados = set()

    if url in visitados or profundidad > 5:
        return []

    visitados.add(url)

    try:
        respuesta = requests.get(url, timeout=30)
        respuesta.raise_for_status()
        raiz = ElementTree.fromstring(respuesta.content)

        locs = [
            elemento.text.strip()
            for elemento in raiz.iter()
            if elemento.tag.endswith("loc") and elemento.text
        ]
    except Exception as error:
        print(f"  Error leyendo sitemap {url}: {error}")
        return []

    resultados = []

    for enlace in locs:
        ruta = urlparse(enlace).path.lower()
        nombre_archivo = ruta.rsplit("/", 1)[-1]

        es_sitemap = (
            nombre_archivo.endswith(".xml")
            or nombre_archivo.endswith(".xml.gz")
        )

        if es_sitemap:
            if any(p in nombre_archivo for p in ("image", "video", "category")):
                continue

            if farmacia == "Cruz Verde":
                if "product" not in nombre_archivo and "sitemap_index" not in nombre_archivo:
                    continue
            elif farmacia == "Salcobrand":
                if not re.fullmatch(r"sitemap\d+\.xml", nombre_archivo):
                    continue

            resultados.extend(
                obtener_urls_sitemap(
                    enlace, farmacia, visitados, profundidad + 1
                )
            )

        elif enlace.startswith(("https://", "http://")):
            resultados.append(enlace)

    return list(dict.fromkeys(resultados))


class Command(BaseCommand):
    help = "Descubre e importa productos de los catálogos de farmacias."

    def add_arguments(self, parser):
        parser.add_argument(
            "--farmacia",
            choices=["Ahumada", "Cruz Verde", "Salcobrand", "Dr. Simi"],
        )
        parser.add_argument("--limite", type=int, default=10)
        parser.add_argument("--guardar", action="store_true")

    def handle(self, *args, **opciones):
        guardar = opciones["guardar"]
        limite = opciones["limite"]
        seleccionada = opciones.get("farmacia")

        if limite < 1:
            self.stderr.write("El límite debe ser mayor que cero.")
            return

        farmacias = [seleccionada] if seleccionada else list(SITEMAPS.keys())

        self.stdout.write(
            self.style.WARNING(
                "MODO GUARDADO" if guardar
                else "VISTA PREVIA: no se guardarán cambios"
            )
        )

        for nombre_farmacia in farmacias:
            self.stdout.write(f"\n--- {nombre_farmacia} ---")

            urls = []
            for sitemap in SITEMAPS[nombre_farmacia]:
                urls.extend(obtener_urls_sitemap(sitemap, nombre_farmacia))

            urls = list(dict.fromkeys(urls))
            self.stdout.write(f"URL descubiertas: {len(urls)}")

            if not urls:
                self.stdout.write(
                    self.style.WARNING("No se encontraron URL.")
                )
                continue

            procesados = guardados = errores = 0

            for url in urls[:limite]:
                try:
                    datos = SCRAPERS[nombre_farmacia](url)

                    if not isinstance(datos, dict):
                        raise ValueError("El scraper no devolvió un diccionario.")

                    nombre = str(datos.get("nombre") or "").strip()
                    if not nombre:
                        self.stdout.write(f"  Omitido: sin nombre - {url}")
                        errores += 1
                        continue

                    datos["nombre"] = nombre
                    datos["url"] = datos.get("url") or datos.get("url_producto") or url
                    datos["categoria"] = detectar_categoria(
                        nombre, datos.get("principio_activo", "")
                    )

                    self.stdout.write(
                        f"  {nombre} | categoría={datos['categoria']} "
                        f"| precio={datos.get('precio')} "
                        f"| disponible={datos.get('disponible')}"
                    )
                    procesados += 1

                    if guardar:
                        with transaction.atomic():
                            guardar_producto(datos, nombre_farmacia)
                        guardados += 1

                    time.sleep(0.3)

                except Exception as error:
                    errores += 1
                    self.stderr.write(f"  Error con {url}: {error}")

            self.stdout.write(
                f"Resumen {nombre_farmacia}: procesados={procesados}, "
                f"guardados={guardados}, errores={errores}"
            )

        if not guardar:
            self.stdout.write(
                self.style.WARNING(
                    "\nVista previa finalizada. Para guardar, utiliza --guardar."
                )
            )
