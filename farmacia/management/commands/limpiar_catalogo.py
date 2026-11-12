
import csv
import unicodedata
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from farmacia.models import Producto


def normalizar(texto):
    texto = str(texto or "").lower().strip()
    return "".join(
        caracter
        for caracter in unicodedata.normalize("NFD", texto)
        if unicodedata.category(caracter) != "Mn"
    )


def clasificar_producto(producto):
    nombre = normalizar(producto.nombre)
    categoria = normalizar(getattr(producto, "categoria", ""))
    principio = normalizar(getattr(producto, "principio_activo", ""))

    # Categorías propias del proyecto.
    if categoria in ("medicamentos", "cosmeticos", "cuidado_personal"):
        return "conservar", "Categoría propia del proyecto"

    # Principios activos: señal fuerte de medicamento.
    if principio:
        return "conservar", "Tiene principio activo"

    # Indicadores de medicamentos y productos farmacéuticos.
    farmaceuticos = [
        "crema topica", "crema dermica", "solucion topica",
        "solucion oftalmica", "unguento", "unguento oftalmico",
        "solucion otologica", "ovulos", "ampolla",
        "insulina", "clotrimazol", "aciclovir",
        "gentamicina", "betametasona", "lidocaina",
        "ciprofloxacino", "mupirocina", "nistatina",
        "metronidazol", "timolol", "pilocarpina",
        "diclofenaco", "ketoconazol", "antazolina",
        "atropina", "polimixina", "neomicina",
        "medicamento", "farmaceutico",
    ]

    if any(palabra in nombre for palabra in farmaceuticos):
        return "conservar", "Producto farmacéutico"

    # Cosméticos y cuidado personal.

    cuidado = [
        "crema", "gel", "mascarilla", "tintura",
        "coloracion", "cepillo", "eau", "enjuague",
        "esmalte", "espuma", "aceite", "protector",
        "fotoprotector", "toallas", "toalla",
        "sombra", "antitranspirante", "mascara",
        "colonia", "spray", "base", "locion",
        "limpiador", "repuesto", "estuche",
        "maquina", "maquina de afeitar",
        "mamadera", "chupete", "biberon",
        "ropa interior", "preservativo",
        "cepillo dental", "hilo dental",
        "desodorante", "shampoo", "acondicionador",
        "serum", "labial", "delineador",
        "rubor", "polvo compacto", "maquillaje",
        "agua micelar", "removedor", "exfoliante",
        "hidratante", "antiedad", "antiarrugas",
        "nuxe", "eucerin", "svr", "nutrisse",
    ]

    if any(palabra in nombre for palabra in cuidado):
        return "conservar", "Cosmético o cuidado personal"


    # Productos veterinarios y para mascotas.
    mascotas = [
        "veterinaria", "veterinario", "para perros",
        "para gatos", "para perro", "para gato",
        "alimento perro", "alimento gato",
        "snack perro", "snack gato",
        "galleta perro", "galleta gato",
        "mascotas", "antipulgas perro",
        "antipulgas gato",
    ]

    if any(palabra in nombre for palabra in mascotas):
        return "eliminar", "Producto para mascotas o veterinario"

    # Artículos de hogar y limpieza.
    hogar = [
        "detergente", "lavaloza", "lavalozas",
        "limpiavidrios", "limpia pisos",
        "limpiador de pisos", "cloro",
        "desinfectante de superficies",
        "bolsas de basura", "esponja",
        "paño de limpieza", "ambientador",
        "suavizante de ropa",
    ]

    if any(palabra in nombre for palabra in hogar):
        return "eliminar", "Artículo de hogar o limpieza"

    # Nutrición, suplementos y productos relacionados con la salud.
    salud = [
        "vitamina", "multivitamin", "gomitas",
        "gummies", "proteina", "protein",
        "whey", "creatina", "colageno",
        "suplemento", "magnesio", "omega 3",
        "omega-3", "probiotico", "prebiotico",
        "propoleo", "isolate", "aminoacido",
        "nutricion infantil", "cereal infantil",
        "alimento infantil", "formula infantil",
        "complemento alimenticio",
    ]

    if principio or any(palabra in nombre for palabra in salud):
        return "conservar", "Medicamento, suplemento o nutrición"

    # Alimentos y bebidas convencionales.
    alimentos = [
        "chocolate", "galletas", "galleta",
        "bombones", "caramelos", "golosinas",
        "papas fritas", "snack", "bebida gaseosa",
        "bebida lactea", "agua saborizada",
        "jugo de fruta", "nectar",
        "mermelada", "brownie", "queque",
        "pastel", "barrita de cereal",
        "barra de cereal", "galletón",
        "galeton",
    ]

    if any(palabra in nombre for palabra in alimentos):
        return "eliminar", "Alimento o bebida convencional"

    # Productos médicos, ortopédicos y de diagnóstico.
    medicos = [
        "accu-chek", "parche", "parches",
        "adhesiva", "adhesivo", "cinta",
        "venda", "vendas", "suerox",
        "lente de contacto", "lentes de contacto",
        "guantes", "guatero", "termometro",
        "gasa", "gasas", "algodon",
        "jeringa", "jeringas", "mascarilla quirurgica",
        "apósito", "aposito", "curita",
    ]

    if any(palabra in nombre for palabra in medicos):
        return "conservar", "Producto médico o de diagnóstico"

    # Marcas de cosmética y cuidado personal.
    marcas_cuidado = [
        "filorga", "isdinceutics", "infallible",
        "loreal", "l'oreal", "eucerin",
        "nuxe", "svr", "lifestyles",
        "accu-chek",
    ]

    if any(marca in nombre for marca in marcas_cuidado):
        return "conservar", "Marca de salud o cuidado personal"

    
    # Medicamentos y productos farmacéuticos reconocibles.
    medicamentos_extra = [
        "salbutamol", "albendazol", "povidona",
        "picosulfato", "pargeverina", "simeticona",
        "sucralfato", "valeriana", "psyllium",
        "bicarbonato", "cloruro", "gluconato",
        "periciazina", "benzocaina", "caolin",
        "hamamelis", "mentol", "vaselina medicinal",
        "extracto fluido", "supositorios", "enema",
        "gotas nasales", "solucion nasal",
        "solucion para nebulizacion",
    ]

    if any(palabra in nombre for palabra in medicamentos_extra):
        return "conservar", "Medicamento o producto farmacéutico"

    # Dispositivos médicos y ortopédicos.
    dispositivos = [
        "tiras de glucosa", "tira de glucosa",
        "aguja hipodermica", "aguja desechable",
        "aerocamara", "aerocamara",
        "compresa", "cabestrillo", "rodillera",
        "muñequera", "munequera", "faja",
        "baja lenguas", "bajalenguas",
        "paleta de madera", "tapón para oidos",
        "tapon para oidos", "optifree",
        "optifree", "optical", "anillo vaginal",
    ]

    if any(palabra in nombre for palabra in dispositivos):
        return "conservar", "Dispositivo o accesorio médico"

    # Nutrición infantil.
    nutricion_infantil = [
        "formula lactea", "formula de inicio",
        "colado", "picado carne",
        "alimento infantil",
    ]

    if any(palabra in nombre for palabra in nutricion_infantil):
        return "conservar", "Nutrición infantil"

    # Cosmética, higiene y accesorios de cuidado personal.
    cuidado_extra = [
        "desmaquillante", "after shave",
        "fragancia", "talco", "emulsion",
        "emulsionado", "cotonitos",
        "anillo denticion", "cortauñas",
        "corta uñas", "pinza de ceja",
        "lima", "fijador", "proteccion solar",
        "protección solar", "aloe vera",
        "esmalte", "tónico", "tonico",
        "sacapuntas",
    ]

    if any(palabra in nombre for palabra in cuidado_extra):
        return "conservar", "Cuidado personal o accesorio"

    # Productos veterinarios.
    veterinarios_extra = [
        "drontal", "ursovet", "ronaxan",
        "puppy", "veterinario", "uso veterinario",
    ]

    if any(palabra in nombre for palabra in veterinarios_extra):
        return "eliminar", "Producto veterinario"
    
    return "revisar", "No se pudo determinar automáticamente"


class Command(BaseCommand):
    help = "Audita y clasifica los productos del catálogo FARMA PRICEY"

    def handle(self, *args, **options):
        productos = (
            Producto.objects
            .all()
            .prefetch_related("precios__farmacia")
            .order_by("id")
        )

        ruta = Path(settings.BASE_DIR) / "auditoria_limpieza_catalogo.csv"

        conteos = {
            "conservar": 0,
            "eliminar": 0,
            "revisar": 0,
        }

        with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
            campos = [
                "ID", "Nombre", "Categoria",
                "Principio activo", "Clasificacion",
                "Motivo", "Cantidad de precios", "Farmacias",
            ]

            escritor = csv.DictWriter(archivo, fieldnames=campos)
            escritor.writeheader()

            for producto in productos:
                clasificacion, motivo = clasificar_producto(producto)
                conteos[clasificacion] += 1

                precios = list(producto.precios.all())

                farmacias = sorted({
                    precio.farmacia.nombre
                    for precio in precios
                    if precio.farmacia
                })

                escritor.writerow({
                    "ID": producto.id,
                    "Nombre": producto.nombre,
                    "Categoria": getattr(producto, "categoria", ""),
                    "Principio activo": getattr(
                        producto, "principio_activo", ""
                    ),
                    "Clasificacion": clasificacion,
                    "Motivo": motivo,
                    "Cantidad de precios": len(precios),
                    "Farmacias": ", ".join(farmacias),
                })

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("AUDITORÍA COMPLETADA"))
        self.stdout.write(f"Productos analizados: {sum(conteos.values())}")
        self.stdout.write(f"Conservar: {conteos['conservar']}")
        self.stdout.write(f"Candidatos a eliminar: {conteos['eliminar']}")
        self.stdout.write(f"Revisión manual: {conteos['revisar']}")
        self.stdout.write("")
        self.stdout.write(f"Archivo generado: {ruta}")
        self.stdout.write(self.style.WARNING(
            "No se eliminó ningún producto."
        ))
