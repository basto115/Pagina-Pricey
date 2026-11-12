from decimal import Decimal, InvalidOperation
import re
import unicodedata

from django.db import transaction

from farmacia.models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio,
)

_BUSQUEDA_NO_REALIZADA = object()

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
    concentración, forma farmacéutica y cantidad.
    """

    texto = normalizar_texto_producto(
        f"{nombre} {presentacion}"
    )

    # Concentraciones, incluyendo proporciones como 200 mg/5 ml.
    patron_concentracion = (
        r"\d+(?:[.,]\d+)?\s*"
        r"(?:mg\s*/\s*ml|mcg\s*/\s*ml|mg|mcg|g)\b"
        r"(?:\s*/\s*\d+(?:[.,]\d+)?\s*ml\b)?"
    )

    concentraciones = re.findall(
        patron_concentracion,
        texto
    )

    concentraciones = sorted(set(
        re.sub(r"\s+", "", c).replace(",", ".")
        for c in concentraciones
    ))

    # Formas farmacéuticas
    formas = {
        "comprimidos": [
            "comprimido", "comprimidos", "comp ad",
            "comp", "tableta", "tabletas"
        ],
        "capsulas": [
            "capsula", "capsulas"
        ],
        "gotas": [
            "gotas", "solucion oral para gotas"
        ],
        "jarabe": ["jarabe"],
        "crema": ["crema"],
        "gel": ["gel"],
        "solucion": ["solucion oral", "solucion"],
        "suspension": ["suspension oral", "suspension"],
    }

    forma = ""

    for nombre_forma, variantes in formas.items():
        if any(v in texto for v in variantes):
            forma = nombre_forma
            break

    # Características especiales de la formulación
    caracteristicas = {
        "recubrimiento_enterico": [
            "recubrimiento enterico",
            "recubiertos entericos",
            "cubierta enterica"
        ],
        "liberacion_prolongada": [
            "liberacion prolongada",
            "liberacion extendida",
            "accion prolongada"
        ],
        "liberacion_retardada": [
            "liberacion retardada"
        ],
        "dispersable": ["dispersable", "dispersables"],
        "efervescente": ["efervescente", "efervescentes"]
    }

    for caracteristica, variantes in caracteristicas.items():
        if any(v in texto for v in variantes):
            forma = (
                f"{forma}_{caracteristica}"
                if forma else caracteristica
            )

    # Cantidad de unidades
    cantidad_unidades = re.search(
        r"(\d+)\s*(?:comprimidos?|comp|capsulas?|tabletas?)\b",
        texto
    )

    cantidad = ""

    if cantidad_unidades:
        cantidad = cantidad_unidades.group(1) + " unidades"

    else:
        # Priorizar el volumen total indicado después de una "x".
        # Ejemplo: 200 mg/5 ml x 15 ml
        cantidad_ml = re.search(
            r"\bx\s*(\d+(?:[.,]\d+)?)\s*ml\b",
            texto
        )

        # Si no existe una "x", buscar el primer volumen en ml.
        if not cantidad_ml:
            cantidad_ml = re.search(
                r"(\d+(?:[.,]\d+)?)\s*ml\b",
                texto
            )

        if cantidad_ml:
            cantidad = (
                cantidad_ml.group(1).replace(",", ".") + " ml"
            )

    return (
        tuple(concentraciones),
        forma,
        cantidad
    )
    
def productos_equivalentes(
    existente,
    nombre,
    principio_activo,
    presentacion,
    laboratorio,
    es_bioequivalente
):
    """Determina si dos registros representan el mismo producto."""

    # Marca comercial: evitar mezclar productos de marcas diferentes.
    nombre_existente = normalizar_texto_producto(existente.nombre)
    nombre_nuevo = normalizar_texto_producto(nombre)

    marcas_ignoradas = {
        "500", "100", "50", "25", "10",
        "mg", "mcg", "g", "ml",
        "comprimidos", "comprimido",
        "capsulas", "capsula",
        "recubiertos", "recubierto",
        "tabletas", "tableta"
    }

    palabras_existente = [
        p for p in nombre_existente.split()
        if p not in marcas_ignoradas
    ]

    palabras_nuevas = [
        p for p in nombre_nuevo.split()
        if p not in marcas_ignoradas
    ]

    if not palabras_existente or not palabras_nuevas:
        return False

    if palabras_existente[0] != palabras_nuevas[0]:
        return False
    
    # Principio activo
    activo_existente = normalizar_texto_producto(
        existente.medicamento.principio_activo
        if existente.medicamento else ""
    )

    activo_nuevo = normalizar_texto_producto(principio_activo)

    if activo_existente and activo_nuevo:
        if activo_existente != activo_nuevo:
            return False

    elif activo_nuevo:
        # Si el registro antiguo no tiene principio activo,
        # comprobar que aparezca explícitamente en su nombre.
        nombre_existente = normalizar_texto_producto(
            existente.nombre
        )

        componentes_activo = [
            parte.strip()
            for parte in activo_nuevo.split("-")
            if parte.strip()
        ]

        if not all(
            re.search(
                rf"\b{re.escape(parte)}\b",
                nombre_existente
            )
            for parte in componentes_activo
        ):
            return False

    elif activo_existente:
        return False
    

    # Laboratorio: si ambos están informados, deben coincidir.
    lab_existente = normalizar_laboratorio(
        existente.laboratorio
    )

    lab_nuevo = normalizar_laboratorio(laboratorio)

    if lab_existente and lab_nuevo and lab_existente != lab_nuevo:
        return False

    # Concentración, forma y cantidad
    firma_existente = extraer_firma_producto(
        existente.nombre,
        existente.presentacion
    )

    firma_nueva = extraer_firma_producto(
        nombre,
        presentacion
    )

    # No homologar automáticamente si faltan datos
    # que permitan comparar las características.
    if not firma_existente[0] or not firma_nueva[0]:
        return False
    
    if not firma_existente[1] or not firma_nueva[1]:
        return False

    if firma_existente != firma_nueva:
        return False

    # Bioequivalencia: evitar mezclar registros con
    # indicadores explícitos diferentes.
    if existente.es_bioequivalente != es_bioequivalente:
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
    """
    Busca productos equivalentes leyendo únicamente
    los campos necesarios y procesando por bloques.
    """

    productos = (
        Producto.objects
        .filter(categoria=categoria)
        .select_related("medicamento")
        .only(
            "id",
            "nombre",
            "presentacion",
            "laboratorio",
            "es_bioequivalente",
            "medicamento__principio_activo",
        )
        .iterator(chunk_size=500)
    )

    for existente in productos:
        if productos_equivalentes(
            existente,
            nombre,
            principio_activo,
            presentacion,
            laboratorio,
            es_bioequivalente,
        ):
            return existente

    return None

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

    categoria = str(
        datos.get("categoria") or "medicamentos"
    ).strip().lower()

    categorias_validas = {
        "medicamentos",
        "cuidado_personal",
        "cosmeticos",
        "otros",
    }

    if categoria not in categorias_validas:
        categoria = "otros"

    principio_activo = str(
        datos.get("principio_activo") or ""
    ).strip()

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