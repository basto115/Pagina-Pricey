from decimal import Decimal, InvalidOperation
import re
import unicodedata

from django.db import transaction
from farmacia.procesamento.normalizar import detectar_categoria

def extraer_principio_activo(nombre):
    """Identifica principios activos conocidos dentro del nombre."""

    import re
    import unicodedata

    def normalizar(texto):
        texto = unicodedata.normalize("NFKD", str(texto).lower())
        texto = texto.encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]+", " ", texto).strip()

    activos = Medicamento.objects.exclude(
        principio_activo=""
    ).exclude(
        principio_activo__isnull=True
    ).values_list("principio_activo", flat=True)

    texto = " " + normalizar(nombre) + " "
    encontrados = {}

    for activo in activos:
        clave = normalizar(activo)

        if len(clave) > 5 and clave != "hidroxido":
            if " " + clave + " " in texto:
                encontrados[clave] = activo.strip()

    if not encontrados:
        return ""

    claves = list(encontrados)

    # Priorizar coincidencias más específicas.
    mejores = [
        clave for clave in claves
        if all(
            otra == clave or (" " + otra + " ") in (" " + clave + " ")
            for otra in claves
        )
    ]

    if len(mejores) == 1:
        return encontrados[mejores[0]]

    return ""

from farmacia.models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio,
)

_BUSQUEDA_NO_REALIZADA = object()
_INDICE_PRODUCTOS = None

def normalizar_nombre_busqueda(nombre):
    """
    Normaliza nombres para comparar productos
    aunque las farmacias los escriban de forma diferente.
    """
    if not nombre:
        return ""

    nombre = str(nombre).lower().strip()
    nombre = nombre.replace("×", " ")
    nombre = re.sub(r"\(b\)", "", nombre, flags=re.IGNORECASE)
    nombre = re.sub(r"\s+x\s*(?=\d)", " ", nombre)
    nombre = unicodedata.normalize("NFD", nombre)
    nombre = "".join(
        caracter for caracter in nombre
        if unicodedata.category(caracter) != "Mn"
    )
    return " ".join(nombre.split()).strip()

def convertir_booleano(valor):
    if isinstance(valor, bool):
        return valor

    if isinstance(valor, str):
        return valor.strip().lower() in {
            "true", "1", "si", "sí", "yes"
        }

    return bool(valor)

def generar_clave_producto(
    nombre,
    principio_activo="",
    presentacion="",
):
    """
    Genera una clave para comparar productos
    y distinguir los bioequivalentes.
    """
    nombre = str(nombre or "").strip()

    es_bioequivalente = bool(
        re.search(r"\(b\)", nombre, flags=re.IGNORECASE)
    )

    nombre_base = re.sub(
        r"\(b\)",
        "",
        nombre,
        flags=re.IGNORECASE,
    )

    return (
        normalizar_nombre_busqueda(nombre_base),
        normalizar_nombre_busqueda(principio_activo),
        normalizar_nombre_busqueda(presentacion),
        es_bioequivalente,
    )

def convertir_precio(valor):
    """
    Convierte un precio válido a Decimal.
    Ejemplos: 1490, '1490', '1.490', '$1.490'.
    """
    if valor is None or valor == "":
        return None

    if isinstance(valor, (int, float, Decimal)):
        try:
            precio = Decimal(str(valor))
        except (InvalidOperation, ValueError):
            return None
    else:
        texto = str(valor).strip()
        texto = texto.replace("$", "").replace(" ", "")
        texto = texto.replace(".", "")

        if not texto.isdigit():
            return None

        try:
            precio = Decimal(texto)
        except InvalidOperation:
            return None

    if not precio.is_finite() or precio <= 0:
        return None

    return precio


def buscar_medicamento(nombre, principio_activo=""):
    """
    Busca un medicamento por nombre normalizado.
    Si no existe, lo crea.
    """
    nombre_busqueda = normalizar_nombre_busqueda(nombre)

    for medicamento in Medicamento.objects.all():
        if (
            normalizar_nombre_busqueda(medicamento.nombre)
            == nombre_busqueda
        ):
            if principio_activo and not medicamento.principio_activo:
                medicamento.principio_activo = principio_activo
                medicamento.save(update_fields=["principio_activo"])

            return medicamento

    return Medicamento.objects.create(
        nombre=nombre,
        principio_activo=principio_activo or "",
    )
    
def normalizar_texto_producto(texto):
    """Normaliza texto para comparar nombres y presentaciones."""
    
    if not texto:
        return ""
    
    texto = str(texto).lower().strip()
    
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    
    texto = texto.replace("×", "x")
    texto = texto.replace("(b)", "")
    texto = re.sub(r"(?<!\d)\.(?!\d)", " ", texto)
    
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def extraer_firma_producto(nombre, presentacion=""):
    """
    Extrae características comparables:
    concentración, forma farmacéutica, características especiales y cantidad.
    """

    texto = normalizar_texto_producto(
        f"{nombre} {presentacion}"
    )

    # Concentraciones, incluyendo proporciones como 500 mg/5 ml.
    patron_concentracion = (
        r"\d+(?:[.,]\d+)?\s*"
        r"(?:mg|mcg|g)"
        r"(?:\s*/\s*\d+(?:[.,]\d+)?\s*ml)?\b"
    )

    concentraciones = re.findall(
        patron_concentracion,
        texto
    )

    concentraciones = sorted(set(
        re.sub(r"\s+", "", c).replace(",", ".")
        for c in concentraciones
    ))

    # Formas farmacéuticas.
    formas = {
        "comprimidos": ["comprimido", "comprimidos", "tableta", "tabletas"],
        "capsulas": ["capsula", "capsulas"],
        "gotas": ["gotas"],
        "jarabe": ["jarabe"],
        "crema": ["crema"],
        "unguento": ["unguento", "pomada"],
        "gel": ["gel"],
        "suspension": ["suspension"],
        "solucion": ["solucion"],
        "polvo": ["polvo"],
        "ampollas": ["ampolla", "ampollas"],
        "supositorios": ["supositorio", "supositorios"],
    }

    forma = ""

    for nombre_forma, variantes in formas.items():
        if any(
            re.search(rf"\b{re.escape(v)}\b", texto)
            for v in variantes
        ):
            forma = nombre_forma
            break

    # Características especiales de la formulación.
    caracteristicas = {
        "xr": [r"\bxr\b"],
        "liberacion_prolongada": [
            r"\bliberacion prolongada\b",
            r"\bliberacion extendida\b",
            r"\baccion prolongada\b",
        ],
        "liberacion_retardada": [
            r"\bliberacion retardada\b"
        ],
        "recubierto": [
            r"\brecubierto(?:s)?\b",
        ],
        "ranurado": [
            r"\branurado(?:s)?\b",
        ],
        "enterico": [
            r"\brecubrimiento enterico\b",
            r"\brecubiertos entericos\b",
            r"\bcubierta enterica\b",
        ],
        "dispersable": [
            r"\bdispersable(?:s)?\b",
        ],
        "efervescente": [
            r"\befervescente(?:s)?\b",
        ],
                "polvo_para_suspension": [
            r"\bpolvo\s+para\s+suspension\b",
        ],
        "plus": [
            r"\bplus\b",
        ],
    }

    caracteristicas_detectadas = []

    for caracteristica, patrones in caracteristicas.items():
        if any(re.search(patron, texto) for patron in patrones):
            caracteristicas_detectadas.append(caracteristica)

    # Cantidad de unidades.
    cantidad_unidades = re.search(
        r"\b(\d+)\s*(?:comprimidos?|comp|capsulas?|tabletas?|"
        r"ampollas?|supositorios?)\b",
        texto
    )

    cantidad = ""

    if cantidad_unidades:
        cantidad = cantidad_unidades.group(1) + " unidades"

    else:
        # Priorizar el volumen total indicado después de una "x".
        cantidad_ml = re.search(
            r"\bx\s*(\d+(?:[.,]\d+)?)\s*ml\b",
            texto
        )

        if not cantidad_ml:
            volumenes = list(re.finditer(
                r"(\d+(?:[.,]\d+)?)\s*ml\b",
                texto
            ))

            for coincidencia in volumenes:
                inicio = coincidencia.start()
                prefijo = texto[max(0, inicio - 12):inicio]

                if re.search(r"/\s*$", prefijo):
                    continue

                cantidad_ml = coincidencia
                break

        if cantidad_ml:
            cantidad = (
                cantidad_ml.group(1).replace(",", ".") + " ml"
            )

    return (
        tuple(concentraciones),
        forma,
        tuple(caracteristicas_detectadas),
        cantidad
    )

def obtener_clave_marca(nombre):
    """Obtiene palabras identificadoras del producto."""

    texto = normalizar_texto_producto(nombre)
    palabras_ignoradas = {
        "500", "100", "50", "25", "10",
        "mg", "mcg", "g", "gr", "ml",
        "comprimidos", "comprimido",
        "capsulas", "capsula",
        "recubiertos", "recubierto",
        "tabletas", "tableta",
        "pasta", "dental", "con", "de", "del",
        "para", "y", "el", "la", "en", "fluor",
        "pomo",
        "desodorante", "roll", "on",
        "serum", "facial",
        "gel", "crema", "limpiador",
        "hidratante", "protector", "solar",
        "shampoo", "acondicionador",
        "labial", "balsamo", "locion",
        "jabon", "spray", "micelar",
    }

    claves = [
        palabra
        for palabra in texto.split()
        if palabra not in palabras_ignoradas
        and len(palabra) >= 3
        and not re.fullmatch(
            r"\d+(?:[.,]\d+)?(?:mg|mcg|g|gr|kg|ml|l|ui)",
            palabra
        )
        and not palabra.isdigit()
    ]

    # Clave especial para la presentación Caristop 5000 de 51 g.
    numeros = re.findall(r"\d+", texto)

    if (
        "5000" in numeros
        and "51" in numeros
        and "pasta" in texto.split()
        and "dental" in texto.split()
    ):
        claves.append("__pasta_dental_5000_51g__")

    return claves

def obtener_indice_productos():
    """Carga los productos existentes una sola vez."""

    global _INDICE_PRODUCTOS

    if _INDICE_PRODUCTOS is None:
        indice = {}

        productos = (
            Producto.objects
            .select_related("medicamento")
            .only(
                "id",
                "nombre",
                "presentacion",
                "laboratorio",
                "es_bioequivalente",
                "categoria",
                "medicamento__principio_activo",
            )
            .iterator(chunk_size=500)
        )

        for producto in productos:
            claves = obtener_clave_marca(producto.nombre)

            for clave in claves:
                indice.setdefault(clave, []).append(producto)

        _INDICE_PRODUCTOS = indice

    return _INDICE_PRODUCTOS

def registrar_producto_en_indice(producto):
    """Agrega productos nuevos al índice durante la importación."""

    if _INDICE_PRODUCTOS is None:
        return

    claves = obtener_clave_marca(producto.nombre)

    for clave in claves:
        candidatos = _INDICE_PRODUCTOS.setdefault(clave, [])

        if not any(p.id == producto.id for p in candidatos):
            candidatos.append(producto)

def productos_equivalentes(
    existente,
    nombre,
    principio_activo,
    presentacion,
    laboratorio,
    es_bioequivalente,
    categoria,
):
    """Determina si dos registros representan el mismo producto."""

    claves_existente = set(obtener_clave_marca(existente.nombre))
    claves_nuevas = set(obtener_clave_marca(nombre))

    
    if categoria != "medicamentos":
        if existente.categoria != categoria:
            return False

        nombre_existente = normalizar_texto_producto(
            f"{existente.nombre} {existente.presentacion}"
        )
        nombre_nuevo = normalizar_texto_producto(
            f"{nombre} {presentacion}"
        )

        # Excepción controlada para Caristop 5000 de 51 g.
        if (
            "5000" in nombre_existente.split()
            and "5000" in nombre_nuevo.split()
        ):
            return (
                "pasta" in nombre_existente.split()
                and "dental" in nombre_existente.split()
                and "pasta" in nombre_nuevo.split()
                and "dental" in nombre_nuevo.split()
                and "51" in re.findall(r"\d+", nombre_existente)
                and "51" in re.findall(r"\d+", nombre_nuevo)
            )

        # Las cantidades y medidas deben coincidir.
        numeros_existente = re.findall(
            r"\d+(?:[.,]\d+)?", nombre_existente
        )
        numeros_nuevos = re.findall(
            r"\d+(?:[.,]\d+)?", nombre_nuevo
        )

        if numeros_existente != numeros_nuevos:
            return False

        palabras_ignoradas = {
            "con", "sin", "de", "del", "para", "y",
            "el", "la", "en", "un", "una",
            "pasta", "dental", "fluor", "crema",
            "producto", "pomo", "unidad", "unidades",
            "pack", "ml", "gr", "g", "mg",
            "desodorante", "roll", "on",
            "serum", "facial", "gel", "limpiador",
            "hidratante", "protector", "solar",
            "shampoo", "acondicionador", "labial",
            "balsamo", "locion", "jabon", "spray",
            "micelar", "enjuague", "bucal",
            "barra", "liquido", "liquida",
        }

        palabras_existentes = {
            palabra
            for palabra in re.findall(
                r"[a-z]+(?:-[a-z]+)*", nombre_existente
            )
            if palabra not in palabras_ignoradas
            and len(palabra) >= 3
        }

        palabras_nuevas = {
            palabra
            for palabra in re.findall(
                r"[a-z]+(?:-[a-z]+)*", nombre_nuevo
            )
            if palabra not in palabras_ignoradas
            and len(palabra) >= 3
        }

        # Deben compartir al menos dos identificadores distintivos.
        if len(palabras_existentes & palabras_nuevas) < 2:
            return False

        # Evitar mezclar variantes, tonos y aromas.
        variantes = {
            "sensitive", "sensibilidad",
            "bi-fluorada", "bifluorada",
            "infantil", "junior", "kids",
            "whitening", "blanqueadora",
            "anticaries", "ortodontic",
            "claro", "clara", "medio", "media",
            "oscuro", "oscura", "light", "medium",
            "dark", "menta", "vainilla", "coco",
            "fresa", "frutilla", "manzana",
            "argan", "karite", "retinol",
        }

        variantes_existentes = palabras_existentes & variantes
        variantes_nuevas = palabras_nuevas & variantes

        if variantes_existentes != variantes_nuevas:
            return False

        return True

    # Medicamentos: mantener las validaciones estrictas.
    claves_existente_marca = {
        palabra for palabra in claves_existente
        if not palabra.isdigit()
    }
    claves_nuevas_marca = {
        palabra for palabra in claves_nuevas
        if not palabra.isdigit()
    }

    if not claves_existente_marca & claves_nuevas_marca:
        return False

    activo_existente = normalizar_texto_producto(
        existente.medicamento.principio_activo
        if existente.medicamento else ""
    )

    activo_nuevo = normalizar_texto_producto(principio_activo)

    if activo_existente and activo_nuevo:
        if activo_existente != activo_nuevo:
            return False

    elif activo_nuevo:
        componentes_activo = [
            parte.strip()
            for parte in activo_nuevo.split("-")
            if parte.strip()
        ]

        nombre_existente = normalizar_texto_producto(
            existente.nombre
        )

        if not all(
            re.search(rf"\b{re.escape(parte)}\b", nombre_existente)
            for parte in componentes_activo
        ):
            return False

    elif activo_existente:
        return False

    if existente.es_bioequivalente != es_bioequivalente:
        return False

    firma_existente = extraer_firma_producto(
        existente.nombre,
        existente.presentacion
    )

    firma_nueva = extraer_firma_producto(
        nombre,
        presentacion
    )

    if not firma_existente[0] or not firma_nueva[0]:
        return False

    if not firma_existente[1] or not firma_nueva[1]:
        return False

    if firma_existente != firma_nueva:
        return False

    return True

def buscar_producto_compatible(
    nombre,
    principio_activo,
    presentacion,
    categoria,
    es_bioequivalente,
    laboratorio="",
):
    """Busca productos compatibles usando el índice y una búsqueda de respaldo."""

    claves = obtener_clave_marca(nombre)
    indice = obtener_indice_productos()
    candidatos = {}

    # Primera búsqueda: índice por marca.
    for clave in claves or []:
        for producto in indice.get(clave, []):
            candidatos[producto.id] = producto

    # Respaldo: revisar productos de la misma categoría.
    # Evita crear duplicados cuando el índice no encuentra la marca.
    if not candidatos:
        for producto in Producto.objects.filter(
            categoria=categoria
        ).select_related("medicamento"):
            candidatos[producto.id] = producto

    compatibles = []

    for existente in candidatos.values():
        if productos_equivalentes(
            existente,
            nombre,
            principio_activo,
            presentacion,
            laboratorio,
            es_bioequivalente,
            categoria,
        ):
            compatibles.append(existente)

    if not compatibles:
        return None

    # Preferir el producto con más precios asociados.
    compatibles.sort(
        key=lambda producto: producto.precios.count(),
        reverse=True,
    )

    return compatibles[0]

def obtener_farmacia(nombre_farmacia):
    """
    Normaliza los nombres para evitar farmacias duplicadas.
    """
    nombres_farmacia = {
        "ahumada": "Farmacias Ahumada",
        "farmacias ahumada": "Farmacias Ahumada",
        "cruz verde": "Cruz Verde",
        "salcobrand": "Salcobrand",
        "dr. simi": "Dr. Simi",
        "dr simi": "Dr. Simi",
    }

    nombre = str(nombre_farmacia or "").strip()
    nombre_normalizado = nombre.lower()

    nombre_canonico = nombres_farmacia.get(
        nombre_normalizado,
        nombre,
    )

    farmacia, _ = Farmacia.objects.get_or_create(
        nombre=nombre_canonico
    )

    return farmacia

@transaction.atomic
def guardar_producto(datos, nombre_farmacia, producto_existente=_BUSQUEDA_NO_REALIZADA):
    """
    Crea o actualiza un producto y su precio.
    Evita duplicados y distingue los bioequivalentes.
    """
    nombre = str(datos.get("nombre") or "").strip()

    if not nombre:
        raise ValueError("El producto no tiene nombre.")

    precio_obtenido = convertir_precio(datos.get("precio"))

    if precio_obtenido is None:
        raise ValueError(
            f"El producto '{nombre}' no tiene un precio válido."
        )

    categoria = detectar_categoria(
        nombre,
        datos.get("principio_activo", ""),
        datos.get("presentacion", ""),
    )

    principio_activo = str(
        datos.get("principio_activo") or ""
    ).strip()

    if not principio_activo:
        principio_activo = extraer_principio_activo(nombre)

    presentacion = str(
        datos.get("presentacion") or ""
    ).strip()

    es_bioequivalente = (
        bool(
            re.search(r"\(b\)", nombre, flags=re.IGNORECASE)
        )
        or convertir_booleano(
            datos.get("es_bioequivalente", False)
        )
    )
    
    laboratorio = str(datos.get("laboratorio") or "").strip()

    if producto_existente is _BUSQUEDA_NO_REALIZADA:
        producto = buscar_producto_compatible(
            nombre,
            principio_activo,
            presentacion,
            categoria,
            es_bioequivalente,
            laboratorio
        )
    else:
        producto = producto_existente

    medicamento = None

    if categoria == "medicamentos":
        if producto is not None and producto.medicamento is not None:
            medicamento = producto.medicamento
        else:
            medicamento = buscar_medicamento(
                nombre,
                principio_activo,
            )
            
        if (
            producto is not None
            and producto.medicamento is not None
            and principio_activo
            and not producto.medicamento.principio_activo
        ):
            producto.medicamento.principio_activo = principio_activo
            producto.medicamento.save(
                update_fields=["principio_activo"]
            )

    farmacia = obtener_farmacia(nombre_farmacia)

    # Evitar duplicados cuando la farmacia repite la misma URL.
    url_producto = str(datos.get("url") or "").strip()

    if producto is None:
        producto = Producto.objects.create(
            medicamento=medicamento,
            nombre=nombre,
            presentacion=presentacion,
            laboratorio=datos.get("laboratorio") or "",
            sku=datos.get("sku") or "",
            categoria=categoria,
            es_bioequivalente=es_bioequivalente,
        )

    else:
        cambios = []

        if producto.medicamento is None and medicamento is not None:
            producto.medicamento = medicamento
            cambios.append("medicamento")

        if not producto.presentacion and presentacion:
            producto.presentacion = presentacion
            cambios.append("presentacion")

        if not producto.laboratorio and datos.get("laboratorio"):
            producto.laboratorio = datos["laboratorio"]
            cambios.append("laboratorio")

        if not producto.sku and datos.get("sku"):
            producto.sku = datos["sku"]
            cambios.append("sku")

        if es_bioequivalente and not producto.es_bioequivalente:
            producto.es_bioequivalente = True
            cambios.append("es_bioequivalente")

        if cambios:
            producto.save(update_fields=cambios)

    registrar_producto_en_indice(producto)
    valores_precio = {
        "precio": precio_obtenido,
        "disponible": convertir_booleano(
            datos.get("disponible", False)
        ),
        "url_producto": datos.get("url") or "",
    }

    precio_normal = convertir_precio(
        datos.get("precio_normal")
    )

    if precio_normal is not None:
        valores_precio["precio_normal"] = precio_normal

    Precio.objects.update_or_create(
        producto=producto,
        farmacia=farmacia,
        defaults=valores_precio,
    )

    return producto

def normalizar_laboratorio(laboratorio):
    laboratorio = normalizar_texto_producto(laboratorio)

    sufijos = [
        " s a ",
        " sa ",
        " s a",
        " sa",
        " spa",
        " s p a",
        " sociedad anonima"
    ]

    laboratorio = f" {laboratorio} "

    for sufijo in sufijos:
        laboratorio = laboratorio.replace(sufijo, " ")

    return " ".join(laboratorio.split())