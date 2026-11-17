from django.core.management.base import BaseCommand
from farmacia.models import Producto, Precio, ImagenProducto
from farmacia.scraping.imagenes import guardar_imagen_producto
from farmacia.management.commands.actualizar_productos import SCRAPERS
from farmacia.models import Producto, Precio, ImagenProducto, Medicamento

class Command(BaseCommand):
    help = "Carga imágenes de productos existentes sin modificar precios."

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=10)
        parser.add_argument("--pendientes", action="store_true")

    def handle(self, *args, **opciones):
        limite = opciones["limite"]
        procesados = guardados = omitidos = errores = 0

        if opciones["pendientes"]:
            ids_con_imagen = ImagenProducto.objects.filter(
                medicamento__isnull=False
            ).values_list("medicamento_id", flat=True)

            ids_pendientes = Medicamento.objects.exclude(
                id__in=ids_con_imagen
            ).values_list("id", flat=True)

            productos = Producto.objects.filter(
                medicamento_id__in=ids_pendientes,
                precios__url_producto__isnull=False
            ).exclude(
                precios__url_producto=""
            ).distinct().order_by("id").iterator()

        else:
            productos = Producto.objects.order_by("id").iterator()

        for producto in productos:
            if procesados >= limite:
                break

            if producto.medicamento_id:
                existe = ImagenProducto.objects.filter(
                    medicamento_id=producto.medicamento_id
                ).exists()
            else:
                existe = ImagenProducto.objects.filter(
                    producto_id=producto.id
                ).exists()

            if existe:
                continue

            procesados += 1
            precios = Precio.objects.filter(
                producto_id=producto.id
            ).exclude(
                url_producto=""
            ).select_related("farmacia").order_by("-fecha_actualizacion")

            imagen_guardada = False

            for precio in precios:
                scraper = SCRAPERS.get({"Farmacias Ahumada": "Ahumada"}.get(precio.farmacia.nombre, precio.farmacia.nombre))

                if not scraper:
                    continue

                try:
                    datos = scraper(precio.url_producto)
                    imagen_url = datos.get("imagen_url") if isinstance(datos, dict) else None

                    if imagen_url and guardar_imagen_producto(imagen_url, producto):
                        guardados += 1
                        imagen_guardada = True
                        self.stdout.write(self.style.SUCCESS(
                            f"Imagen guardada: {producto.nombre}"
                        ))
                        break

                except Exception as error:
                    errores += 1
                    self.stdout.write(f"Error en {producto.nombre}: {error}")

            if not imagen_guardada:
                omitidos += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nResultado: revisados={procesados}, "
            f"imágenes_guardadas={guardados}, "
            f"sin_imagen={omitidos}, errores={errores}"
        ))

