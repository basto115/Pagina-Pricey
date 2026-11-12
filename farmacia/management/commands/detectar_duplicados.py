from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count

from farmacia.models import Producto
from farmacia.procesamento.guardar_productos import (
    normalizar_texto_producto,
    extraer_firma_producto,
)


class Command(BaseCommand):
    help = "Detecta posibles homologaciones entre Cruz Verde y Ahumada."

    def handle(self, *args, **options):
        grupos = defaultdict(list)

        productos = (
            Producto.objects
            .select_related("medicamento")
            .prefetch_related("precios__farmacia")
            .annotate(cantidad_precios=Count("precios"))
            .filter(precios__isnull=False)
            .distinct()
            .iterator(chunk_size=500)
        )

        total = 0
        descartados = 0

        self.stdout.write("Analizando productos...")

        for producto in productos:
            total += 1

            # Solo productos con un único precio registrado.
            if producto.cantidad_precios != 1:
                descartados += 1
                continue

            if not producto.medicamento:
                continue

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

            nombres_farmacias = [
                normalizar_texto_producto(precio.farmacia.nombre)
                for precio in producto.precios.all()
            ]

            tiene_cruz_verde = any(
                "cruz verde" in nombre
                for nombre in nombres_farmacias
            )

            tiene_ahumada = any(
                "ahumada" in nombre
                for nombre in nombres_farmacias
            )

            if not tiene_cruz_verde and not tiene_ahumada:
                continue
            
            nombre_normalizado = normalizar_texto_producto(producto.nombre)
            marca = nombre_normalizado.split()[0] if nombre_normalizado else ""
            
            # No se utiliza la categoría ni la marca como criterio.
            clave = (
                principio_activo,
                firma,
                producto.es_bioequivalente,
                marca
            )

            grupos[clave].append({
                "id": producto.id,
                "nombre": producto.nombre,
                "categoria": producto.categoria,
                "laboratorio": producto.laboratorio,
                "presentacion": producto.presentacion,
                "farmacias": nombres_farmacias,
                "tiene_cruz_verde": tiene_cruz_verde,
                "tiene_ahumada": tiene_ahumada,
            })

        candidatos = []

        for clave, productos_grupo in grupos.items():
            ids_cruz_verde = {
                p["id"] for p in productos_grupo
                if p["tiene_cruz_verde"]
            }

            ids_ahumada = {
                p["id"] for p in productos_grupo
                if p["tiene_ahumada"]
            }

            if len(productos_grupo) > 1 and ids_cruz_verde and ids_ahumada:
                candidatos.append((clave, productos_grupo))

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("RESULTADO DE DETECCIÓN CRUZ VERDE - AHUMADA")
        self.stdout.write("=" * 65)

        self.stdout.write(f"Productos analizados: {total}")
        self.stdout.write(f"Productos descartados por tener varios precios: {descartados}")
        self.stdout.write(f"Grupos candidatos: {len(candidatos)}")

        total_candidatos = sum(
            len(grupo) for _, grupo in candidatos
        )

        self.stdout.write(
            f"Productos involucrados: {total_candidatos}\n"
        )

        for numero, (clave, grupo) in enumerate(candidatos, start=1):
            activo, firma, bioequivalente, marca = clave

            self.stdout.write("-" * 65)
            self.stdout.write(f"GRUPO {numero}")
            self.stdout.write(f"Principio activo: {activo}")
            self.stdout.write(f"Firma: {firma}")
            self.stdout.write(
                f"Bioequivalente: {'Sí' if bioequivalente else 'No'}"
            )
            self.stdout.write(f"Marca identificada: {marca}")

            for producto in grupo:
                farmacias = ", ".join(producto["farmacias"])

                self.stdout.write(
                    f"\n  ID: {producto['id']} | {producto['nombre']}"
                )
                self.stdout.write(
                    f"    Categoría: {producto['categoria']}"
                )
                self.stdout.write(
                    f"    Laboratorio: {producto['laboratorio'] or 'Sin dato'}"
                )
                self.stdout.write(
                    f"    Farmacia: {farmacias}"
                )

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write(
            "Detección finalizada. No se modificó ningún registro."
        )

