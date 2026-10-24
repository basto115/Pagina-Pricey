
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from farmacia.management.commands.actualizar_productos import detectar_categoria
from farmacia.procesamento.guardar_productos import (
    convertir_precio,
    guardar_producto,
)


class Command(BaseCommand):
    help = "Importa productos de Cruz Verde desde un archivo JSON."

    def add_arguments(self, parser):
        parser.add_argument(
            "--archivo",
            default="dataset_cruz_verde.json",
            help="Ruta del archivo JSON.",
        )
        parser.add_argument(
            "--limite",
            type=int,
            default=0,
            help="Cantidad máxima de registros; 0 procesa todos.",
        )
        parser.add_argument(
            "--guardar",
            action="store_true",
            help="Guarda los productos y precios en la base de datos.",
        )

    def handle(self, *args, **options):
        ruta = Path(options["archivo"])

        if not ruta.is_absolute():
            ruta = Path.cwd() / ruta

        if not ruta.exists():
            raise CommandError(f"No se encontró el archivo: {ruta}")

        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise CommandError(f"El JSON no es válido: {error}")

        if not isinstance(datos, list):
            raise CommandError("El JSON debe contener una lista de productos.")

        if options["limite"] < 0:
            raise CommandError("--limite no puede ser negativo.")

        if options["limite"]:
            datos = datos[:options["limite"]]

        self.stdout.write(f"Archivo: {ruta}")
        self.stdout.write(f"Registros por revisar: {len(datos)}")

        validos = []

        for numero, item in enumerate(datos, start=1):
            nombre = str(item.get("name") or "").strip()
            precio = convertir_precio(item.get("price"))
            precio_normal = convertir_precio(item.get("list_price"))
            url = str(item.get("url") or "").strip()

            if not nombre or precio is None or not url.startswith("https://"):
                self.stdout.write(
                    self.style.WARNING(
                        f"Registro {numero} omitido: nombre, precio o URL inválidos."
                    )
                )
                continue

            categoria = detectar_categoria(nombre, "")

            producto = {
                "nombre": nombre,
                "laboratorio": item.get("brand") or "",
                "precio": precio,
                "precio_normal": precio_normal,
                "url": url,
                "categoria": categoria,
                "disponible": bool(
                    item.get("store_pickup") or item.get("home_delivery")
                ),
            }

            validos.append(producto)

            self.stdout.write(
                f"{numero}. {nombre} | categoría: {categoria} "
                f"| precio: ${precio} | normal: "
                f"${precio_normal if precio_normal is not None else 'No informado'} "
                f"| disponible según retiro/despacho: {producto['disponible']}"
            )

        self.stdout.write(
            self.style.SUCCESS(f"\nRegistros válidos: {len(validos)}")
        )

        if not options["guardar"]:
            self.stdout.write(
                self.style.WARNING(
                    "Vista previa: no se modificó la base de datos. "
                    "Usa --guardar para importar."
                )
            )
            return

        guardados = 0

        with transaction.atomic():
            for item in validos:
                guardar_producto(item, "Cruz Verde")
                guardados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Importación terminada. Registros procesados: {guardados}"
            )
        )
