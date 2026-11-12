
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from farmacia.models import Producto
from farmacia.procesamento.guardar_productos import (
    normalizar_texto_producto,
    extraer_firma_producto,
)


class Command(BaseCommand):
    help = "Homologa productos duplicados entre las cuatro farmacias."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Confirma y ejecuta la homologación."
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

            if not producto.medicamento:
                continue

            activo = normalizar_texto_producto(
                producto.medicamento.principio_activo
            )

            if not activo:
                continue

            firma = extraer_firma_producto(
                producto.nombre,
                producto.presentacion
            )

            concentraciones, forma, cantidad = firma

            if not concentraciones or not forma or not cantidad:
                continue

            nombre = normalizar_texto_producto(producto.nombre)
            marca = nombre.split()[0] if nombre else ""
            
            laboratorio = normalizar_texto_producto(
                producto.laboratorio or ""
            )

            # Los genéricos deben tener laboratorio identificado.
            if marca == activo and not laboratorio:
                continue

            laboratorio_clave = laboratorio if marca == activo else ""
            
            texto_detalle = normalizar_texto_producto(
                f"{producto.nombre} {producto.presentacion or ''}"
            )
            

            formulaciones = (
                "masticable" if "masticable" in texto_detalle else "",
                "efervescente" if "efervescente" in texto_detalle else "",
                "dispersable" if "dispersable" in texto_detalle else "",
                "liberacion_prolongada" if any(
                    palabra in texto_detalle
                    for palabra in ("liberacion prolongada", "liberacion extendida")
                ) else "",
                "liberacion_retardada" if "liberacion retardada" in texto_detalle else "",
                "capsula_blanda" if "capsula blanda" in texto_detalle else "",
                "recubrimiento_enterico" if (
                    "recubrimiento enterico" in texto_detalle
                    or "recubierto enterico" in texto_detalle
                ) else "",
                "recubierto" if "recubiert" in texto_detalle else "",
                "bioequivalente" if "bioequivalente" in texto_detalle else "",
                "capsula_blanda" if (
                    "capsula" in texto_detalle and "bland" in texto_detalle
                ) else "",
            )

            if not marca:
                continue

            precios = list(producto.precios.all())

            if not precios:
                continue

            clave = (
                marca,
                activo,
                firma,
                producto.es_bioequivalente,
                formulaciones,
                laboratorio_clave,
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

            # No fusionar si dos productos tienen precios
            # de la misma farmacia.
            farmacias_vistas = set()
            conflicto = False

            for elemento in elementos:
                if farmacias_vistas.intersection(elemento["farmacias"]):
                    conflicto = True
                    break

                farmacias_vistas.update(elemento["farmacias"])

            if conflicto:
                continue

            candidatos.append((clave, elementos))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("HOMOLOGACIÓN GENERAL DE PRODUCTOS")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Productos analizados: {total}")
        self.stdout.write(f"Grupos candidatos: {len(candidatos)}")

        total_productos = sum(
            len(elementos) for _, elementos in candidatos
        )

        self.stdout.write(f"Productos involucrados: {total_productos}")

        for numero, (clave, elementos) in enumerate(candidatos, start=1):
            marca, activo, firma, bioequivalente, formulaciones, laboratorio_clave  = clave

            self.stdout.write("-" * 60)
            self.stdout.write(f"GRUPO {numero}: {marca}")
            self.stdout.write(f"Principio activo: {activo}")
            self.stdout.write(f"Firma: {firma}")

            for elemento in elementos:
                producto = elemento["producto"]
                farmacias = ", ".join(elemento["nombres_farmacias"])

                self.stdout.write(
                    f"ID {producto.id}: {producto.nombre} "
                    f"| Farmacias ID: {farmacias}"
                )

        if not options["confirmar"]:
            self.stdout.write(
                self.style.WARNING(
                    "\nSimulación terminada. No se modificó la base de datos."
                )
            )
            self.stdout.write(
                "Usa --confirmar para ejecutar la homologación."
            )
            return

        homologados = 0
        omitidos = 0

        for clave, elementos in candidatos:
            try:
                with transaction.atomic():
                    # Conservar como principal el producto
                    # que ya tenga más precios registrados.
                    elementos_ordenados = sorted(
                        elementos,
                        key=lambda e: (
                            -len(e["farmacias"]),
                            -bool(e["producto"].laboratorio),
                            -bool(e["producto"].presentacion),
                            -bool(e["producto"].sku),
                            -len(e["producto"].nombre),
                            e["producto"].id,
                        )
                    )

                    principal = Producto.objects.select_for_update().get(
                        pk=elementos_ordenados[0]["producto"].pk
                    )

                    duplicados = elementos_ordenados[1:]

                    for elemento in duplicados:
                        duplicado = Producto.objects.select_for_update().get(
                            pk=elemento["producto"].pk
                        )

                        precios = list(duplicado.precios.all())

                        # Verificación final antes de transferir.
                        for precio in precios:
                            if principal.precios.filter(
                                farmacia_id=precio.farmacia_id
                            ).exists():
                                raise ValueError(
                                    f"Conflicto de farmacia en {principal.nombre}"
                                )

                        for precio in precios:
                            precio.producto = principal
                            precio.save(update_fields=["producto"])

                        nombre = duplicado.nombre
                        duplicado.delete()

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Fusionado: {nombre} -> {principal.nombre}"
                            )
                        )

                    homologados += len(duplicados)

            except Exception as error:
                omitidos += len(elementos) - 1
                self.stdout.write(
                    self.style.ERROR(
                        f"Grupo omitido: {error}"
                    )
                )

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"Productos fusionados: {homologados}")
        self.stdout.write(f"Productos omitidos: {omitidos}")
        self.stdout.write("Proceso finalizado.")
