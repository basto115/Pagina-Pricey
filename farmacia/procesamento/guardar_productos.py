
from decimal import Decimal, InvalidOperation

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

    nombre = str(nombre).lower()
    nombre = nombre.replace("(b)", "")
    nombre = nombre.replace("×", " ")
    nombre = nombre.replace("Ã—", " ")

    return " ".join(nombre.split()).strip()


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


def guardar_producto(datos, nombre_farmacia):
    """
    Crea o actualiza un producto y su precio.
    Los productos no medicinales pueden guardarse
    sin asociación a un medicamento.
    """
    nombre = str(datos.get("nombre") or "").strip()

    if not nombre:
        raise ValueError("El producto no tiene nombre.")

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

    principio_activo = datos.get("principio_activo") or ""

    farmacia, _ = Farmacia.objects.get_or_create(
        nombre=nombre_farmacia
    )

    if categoria == "medicamentos":
        medicamento = buscar_medicamento(
            nombre,
            principio_activo,
        )
    else:
        medicamento = None

    nombre_busqueda = normalizar_nombre_busqueda(nombre)

    productos = Producto.objects.filter(categoria=categoria)

    if medicamento is not None:
        productos = productos.filter(medicamento=medicamento)
    else:
        productos = productos.filter(medicamento__isnull=True)

    producto = None

    for existente in productos:
        if (
            normalizar_nombre_busqueda(existente.nombre)
            == nombre_busqueda
        ):
            producto = existente
            break

    if producto is None:
        producto = Producto.objects.create(
            medicamento=medicamento,
            nombre=nombre,
            presentacion=datos.get("presentacion") or "",
            laboratorio=datos.get("laboratorio") or "",
            sku=datos.get("sku") or "",
            categoria=categoria,
        )
    else:
        cambios = []

        if not producto.presentacion and datos.get("presentacion"):
            producto.presentacion = datos["presentacion"]
            cambios.append("presentacion")

        if not producto.laboratorio and datos.get("laboratorio"):
            producto.laboratorio = datos["laboratorio"]
            cambios.append("laboratorio")

        if not producto.sku and datos.get("sku"):
            producto.sku = datos["sku"]
            cambios.append("sku")

        if cambios:
            producto.save(update_fields=cambios)

    precio_obtenido = convertir_precio(datos.get("precio"))

    if precio_obtenido is not None:
        precio_normal = convertir_precio(datos.get("precio_normal"))

        Precio.objects.update_or_create(
            producto=producto,
            farmacia=farmacia,
            defaults={
                "precio": precio_obtenido,
                "precio_normal": precio_normal,
                "disponible": datos.get("disponible", False),
                "url_producto": datos.get("url") or "",
            },
        )

    return producto
