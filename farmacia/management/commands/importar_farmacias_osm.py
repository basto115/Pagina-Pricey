import requests
import time

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from farmacia.models import Sucursal


#este def es geocodificacion inversa, wowzers
def obtener_direccion(latitud, longitud):
    url = "https://nominatim.openstreetmap.org/reverse"

    parametros = {
        "lat": latitud,
        "lon": longitud,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 18,
    }

    encabezados = {
        "User-Agent": "FarmaPricey/1.0 (academic project)"
    }

    try:
        respuesta = requests.get(
            url,
            params=parametros,
            headers=encabezados,
            timeout=20,
        )

        respuesta.raise_for_status()
        datos = respuesta.json()

        direccion = datos.get("address", {})

        calle = (
            direccion.get("road")
            or direccion.get("pedestrian")
            or direccion.get("residential")
            or ""
        )

        numero = direccion.get("house_number", "")

        sector = (
            direccion.get("suburb")
            or direccion.get("neighbourhood")
            or direccion.get("town")
            or direccion.get("city")
            or ""
        )

        resultado = " ".join(
            parte for parte in [calle, numero] if parte
        )

        if sector:
            resultado = f"{resultado}, {sector}" if resultado else sector

        return resultado

    except requests.RequestException:
        return ""

class Command(BaseCommand):
    help = "Importa y actualiza farmacias desde OpenStreetMap"

    COMUNAS = [
        "Curacaví",
        "Providencia",
        "Ñuñoa",
        "Las Condes",
        "Santiago",
        "Vitacura",
        "Recoleta",
        "Macul",
        "La Reina",
    ]

    URL_OVERPASS = "https://overpass-api.de/api/interpreter"

    def add_arguments(self, parser):
        parser.add_argument(
            "--comuna",
            type=str,
            help="Importar solamente una comuna.",
        )

    def handle(self, *args, **options):
        comuna_individual = options.get("comuna")

        if comuna_individual:
            comunas = [comuna_individual]
        else:
            comunas = self.COMUNAS

        total_nuevas = 0
        total_actualizadas = 0
        total_existentes = 0
        total_sin_nombre = 0
        total_errores = 0

        self.stdout.write(
            self.style.SUCCESS("Iniciando importación desde OpenStreetMap...")
        )

        for comuna in comunas:
            self.stdout.write(f"\nConsultando {comuna}...")

            consulta = f"""
            [out:json][timeout:90];
            area["name"="Chile"]["boundary"="administrative"]->.chile;
            area["name"="{comuna}"]["boundary"="administrative"](area.chile)->.zona;
            (
                node["amenity"="pharmacy"](area.zona);
                way["amenity"="pharmacy"](area.zona);
                relation["amenity"="pharmacy"](area.zona);
            );
            out center tags;
            """

            try:
                respuesta = requests.post(
                    self.URL_OVERPASS,
                    data={"data": consulta},
                    timeout=120,
                    headers={
                        "User-Agent": "FarmaPricey/1.0 (academic project)"
                    },
                )

                respuesta.raise_for_status()
                elementos = respuesta.json().get("elements", [])

            except (requests.RequestException, ValueError) as error:
                total_errores += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"No se pudo consultar {comuna}: {error}"
                    )
                )
                continue

            nuevas_comuna = 0
            actualizadas_comuna = 0

            for elemento in elementos:
                osm_id = f'{elemento["type"]}/{elemento["id"]}'
                etiquetas = elemento.get("tags", {})

                nombre = etiquetas.get("name", "").strip()

                if not nombre:
                    total_sin_nombre += 1
                    continue

                latitud = elemento.get("lat")
                longitud = elemento.get("lon")

                centro = elemento.get("center", {})

                if latitud is None:
                    latitud = centro.get("lat")

                if longitud is None:
                    longitud = centro.get("lon")

                if latitud is None or longitud is None:
                    total_errores += 1
                    continue

                direccion = etiquetas.get("addr:full", "").strip()

                if not direccion:
                    calle = etiquetas.get("addr:street", "").strip()
                    numero = etiquetas.get("addr:housenumber", "").strip()

                    direccion = " ".join(
                        parte for parte in [calle, numero] if parte
                    )

                if not direccion:
                    direccion = etiquetas.get("addr:place", "").strip()

                if not direccion:
                    direccion = etiquetas.get("addr:suburb", "").strip()
                
                sitio_web = (
                    etiquetas.get("website")
                    or etiquetas.get("contact:website")
                    or ""
                )

                if not direccion:
                    direccion = obtener_direccion(latitud, longitud)
                    time.sleep(1)

                datos = {
                    "nombre": nombre,
                    "direccion": direccion,
                    "comuna": comuna,
                    "latitud": latitud,
                    "longitud": longitud,
                    "sitio_web": sitio_web,
                }

                try:
                    sucursal = Sucursal.objects.filter(
                        osm_id=osm_id
                    ).first()

                    if sucursal:
                        for campo, valor in datos.items():
                            setattr(sucursal, campo, valor)

                        sucursal.save()
                        total_actualizadas += 1
                        actualizadas_comuna += 1

                    else:
                        Sucursal.objects.create(
                            osm_id=osm_id,
                            origen="openstreetmap",
                            aprobada=False,
                            farmacia=None,
                            **datos,
                        )

                        total_nuevas += 1
                        nuevas_comuna += 1

                except Exception as error:
                    total_errores += 1
                    
                    self.stderr.write(
                        self.style.ERROR(
                            f"Error procesando {nombre} ({osm_id}): {error!r}"
                        )
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{comuna}: {nuevas_comuna} nuevas, "
                    f"{actualizadas_comuna} actualizadas."
                )
            )

        self.stdout.write("\n========== RESUMEN ==========")
        self.stdout.write(f"Nuevas sucursales: {total_nuevas}")
        self.stdout.write(f"Actualizadas: {total_actualizadas}")
        self.stdout.write(f"Sin nombre: {total_sin_nombre}")
        self.stdout.write(f"Errores: {total_errores}")

        self.stdout.write(
            self.style.SUCCESS("Importación finalizada.")
        )
