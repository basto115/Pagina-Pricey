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

def buscar_producto_compatible(
    nombre,
    principio_activo,
    presentacion,
    categoria,
    es_bioequivalente,
):
    """
    Busca productos equivalentes sin mezclar
    medicamentos bioequivalentes con los normales.
    """
    clave_nueva = generar_clave_producto(
        nombre,
        principio_activo,
        presentacion,
    )

    productos = Producto.objects.filter(
        categoria=categoria
    ).select_related("medicamento")

    for existente in productos:
        activo_existente = (
            existente.medicamento.principio_activo
            if existente.medicamento
            else ""
        )

        clave_existente = generar_clave_producto(
            existente.nombre,
            activo_existente,
            existente.presentacion,
        )

        if clave_existente[0] != clave_nueva[0]:
            continue

        if (
            clave_existente[1]
            and clave_nueva[1]
            and clave_existente[1] != clave_nueva[1]
        ):
            continue

        if (
            clave_existente[2]
            and clave_nueva[2]
            and clave_existente[2] != clave_nueva[2]
        ):
            continue

        bio_existente = (
            existente.es_bioequivalente
            or clave_existente[3]
        )

        if bio_existente != es_bioequivalente:
            continue

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
def guardar_producto(datos, nombre_farmacia):
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

    producto = buscar_producto_compatible(
        nombre,
        principio_activo,
        presentacion,
        categoria,
        es_bioequivalente,
    )

    medicamento = None

    if categoria == "medicamentos":
        if producto is not None and producto.medicamento is not None:
            medicamento = producto.medicamento
        else:
            medicamento = buscar_medicamento(
                nombre,
                principio_activo,
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
