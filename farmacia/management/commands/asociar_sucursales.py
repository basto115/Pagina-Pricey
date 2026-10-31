import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

from farmacia.models import Farmacia, Sucursal


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.casefold())
    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(texto.split())


class Command(BaseCommand):
    help = "Asocia sucursales con las cuatro cadenas de FARMA PRICEY"

    CADENAS = {
        "cruz verde": ("cruz verde",),
        "salcobrand": ("salcobrand",),
        "ahumada": ("ahumada",),
        "dr simi": (
            "dr simi",
            "doctor simi",
            "farmacia simi",
            "farmacias simi",
            "farmacia del dr simi",
            "farmacias del dr. simi",
        ),
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--simular",
            action="store_true",
            help="Muestra las asociaciones sin guardar cambios.",
        )

    def handle(self, *args, **options):
        simular = options["simular"]

        farmacias = list(Farmacia.objects.all())

        # Identificar los registros de las cuatro cadenas.
        registros_cadenas = {}

        for cadena, alias in self.CADENAS.items():
            coincidencias = [
                farmacia
                for farmacia in farmacias
                if any(
                    nombre in normalizar(farmacia.nombre)
                    or normalizar(farmacia.nombre) in nombre
                    for nombre in alias
                )
            ]

            if len(coincidencias) == 1:
                registros_cadenas[cadena] = coincidencias[0]
            elif len(coincidencias) == 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"No se encontró el registro de Farmacia: {cadena}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Hay varios registros para {cadena}. "
                        "Se requiere revisión manual."
                    )
                )

        nuevas_asociaciones = 0
        sin_identificar = 0
        ya_asociadas = 0
        posibles_cadenas = []

        sucursales = Sucursal.objects.select_related(
            "farmacia"
        ).all()

        for sucursal in sucursales:
            if sucursal.farmacia_id is not None:
                ya_asociadas += 1
                continue

            nombre = normalizar(sucursal.nombre)

            coincidencias = [
                cadena
                for cadena in self.CADENAS
                if any(
                    alias in nombre
                    for alias in self.CADENAS[cadena]
                )
            ]

            if len(coincidencias) != 1:
                sin_identificar += 1

                if any(
                    palabra in nombre
                    for palabra in [
                        "cruz",
                        "verde",
                        "salco",
                        "ahum",
                        "simi",
                        "farmacia",
                    ]
                ):
                    posibles_cadenas.append(sucursal.nombre)

                continue

            cadena = coincidencias[0]
            farmacia = registros_cadenas.get(cadena)

            if farmacia is None:
                sin_identificar += 1
                continue

            self.stdout.write(
                f"{sucursal.nombre} -> {farmacia.nombre}"
            )

            if not simular:
                with transaction.atomic():
                    sucursal.farmacia = farmacia
                    sucursal.save(update_fields=["farmacia"])

            nuevas_asociaciones += 1
        
        self.stdout.write("\n--- Posibles cadenas no identificadas ---")

        for nombre in posibles_cadenas[:100]:
            self.stdout.write(f"- {nombre}")

        self.stdout.write(
            f"Total de nombres para revisar: {len(posibles_cadenas)}"
        )

        self.stdout.write("\n========== RESUMEN ==========")
        self.stdout.write(
            f"Asociaciones posibles: {nuevas_asociaciones}"
        )
        self.stdout.write(
            f"Ya asociadas anteriormente: {ya_asociadas}"
        )
        self.stdout.write(
            f"Sin identificar o con dudas: {sin_identificar}"
        )

        if simular:
            self.stdout.write(
                self.style.WARNING(
                    "SIMULACIÓN: no se guardaron cambios."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Asociaciones guardadas correctamente."
                )
            )
