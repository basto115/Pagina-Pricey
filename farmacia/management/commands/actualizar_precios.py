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
            nombre_farmacia = registro.farmacia.nombre.strip().lower()
            scraper = SCRAPERS.get(nombre_farmacia)

            if scraper is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"Farmacia no reconocida: {registro.farmacia.nombre}"
                    )
                )
                errores += 1
                continue

            try:
                datos = scraper(registro.url_producto)
                normalizado = normalizar_producto(
                    datos, registro.farmacia.nombre
                )
                precio_nuevo = normalizado["precio"]

                if not normalizado["nombre"]:
                    raise ValueError("No se pudo obtener el nombre del producto.")

                if precio_nuevo is None or precio_nuevo <= 0:
                    raise ValueError(
                        f"Precio no válido: {precio_nuevo}. Se conserva el actual."
                    )

                self.stdout.write(
                    f"{registro.farmacia.nombre}: "
                    f"${registro.precio} -> ${precio_nuevo}"
                )

                
                if guardar:
                    registro.precio = precio_nuevo
                    registro.disponible = normalizado["disponible"]

                    precio_normal = normalizado["precio_normal"]
                    if precio_normal is not None and precio_normal > 0:
                        registro.precio_normal = precio_normal

                    registro.save()
                    actualizados += 1

            except Exception as error:
                errores += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Error en {registro.farmacia.nombre}: {error}"
                    )
                )

        if guardar:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Proceso terminado. Registros guardados: {actualizados}. "
                    f"Errores: {errores}."
                )
            )
        else:
            self.stdout.write(
                f"Vista previa terminada. Errores: {errores}. "
                "No se modificó la base de datos. "
                "Revisa los precios antes de ejecutar con --guardar."
            )