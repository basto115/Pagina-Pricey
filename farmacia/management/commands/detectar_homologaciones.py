
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from farmacia.models import Producto
from farmacia.procesamento.guardar_productos import (
    normalizar_texto_producto,
    extraer_firma_producto,
)


FARMACIAS = {
    "farmacias ahumada": "Ahumada",
    "salcobrand": "Salcobrand",
    "dr. simi": "Dr. Simi",
    "cruz verde": "Cruz Verde",
}


class Command(BaseCommand):
    help = "Detecta posibles homologaciones entre las cuatro farmacias."

    def handle(self, *args, **options):
        grupos = defaultdict(list)

        productos = (
            Producto.objects
            .select_related("medicamento")
            .prefetch_related("precios__farmacia")
            .annotate(cantidad_precios=Count("precios", distinct=True))
            .iterator(chunk_size=500)
        )

        total = 0

        self.stdout.write("Analizando catálogo completo...\n")

        for producto in productos:
            total += 1

            principio_activo = ""

            if producto.medicamento:
                principio_activo = normalizar_texto_producto(
                    producto.medicamento.principio_activo
                )

            if not principio_activo:
                continue

            firma = extraer_firma_producto(
                producto.nombre,
                producto.presentacion
            )

            concentraciones, forma, cantidad = firma

            if not concentraciones or not forma or not cantidad:
                continue

            farmacias_producto = set()

            for precio in producto.precios.all():
                nombre_farmacia = normalizar_texto_producto(
                    precio.farmacia.nombre
                )

                for nombre, etiqueta in FARMACIAS.items():
                    if normalizar_texto_producto(nombre) == nombre_farmacia:
                        farmacias_producto.add(etiqueta)
                        break

            if not farmacias_producto:
                continue

            # No se considera la marca ni el laboratorio en esta etapa.
            # Se buscan productos con características farmacológicas similares.
            clave = (
                producto.categoria,
                principio_activo,
                firma,
                producto.es_bioequivalente,
            )

            grupos[clave].append({
                "id": producto.id,
                "nombre": producto.nombre,
                "laboratorio": producto.laboratorio,
                "presentacion": producto.presentacion,
                "cantidad_precios": producto.cantidad_precios,
                "farmacias": sorted(farmacias_producto),
            })

        candidatos = []

        for clave, productos_grupo in grupos.items():

            if len(productos_grupo) < 2:
                continue

            farmacias_grupo = set()

            for producto in productos_grupo:
                farmacias_grupo.update(producto["farmacias"])

            # Solo grupos con participación de al menos dos farmacias.
            if len(farmacias_grupo) >= 2:
                candidatos.append(
                    (clave, productos_grupo, farmacias_grupo)
                )

        # Ordenar grupos por cantidad de farmacias y productos.
        candidatos.sort(
            key=lambda grupo: (
                -len(grupo[2]),
                -len(grupo[1])
            )
        )

        cantidad_por_farmacias = {
            2: 0,
            3: 0,
            4: 0,
        }

        productos_por_farmacia = {
            nombre: set()
            for nombre in FARMACIAS.values()
        }

        for _, productos_grupo, farmacias_grupo in candidatos:
            cantidad_por_farmacias[len(farmacias_grupo)] += 1

            for producto in productos_grupo:
                for farmacia in producto["farmacias"]:
                    productos_por_farmacia[farmacia].add(
                        producto["id"]
                    )

        total_candidatos = sum(
            len(productos_grupo)
            for _, productos_grupo, _ in candidatos
        )

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("RESUMEN DE HOMOLOGACIONES")
        self.stdout.write("=" * 70)

        self.stdout.write(f"Productos analizados: {total}")
        self.stdout.write(f"Grupos candidatos: {len(candidatos)}")
        self.stdout.write(
            f"Productos involucrados: {total_candidatos}"
        )

        self.stdout.write("\nCoincidencias por farmacias:")

        self.stdout.write(
            f"  2 farmacias: {cantidad_por_farmacias[2]} grupos"
        )
        self.stdout.write(
            f"  3 farmacias: {cantidad_por_farmacias[3]} grupos"
        )
        self.stdout.write(
            f"  4 farmacias: {cantidad_por_farmacias[4]} grupos"
        )

        self.stdout.write("\nProductos participantes por farmacia:")

        for farmacia, ids in productos_por_farmacia.items():
            self.stdout.write(
                f"  {farmacia}: {len(ids)} productos"
            )

        for numero, (clave, productos_grupo, farmacias_grupo) in enumerate(
            candidatos,
            start=1
        ):
            categoria, activo, firma, bioequivalente = clave

            self.stdout.write("\n" + "-" * 70)
            self.stdout.write(f"GRUPO {numero}")
            self.stdout.write(f"Categoría: {categoria}")
            self.stdout.write(f"Principio activo: {activo}")
            self.stdout.write(f"Firma: {firma}")
            self.stdout.write(
                f"Bioequivalente: {'Sí' if bioequivalente else 'No'}"
            )
            self.stdout.write(
                f"Farmacias participantes: {', '.join(sorted(farmacias_grupo))}"
            )

            for producto in productos_grupo:
                self.stdout.write(
                    f"\n  ID: {producto['id']} | {producto['nombre']}"
                )
                self.stdout.write(
                    f"    Laboratorio: {producto['laboratorio'] or 'Sin dato'}"
                )
                self.stdout.write(
                    f"    Farmacias: {', '.join(producto['farmacias'])}"
                )
                self.stdout.write(
                    f"    Precios registrados: {producto['cantidad_precios']}"
                )

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("RESUMEN DE HOMOLOGACIONES")
        self.stdout.write("=" * 70)

        self.stdout.write(f"Productos analizados: {total}")
        self.stdout.write(f"Grupos candidatos: {len(candidatos)}")
        self.stdout.write(
            f"Productos involucrados: {total_candidatos}"
        )

        self.stdout.write("\nCoincidencias por farmacias:")

        self.stdout.write(
            f"  2 farmacias: {cantidad_por_farmacias[2]} grupos"
        )
        self.stdout.write(
            f"  3 farmacias: {cantidad_por_farmacias[3]} grupos"
        )
        self.stdout.write(
            f"  4 farmacias: {cantidad_por_farmacias[4]} grupos"
        )

        self.stdout.write("\nProductos participantes por farmacia:")
        
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(
            "Detección finalizada. No se modificó ningún registro."
        )
