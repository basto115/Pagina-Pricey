import csv

from django.core.management.base import BaseCommand
from farmacia.models import Producto


class Command(BaseCommand):
    help = "Genera un CSV con productos homologados entre farmacias."

    def add_arguments(self, parser):
        parser.add_argument(
            "--salida",
            type=str,
            default="reporte_homologacion.csv",
            help="Nombre del archivo CSV de salida."
        )

    def handle(self, *args, **options):
        archivo = options["salida"]

        productos = (
            Producto.objects
            .prefetch_related("precios__farmacia")
            .order_by("nombre")
        )

        total_productos = 0
        total_farmacias = 0

        with open(
            archivo,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as csvfile:

            writer = csv.writer(csvfile, delimiter=";")

            writer.writerow([
                "ID Producto",
                "Producto",
                "Cantidad de farmacias",
                "Farmacia",
                "Precio",
                "URL"
            ])

            for producto in productos:
                precios = list(producto.precios.all())

                farmacias = {
                    precio.farmacia_id
                    for precio in precios
                }

                if len(farmacias) < 2:
                    continue

                total_productos += 1
                total_farmacias += len(farmacias)

                for precio in precios:
                    writer.writerow([
                        producto.id,
                        producto.nombre,
                        len(farmacias),
                        precio.farmacia.nombre,
                        precio.precio,
                        precio.url_producto or ""
                    ])

        self.stdout.write(
            self.style.SUCCESS(
                f"Reporte generado: {archivo}"
            )
        )

        self.stdout.write(
            f"Productos homologados: {total_productos}"
        )

        self.stdout.write(
            f"Registros de precios: {total_farmacias}"
        )