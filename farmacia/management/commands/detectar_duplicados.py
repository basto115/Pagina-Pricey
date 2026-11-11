from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from farmacia.models import Producto
from farmacia.procesamento.guardar_productos import (
    normalizar_texto_producto,
    extraer_firma_producto,
)


PALABRAS_IGNORADAS = {
    "500", "100", "50", "25", "10",
    "mg", "mcg", "g", "ml",
    "comprimidos", "comprimido",
    "capsulas", "capsula",
    "recubiertos", "recubierto",
    "tabletas", "tableta",
}


class Command(BaseCommand):
    help = "Detecta posibles productos duplicados sin modificar la base de datos."

    def handle(self, *args, **options):
        grupos = defaultdict(list)

        productos = (
            Producto.objects
            .select_related("medicamento")
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

        self.stdout.write("Analizando productos...\n")

        for producto in productos:
            total += 1

            principio_activo = ""

            if producto.medicamento:
                principio_activo = normalizar_texto_producto(
                    producto.medicamento.principio_activo
                )

            # Sin principio activo no agrupamos automáticamente.
            if not principio_activo:
                continue

            firma = extraer_firma_producto(
                producto.nombre,
                producto.presentacion
            )

            concentraciones, forma, cantidad = firma

            # Evitar candidatos con información insuficiente.
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

        self.stdout.write("=" * 65)
        self.stdout.write("RESULTADO DE DETECCIÓN")
        self.stdout.write("=" * 65)

        self.stdout.write(f"Productos analizados: {total}")
        self.stdout.write(f"Grupos candidatos: {len(candidatos)}")

        total_candidatos = sum(
            len(productos_grupo)
            for _, productos_grupo in candidatos
        )

        self.stdout.write(
            f"Productos involucrados: {total_candidatos}\n"
        )

        for numero, (clave, productos_grupo) in enumerate(
            candidatos, start=1
        ):
            categoria, activo, firma, bioequivalente, marca = clave

            self.stdout.write("-" * 65)
            self.stdout.write(f"GRUPO {numero}")
            self.stdout.write(f"Categoría: {categoria}")
            self.stdout.write(f"Principio activo: {activo}")
            self.stdout.write(f"Firma: {firma}")
            self.stdout.write(f"Marca inicial: {marca}")
            self.stdout.write(
                f"Bioequivalente: {'Sí' if bioequivalente else 'No'}"
            )

            for producto in productos_grupo:
                self.stdout.write(
                    f"  ID: {producto['id']} | "
                    f"{producto['nombre']}"
                )
                self.stdout.write(
                    f"     Laboratorio: {producto['laboratorio'] or 'Sin dato'} | "
                    f"Precios: {producto['cantidad_precios']}"
                )

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write(
            "Detección finalizada. No se modificó ningún registro."
        )
