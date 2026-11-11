from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from farmacia.models import Producto
from farmacia.procesamento.guardar_productos import (
    normalizar_texto_producto,
    extraer_firma_producto
)

PALABRAS_IGNORADAS = {
    "500", "100", "50", "25", "10",
    "mg", "mcg", "g", "ml",
    "comprimidos", "comprimido",
    "capsulas", "capsula",
    "recubiertos", "recubierto",
    "tabletas", "tableta"
}

class command(BaseCommand):
    help = "Detecta posibles productos duplicados sin modificar la base de datos."

    def handle(self, *args, **options):
        grupos = defaultdict(list)

        productos = (
            Producto.objects.select_related("medicamento")
            .annotate(cantidad_precios=Count("precios"))
            .only(
                "id",
                "nombre",
                "presentacion",
                "laboratorio",
                "categoria",
                "es_bioequivalente",
                "medicamento__principio_activo",
            )
            .iterator(chunk_size=500)
        )

        total = 0

        self.stdout.write("Analizando productos... \n")

        for producto in productos:
            total += 1

            principio_activo = ""

            if producto.medicamento:
                principio_activo = normalizar_texto_producto(
                    producto.medicamento.principio_activo
                )
            
            #Sin principio activo no se agrupa automaticamente
            if not principio_activo:
                continue

            firma = extraer_firma_producto(
                producto.nombre,
                producto.presentacion
            )

            concentraciones, forma, cantidad = firma

            #evitar candidatos con información insuficiente
            if not concentraciones or not forma or not cantidad:
                continue

            nombre_normalizado = normalizar_texto_producto(
                producto.nombre
            )

            palabras = [
                palabra
                for palabra in nombre_normalizado.split()
                if palabra not in PALABRAS_IGNORADAS
            ]

            if not palabras:
                continue

            marca = palabras[0]

            clave = (
                producto.categoria,
                principio_activo,
                firma,
                producto.es_bioequivalente,
                marca,
            )

            grupos[clave].append({
                "id": producto.id,
                "nombre": producto.nombre,
                "laboratorio": producto.laboratorio,
                "presentacion": producto.presentacion,
                "cantidad_precios": producto.cantidad_precios,
            })

            candidatos = [
                (clave, productos_grupo)
                for clave, productos_grupo in grupos.items()
                if len(productos_grupo) > 1
            ]
