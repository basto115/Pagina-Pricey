
import csv
from pathlib import Path
from collections import Counter

from django.core.management.base import BaseCommand

from farmacia.models import Producto


FARMACIAS = {
    1: "Cruz Verde",
    3: "Dr. Simi",
    4: "Salcobrand",
    5: "Farmacias Ahumada",
}


class Command(BaseCommand):
    help = "Audita los productos de Cruz Verde sin modificar la base de datos."

    def handle(self, *args, **options):

        productos = (
            Producto.objects
            .filter(precios__farmacia_id=1)
            .select_related("medicamento")
            .prefetch_related("precios__farmacia")
            .distinct()
            .order_by("id")
        )

        total = 0
        productos_exclusivos = 0
        productos_compartidos = 0

        coincidencias = Counter()
        sin_principio_activo = 0
        sin_presentacion = 0
        sin_laboratorio = 0

        total_precios = Counter()

        archivo = Path("auditoria_cruz_verde.csv")

        self.stdout.write("Analizando catálogo de Cruz Verde...\n")

        with archivo.open("w", newline="", encoding="utf-8-sig") as csvfile:

            campos = [
                "ID",
                "Nombre",
                "Principio activo",
                "Presentacion",
                "Laboratorio",
                "Categoria",
                "Bioequivalente",
                "Farmacias",
                "Cantidad de precios",
                "Precios Cruz Verde",
                "Precios Ahumada",
                "Precios Salcobrand",
                "Precios Dr. Simi",
                "Clasificacion",
                "Informacion incompleta",
            ]

            escritor = csv.DictWriter(
                csvfile,
                fieldnames=campos
            )

            escritor.writeheader()

            for producto in productos.iterator(chunk_size=500):

                total += 1

                principio_activo = ""

                if producto.medicamento:
                    principio_activo = (
                        producto.medicamento.principio_activo or ""
                    ).strip()

                presentacion = (producto.presentacion or "").strip()
                laboratorio = (producto.laboratorio or "").strip()

                precios_por_farmacia = Counter()

                for precio in producto.precios.all():

                    farmacia_id = precio.farmacia_id

                    if farmacia_id in FARMACIAS:
                        precios_por_farmacia[farmacia_id] += 1
                        total_precios[FARMACIAS[farmacia_id]] += 1

                otras_farmacias = [
                    farmacia_id
                    for farmacia_id in (3, 4, 5)
                    if precios_por_farmacia[farmacia_id] > 0
                ]

                nombres_farmacias = ["Cruz Verde"]

                for farmacia_id in otras_farmacias:
                    nombres_farmacias.append(
                        FARMACIAS[farmacia_id]
                    )

                if not otras_farmacias:
                    clasificacion = "Exclusivo Cruz Verde"
                    productos_exclusivos += 1
                else:
                    clasificacion = "Compartido"
                    productos_compartidos += 1

                coincidencias[tuple(sorted(otras_farmacias))] += 1

                incompletos = []

                if not principio_activo:
                    sin_principio_activo += 1
                    incompletos.append("Sin principio activo")

                if not presentacion:
                    sin_presentacion += 1
                    incompletos.append("Sin presentación")

                if not laboratorio:
                    sin_laboratorio += 1
                    incompletos.append("Sin laboratorio")

                escritor.writerow({
                    "ID": producto.id,
                    "Nombre": producto.nombre,
                    "Principio activo": principio_activo,
                    "Presentacion": presentacion,
                    "Laboratorio": laboratorio,
                    "Categoria": producto.categoria,
                    "Bioequivalente": producto.es_bioequivalente,
                    "Farmacias": " | ".join(nombres_farmacias),
                    "Cantidad de precios": sum(
                        precios_por_farmacia.values()
                    ),
                    "Precios Cruz Verde": precios_por_farmacia[1],
                    "Precios Ahumada": precios_por_farmacia[5],
                    "Precios Salcobrand": precios_por_farmacia[4],
                    "Precios Dr. Simi": precios_por_farmacia[3],
                    "Clasificacion": clasificacion,
                    "Informacion incompleta": (
                        " | ".join(incompletos) if incompletos else "No"
                    ),
                })

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("AUDITORÍA DEL CATÁLOGO CRUZ VERDE")
        self.stdout.write("=" * 65)

        self.stdout.write(f"Productos analizados: {total}")
        self.stdout.write(
            f"Productos exclusivos: {productos_exclusivos}"
        )
        self.stdout.write(
            f"Productos compartidos: {productos_compartidos}"
        )

        self.stdout.write("\nCoincidencias por farmacia:")

        for farmacia_id in (5, 4, 3):
            self.stdout.write(
                f"  {FARMACIAS[farmacia_id]}: "
                f"{coincidencias[(farmacia_id,)]} productos"
            )

        self.stdout.write(
            f"  Compartidos con dos farmacias: "
            f"{sum(cantidad for grupo, cantidad in coincidencias.items() if len(grupo) == 2)}"
        )

        self.stdout.write(
            f"  Compartidos con tres farmacias: "
            f"{coincidencias[(3, 4, 5)]}"
        )

        self.stdout.write("\nInformación incompleta:")

        self.stdout.write(
            f"  Sin principio activo: {sin_principio_activo}"
        )
        self.stdout.write(
            f"  Sin presentación: {sin_presentacion}"
        )
        self.stdout.write(
            f"  Sin laboratorio: {sin_laboratorio}"
        )

        self.stdout.write("\nRegistros Precio asociados:")

        for nombre, cantidad in total_precios.items():
            self.stdout.write(f"  {nombre}: {cantidad}")

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("Auditoría finalizada. No se modificó ningún registro.")
        self.stdout.write(f"Archivo generado: {archivo.resolve()}")
