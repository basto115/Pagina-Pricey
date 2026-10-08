from farmacia.models import (
    Medicamento,
    Farmacia,
    Producto,
    Precio
)


def normalizar_nombre_busqueda(nombre):
    """
    Normaliza el nombre para poder comparar productos
    aunque las farmacias lo escriban de forma diferente.
    """

    if not nombre:
        return ""

    nombre = str(nombre).lower()

    # Diferencias comunes entre farmacias
    nombre = nombre.replace("(b)", "")
    nombre = nombre.replace(" x ", " ")
    nombre = nombre.replace("×", " ")

    # Eliminar espacios repetidos
    nombre = " ".join(nombre.split())

    return nombre.strip()


def buscar_medicamento(nombre, principio_activo=""):
    """
    Busca un medicamento existente comparando su nombre
    de forma normalizada.

    Si no existe, crea uno nuevo.
    """

    nombre_busqueda = normalizar_nombre_busqueda(nombre)

    medicamentos = Medicamento.objects.all()

    for medicamento in medicamentos:

        nombre_existente = normalizar_nombre_busqueda(
            medicamento.nombre
        )

        if nombre_existente == nombre_busqueda:
            return medicamento

    medicamento = Medicamento.objects.create(
        nombre=nombre,
        principio_activo=principio_activo or ""
    )

    return medicamento


def guardar_producto(datos, nombre_farmacia):
    """
    Guarda o actualiza un producto obtenido
    desde un scraper.
    """

    # -----------------------------
    # FARMACIA
    # -----------------------------

    farmacia, _ = Farmacia.objects.get_or_create(
        nombre=nombre_farmacia
    )

    # -----------------------------
    # DATOS
    # -----------------------------

    nombre = datos.get("nombre", "")
    principio_activo = datos.get(
        "principio_activo",
        ""
    )

    # -----------------------------
    # MEDICAMENTO
    # -----------------------------

    medicamento = buscar_medicamento(
        nombre,
        principio_activo
    )

    # Actualizar principio activo si antes estaba vacío
    if (
        principio_activo
        and not medicamento.principio_activo
    ):
        medicamento.principio_activo = principio_activo
        medicamento.save()

    # -----------------------------
    # PRODUCTO
    # -----------------------------

    producto = None

    productos = Producto.objects.filter(
        medicamento=medicamento
    )

    nombre_busqueda = normalizar_nombre_busqueda(
        nombre
    )

    for producto_existente in productos:

        nombre_existente = normalizar_nombre_busqueda(
            producto_existente.nombre
        )

        if nombre_existente == nombre_busqueda:
            producto = producto_existente
            break

    # Si no existe, crear producto
    if producto is None:

        producto = Producto.objects.create(
            medicamento=medicamento,
            nombre=nombre,
            presentacion=datos.get(
                "presentacion",
                ""
            ),
            laboratorio=datos.get(
                "laboratorio",
                ""
            ),
            sku=datos.get(
                "sku",
                ""
            )
        )

    # -----------------------------
    # ACTUALIZAR INFORMACIÓN
    # -----------------------------

    cambios = False

    if (
        datos.get("presentacion")
        and not producto.presentacion
    ):
        producto.presentacion = datos["presentacion"]
        cambios = True

    if (
        datos.get("laboratorio")
        and not producto.laboratorio
    ):
        producto.laboratorio = datos["laboratorio"]
        cambios = True

    if (
        datos.get("sku")
        and not producto.sku
    ):
        producto.sku = datos["sku"]
        cambios = True

    if cambios:
        producto.save()

    # -----------------------------
    # PRECIO
    # -----------------------------

    Precio.objects.update_or_create(
        producto=producto,
        farmacia=farmacia,
        defaults={
            "precio": datos.get("precio") or 0,

            "precio_normal": datos.get(
                "precio_normal"
            ),

            "disponible": datos.get(
                "disponible",
                False
            ),

            "url_producto": datos.get(
                "url",
                ""
            )
        }
    )

    return producto