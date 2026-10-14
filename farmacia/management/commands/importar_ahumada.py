
import time
import requests
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand, CommandError

from farmacia.scraping.ahumada import obtener_producto
from farmacia.procesamento.guardar_productos import guardar_producto


SITEMAP_URL = (
    "https://www.farmaciasahumada.cl/sitemap_0-product.xml"
)


class Command(BaseCommand):
    help = "Importa productos del catálogo de Farmacias Ahumada"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limite",
            type=int,
            default=5,
            help="Cantidad máxima de productos que se procesarán",
        )
        parser.add_argument(
            "--pausa",
            type=float,
            default=2.0,
            help="Segundos de espera entre productos",
        )
        parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Cantidad de enlaces que se omitirán al inicio",
        )
        parser.add_argument(
            "--solo-probar",
            action="store_true",
            help="Consulta productos sin guardarlos en la base de datos",
        )

    def handle(self, *args, **options):
        limite = options["limite"]
        pausa = options["pausa"]
        offset = options["offset"]
        solo_probar = options["solo_probar"]

        if limite < 1 or pausa < 0 or offset < 0:
            raise CommandError(
                "El límite debe ser positivo y la pausa y el offset "
                "no pueden ser negativos."
            )

        self.stdout.write("Descargando sitemap de productos...")

        try:
            respuesta = requests.get(
                SITEMAP_URL,
                timeout=30,
                headers={"User-Agent": "FarmaPricey/1.0"},
            )
            respuesta.raise_for_status()
            raiz = ET.fromstring(respuesta.content)

        except (requests.RequestException, ET.ParseError) as error:
            raise CommandError(
                f"No se pudo leer el sitemap: {error}"
            ) from error

        urls = [
            elemento.text.strip()
            for elemento in raiz.iter()
            if elemento.tag.endswith("loc") and elemento.text
        ]

        urls = urls[offset:offset + limite]

        if not urls:
            self.stdout.write(
                self.style.WARNING("No hay enlaces para procesar.")
            )
            return

        self.stdout.write(
            f"Se procesarán {len(urls)} productos."
        )

        if solo_probar:
            self.stdout.write(
                self.style.WARNING(
                    "MODO DE PRUEBA: no se guardarán cambios."
                )
            )

        guardados = 0
        errores = 0

        for numero, url in enumerate(urls, start=1):
            try:
                datos = obtener_producto(url)

                if not datos or not datos.get("nombre"):
                    errores += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"[{numero}] Sin datos válidos: {url}"
                        )
                    )
                    continue

                if solo_probar:
                    self.stdout.write(
                        f"[{numero}/{len(urls)}] "
                        f"Producto: {datos.get('nombre')} | "
                        f"Precio: {datos.get('precio')} | "
                        f"Disponible: {datos.get('disponible')}"
                    )
                    continue

                producto = guardar_producto(
                    datos,
                    "Farmacias Ahumada",
                )

                if producto is None:
                    errores += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"[{numero}] No se pudo guardar: {url}"
                        )
                    )
                    continue

                guardados += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{numero}/{len(urls)}] Procesado: "
                        f"{producto.nombre}"
                    )
                )

            except Exception as error:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"[{numero}] Error en {url}: {error}"
                    )
                )

            finally:
                if numero < len(urls):
                    time.sleep(pausa)

        if solo_probar:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Prueba terminada. Productos consultados: "
                    f"{len(urls) - errores}. Errores: {errores}. "
                    "No se guardaron cambios mediante este comando."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Proceso terminado. Productos procesados: "
                    f"{guardados}. Errores: {errores}."
                )
            )
