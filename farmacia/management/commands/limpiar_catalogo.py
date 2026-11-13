
import csv
import unicodedata
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from farmacia.models import Producto

def normalizar(texto):
    texto = str(texto or "").lower().strip()
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )

def clasificar_producto(producto):
    cantidad = producto.cantidad_farmacias

    if cantidad >= 2:
        return "conservar", f"Disponible en {cantidad} farmacias"

    if cantidad == 1:
        return "eliminar", "Solo aparece en una farmacia; no permite comparar precios"

    return "eliminar", "No tiene registros de precios"
    
class Command(BaseCommand):
    help = "Audita y clasifica los productos del catálogo FARMA PRICEY"

    def handle(self, *args, **options):
        productos = (
            Producto.objects    
            .all()
            .annotate(
                cantidad_farmacias=Count(
                    "precios__farmacia",
                    distinct=True
                )
            )
            .prefetch_related("precios__farmacia")
            .order_by("id")
        )

        ruta = Path(settings.BASE_DIR) / "auditoria_limpieza_catalogo.csv"

        conteos = {
            "conservar": 0,
            "eliminar": 0,
            "revisar": 0,
        }

        with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
            campos = [
                "ID", "Nombre", "Categoria",
                "Principio activo", "Clasificacion",
                "Motivo", "Cantidad de farmacias",
                "Cantidad de precios", "Farmacias",
            ]

            escritor = csv.DictWriter(archivo, fieldnames=campos)
            escritor.writeheader()

            for producto in productos:
                clasificacion, motivo = clasificar_producto(producto)
                conteos[clasificacion] += 1

                precios = list(producto.precios.all())

                farmacias = sorted({
                    precio.farmacia.nombre
                    for precio in precios
                    if precio.farmacia
                })

                escritor.writerow({
                    "ID": producto.id,
                    "Nombre": producto.nombre,
                    "Categoria": getattr(producto, "categoria", ""),
                    "Principio activo": getattr(
                        producto, "principio_activo", ""
                    ),
                    "Clasificacion": clasificacion,
                    "Motivo": motivo,
                    "Cantidad de precios": len(precios),
                    "Farmacias": ", ".join(farmacias),
                    "Cantidad de farmacias": producto.cantidad_farmacias,
                })

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("AUDITORÍA COMPLETADA"))
        self.stdout.write(f"Productos analizados: {sum(conteos.values())}")
        self.stdout.write(f"Conservar: {conteos['conservar']}")
        self.stdout.write(f"Candidatos a eliminar: {conteos['eliminar']}")
        self.stdout.write(f"Revisión manual: {conteos['revisar']}")
        self.stdout.write("")
        self.stdout.write(f"Archivo generado: {ruta}")
        self.stdout.write(self.style.WARNING(
            "No se eliminó ningún producto."
        ))
