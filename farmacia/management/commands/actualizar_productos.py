import re
import time
import requests
from urllib.parse import urlparse
from xml.etree import ElementTree
from farmacia.procesamento.normalizar import detectar_categoria

from django.core.management.base import BaseCommand
from django.db import transaction
from farmacia.models import ProgresoImportacion, Precio

from farmacia.procesamento.guardar_productos import guardar_producto, buscar_producto_compatible, obtener_farmacia, convertir_booleano
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

            if farmacia == "Salcobrand":
                partes = [
                    parte
                    for parte in ruta.split("/")
                    if parte
                ]

                # Aceptar solamente páginas individuales
                # con formato /products/nombre-producto.
                if (
                    len(partes) < 2
                    or partes[0] != "products"
                ):
                    continue

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

            progreso = ProgresoImportacion.objects.filter(
                farmacia=nombre_farmacia
            ).first()

            ultima_url = progreso.ultima_url if progreso else ""
            inicio = 0

            if ultima_url:
                try:
                    inicio = urls.index(ultima_url) + 1
                except ValueError:
                    inicio = 0

            if inicio >= len(urls):
                inicio = 0

            self.stdout.write(
                f"Continuando desde la URL {inicio + 1} de {len(urls)}"
            )

            procesados = guardados = errores = 0
            productos_nuevos = precios_nuevos = precios_actualizados = 0
            intentos = 0
            max_intentos = limite * 5

            for indice in range(inicio, len(urls)):

                if procesados >= limite:
                    break

                if intentos >= max_intentos:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Se alcanzó el máximo de {max_intentos} intentos."
                        )
                    )
                    break

                url = urls[indice]
                intentos += 1

                try:
                    print(f"\nURL ANALIZADA: {url}")
                    datos = SCRAPERS[nombre_farmacia](url)

                    if not isinstance(datos, dict):
                        raise ValueError(
                            "El scraper no devolvió un diccionario."
                        )

                    nombre = str(datos.get("nombre") or "").strip()

                    if not nombre:
                        self.stdout.write(f"  Omitido: sin nombre - {url}")
                        errores += 1
                        continue

                    if datos.get("precio") is None:
                        self.stdout.write(
                            f"  Omitido: sin precio válido - {url}"
                        )
                        errores += 1
                        continue

                    datos["nombre"] = nombre
                    datos["url"] = (
                        datos.get("url")
                        or datos.get("url_producto")
                        or url
                    )

                    datos["categoria"] = detectar_categoria(
                        nombre,
                        datos.get("principio_activo", "")
                    )

                    self.stdout.write(
                        f"  {nombre} | categoría={datos['categoria']} "
                        f"| precio={datos.get('precio')} "
                        f"| disponible={datos.get('disponible')}"
                    )

                    procesados += 1

                    bioequivalente = (
                        bool(re.search(r"\(b\)", nombre, flags=re.IGNORECASE))
                        or convertir_booleano(datos.get("es_bioequivalente", False))
                    )

                    producto_existente = buscar_producto_compatible(
                        nombre=nombre,
                        principio_activo=datos.get("principio_activo", ""),
                        presentacion=datos.get("presentacion", ""),
                        categoria=datos["categoria"],
                        es_bioequivalente=bioequivalente,
                        laboratorio=datos.get("laboratorio", "") or "",
                    )

                    farmacia_obj = obtener_farmacia(nombre_farmacia)

                    precio_existente = (
                        Precio.objects.filter(
                            producto=producto_existente,
                            farmacia=farmacia_obj
                        ).exists()
                        if producto_existente else False
                    )

                    if producto_existente is None:
                        productos_nuevos += 1
                        clasificacion = "PRODUCTO NUEVO"
                    elif precio_existente:
                        precios_actualizados += 1
                        clasificacion = f"YA EXISTE EN {nombre_farmacia}"
                    else:
                        precios_nuevos += 1
                        clasificacion = f"PRODUCTO HOMOLOGADO (ID {producto_existente.id})"

                    self.stdout.write(f"  Clasificación: {clasificacion}")

                    if guardar:
                        with transaction.atomic():
                            guardar_producto(
                                datos,
                                nombre_farmacia,
                                producto_existente=producto_existente
                            )
                        guardados += 1

                    time.sleep(0.3)

                except Exception as error:
                    errores += 1
                    self.stderr.write(
                        f"  URL omitida: {url}: {error}"
                    )

                finally:
                    if guardar:
                        ProgresoImportacion.objects.update_or_create(
                            farmacia=nombre_farmacia,
                            defaults={"ultima_url": url}
                        )

            self.stdout.write(
                f"Resumen {nombre_farmacia}: "
                f"procesados={procesados}, "
                f"guardados={guardados}, "
                f"productos_nuevos={productos_nuevos}, "
                f"precios_nuevos={precios_nuevos}, "
                f"precios_actualizados={precios_actualizados}, "
                f"errores={errores}"
            )

        if not guardar:
            self.stdout.write(
                self.style.WARNING(
                    "\nVista previa finalizada. Para guardar, utiliza --guardar."
                )
            )
