from collections import defaultdict
import re
from django.core.management.base import BaseCommand
from django.db import transaction

from farmacia.models import Producto
from farmacia.procesamento.guardar_productos import (
    normalizar_texto_producto,
    extraer_firma_producto,
)

IDS_REVISION_MANUAL = {
    1460, 15872,       # Metamizol
    1518, 10122,       # Melatonina
    3577, 13708,       # Metotrexato
    11139, 15752,      # Carvedilol
}


def caracteristicas_adicionales(producto, precios):
    textos = [
        producto.nombre or "",
        producto.presentacion or "",
    ]

    textos.extend(
        precio.url_producto or ""
        for precio in precios
    )

    texto = normalizar_texto_producto(" ".join(textos))

    patrones = {
        "masticable": r"\bmasticables?\b",
        "macrocristales": r"\bmacrocristales?\b",
        "capsula_blanda": r"\bcapsulas? blandas?\b|\bsoftgel\b",
        "enterico": (
            r"\benteric[oa]s?\b|"
            r"\brecubrimiento enterico\b|"
            r"\bmicrogranulos entericos\b"
        ),
    }

    return tuple(sorted(
        nombre
        for nombre, patron in patrones.items()
        if re.search(patron, texto)
    ))

class Command(BaseCommand):
    help = "Analiza productos equivalentes entre farmacias."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Ejecuta la homologacion de los grupos revisados.",
        )

    def handle(self, *args, **options):
        grupos = defaultdict(list)

        productos = (
            Producto.objects
            .select_related("medicamento")
            .prefetch_related("precios__farmacia")
            .filter(precios__isnull=False)
            .distinct()
            .iterator(chunk_size=500)
        )

        total = 0
        self.stdout.write("Analizando productos...")

        for producto in productos:
            total += 1

            if producto.id in IDS_REVISION_MANUAL:
                continue

            if not producto.medicamento:
                continue
            activo = normalizar_texto_producto(
                producto.medicamento.principio_activo or ""
            )

            if not activo:
                continue

            firma = extraer_firma_producto(
                producto.nombre,
                producto.presentacion or "",
            )

            concentraciones, forma, caracteristicas, cantidad = firma

            # Se exige una firma suficiente para evitar coincidencias debiles.
            if not concentraciones or not forma or not cantidad:
                continue

            nombre = normalizar_texto_producto(producto.nombre)

            if not nombre:
                continue

            # Los genericos se agrupan aunque tengan laboratorios distintos.
            # Las marcas comerciales solo se agrupan con la misma primera palabra.
            if nombre == activo or nombre.startswith(activo + " "):
                identidad = "generico"
            else:
                identidad = "marca:" + nombre.split()[0]

            precios = list(producto.precios.all())

            if not precios:
                continue

            adicionales = caracteristicas_adicionales(
                producto,
                precios,
            )

            # La firma ya contiene concentracion, forma, caracteristicas y cantidad.
            clave = (
                identidad,
                activo,
                firma,
                adicionales,
                bool(producto.es_bioequivalente),
            )

            grupos[clave].append({
                "producto": producto,
                "farmacias": {
                    precio.farmacia_id for precio in precios
                },
                "nombres_farmacias": sorted({
                    precio.farmacia.nombre for precio in precios
                }),
            })

        candidatos = []

        for clave, elementos in grupos.items():
            if len(elementos) < 2:
                continue

            farmacias_vistas = set()
            conflicto = False

            for elemento in elementos:
                if farmacias_vistas.intersection(elemento["farmacias"]):
                    conflicto = True
                    break

                farmacias_vistas.update(elemento["farmacias"])

            if not conflicto:
                candidatos.append((clave, elementos))

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write("SIMULACION DE HOMOLOGACION DE PRODUCTOS")
        self.stdout.write("=" * 65)
        self.stdout.write(f"Productos analizados: {total}")
        self.stdout.write(f"Grupos candidatos: {len(candidatos)}")

        total_productos = sum(
            len(elementos) for _, elementos in candidatos
        )

        self.stdout.write(f"Productos involucrados: {total_productos}")

        for numero, (clave, elementos) in enumerate(candidatos, start=1):
            identidad, activo, firma, adicionales, bioequivalente = clave

            self.stdout.write("-" * 65)
            self.stdout.write(f"GRUPO {numero}: {identidad}")
            self.stdout.write(f"Principio activo: {activo}")
            self.stdout.write(f"Firma: {firma}")
            self.stdout.write(f"Características adicionales: {adicionales}")
            self.stdout.write(f"Bioequivalente: {bioequivalente}")

            for elemento in elementos:
                producto = elemento["producto"]
                farmacias = ", ".join(elemento["nombres_farmacias"])

                self.stdout.write(
                    f"ID {producto.id}: {producto.nombre} "
                    f"| Laboratorio: {producto.laboratorio or 'Sin dato'} "
                    f"| Farmacias: {farmacias}"
                )

        if not options["confirmar"]:
            self.stdout.write(
                "\nSIMULACION TERMINADA. No se modifico la base de datos."
            )
            self.stdout.write(
                "No ejecutar --confirmar hasta revisar los grupos."
            )
            return

        homologados = 0
        omitidos = 0

        for clave, elementos in candidatos:
            fusionados_grupo = 0

            try:
                with transaction.atomic():
                    ordenados = sorted(
                        elementos,
                        key=lambda elemento: (
                            -len(elemento["farmacias"]),
                            -bool(elemento["producto"].laboratorio),
                            -bool(elemento["producto"].presentacion),
                            -bool(elemento["producto"].sku),
                            -len(elemento["producto"].nombre),
                            elemento["producto"].id,
                        ),
                    )

                    principal = Producto.objects.select_for_update().get(
                        pk=ordenados[0]["producto"].pk
                    )

                    for elemento in ordenados[1:]:
                        duplicado = Producto.objects.select_for_update().get(
                            pk=elemento["producto"].pk
                        )

                        precios = list(duplicado.precios.all())

                        for precio in precios:
                            if principal.precios.filter(
                                farmacia_id=precio.farmacia_id
                            ).exists():
                                raise ValueError(
                                    f"Conflicto de farmacia para {principal.nombre}"
                                )

                        for precio in precios:
                            precio.producto = principal
                            precio.save(update_fields=["producto"])

                        id_duplicado = duplicado.pk 
                        duplicado.delete()
                        fusionados_grupo += 1

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Fusionado ID {id_duplicado} -> ID {principal.pk}"
                            )
                        )
            
                        homologados += fusionados_grupo

            except Exception as error:
                omitidos += len(elementos) - 1
                self.stdout.write(
                    self.style.ERROR(f"Grupo omitido: {error}")
                )

        self.stdout.write("\n" + "=" * 65)
        self.stdout.write(f"Productos fusionados: {homologados}")
        self.stdout.write(f"Productos omitidos: {omitidos}")
        self.stdout.write("Proceso finalizado.")
