
import re
import unicodedata
from difflib import SequenceMatcher

from django.core.management.base import BaseCommand

from farmacia.models import Precio
from farmacia.scraping.ahumada import (
    obtener_producto as obtener_ahumada,
)
from farmacia.scraping.cruz_verde import (
    obtener_producto as obtener_cruz_verde,
)
from farmacia.scraping.salcobrand import (
    obtener_producto as obtener_salcobrand,
)
from farmacia.scraping.dr_simi import (
    obtener_producto as obtener_dr_simi,
)
from farmacia.procesamento.normalizar import normalizar_producto


SCRAPERS = {
    "farmacias ahumada": obtener_ahumada,
    "cruz verde": obtener_cruz_verde,
    "salcobrand": obtener_salcobrand,
    "dr. simi": obtener_dr_simi,
}


def normalizar_nombre_comparacion(nombre):
    """Normaliza nombres para compararlos sin acentos ni puntuación."""
    nombre = str(nombre or "").lower()
    nombre = unicodedata.normalize("NFKD", nombre)

    nombre = "".join(
        caracter
        for caracter in nombre
        if not unicodedata.combining(caracter)
    )

    return re.findall(r"[a-z0-9]+", nombre)


def nombres_compatibles(nombre_registrado, nombre_obtenido):
    """
    Comprueba si dos nombres son suficientemente parecidos.
    Esta validación no garantiza que sean el mismo producto.
    """
    registrado = normalizar_nombre_comparacion(nombre_registrado)
    obtenido = normalizar_nombre_comparacion(nombre_obtenido)

    if not registrado or not obtenido:
        return False

    texto_registrado = " ".join(registrado)
    texto_obtenido = " ".join(obtenido)

    similitud = SequenceMatcher(
        None,
        texto_registrado,
        texto_obtenido,
    ).ratio()

    palabras_registradas = set(registrado)
    palabras_obtenidas = set(obtenido)

    coincidencias = palabras_registradas & palabras_obtenidas

    proporcion = (
        len(coincidencias) / len(palabras_registradas)
    )

    return similitud >= 0.65 or proporcion >= 0.65


class Command(BaseCommand):
    help = "Consulta y actualiza precios de productos en Neon."

    def add_arguments(self, parser):
        parser.add_argument(
            "--guardar",
            action="store_true",
            help="Guarda los precios extraídos en la base de datos.",
        )

    def handle(self, *args, **options):
        guardar = options["guardar"]
        actualizados = 0
        errores = 0

        registros = (
            Precio.objects
            .select_related("producto", "farmacia")
            .exclude(url_producto="")
        )

        for registro in registros:
            nombre_farmacia = (
                registro.farmacia.nombre.strip().lower()
            )

            scraper = SCRAPERS.get(nombre_farmacia)

            if scraper is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"Farmacia no reconocida: "
                        f"{registro.farmacia.nombre}"
                    )
                )
                errores += 1
                continue

            try:
                datos = scraper(registro.url_producto)

                normalizado = normalizar_producto(
                    datos,
                    registro.farmacia.nombre,
                )

                nombre_nuevo = normalizado["nombre"]
                precio_nuevo = normalizado["precio"]

                if not nombre_nuevo:
                    raise ValueError(
                        "No se pudo obtener el nombre del producto."
                    )

                if not nombres_compatibles(
                    registro.producto.nombre,
                    nombre_nuevo,
                ):
                    raise ValueError(
                        "El nombre obtenido no coincide suficientemente "
                        "con el producto registrado. "
                        f"Registrado: {registro.producto.nombre!r}; "
                        f"obtenido: {nombre_nuevo!r}. "
                        "Se omite la actualización."
                    )

                if precio_nuevo is None or precio_nuevo <= 0:
                    raise ValueError(
                        f"Precio no válido: {precio_nuevo}. "
                        "Se conserva el precio actual."
                    )

                self.stdout.write(
                    f"{registro.farmacia.nombre} | "
                    f"{registro.producto.nombre} | "
                    f"${registro.precio} -> ${precio_nuevo}"
                )

                if guardar:
                    registro.precio = precio_nuevo

                    disponible = normalizado["disponible"]

                    if isinstance(disponible, bool):
                        registro.disponible = disponible

                    precio_normal = normalizado["precio_normal"]

                    if (
                        precio_normal is not None
                        and precio_normal > 0
                    ):
                        registro.precio_normal = precio_normal

                    registro.save()
                    actualizados += 1

            except Exception as error:
                errores += 1

                self.stdout.write(
                    self.style.ERROR(
                        f"Error en {registro.farmacia.nombre} | "
                        f"{registro.producto.nombre}: {error}"
                    )
                )

        if guardar:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Proceso terminado. "
                    f"Registros guardados: {actualizados}. "
                    f"Errores: {errores}."
                )
            )
        else:
            self.stdout.write(
                f"Vista previa terminada. Errores: {errores}. "
                "No se modificó la base de datos. "
                "Revisa los resultados antes de ejecutar con --guardar."
            )
